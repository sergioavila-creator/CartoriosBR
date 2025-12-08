import os
import time
import glob
import pandas as pd
import gspread
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ActionChains

# Configurações
CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_cnj")
SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"  # ID da planilha fornecida

def setup_driver(headless=True):
    """Configura o driver do Chrome"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configurar downloads automáticos
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR)
    
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def wait_for_download(timeout=60):
    """Aguarda o download terminar"""
    print("Aguardando download...")
    seconds = 0
    while seconds < timeout:
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx"))
        if files:
            # Verifica se não é um arquivo temporário (.crdownload)
            if not glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload")):
                return files[0]
        time.sleep(1)
        seconds += 1
    return None

def click_export_menu(driver):
    """Navega pelos menus de exportação do Qlik"""
    try:
        # Procura opção "Exportar"
        menus = driver.find_elements(By.TAG_NAME, "li")
        export_btn = None
        for menu in menus:
            if "Exportar" in menu.text or "Export" in menu.text:
                export_btn = menu
                break
        
        if not export_btn: return False
        
        export_btn.click()
        time.sleep(1)
        
        # Procura "Exportar dados"
        submenus = driver.find_elements(By.TAG_NAME, "li")
        data_btn = None
        for sub in submenus:
            if "dados" in sub.text or "Data" in sub.text:
                data_btn = sub
                break
                
        if not data_btn: return False
        
        data_btn.click()
        return True
    except:
        return False


def extract_cnj_data():
    """Executa a extração dos dados (Download de 2 tabelas)"""
    is_headless = os.environ.get("HEADLESS", "true").lower() == "true"
    print(f"Iniciando extração (Headless: {is_headless})...")
    
    driver = setup_driver(headless=is_headless)
    downloaded_files = {} # Dicionário para guardar os caminhos
    
    try:
        driver.get(CNJ_URL)
        print("Página carregada, aguardando renderização...")
        
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "qv-grid-object-scroll-area"))
        )
        time.sleep(15) # Tempo extra para renderizar tudo
        
        # Localiza gráficos
        charts = driver.find_elements(By.CLASS_NAME, "qv-object-content-container")
        print(f"Encontrados {len(charts)} gráficos na tela.")
        
        # Mapeamento: Índice 0 -> Serventias, Índice 1 -> Arrecadação
        targets_map = {
            0: "serventias",
            1: "arrecadacao"
        }
        
        action = ActionChains(driver)
        
        for idx, name in targets_map.items():
            if idx >= len(charts):
                print(f"Gráfico índice {idx} ({name}) não encontrado.")
                continue
                
            print(f"--- Processando Tabela {idx+1}: {name.upper()} ---")
            target = charts[idx]
            
            # Limpa downloads anteriores para garantir que pegamos o arquivo novo
            for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx")):
                try: os.remove(f)
                except: pass
            
            # Botão direito
            action.context_click(target).perform()
            time.sleep(2)
            
            if click_export_menu(driver):
                print("Iniciando download...")
                try:
                    # Aguarda link de download
                    download_link = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Clique aqui"))
                    )
                    download_link.click()
                    
                    file_path = wait_for_download()
                    if file_path:
                        print(f"Download concluído: {file_path}")
                        # Renomeia para evitar conflito
                        new_path = os.path.join(DOWNLOAD_DIR, f"{name}.xlsx")
                        if os.path.exists(new_path): os.remove(new_path)
                        shutil.move(file_path, new_path)
                        downloaded_files[name] = new_path
                        print(f"Arquivo salvo como: {new_path}")
                        
                        # Fecha modal (clicando fora ou no X se necessário, mas geralmente clicar no link fecha ou reseta)
                        # Vamos dar um refresh ou clicar no body para limpar menus?
                        # Melhor apenas esperar um pouco. O Qlik fecha modal após clique? Às vezes não.
                        # Clicar no body para fechar context menus abertos
                        try:
                            driver.find_element(By.TAG_NAME, "body").click()
                        except: pass
                        time.sleep(2)
                        
                    else:
                        print("Timeout esperando arquivo.")
                except Exception as e:
                    print(f"Erro no download de {name}: {e}")
            else:
                print(f"Menu de exportação não encontrado para {name}")
                
            time.sleep(3) # Pausa entre downloads
            
    except Exception as e:
        print(f"Erro geral durante a extração: {e}")
        driver.save_screenshot("erro_extracao.png")
    finally:
        driver.quit()
    
    return downloaded_files

def upload_sheet_generic(sh, file_path, tab_name):
    """Função auxiliar para subir um arquivo para uma aba"""
    if not file_path or not os.path.exists(file_path): return
    
    print(f"Processando upload de {file_path} para aba '{tab_name}'...")
    try:
        df = pd.read_excel(file_path)
        df = df.dropna(how='all')
        df = df.astype(str)
        
        try:
            ws = sh.worksheet(tab_name)
            ws.clear()
        except:
            ws = sh.add_worksheet(title=tab_name, rows=len(df)+100, cols=len(df.columns)+5)
            
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        
        # Formatação
        try:
            ws.freeze(rows=1)
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
            print("Formatação aplicada.")
        except: pass
        
    except Exception as e:
        print(f"Erro ao subir {tab_name}: {e}")

def upload_to_gsheets(files_dict):
    """Sobe os dados para o Google Sheets (Multi-abas)"""
    if not files_dict:
        print("Nenhum arquivo para processar.")
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
        
        # Upload 1: Serventias
        if 'serventias' in files_dict:
            upload_sheet_generic(sh, files_dict['serventias'], "Dados_CNJ_Bot")
            
        # Upload 2: Arrecadação
        if 'arrecadacao' in files_dict:
            upload_sheet_generic(sh, files_dict['arrecadacao'], "Arrecadacao")
            
        # Log
        try:
            log_ws = sh.worksheet("Log_Bot")
        except:
            log_ws = sh.add_worksheet(title="Log_Bot", rows=100, cols=2)
        from datetime import datetime
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"Atualizado: {list(files_dict.keys())}"])
        
        print("Processo de upload finalizado!")
        
    except Exception as e:
        print(f"Erro geral no GSheets: {e}")

if __name__ == "__main__":
    files = extract_cnj_data()
    if files:
        upload_to_gsheets(files)
    else:
        print("Nenhum dado extraído.")
