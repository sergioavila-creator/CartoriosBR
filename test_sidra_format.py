import requests

# Teste rápido da API SIDRA para ver formato real
url = "https://apisidra.ibge.gov.br/values/t/6579/n6/3300100/v/9324/p/last%201"
response = requests.get(url, timeout=30)
data = response.json()

print("Formato da resposta SIDRA:")
print(f"Tipo: {type(data)}")
print(f"Tamanho: {len(data)}")
if len(data) > 0:
    print(f"\nPrimeira linha (cabeçalho):")
    print(data[0])
    if len(data) > 1:
        print(f"\nSegunda linha (dados):")
        print(data[1])
