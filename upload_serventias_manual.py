"""
Script para upload manual da Lista de Serventias
Use este script quando baixar manualmente o CSV do Qlik Sense
"""

import pandas as pd
import gspread
import toml
from cns_utils import normalize_cns_column

print("=== Upload Manual - Lista de Serventias ===\n")

# Solicita caminho do arquivo
arquivo_csv = input("Digite o caminho completo do arquivo CSV baixado: ").strip().strip('"')

if not arquivo_csv:
    print("Erro: Caminho não fornecido!")
    exit(1)

print(f"\nCarregando arquivo: {arquivo_csv}")

# Tenta ler o CSV
try:
    df = pd.read_csv(arquivo_csv, encoding='utf-8', sep=';')
    print(f"✅ Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")
except:
    try:
        df = pd.read_csv(arquivo_csv, encoding='latin1', sep=';')
        print(f"✅ Arquivo carregado (latin1): {len(df)} linhas, {len(df.columns)} colunas")
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        exit(1)

# Normaliza CNS
print("\nNormalizando CNS...")
df = normalize_cns_column(df, 'CNS')
print("✅ CNS normalizado para 6 dígitos")

# Conecta ao Google Sheets
print("\nConectando ao Google Sheets...")
gc = gspread.service_account_from_dict(toml.load('.streamlit/secrets.toml')['gcp_service_account'])
sh = gc.open_by_key('1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y')

# Atualiza aba
print("Atualizando aba 'Lista de Serventias'...")
try:
    ws = sh.worksheet('Lista de Serventias')
    ws.clear()
except:
    ws = sh.add_worksheet(title='Lista de Serventias', rows=len(df)+100, cols=len(df.columns)+5)

# Upload
data_to_write = [df.columns.values.tolist()] + df.values.tolist()
ws.update(data_to_write, value_input_option='USER_ENTERED')

# Formatação
ws.freeze(rows=1)
try:
    ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
except:
    pass

print(f"\n✅ Upload concluído!")
print(f"📊 {len(df)} linhas enviadas para 'Lista de Serventias'")
print("\nAgora você pode usar o VLOOKUP normalmente! 🎯")
