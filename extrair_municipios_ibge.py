import os
import requests
import pandas as pd
import gspread
from datetime import datetime
import time

# Configurações
IBGE_API_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
SHEET_ID = "1ktKGyouWoVVC3Vbp-amltr_rRJiZHZAFcp7GaUXmDmo"
WORKSHEET_NAME = "Municipios_IBGE"

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
                    df = pd.DataFrame(data[1:])  # Pula cabeçalho
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
            df = df.rename(columns={'D1C': 'codigo_municipio', 'V': 'populacao_estimada', 'D3N': 'ano_populacao'})
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['populacao_estimada'] = pd.to_numeric(df['populacao_estimada'], errors='coerce')
            print(f"População obtida: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar população: {e}")
    return None

def get_gdp_data():
    """Busca PIB municipal via SIDRA API (Tabela 5938)"""
    df = get_sidra_data('5938', '37', 'PIB')
    if df is not None:
        try:
            df = df.rename(columns={'D1C': 'codigo_municipio', 'V': 'pib_total', 'D3N': 'ano_pib'})
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['pib_total'] = pd.to_numeric(df['pib_total'], errors='coerce')
            print(f"PIB obtido: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar PIB: {e}")
    return None

def get_vab_data():
    """Busca Valor Adicionado Bruto por setor (Tabela 5938)"""
    print("Buscando VAB por setor...")
    
    df_agro = get_sidra_data('5938', '513', 'VAB Agropecuária')
    df_ind = get_sidra_data('5938', '514', 'VAB Indústria')
    df_serv = get_sidra_data('5938', '515', 'VAB Serviços')
    
    dfs = []
    if df_agro is not None:
        df_agro = df_agro.rename(columns={'D1C': 'codigo_municipio', 'V': 'vab_agropecuaria'})
        dfs.append(df_agro[['codigo_municipio', 'vab_agropecuaria']])
    
    if df_ind is not None:
        df_ind = df_ind.rename(columns={'D1C': 'codigo_municipio', 'V': 'vab_industria'})
        dfs.append(df_ind[['codigo_municipio', 'vab_industria']])
    
    if df_serv is not None:
        df_serv = df_serv.rename(columns={'D1C': 'codigo_municipio', 'V': 'vab_servicos'})
        dfs.append(df_serv[['codigo_municipio', 'vab_servicos']])
    
    if dfs:
        df_final = dfs[0]
        for df in dfs[1:]:
            df_final = df_final.merge(df, on='codigo_municipio', how='outer')
        
        df_final['codigo_municipio'] = df_final['codigo_municipio'].astype(str)
        for col in ['vab_agropecuaria', 'vab_industria', 'vab_servicos']:
            if col in df_final.columns:
                df_final[col] = pd.to_numeric(df_final[col], errors='coerce')
        
        print(f"VAB obtido: {len(df_final)} registros")
        return df_final
    
    return None

def get_idhm_data():
    """Busca IDHM (Índice de Desenvolvimento Humano Municipal) - Tabela 1612"""
    print("Buscando IDHM...")
    df = get_sidra_data('1612', '120', 'IDHM')
    
    if df is not None:
        try:
            df = df.rename(columns={'D1C': 'codigo_municipio', 'V': 'idhm', 'D3N': 'ano_idhm'})
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['idhm'] = pd.to_numeric(df['idhm'], errors='coerce')
            print(f"IDHM obtido: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar IDHM: {e}")
    
    return None

def get_income_data():
    """Busca Rendimento Médio Mensal - Tabela 1552"""
    print("Buscando rendimento médio...")
    df = get_sidra_data('1552', '1615', 'Rendimento médio')
    
    if df is not None:
        try:
            df = df.rename(columns={'D1C': 'codigo_municipio', 'V': 'rendimento_medio_mensal', 'D3N': 'ano_rendimento'})
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['rendimento_medio_mensal'] = pd.to_numeric(df['rendimento_medio_mensal'], errors='coerce')
            print(f"Rendimento obtido: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar rendimento: {e}")
    
    return None

def get_health_data():
    """Busca Estabelecimentos de Saúde - Tabela 1378"""
    print("Buscando estabelecimentos de saúde...")
    df = get_sidra_data('1378', '265', 'Estabelecimentos de saúde')
    
    if df is not None:
        try:
            df = df.rename(columns={'D1C': 'codigo_municipio', 'V': 'estabelecimentos_saude', 'D3N': 'ano_saude'})
            df['codigo_municipio'] = df['codigo_municipio'].astype(str)
            df['estabelecimentos_saude'] = pd.to_numeric(df['estabelecimentos_saude'], errors='coerce')
            print(f"Estabelecimentos de saúde obtidos: {len(df)} registros")
            return df
        except Exception as e:
            print(f"Erro ao processar estabelecimentos de saúde: {e}")
    
    return None

def extract_ibge_data():
    """Extrai dados de municípios da API do IBGE e enriquece com dados socioeconômicos"""
    print("Conectando à API do IBGE...")
    
    try:
        # 1. Dados básicos de municípios (INCLUI ÁREA!)
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
            
            # ÁREA vem direto na resposta principal!
            area_obj = item.get('area', {})
            area_km2 = None
            if area_obj:
                try:
                    area_km2 = float(area_obj) if isinstance(area_obj, (int, float)) else float(area_obj.get('area', 0))
                except:
                    area_km2 = None
            
            municipio = {
                'codigo_municipio': str(item.get('id')),
                'nome_municipio': item.get('nome'),
                'codigo_uf': uf.get('id'),
                'sigla_uf': uf.get('sigla'),
                'nome_uf': uf.get('nome'),
                'codigo_regiao': regiao.get('id'),
                'sigla_regiao': regiao.get('sigla'),
                'nome_regiao': regiao.get('nome'),
                'area_territorial_km2': area_km2
            }
            municipios.append(municipio)
        
        df = pd.DataFrame(municipios)
        print(f"DataFrame básico criado: {len(df)} linhas")
        print(f"Municípios com área: {df['area_territorial_km2'].notna().sum()}")
        
        # 2. Busca dados socioeconômicos
        pop_df = get_population_data()
        gdp_df = get_gdp_data()
        vab_df = get_vab_data()
        idhm_df = get_idhm_data()
        income_df = get_income_data()
        health_df = get_health_data()
        
        # 3. Merge dos dados
        if pop_df is not None:
            df = df.merge(pop_df, on='codigo_municipio', how='left')
            print("População integrada")
        
        if gdp_df is not None:
            df = df.merge(gdp_df, on='codigo_municipio', how='left')
            print("PIB integrado")
        
        if vab_df is not None:
            df = df.merge(vab_df, on='codigo_municipio', how='left')
            print("VAB integrado")
        
        if idhm_df is not None:
            df = df.merge(idhm_df, on='codigo_municipio', how='left')
            print("IDHM integrado")
        
        if income_df is not None:
            df = df.merge(income_df, on='codigo_municipio', how='left')
            print("Rendimento integrado")
        
        if health_df is not None:
            df = df.merge(health_df, on='codigo_municipio', how='left')
            print("Estabelecimentos de saúde integrados")
        
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
    from logging_utils import print_start_log, print_end_log
    
    start_time = print_start_log("Extração Municípios IBGE")
    
    try:
        df = extract_ibge_data()
        if df is not None:
            upload_to_gsheets(df)
            print_end_log(start_time, success=True)
        else:
            print("Falha na extração.")
            print_end_log(start_time, success=False, error_msg="Falha na extração de dados")
    except Exception as e:
        print_end_log(start_time, success=False, error_msg=str(e))
        raise
