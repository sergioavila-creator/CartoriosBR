import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd
from datetime import datetime
from cnj_api import CNJClient
import time

def main():
    print("Iniciando atualização do Cadastro CNJ (V3 - Fix ID)...")
    
    # 1. Autenticação e Configuração
    try:
        creds_dict = None
        sheet_id = None
        
        # Tenta carregar de .streamlit/secrets.toml primeiro para pegar o SHEET_ID correto
        try:
             import toml
             if os.path.exists(".streamlit/secrets.toml"):
                 secrets = toml.load(".streamlit/secrets.toml")
                 if "gcp_service_account" in secrets:
                     creds_dict = secrets["gcp_service_account"]
                 if "SHEET_ID" in secrets:
                     sheet_id = secrets["SHEET_ID"]
        except Exception as e:
             print(f"Erro ao ler secrets.toml: {e}")

        # Se não achou creds no toml, tenta env var
        if not creds_dict and "GCP_SERVICE_ACCOUNT" in os.environ:
             creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
        
        # Se não achou SHEET_ID no toml, tenta env var
        if not sheet_id and "SHEET_ID" in os.environ:
            sheet_id = os.environ["SHEET_ID"]
            
        if not creds_dict:
             print("ERRO: Credenciais GCP não encontradas (Env ou TOML)")
             return
             
        if not sheet_id:
            # Fallback para o ID descoberto como correto se nada mais funcionar
            print("AVISO: SHEET_ID não encontrado. Usando ID hardcoded descoberto (1_BX...).")
            sheet_id = "1_BXjFfmKM_K0ZHpcU8qiEWYQm4weZeekg8E2CbOiQfE"

        print(f"Usando Planilha ID: {sheet_id}")

        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        gc = gspread.authorize(credentials)
        print("Autenticação Google Sheets OK.")
        
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return

    # 2. Buscar dados da API
    client = CNJClient()
    estados = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
    
    all_data = []
    # Data fixa 2024 para garantir compatibilidade com UI
    start_date = "01/01/2024" 
    today_str = datetime.now().strftime('%d/%m/%Y')
    print(f"Consultando {len(estados)} estados com período {start_date} a {today_str}...")
    
    for uf in estados:
        try:
            print(f"  > {uf}...", end=" ")
            data = client.buscar_serventias_ativas(start_date, today_str, uf)
            
            if not data.empty:
                print(f"OK ({len(data)} registros)")
                all_data.append(data)
            else:
                print("Vazio")
            time.sleep(0.2)
        except Exception as e:
            print(f"Erro: {e}")

    if not all_data:
        print("Nenhum dado encontrado em nenhum estado (API retornou vazio). Abortando upload.")
        return

    # 3. Preparar DataFrame
    df = pd.concat(all_data, ignore_index=True)
    print(f"Total de registros encontrados: {len(df)}")
    
    df['data_upload'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Normaliza CNS
    from cns_utils import normalize_cns_column
    df = normalize_cns_column(df, 'cns')
    
    df = df.astype(str)

    # 4. Salvar no Google Sheets
    WORKSHEET_NAME = 'Lista de Serventias'  # Mudado de 'Dados CNJ' para 'Lista de Serventias'
    
    try:
        sh = gc.open_by_key(sheet_id)
        try:
            ws = sh.worksheet(WORKSHEET_NAME)
            print(f"Aba '{WORKSHEET_NAME}' encontrada. Limpando...")
            ws.clear()
        except:
            print(f"Aba '{WORKSHEET_NAME}' não existe. Criando...")
            ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=len(df)+100, cols=len(df.columns)+5)
        
        print("Enviando dados...")
        data_to_write = [df.columns.values.tolist()] + df.values.tolist()
        ws.update(data_to_write, value_input_option='USER_ENTERED')
        
        # Formatação básica
        ws.freeze(rows=1)
        try:
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
        except: pass
        
        print(f"✅ Upload concluído! {len(df)} registros salvos em '{WORKSHEET_NAME}'")
        
    except Exception as e:
        print(f"Erro ao salvar no Google Sheets: {e}")
        exit(1)

if __name__ == "__main__":
    from logging_utils import print_start_log, print_end_log
    
    start_time = print_start_log("Extração Cadastro CNJ")
    
    try:
        main()
        print_end_log(start_time, success=True)
    except Exception as e:
        print_end_log(start_time, success=False, error_msg=str(e))
        raise
