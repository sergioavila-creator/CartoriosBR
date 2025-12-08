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
    chrome_options.add_argument("--window-size=2560,1440") # Aumentado resolução para garantir renderização de menus
    
    # CRÍTICO: Desabilita detecção de automação para permitir downloads
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Configurar downloads automáticos
    if os.path.exists(DOWNLOAD_DIR):
        if os.path.exists(DOWNLOAD_DIR):
            try: shutil.rmtree(DOWNLOAD_DIR)
            except: pass
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Remove indicadores de webdriver
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver

def wait_for_download(timeout=120):
    """Aguarda o download terminar - aumentado para 120s para downloads assíncronos"""
    print("Aguardando download (pode demorar até 2 minutos)...")
    seconds = 0
    while seconds < timeout:
        # Procura por arquivos CSV ou XLSX
        files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")) + glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx"))
        if files:
            # Verifica se não é um arquivo temporário (.crdownload)
            if not glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload")):
                return files[0]
        
        # Feedback a cada 10 segundos
        if seconds % 10 == 0 and seconds > 0:
            print(f"  ... {seconds}s aguardando...")
        
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
    downloaded_files = {}
    
    try:
        driver.get(CNJ_URL)
        print("Página carregada, aguardando renderização...")
        time.sleep(45)  # Aumentado para 45 segundos para carga pesada do Qlik
        
        # Aguarda explicitamente pelos botões de exportação
        try:
            WebDriverWait(driver, 45).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Exportar dados em .csv')]"))
            )
            print("Botões de exportação detectados!")
        except:
            print("ERRO: Botões de exportação não apareceram após 30 segundos")
            return downloaded_files
        
        # Procura TODOS os botões "Exportar dados em .csv"
        export_buttons = driver.find_elements(
            By.XPATH, 
            "//*[contains(text(), 'Exportar dados em .csv')]"
        )
        
        print(f"Encontrados {len(export_buttons)} botões de exportação")
        
        if len(export_buttons) < 2:
            print("ERRO: Menos de 2 botões encontrados")
            return downloaded_files
        
        # Mapeamento
        targets_map = {
            0: "serventias",
            1: "arrecadacao"
        }
        
        # SOLUÇÃO: Usar ActionChains para cliques mais "humanos"
        actions = ActionChains(driver)
        
        for idx, name in targets_map.items():
            print(f"\n--- Processando Tabela {idx+1}: {name.upper()} ---")
            
            # Limpa downloads anteriores
            for f in glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx")) + glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")):
                try: os.remove(f)
                except: pass
            
            try:
                btn = export_buttons[idx]
                
                if not btn.is_displayed():
                    print(f"Botão {idx} não visível")
                    continue
                
                # Scroll suave até o elemento
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                time.sleep(2)
                
                # Clique humano com ActionChains
                print(f"Clicando com ActionChains...")
                actions.move_to_element(btn).pause(0.5).click().perform()
                print(f"Clicou! Aguardando download (até 40 segundos)...")
                
                # Aguarda download (até 60 segundos para garantir)
                file_path = wait_for_download(timeout=60)
                
                if file_path:
                    print(f"✓ Download concluído: {os.path.basename(file_path)}")
                    # Renomeia para nome padrão
                    new_path = os.path.join(DOWNLOAD_DIR, f"{name}.csv")
                    if os.path.exists(new_path): os.remove(new_path)
                    shutil.move(file_path, new_path)
                    downloaded_files[name] = new_path
                    print(f"✓ Salvo como: {name}.csv")
                else:
                    print(f"✗ Timeout esperando download de {name}")
                
            except Exception as e:
                print(f"✗ Erro ao processar {name}: {e}")
            
            time.sleep(2)
            
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
        if file_path.endswith('.csv'):
            # Tenta diferentes encodings
            try:
                df = pd.read_csv(file_path, encoding='utf-8', sep=';')
            except:
                df = pd.read_csv(file_path, encoding='latin1', sep=';')
        else:
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
