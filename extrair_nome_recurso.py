import json
import requests
import re
from difflib import SequenceMatcher

# ----------------- CONFIGURAÇÕES -----------------
TIPO_DESEJADO = "Nome_Recurso"
ARQUIVO_ACORDAO = "data/acordao.txt"
ARQUIVO_GABARITO = "resultados/entidades_gabarito.json"

MISTRAL_API_KEY = "jvpfO8FcTc5jZV9oIuJpYaALI7QSi4Qj"
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_MISTRAL = "mistral-small"

# ----------------- UTIL -----------------
def normalizar_texto(texto: str) -> str:
    """Remove acentos simples, pontuação e deixa minúsculo para matching aproximado."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', texto.lower()).strip()

def similar(a: str, b: str, threshold: float = 0.7) -> bool:
    return SequenceMatcher(None, normalizar_texto(a), normalizar_texto(b)).ratio() >= threshold

def carregar_gabarito(caminho: str):
    """Carrega gabarito e mantém apenas entradas de apelação."""
    with open(caminho, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    # Espera [{"Entidade":"Nome_Recurso","tipo":"apelação nº ..."}, ...]
    return [ent for ent in dados if "apelação" in ent.get("tipo", "").lower()]

def carregar_texto(caminho: str) -> str:
    with open(caminho, 'r', encoding='utf-8') as f:
        return f.read()

def sanitize_json_str(s: str) -> str:
    """Remove cercas de código e espaços extras."""
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()

def normalizar_rotulo_apelacao(rotulo: str) -> str:
    """
    Converte variações para o formato canônico: 'apelação nº <número>'.
    Remove 'cível', 'com revisão', etc. Garante minúsculas e espaço após nº.
    """
    if not rotulo:
        return rotulo
    t = rotulo.lower().strip()

    # Converte diversos marcadores de número para "nº"
    t = re.sub(r'\b(n[\.\°ºo]?|nro|nro\.|no)\b', 'nº', t, flags=re.IGNORECASE)
    # Força prefixo "apelação" (se houver variações como "apelação cível", "apelação com revisão")
    t = re.sub(r'\bapelação(?:\s+c[ií]vel|\s+com\s+revis[aã]o)?\b', 'apelação', t, flags=re.IGNORECASE)

    # Extrai número CNJ ou números antigos (ex: 994.06023739-8)
    # CNJ: 0000000-00.0000.0.00.0000
    padrao_cnj = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'
    padrao_antigo = r'\d{3}\.\d{2}\.\d{8}-\d|\d{3}\.\d{2}\.\d{6,8}-\d|\d{3}\.\d{2}\.\d{6,9}-\d|\d{3}\.\d{2}\.\d{6,}-\d'
    padrao_misc = r'\d{7,}-\d|\d{7,}\.\d+[-]\d|\d{7,}\.\d+'

    match = re.search(padrao_cnj, t)
    numero = None
    if match:
        numero = match.group(0)
    else:
        # tenta padrões antigos/mistos
        m2 = re.search(padrao_antigo, t)
        if m2:
            numero = m2.group(0)
        else:
            m3 = re.search(padrao_misc, t)
            if m3:
                numero = m3.group(0)

    if numero:
        return f"apelação nº {numero}"
    # Se já estiver no formato correto, padroniza
    mfinal = re.search(r'apelação\s*nº\s*([^\s].*)', t)
    if mfinal:
        num = mfinal.group(1).strip()
        return f"apelação nº {num}"
    return t

def dedupe_entidades(entidades):
    """Remove duplicados com base em 'tipo' normalizado."""
    vistos = set()
    out = []
    for e in entidades:
        tipo = normalizar_rotulo_apelacao(e.get("tipo", ""))
        if not tipo:
            continue
        chave = normalizar_texto(tipo)
        if chave not in vistos:
            vistos.add(chave)
            out.append({"Entidade": "Nome_Recurso", "tipo": tipo})
    return out

# ----------------- REGEX FALLBACK -----------------
def extrair_por_regex(texto: str):
    """
    Captura apelações por padrão textual (robusto para FN do LLM).
    Retorna lista no formato final.
    """
    # normaliza alguns caracteres de número
    t = re.sub(r'[°º]', 'º', texto)

    # Procura sequências do tipo "Apelação ... nº <número>" (cobre cível / com revisão)
    padrao_base = r'(?i)\bapelaç[aã]o(?:\s+c[ií]vel|\s+com\s+revis[aã]o)?\s*(?:n[\.\°ºo]?|nro|no)?\s*[:º\.\-]?\s*'

    # Números CNJ e antigos
    cnj = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'
    antigo = r'\d{3}\.\d{2}\.\d{6,9}-\d'
    miscelanea = r'\d{7,}-\d|\d{7,}\.\d+[-]\d|\d{7,}\.\d+'

    regex = re.compile(padrao_base + f'({cnj}|{antigo}|{miscelanea})')
    encontrados = []
    for m in regex.finditer(t):
        numero = m.group(1)
        encontrados.append({"Entidade": "Nome_Recurso", "tipo": f"apelação nº {numero}"})
    return dedupe_entidades(encontrados)

# ----------------- PROMPT (Few-shot + CoT interno) -----------------
def criar_prompt_few_shot_cot(texto_alvo: str, exemplos: list) -> str:
    """
    Few-shot com instrução de raciocinar passo a passo INTERNAMENTE (sem expor),
    e retornar SOMENTE JSON final (lista de objetos).
    """
    header = (
        "Você é especialista em NER jurídico. Extraia TODAS as apelações do texto.\n"
        "Importante: R raciocine passo a passo INTERNAMENTE e NÃO revele seu raciocínio.\n"
        "Saída: apenas JSON (array de objetos), cada objeto com campos exatamente:\n"
        "  {\"Entidade\": \"Nome_Recurso\", \"tipo\": \"apelação nº <número>\"}\n"
        "Regras de normalização:\n"
        "  • Sempre use 'apelação nº <número>' em minúsculas.\n"
        "  • Remova 'cível', 'com revisão' do rótulo (não do número).\n"
        "  • Aceite variações de 'nº' ('n.', 'n', 'n°', 'nº').\n"
        "  • Não repita entradas.\n"
        "  • Responda SOMENTE com o JSON final (sem comentários, sem explicações).\n\n"
        "Exemplos de saída (formato esperado):\n"
    )
    # exemplos é uma lista de listas ou lista simples; vamos imprimir cada bloco
    exemplos_str = ""
    for ex in exemplos:
        if isinstance(ex, list):
            exemplos_str += json.dumps(ex, ensure_ascii=False) + "\n"
        else:
            exemplos_str += json.dumps([ex], ensure_ascii=False) + "\n"

    corpo = (
        "\nAgora, analise o texto a seguir e extraia todas as apelações conforme as regras.\n"
        "Lembre-se: raciocine internamente e RETORNE APENAS O JSON FINAL.\n\n"
        f"TEXTO:\n{texto_alvo}\n"
    )
    return header + exemplos_str + corpo

# ----------------- LLM -----------------
def parse_llm_json(conteudo: str):
    """Torna robusto o parse do retorno do LLM (lista ou objeto com lista)."""
    s = sanitize_json_str(conteudo)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        # às vezes o modelo retorna string JSON dentro de string
        try:
            data = json.loads(json.loads(s))
        except Exception:
            return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # procura primeira lista dentro do dict
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    return []

def chamar_mistral(prompt: str):
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_MISTRAL,
        "messages": [{"role": "user", "content": prompt}],
        # importante: nós pedimos explicitamente apenas JSON na instrução;
        # evitar forçar json_object porque alguns modelos encapsulam em dict.
        "temperature": 0.0,
    }
    resp = requests.post(MISTRAL_API_URL, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']

def extrair_entidades_few_shot_cot(texto: str, exemplos: list):
    prompt = criar_prompt_few_shot_cot(texto, exemplos)
    try:
        conteudo = chamar_mistral(prompt)
        llm_raw = parse_llm_json(conteudo)
    except Exception as e:
        print(f"[LLM] Erro: {e}")
        llm_raw = []

    # Normaliza + dedup
    llm_norm = []
    for item in llm_raw:
        if not isinstance(item, dict):
            continue
        tipo = normalizar_rotulo_apelacao(item.get("tipo", ""))
        if tipo:
            llm_norm.append({"Entidade": "Nome_Recurso", "tipo": tipo})
    llm_norm = dedupe_entidades(llm_norm)

    # Fallback regex e união com LLM
    regex_res = extrair_por_regex(texto)
    combinados = dedupe_entidades(llm_norm + regex_res)
    return combinados

# ----------------- MÉTRICAS -----------------
def calcular_metricas(predicoes, gabarito, threshold_similaridade=0.7):
    tp = 0
    fp = 0
    matched_gabarito = set()

    for pred in predicoes:
        p_tipo = pred.get("tipo", "")
        matched = False
        for i, gab in enumerate(gabarito):
            if i in matched_gabarito:
                continue
            if similar(p_tipo, gab.get("tipo", ""), threshold_similaridade):
                tp += 1
                matched_gabarito.add(i)
                matched = True
                break
        if not matched:
            fp += 1

    fn = len(gabarito) - len(matched_gabarito)
    precisao = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * (precisao * recall) / (precisao + recall) if (precisao + recall) else 0.0
    return tp, fp, fn, precisao, recall, f1

# ----------------- EXECUÇÃO -----------------
if __name__ == "__main__":
    texto = carregar_texto(ARQUIVO_ACORDAO)
    gabarito = carregar_gabarito(ARQUIVO_GABARITO)

    # Exemplos few-shot (saída-alvo; ajudam o modelo a padronizar)
    exemplos_few_shot = [
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 000014989.2015.8.26.0480"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 1009452-83.2015.8.26.0004"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 1001015-30.2016.8.26.0356"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 0003570-25.2012.8.26.0664"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 1008833-26.2018.8.26.0562"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 1051724-61.2016.8.26.0100"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 1000562-68.2019.8.26.0311"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 0014410-79.2013.8.26.0011"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 0914410-79.2013.8.26.0011"}],
        [{"Entidade": "Nome_Recurso", "tipo": "apelação nº 994.06023739-8"}],
    ]

    print("🔍 Extraindo entidades (few-shot + CoT interno + regex fallback)...")
    predicoes = extrair_entidades_few_shot_cot(texto, exemplos_few_shot)

    print(f"\n✅ {len(predicoes)} entidades extraídas:")
    for ent in predicoes[:50]:
        print(f"- {ent['Entidade']}: {ent['tipo']}")

    print("\n📊 Calculando métricas (com similaridade de texto)")
    tp, fp, fn, precisao, recall, f1 = calcular_metricas(predicoes, gabarito, threshold_similaridade=0.7)

    print(f"\n✔️ True Positives (TP): {tp}")
    print(f"✖️ False Positives (FP): {fp}")
    print(f"❌ False Negatives (FN): {fn}")
    print(f"📌 Precisão: {precisao:.2%}")
    print(f"↩️ Recall: {recall:.2%}")
    print(f"🔷 F1-Score: {f1:.2%}")
