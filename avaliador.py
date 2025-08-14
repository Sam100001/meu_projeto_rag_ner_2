import json
import re
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict

# --------- CONFIG ---------

# Mapeia tipos do gabarito para os tipos usados nos prompts
TIPO_MAP = {
    "nome_recurso": "Processo Judicial",
    "origem": "Local",                          # ou "Instituição", escolha 1 e mantenha
    "recorrente": "Pessoa",                     # ou "Empresa" dependendo do caso (banco -> Empresa)
    "recorrido": "Pessoa",                      # idem acima
    "orgao_julgador": "Instituição",            # ou "Outro"
    "nome_desembargador_ministro": "Pessoa",
    "nome_relator": "Pessoa",
    "Resultado_Acordão": "Resulltado",
    "data": "Data",
    "titulo": "Documento Judicial",
    "tema_recurso": "Jurisprudência",
    "tema_keyword": "Jurisprudência",
    "tema_complemento": "Informação_Complementar",
    "voto": "voto",
}

# Limiar para considerar um match fuzzy (0-1)
FUZZY_THRESHOLD = 0.92


def strip_accents(s: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )

def clean_spaces(s: str) -> str:
    # colapsa espaços e remove espaços ao redor de pontuações comuns
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*([/.,;:()\-])\s*', r'\1', s)
    return s.strip()

def normalize_no_case(s: str) -> str:
    s2 = s.strip()
    s2 = strip_accents(s2)
    s2 = s2.lower()
    # normalizar "nº", "no.", "n."
    s2 = re.sub(r'\bn[°ºo]\.?\b', 'nº', s2)  # n°, nº, no., n. -> nº
    # normalizar "art.", "artigo"
    s2 = re.sub(r'\bart\.?\b', 'artigo', s2)
    # normalizar "§" -> "paragrafo"
    s2 = s2.replace('§', 'paragrafo ')
    # normaliza espaços/pontuação
    s2 = clean_spaces(s2)
    return s2

def canonical_entity(s: str) -> str:
    """
    Normalização mais forte para comparação:
    - remove acentos, case-insensitive, limpa espaços/pontuação redundante,
    - normaliza formatos frequentes (nº, art., etc).
    """
    return normalize_no_case(s)

def map_tipo(tipo: str) -> str:
    t = tipo.strip()
    t_norm = strip_accents(t).lower()
    # tenta mapear por chave original e pela normalizada
    if tipo in TIPO_MAP:
        return TIPO_MAP[tipo]
    for k, v in TIPO_MAP.items():
        if strip_accents(k).lower() == t_norm:
            return v
    # se não encontrado, devolve título-case para evitar zeros à toa
    return tipo


def carregar_json(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)
    
def carregar_gabarito(caminho_arquivo="resultados/entidades_gabarito.json"):
    """
    Carrega o gabarito de entidades nomeadas.
    Por padrão, lê o arquivo 'resultados/entidades_gabarito.json'.
    """
    return carregar_json(caminho_arquivo)

def extrair_entidades(saida_modelo, origem="desconhecido"):
    """
    Extrai entidades do JSON retornado pelo modelo.
    Se o formato não estiver correto, tenta corrigir ou ignora entradas inválidas.
    """
    # Se vier string, tentar converter para lista/dict
    if isinstance(saida_modelo, str):
        try:
            saida_modelo = json.loads(saida_modelo)
        except json.JSONDecodeError:
            print(f"[ERRO] Retorno {origem} não está em JSON válido.")
            print("Conteúdo retornado:\n", saida_modelo)
            return []

    # Se não for lista, abortar
    if not isinstance(saida_modelo, list):
        print(f"[ERRO] Retorno {origem} não é lista de entidades:", saida_modelo)
        return []

    entidades_formatadas = []

    for ent in saida_modelo:
        if isinstance(ent, dict):
            entidade = ent.get("entidade")
            tipo = ent.get("tipo")
        elif isinstance(ent, str):
            # Caso venha string, tenta criar dict genérico
            entidade = ent
            tipo = "DESCONHECIDO"
        else:
            continue  # ignora entradas inválidas

        if entidade and tipo:
            entidades_formatadas.append({"entidade": entidade, "tipo": tipo})

    return entidades_formatadas

def exact_metrics(pred_list, gold_list):
    # Converte para sets de tuplas (entidade, tipo)
    pred_set = set((ent["entidade"], ent["tipo"]) for ent in pred_list)
    gold_set = set((ent["entidade"], ent["tipo"]) for ent in gold_list)

    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return tp, fp, fn, precision, recall, f1

def exact_metrics(pred_list, gold_list):
    """
    Calcula TP, FP, FN, Precision, Recall e F1
    pred_list e gold_list: listas de dicionários {"entidade": ..., "tipo": ...}
    """
    # Garante que são listas válidas
    if not isinstance(pred_list, list):
        pred_list = []
    if not isinstance(gold_list, list):
        gold_list = []

    # Converte para sets de tuplas (entidade, tipo)
    pred_set = set((ent["entidade"], ent["tipo"]) for ent in pred_list)
    gold_set = set((ent["entidade"], ent["tipo"]) for ent in gold_list)

    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return tp, fp, fn, precision, recall, f1

def best_match_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def fuzzy_match(pred_set, gold_set, threshold=FUZZY_THRESHOLD):
    """
    Aplica matching guloso por tipo, usando similaridade de string na entidade.
    Evita matches duplicados.
    """
    pred_by_type = defaultdict(list)
    gold_by_type = defaultdict(list)
    for e, t in pred_set:
        pred_by_type[t].append(e)
    for e, t in gold_set:
        gold_by_type[t].append(e)

    matched_gold = set()
    tp = 0
    fp = 0

    # para cada tipo, casa os melhores pares com ratio >= threshold
    for t, pred_list in pred_by_type.items():
        gold_list = gold_by_type.get(t, [])
        used = set()
        for p in pred_list:
            best = -1.0
            best_idx = -1
            for idx, g in enumerate(gold_list):
                if idx in used:
                    continue
                r = best_match_ratio(p, g)
                if r > best:
                    best = r
                    best_idx = idx
            if best >= threshold and best_idx >= 0:
                tp += 1
                used.add(best_idx)
            else:
                fp += 1

    total_gold = len(gold_set)
    fn = total_gold - tp
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec  = tp / (tp + fn) if tp + fn else 0.0
    f1   = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return tp, fp, fn, prec, rec, f1

def per_type_report(pred_set, gold_set):
    types = sorted(set(t for _, t in pred_set | gold_set))
    lines = []
    for t in types:
        pred_t = {(e, tt) for (e, tt) in pred_set if tt == t}
        gold_t = {(e, tt) for (e, tt) in gold_set if tt == t}
        tp, fp, fn, prec, rec, f1 = exact_metrics(pred_t, gold_t)
        lines.append(f"- {t}: TP={tp} FP={fp} FN={fn} | P={prec:.2f} R={rec:.2f} F1={f1:.2f}")
    return "\n".join(lines)

def sample_errors(pred_list, gold_list, k=10):
    """
    Retorna amostras de FP e FN para inspeção.
    Converte listas de dicts em sets de tuplas para fazer diferença.
    """
    # Converte listas de dicts para sets de tuplas (entidade, tipo)
    pred_set = set((ent["entidade"], ent["tipo"]) for ent in pred_list)
    gold_set = set((ent["entidade"], ent["tipo"]) for ent in gold_list)

    fps = list(pred_set - gold_set)[:k]  # Predições falsas positivas
    fns = list(gold_set - pred_set)[:k]  # Predições falsas negativas

    return fps, fns

def main():
    caminho_gabarito = 'resultados/entidades_gabarito.json'
    caminho_fewshot  = 'resultados/resultado_fewshot.json'
    caminho_zeroshot = 'resultados/resultado_zeroshot.json'
    caminho_oneshot  = 'resultados/resultado_oneshot.json'

    gabarito = carregar_json(caminho_gabarito)
    fewshot  = carregar_json(caminho_fewshot)
    zeroshot = carregar_json(caminho_zeroshot)
    oneshot  = carregar_json(caminho_oneshot)

    gold = extrair_entidades(gabarito, origem="gold")
    pfew = extrair_entidades(fewshot,  origem="few")
    pzer = extrair_entidades(zeroshot, origem="zero")
    pone = extrair_entidades(oneshot,  origem="one")

    print(f"Gabarito: {len(gold)} entidades")
    print(f"Fewshot:  {len(pfew)} entidades")
    print(f"Zeroshot: {len(pzer)} entidades")
    print(f"Oneshot:  {len(pone)} entidades\n")

    # --- AVALIAÇÃO EXATA
    print("=== AVALIAÇÃO EXATA (entidade+tipo) ===")
    for nome, pset in [("Fewshot", pfew), ("Zeroshot", pzer), ("Oneshot", pone)]:
        tp, fp, fn, prec, rec, f1 = exact_metrics(pset, gold)
        print(f"[{nome}] TP={tp} FP={fp} FN={fn} | P={prec:.3f} R={rec:.3f} F1={f1:.3f}")
    print()

    # --- AVALIAÇÃO FUZZY
    print(f"=== AVALIAÇÃO FUZZY (threshold={FUZZY_THRESHOLD}) ===")
    for nome, pset in [("Fewshot", pfew), ("Zeroshot", pzer), ("Oneshot", pone)]:
        tp, fp, fn, prec, rec, f1 = fuzzy_match(pset, gold, FUZZY_THRESHOLD)
        print(f"[{nome}] TP={tp} FP={fp} FN={fn} | P={prec:.3f} R={rec:.3f} F1={f1:.3f}")
    print()

    # --- AMOSTRAS DE ERROS
    print("=== AMOSTRAS DE ERROS (Fewshot, exato) ===")
    fps, fns = sample_errors(pfew, gold, k=10)
    if fps: print("FP:", fps)
    if fns: print("FN:", fns)

if __name__ == "__main__":
    main()