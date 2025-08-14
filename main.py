import os
import json
from retriever import recuperar_contexto
from mistral_ner import chamar_mistral
from avaliador import carregar_gabarito
from prompts import PROMPT_ZERO_SHOT, PROMPT_ONE_SHOT, PROMPT_FEW_SHOT

RESULTS_DIR = "resultados"
os.makedirs(RESULTS_DIR, exist_ok=True)

CAMINHO_GABARITO = "data/gabarito.json"
CAMINHO_TEXTO = "data/acordao.txt"

def rodar_experimento(nome, prompt_template, texto, contexto=""):
    print(f"\nRodando experimento: {nome}")

    # Preenche o prompt com texto e contexto
    prompt_final = prompt_template.format(text=texto, contexto=contexto)

    # Chama a API do Mistral
    resultado = chamar_mistral(prompt_final)

    # Salva resultado
    caminho_resultado = os.path.join(RESULTS_DIR, f"resultado_{nome}.json")
    with open(caminho_resultado, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"Resultado salvo em: {caminho_resultado}")

    return resultado

def main():
    # Carrega o texto do acórdão
    with open(CAMINHO_TEXTO, "r", encoding="utf-8") as f:
        texto_principal = f.read()

    # Recupera contexto relevante usando RAG
    contexto = recuperar_contexto(texto_principal)
    if not contexto:
        # Caso não haja contexto retornado pelo RAG, podemos definir manualmente
        contexto = "O texto refere-se a um acórdão do Tribunal de Justiça do Estado de São Paulo envolvendo questões de direito do consumidor."

    # Carrega gabarito para avaliação
    gabarito = carregar_gabarito(CAMINHO_GABARITO)

    # Define os experimentos
    experimentos = [
        ("zeroshot", PROMPT_ZERO_SHOT),
        ("oneshot", PROMPT_ONE_SHOT),
        ("fewshot", PROMPT_FEW_SHOT)
    ]

    resultados = {}
    for nome, prompt_template in experimentos:
        resultado = rodar_experimento(nome, prompt_template, texto_principal, contexto)
        resultados[nome] = resultado

    print("\nTodos os experimentos concluídos!")

if __name__ == "__main__":
    main()
