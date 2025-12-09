import gspread
import pandas as pd
import toml
import os

SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"

def verify_merge():
    print("Verificando lógica de merge...")
    try:
        # Autenticação
        if os.path.exists(".streamlit/secrets.toml"):
            secrets = toml.load(".streamlit/secrets.toml")
            if "gcp_service_account" in secrets:
                creds_dict = dict(secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(creds_dict)
            else:
                gc = gspread.service_account()
        else:
            gc = gspread.service_account()
            
        sh = gc.open_by_key(SHEET_ID)
        
        # 1. Carrega Arrecadação
        print("Carregando Arrecadação...")
        ws_arr = sh.worksheet("Arrecadacao")
        df_arr = pd.DataFrame(ws_arr.get_all_records())
        print(f"Arrecadação: {len(df_arr)} linhas. Colunas: {list(df_arr.columns)}")
        
        # 2. Carrega Serventias
        print("Carregando Serventias...")
        ws_serv = sh.worksheet("Lista de Serventias")
        df_serv = pd.DataFrame(ws_serv.get_all_records())
        print(f"Serventias: {len(df_serv)} linhas. Colunas: {list(df_serv.columns)}")
        
        # 3. Merge
        if 'CNS' in df_arr.columns and 'CNS' in df_serv.columns:
             df_arr['CNS'] = df_arr['CNS'].astype(str).str.strip()
             df_serv['CNS'] = df_serv['CNS'].astype(str).str.strip()
             
             cols_to_fetch = ['CNS']
             rename_map = {}
             
             if 'UF' in df_serv.columns: 
                 cols_to_fetch.append('UF')
                 rename_map['UF'] = 'Estado'
             
             if 'Município' in df_serv.columns: 
                 cols_to_fetch.append('Município')
             elif 'Cidade' in df_serv.columns:
                 cols_to_fetch.append('Cidade')
                 rename_map['Cidade'] = 'Município'
                 
             print(f"Tentando merge com colunas: {cols_to_fetch}")
             
             if len(cols_to_fetch) > 1:
                 df_merged = pd.merge(df_arr, df_serv[cols_to_fetch], on='CNS', how='left')
                 if rename_map:
                     df_merged = df_merged.rename(columns=rename_map)
                 
                 print("Merge realizado!")
                 print(f"Colunas finais: {list(df_merged.columns)}")
                 
                 if 'Estado' in df_merged.columns:
                     print("SUCCESS: Coluna 'Estado' encontrada.")
                     print("Exemplos:", df_merged['Estado'].unique()[:5])
                 else:
                     print("FAILURE: Coluna 'Estado' NÃO encontrada.")
                     
                 if 'Município' in df_merged.columns:
                     print("SUCCESS: Coluna 'Município' encontrada.")
                 else:
                     print("FAILURE: Coluna 'Município' NÃO encontrada.")
                     
        else:
            print("FAILURE: Coluna CNS não encontrada em ambas as tabelas.")

    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    verify_merge()
