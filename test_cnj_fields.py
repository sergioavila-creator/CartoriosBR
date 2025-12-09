from cnj_api import CNJClient
from datetime import datetime

print("Testando campos da API CNJ...\n")

client = CNJClient()
df = client.buscar_serventias_ativas('01/01/2024', datetime.now().strftime('%d/%m/%Y'), 'RJ')

print(f"Total de registros: {len(df)}")
print(f"Total de colunas: {len(df.columns)}\n")

print("Colunas disponíveis:")
for i, col in enumerate(df.columns, 1):
    print(f"{i}. {col}")

if not df.empty:
    print("\n" + "="*50)
    print("Exemplo de dados (primeira serventia):")
    print("="*50)
    for col in df.columns:
        valor = df.iloc[0][col]
        if valor and str(valor).strip():
            print(f"{col}: {valor}")
