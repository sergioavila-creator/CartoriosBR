import gspread
import toml

# Conecta
gc = gspread.service_account_from_dict(toml.load('.streamlit/secrets.toml')['gcp_service_account'])
sh = gc.open_by_key('1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y')

# Pega exemplos
ws_arr = sh.worksheet('Arrecadacao')
ws_serv = sh.worksheet('Lista de Serventias')

print("=== TESTE DE FORMATO CNS ===\n")

# Arrecadacao
cns_arr_raw = ws_arr.acell('A2').value
print(f"CNS em Arrecadacao (A2): '{cns_arr_raw}'")
print(f"  Tipo: {type(cns_arr_raw)}")

# Normaliza
cns_arr_clean = cns_arr_raw.replace('.', '').replace('-', '')
print(f"  Limpo: '{cns_arr_clean}'")
cns_arr_padded = cns_arr_clean.zfill(5)
print(f"  Com zeros: '{cns_arr_padded}'")

# Lista de Serventias
print("\n--- Lista de Serventias (primeiros 5 CNS) ---")
serv_data = ws_serv.col_values(3)[1:6]  # Col C, pula header
for i, cns in enumerate(serv_data, 2):
    print(f"  Linha {i}: '{cns}' (tipo: {type(cns)})")

# Testa match
print(f"\n--- Teste de Match ---")
print(f"Procurando '{cns_arr_padded}' em Lista de Serventias...")
all_cns = ws_serv.col_values(3)[1:]
matches = [i for i, c in enumerate(all_cns, 2) if c == cns_arr_padded]
print(f"Encontrado: {len(matches)} vez(es)")

if matches:
    row_data = ws_serv.row_values(matches[0])
    print(f"Dados da linha {matches[0]}:")
    print(f"  CNS: {row_data[2]}")
    print(f"  UF: {row_data[10]}")
    print(f"  Município: {row_data[11]}")
