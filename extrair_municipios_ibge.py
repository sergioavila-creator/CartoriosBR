import os
import requests
import pandas as pd
import gspread
from datetime import datetime

# Configurações
IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
SHEET_ID = "1ktKGyouWoVVC3Vbp-amltr_rRJiZHZAFcp7GaUXmDmo"
WORKSHEET_NAME = "Municipios_IBGE"

import time

def get_sidra_data(table_code, variable_code, desc):
    """Função genérica para buscar dados do SIDRA com retry"""
    print(f"Buscando dados de {desc}...")
    url = f"https://apisidra.ibge.gov.br/values/t/{table_code}/n6/all/v/{variable_code}/p/last%201"
    
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    df = pd.DataFrame(data[1:]) # Pula cabeçalho
                    # D1C = Código do Município
                    # V = Valor
                    # D3N = Ano
                    return df[['D1C', 'V', 'D3N']]
            elif response.status_code >= 500:
                print(f"Erro no servidor IBGE ({response.status_code}). Tentativa {attempt+1}/3...")
                time.sleep(5)
                continue
            else:
                print(f"Erro na requisição ({response.status_code})")
                return None
        except Exception as e:
            print(f"Exceção ao buscar {desc}: {e}")
            time.sleep(2)
    return None

def get_population_data():
    """Busca população estimada via SIDRA API (Tabela 6579)"""
    df = get_sidra_data('6579', '9324', 'população')
    if df is not None:
        try:
            df = df.rename(columns={
                'D1C': 'codigo_municipio',
                'V': 'populacao_estimada',
                'D3N': 'ano_populacao'
            })
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['populacao_estimada'] = pd.to_numeric(df['populacao_estimada'], errors='coerce')
            print(f"População obtida: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar dataframe de população: {e}")
    return None

def get_gdp_data():
    """Busca PIB municipal via SIDRA API (Tabela 5938)"""
    df = get_sidra_data('5938', '37', 'PIB')
    if df is not None:
        try:
            df = df.rename(columns={
                'D1C': 'codigo_municipio',
                'V': 'pib_total',
                'D3N': 'ano_pib'
            })
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['pib_total'] = pd.to_numeric(df['pib_total'], errors='coerce')
            print(f"PIB obtido: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar dataframe de PIB: {e}")
    return None

def get_area_data():
    """Busca área territorial via API de Agregados"""
    print("Buscando dados de área territorial...")
    # Tenta obter dados de área. Se a API de agregados estiver instável, retorna None
    # Agregado 1301 - Área territorial
    url = "https://servicodados.ibge.gov.br/api/v3/agregados/1301/periodos/2021/variaveis/614?localidades=N6[all]"
    
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=60)
            if response.status_code != 200:
                print(f"API de Agregados retornou erro {response.status_code} para Área. Tentativa {attempt+1}")
                time.sleep(2)
                continue
                
            data = response.json()
            areas = []
            if data and len(data) > 0:
                resultados = data[0].get('resultados', [])
                if resultados:
                    series = resultados[0].get('series', [])
                    for item in series:
                        codigo = item.get('localidade', {}).get('id')
                        valor = item.get('serie', {}).get('2021')
                        if codigo and valor and valor != '...':
                             areas.append({
                                'codigo_municipio': str(codigo),
                                'area_territorial_km2': float(valor)
                            })
            
            if areas:
                df = pd.DataFrame(areas)
                print(f"Área obtida: {len(df)} registros")
                return df
                
        except Exception as e:
            print(f"Erro ao buscar área (Agregados): {e}")
            time.sleep(2)
            
    print("Não foi possível obter dados de área após tentativas.")
    return None

def extract_ibge_data():
    """Extrai dados de municípios da API do IBGE e enriquece com dados socioeconômicos"""
    print("Conectando à API do IBGE...")
    
    try:
        # 1. Dados básicos de municípios
        response = requests.get(IBGE_API_URL, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"Recebidos {len(data)} municípios da API")
        
        # Processa os dados básicos
        municipios = []
        for item in data:
            microrregiao = item.get('microrregiao', {}) or {}
            mesorregiao = microrregiao.get('mesorregiao', {}) or {}
            uf = mesorregiao.get('UF', {}) or {}
            regiao = uf.get('regiao', {}) or {}
            
            municipio = {
                'codigo_municipio': str(item.get('id')),
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
        print(f"DataFrame básico criado: {len(df)} linhas")
        
        # 2. Busca dados socioeconômicos
        pop_df = get_population_data()
        gdp_df = get_gdp_data()
        area_df = get_area_data()
        
        # 3. Merge dos dados
        if pop_df is not None:
            df = df.merge(pop_df, on='codigo_municipio', how='left')
            print("População integrada")
        
        if gdp_df is not None:
            df = df.merge(gdp_df, on='codigo_municipio', how='left')
            print("PIB integrado")
        
        if area_df is not None:
            df = df.merge(area_df, on='codigo_municipio', how='left')
            print("Área integrada")
        
        # 4. Calcula indicadores derivados
        if 'populacao_estimada' in df.columns and 'area_territorial_km2' in df.columns:
            df['densidade_demografica'] = df['populacao_estimada'] / df['area_territorial_km2']
            df['densidade_demografica'] = df['densidade_demografica'].round(2)
            print("Densidade demográfica calculada")
        
        if 'pib_total' in df.columns and 'populacao_estimada' in df.columns:
            df['pib_per_capita'] = (df['pib_total'] * 1000) / df['populacao_estimada']
            df['pib_per_capita'] = df['pib_per_capita'].round(2)
            print("PIB per capita calculado")
        
        print(f"DataFrame final: {len(df)} linhas e {len(df.columns)} colunas")
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
