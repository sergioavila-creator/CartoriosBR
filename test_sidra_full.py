import requests
import json

# Teste com município do Rio de Janeiro
url = "https://apisidra.ibge.gov.br/values/t/6579/n6/3304557/v/9324/p/last%201"
response = requests.get(url, timeout=30)
data = response.json()

print("Resposta completa:")
print(json.dumps(data, indent=2, ensure_ascii=False))
