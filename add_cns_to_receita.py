"""
Script para adicionar CNS à planilha Receita TJRJ
Usa matching inteligente baseado em:
1. Nome do Gestor (único) → CNS direto
2. Nome do Gestor (múltiplo) + Fuzzy Matching no nome da serventia
3. Fallback: Fuzzy Matching apenas no nome da serventia
"""

import gspread
import toml
import pandas as pd
from rapidfuzz import fuzz, process
from cns_utils import normalize_cns

print("=== Adicionando CNS à Receita TJRJ ===\n")

# Conecta
gc = gspread.service_account_from_dict(toml.load('.streamlit/secrets.toml')['gcp_service_account'])

# Planilha Receita TJRJ
sh_receita = gc.open_by_key('1_BXjFfmKM_K0ZHpcU8qiEWYQm4weZeekg8E2CbOiQfE')
ws_receita = sh_receita.get_worksheet(0)

# Planilha Lista de Serventias
sh_serventias = gc.open_by_key('1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y')
ws_serventias = sh_serventias.worksheet('Lista de Serventias')

print("Carregando dados...")
receita_data = ws_receita.get_all_records()
serventias_data = ws_serventias.get_all_records()

df_receita = pd.DataFrame(receita_data)
df_serventias = pd.DataFrame(serventias_data)

print(f"Receita TJRJ: {len(df_receita)} registros")
print(f"Lista de Serventias: {len(df_serventias)} registros\n")

# Cria índice: gestor → lista de CNS
print("Criando índice de gestores...")
gestor_index = {}
for _, row in df_serventias.iterrows():
    # Preciso identificar qual coluna tem o nome do gestor em Lista de Serventias
    # Por enquanto, vou assumir que não existe e usar apenas fuzzy matching
    pass

# Função de matching
def find_cns(row):
    """
    Encontra CNS para uma linha de Receita TJRJ
    Retorna: (CNS, confidence, method)
    """
    gestor = str(row.get('gestor', '')).strip()
    designacao = str(row.get('designacao', '')).strip()
    cidade = str(row.get('cidade', '')).strip()
    
    if not designacao:
        return ('', 0, 'NO_DATA')
    
    # Método 1: Fuzzy matching no nome da serventia + cidade
    # Cria string de busca combinando cidade e designação
    search_str = f"{cidade} {designacao}".upper()
    
    # Prepara lista de serventias para matching
    serventias_list = []
    for _, s_row in df_serventias.iterrows():
        municipio = str(s_row.get('municipio', '')).strip().upper()
        denominacao = str(s_row.get('denominacao_serventia', '')).strip().upper()
        cns = str(s_row.get('cns', '')).strip()
        
        # Combina município + denominação
        serventia_str = f"{municipio} {denominacao}"
        serventias_list.append((serventia_str, cns))
    
    # Fuzzy matching
    if serventias_list:
        # Usa token_sort_ratio para ignorar ordem das palavras
        best_match = process.extractOne(
            search_str,
            [s[0] for s in serventias_list],
            scorer=fuzz.token_sort_ratio
        )
        
        if best_match:
            match_str, confidence, idx = best_match
            matched_cns = serventias_list[idx][1]
            
            # Normaliza CNS
            matched_cns = normalize_cns(matched_cns)
            
            return (matched_cns, confidence, 'FUZZY_MATCH')
    
    return ('', 0, 'NO_MATCH')

# Processa cada linha
print("Processando matches...")
results = []
stats = {'FUZZY_MATCH': 0, 'NO_MATCH': 0}

for idx, row in df_receita.iterrows():
    cns, confidence, method = find_cns(row)
    results.append({
        'CNS': cns,
        'Match_Confidence': confidence,
        'Match_Method': method
    })
    stats[method] = stats.get(method, 0) + 1
    
    if (idx + 1) % 100 == 0:
        print(f"  Processado: {idx + 1}/{len(df_receita)}")

print("\n=== Estatísticas ===")
for method, count in stats.items():
    pct = (count / len(df_receita) * 100)
    print(f"{method}: {count} ({pct:.1f}%)")

# Adiciona colunas ao DataFrame
df_results = pd.DataFrame(results)
df_receita['CNS'] = df_results['CNS']
df_receita['Match_Confidence'] = df_results['Match_Confidence']
df_receita['Match_Method'] = df_results['Match_Method']

# Atualiza planilha
print("\nAtualizando planilha...")

# Adiciona cabeçalhos das novas colunas
headers = ws_receita.row_values(1)
new_headers = headers + ['CNS', 'Match_Confidence', 'Match_Method']
ws_receita.update('1:1', [new_headers])

# Atualiza dados (apenas novas colunas)
num_rows = len(df_receita)
cns_col_letter = chr(ord('A') + len(headers))
conf_col_letter = chr(ord('A') + len(headers) + 1)
method_col_letter = chr(ord('A') + len(headers) + 2)

ws_receita.update(
    f'{cns_col_letter}2:{method_col_letter}{num_rows + 1}',
    df_receita[['CNS', 'Match_Confidence', 'Match_Method']].values.tolist()
)

print("✅ CNS adicionado com sucesso!")
print(f"\nRevisão recomendada: linhas com confiança < 80%")
low_conf = df_receita[df_receita['Match_Confidence'] < 80]
print(f"Total para revisar: {len(low_conf)}")
