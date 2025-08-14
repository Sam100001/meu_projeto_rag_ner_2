import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

def chamar_mistral(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(MISTRAL_ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()
    resposta = response.json()["choices"][0]["message"]["content"]

    # Tenta extrair JSON do texto retornado
    try:
        inicio = resposta.find('[')
        fim = resposta.rfind(']') + 1
        json_str = resposta[inicio:fim]
        return json.loads(json_str)
    except Exception as e:
        print("Erro ao parsear JSON da resposta:", e)
        return resposta
