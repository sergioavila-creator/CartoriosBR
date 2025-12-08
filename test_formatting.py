
import pandas as pd
import sys
import os

# Importa a função de upload do script principal
from extrair_cnj_analytics import upload_to_gsheets

# Cria um Excel falso para teste
df = pd.DataFrame({
    'Coluna A': [1, 2, 3],
    'Coluna B': ['A', 'B', 'C'],
    'Coluna C': [10.5, 20.5, 30.5]
})

test_file = "download_teste.xlsx"
df.to_excel(test_file, index=False)

print(f"Criado arquivo de teste: {test_file}")
print("Tentando upload e formatação...")

try:
    upload_to_gsheets(test_file)
    print("Teste concluído!")
except Exception as e:
    print(f"Erro no teste: {e}")
