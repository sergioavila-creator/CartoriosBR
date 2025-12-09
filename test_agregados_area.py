import requests
import json

# Teste API Agregados para Área
# Rio de Janeiro: 3304557
url = "https://servicodados.ibge.gov.br/api/v3/agregados/1301/periodos/2021/variaveis/614?localidades=N6[3304557]"
try:
    response = requests.get(url, timeout=30)
    data = response.json()
    print("Resposta Agregados (Área):")
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Erro: {e}")
