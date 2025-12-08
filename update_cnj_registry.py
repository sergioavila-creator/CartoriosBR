"""
Script para atualizar dados do Cadastro CNJ
Wrapper para integração com o botão de atualização geral
"""
import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials
from cnj_api import CNJClient
import pandas as pd
from datetime import datetime

# Configurações
SHEET_ID = "1SkxwQoAnNpcNBg1niLpaRaMs79h8rp143NPgsr1EAXo"
WORKSHEET_NAME = "Dados CNJ"

def main():
    print("Iniciando atualização do Cadastro CNJ...")
    
    try:
        # Autenticação
        if "GCP_SERVICE_ACCOUNT" in os.environ:
            creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            gc = gspread.authorize(credentials)
        elif os.path.exists(".streamlit/secrets.toml"):
            import toml
            secrets = toml.load(".streamlit/secrets.toml")
            if "gcp_service_account" in secrets:
                creds_dict = dict(secrets["gcp_service_account"])
                scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
                gc = gspread.authorize(credentials)
            else:
                gc = gspread.service_account()
        else:
            gc = gspread.service_account()
        
        # Buscar dados
        client = CNJClient()
        estados = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 
                   'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
        
        all_data = []
        for uf in estados:
            print(f'Buscando {uf}...')
            try:
                data = client.buscar_serventias(uf)
                all_data.extend(data)
            except Exception as e:
                print(f'Erro em {uf}: {e}')
        
        print(f"Total de registros coletados: {len(all_data)}")
        
        # Salvar
        df = pd.DataFrame(all_data)
        df.insert(0, 'data_atualizacao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        df = df.astype(str)
        
        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet(WORKSHEET_NAME)
            ws.clear()
        except:
            ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=len(df)+100, cols=len(df.columns)+5)
        
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        
        # Formatação
        try:
            ws.freeze(rows=1)
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
        except: pass
        
        print(f'Cadastro CNJ atualizado: {len(df)} registros')
        
    except Exception as e:
        print(f"Erro na atualização: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
