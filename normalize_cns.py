import gspread
import toml
import time

print("=== Normalizando CNS em Lista de Serventias ===\n")

# Conecta
gc = gspread.service_account_from_dict(toml.load('.streamlit/secrets.toml')['gcp_service_account'])
sh = gc.open_by_key('1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y')
ws = sh.worksheet('Lista de Serventias')

print("Carregando dados da coluna CNS (C)...")
all_data = ws.get_all_values()
num_rows = len(all_data)
print(f"Total de linhas: {num_rows}")

# Pula header (linha 1)
print("\nExemplos ANTES da normalização:")
for i in range(1, min(6, num_rows)):
    print(f"  Linha {i+1}: '{all_data[i][2]}'")  # Col C = index 2

# Normaliza CNS: 6 dígitos com zeros à esquerda
print("\nNormalizando CNS...")
normalized_cns = []
for i in range(1, num_rows):  # Pula header
    cns_raw = all_data[i][2]  # Col C
    # Remove caracteres não numéricos e adiciona zeros
    cns_clean = ''.join(filter(str.isdigit, str(cns_raw)))
    cns_padded = cns_clean.zfill(6)  # 6 dígitos
    normalized_cns.append([cns_padded])

print(f"Atualizando {len(normalized_cns)} valores...")
ws.update(values=normalized_cns, range_name='C2:C' + str(num_rows))

print("\nExemplos DEPOIS da normalização:")
cns_new = ws.col_values(3)
for i in range(1, min(6, len(cns_new))):
    print(f"  Linha {i+1}: '{cns_new[i]}'")

print("\n✅ Normalização concluída!")
print("Agora todos os CNS têm 6 dígitos com zeros à esquerda.")
