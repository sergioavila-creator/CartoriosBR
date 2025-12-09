import gspread
import os
import toml
import glob
import pandas as pd
import shutil

SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_cnj")

def fix_upload():
    print("Iniciando fix manual de upload Arrecadação...")
    
    # 1. Encontrar o arquivo correto
    # Procura o arquivo com nome de GUID ou o mais recente que tenha colunas de valor
    files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv"))
    if not files:
        print("Nenhum arquivo CSV encontrado em downloads_cnj")
        return

    target_file = None
    for f in files:
        if "arrecadacao" in f.lower():
            target_file = f
            break
            
    if not target_file:
        # Pega o mais recente
        target_file = max(files, key=os.path.getmtime)
        
    print(f"Arquivo selecionado: {target_file}")
    
    # 2. Ler e verificar
    try:
        # Tenta lógica robusta de leitura igual ao script principal
        separators = [';', ',', '\t']
        encodings = ['utf-8', 'latin1']
        df = None
        
        for enc in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(target_file, encoding=enc, sep=sep, on_bad_lines='warn', engine='python')
                    if len(df.columns) > 1 and any("arr" in col.lower() for col in df.columns):
                        print(f"Lido com sucesso: enc={enc}, sep='{sep}'")
                        break
                    df = None # Reset se não tiver colunas certas
                except:
                    continue
            if df is not None: break
            
        if df is None:
            print("Não foi possível ler o arquivo como Arrecadação (colunas não batem).")
            # Tenta ler como excel se for o caso? Não, é CSV.
            return

        print("Colunas encontradas:", list(df.columns))
        
        # Check for Arrecadação column
        col_names = [c for c in df.columns if "Valor arrecada" in c]
        if not col_names:
            print("ALERTA: Coluna 'Valor arrecadação' não encontrada explicitamente.")
        else:
            print(f"Coluna de valor encontrada: {col_names[0]}")
            # Normalizar nome da coluna se necessário?
            # O app espera 'Valor arrecadação'.
            # Se for 'Valor arrecadação', ok.
            
    except Exception as e:
        print(f"Erro ao ler arquivo: {e}")
        return

    # 3. Upload para Google Sheets
    try:
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
        
        tab_name = "Arrecadacao"
        try:
            ws = sh.worksheet(tab_name)
            ws.clear()
        except:
            ws = sh.add_worksheet(title=tab_name, rows=len(df)+100, cols=len(df.columns)+5)
            
        df = df.astype(str)
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        
        # Formatação
        try:
            ws.freeze(rows=1)
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
        except: pass
        
        print(f"Upload realizado com sucesso para aba '{tab_name}'!")
        
        # 4. Renomear para arrecadacao.csv
        new_path = os.path.join(DOWNLOAD_DIR, "arrecadacao.csv")
        if target_file != new_path:
            shutil.copy(target_file, new_path)
            print("Arquivo renomeado/copiado para arrecadacao.csv")
            
    except Exception as e:
        print(f"Erro no upload: {e}")

if __name__ == "__main__":
    fix_upload()
