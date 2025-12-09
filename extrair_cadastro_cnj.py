import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd
from datetime import datetime
from cnj_api import CNJClient
import time

def main():
    print("Iniciando atualização do Cadastro CNJ...")
    
    # 1. Autenticação
    try:
        if "GCP_SERVICE_ACCOUNT" in os.environ:
             creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
        else:
             # Fallback ou erro
             print("ERRO: Variável GCP_SERVICE_ACCOUNT não encontrada")
             return

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
    today_str = datetime.now().strftime('%d/%m/%Y')
    print(f"Consultando {len(estados)} estados com período 01/01/2000 a {today_str}...")
    
    for uf in estados:
        try:
            print(f"  > {uf}...", end=" ")
            # CRÍTICO: O método correto é buscar_serventias_ativas e EXIGE período.
            # Usando período amplo para tentar trazer histórico/cadastro completo
            data = client.buscar_serventias_ativas("01/01/2000", today_str, uf)
            
            if not data.empty:
                print(f"OK ({len(data)} registros)")
                # Converte para lista de dicts para o extend
                all_data.extend(data.to_dict('records'))
            else:
                print("Vazio")
            time.sleep(0.5) # Evitar rate limit
        except Exception as e:
            print(f"Erro em {uf}: {e}")

    if not all_data:
        print("Nenhum dado encontrado em nenhum estado. Abortando upload.")
        return

    # 3. Preparar DataFrame
    print(f"Total de registros encontrados: {len(all_data)}")
    df = pd.DataFrame(all_data)
    df.insert(0, 'data_atualizacao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    df = df.astype(str) # Garante que tudo vai como texto para evitar erros de JSON

    # 4. Salvar no Google Sheets
    SHEET_ID = '1SkxwQoAnNpcNBg1niLpaRaMs79h8rp143NPgsr1EAXo'
    WORKSHEET_NAME = 'Dados CNJ'
    
    try:
        sh = gc.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet(WORKSHEET_NAME)
            print(f"Aba '{WORKSHEET_NAME}' encontrada. Limpando...")
            ws.clear()
        except:
            print(f"Aba '{WORKSHEET_NAME}' não existe. Criando...")
            ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=len(df)+100, cols=len(df.columns)+5)
        
        print("Enviando dados...")
        # Adiciona cabeçalho
        data_to_write = [df.columns.values.tolist()] + df.values.tolist()
        ws.update(data_to_write, value_input_option='USER_ENTERED')
        
        # Formatação básica
        ws.freeze(rows=1)
        try:
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
        except: pass
        
        print("Upload concluído com sucesso!")
        
        # 5. Verificação Pós-Upload
        print("Verificando persistência...")
        check_data = ws.get_all_records()
        print(f"Verificação: {len(check_data)} registros lidos da planilha.")
        
        if len(check_data) == 0:
            print("CRÍTICO: A planilha está vazia após o upload! Algo falhou no gspread.")
            exit(1)
            
    except Exception as e:
        print(f"Erro ao salvar no Google Sheets: {e}")
        exit(1)

if __name__ == "__main__":
    main()
