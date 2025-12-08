import os
import requests
import pandas as pd
import gspread
from datetime import datetime

# Configurações
IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"
WORKSHEET_NAME = "Municipios_IBGE"

def extract_ibge_data():
    """Extrai dados de municípios da API do IBGE"""
    print("Conectando à API do IBGE...")
    
    try:
        response = requests.get(IBGE_API_URL, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"Recebidos {len(data)} municípios da API")
        
        # Processa os dados
        municipios = []
        for item in data:
            # Acesso seguro aos dados aninhados
            microrregiao = item.get('microrregiao', {}) or {}
            mesorregiao = microrregiao.get('mesorregiao', {}) or {}
            uf = mesorregiao.get('UF', {}) or {}
            regiao = uf.get('regiao', {}) or {}
            
            municipio = {
                'codigo_municipio': item.get('id'),
                'nome_municipio': item.get('nome'),
                'codigo_uf': uf.get('id'),
                'sigla_uf': uf.get('sigla'),
                'nome_uf': uf.get('nome'),
                'codigo_regiao': regiao.get('id'),
                'sigla_regiao': regiao.get('sigla'),
                'nome_regiao': regiao.get('nome'),
            }
            municipios.append(municipio)
        
        df = pd.DataFrame(municipios)
        print(f"DataFrame criado com {len(df)} linhas e {len(df.columns)} colunas")
        return df
        
    except Exception as e:
        print(f"Erro ao extrair dados do IBGE: {e}")
        return None

def upload_to_gsheets(df):
    """Sobe os dados para o Google Sheets"""
    if df is None or df.empty:
        print("Nenhum dado para processar.")
        return

    print("Conectando ao Google Sheets...")
    
    try:
        # Autenticação
        if "GCP_SERVICE_ACCOUNT" in os.environ:
            import json
            creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
            gc = gspread.service_account_from_dict(creds_dict)
        elif os.path.exists(".streamlit/secrets.toml"):
            import toml
            secrets = toml.load(".streamlit/secrets.toml")
            if "gcp_service_account" in secrets:
                creds_dict = dict(secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(creds_dict)
            else:
                gc = gspread.service_account()
        else:
            gc = gspread.service_account()
            
        sh = gc.open_by_key(SHEET_ID)
        
        # Adiciona timestamp
        df.insert(0, 'data_atualizacao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Converte para string
        df = df.astype(str)
        
        # Cria ou atualiza aba
        try:
            ws = sh.worksheet(WORKSHEET_NAME)
            ws.clear()
            print(f"Atualizando aba existente '{WORKSHEET_NAME}'...")
        except:
            ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=len(df)+100, cols=len(df.columns)+5)
            print(f"Criando nova aba '{WORKSHEET_NAME}'...")
            
        # Upload
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        
        # Formatação
        try:
            ws.freeze(rows=1)
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
            print("Formatação aplicada.")
        except Exception as e_fmt:
            print(f"Aviso de formatação: {e_fmt}")
        
        # Log
        try:
            log_ws = sh.worksheet("Log_Bot")
        except:
            log_ws = sh.add_worksheet(title="Log_Bot", rows=100, cols=2)
        
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"Municípios IBGE: {len(df)} registros"])
        
        print(f"Upload concluído! {len(df)} municípios enviados.")
        
    except Exception as e:
        print(f"Erro no upload para o Sheets: {e}")

if __name__ == "__main__":
    df = extract_ibge_data()
    if df is not None:
        upload_to_gsheets(df)
    else:
        print("Falha na extração.")
