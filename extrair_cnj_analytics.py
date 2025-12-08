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

def extract_cnj_data():
    """Executa a extração dos dados"""
    # Verifica se deve rodar headless (padrão para servidor) ou visual (se configurado)
    is_headless = os.environ.get("HEADLESS", "true").lower() == "true"
    print(f"Iniciando extração (Headless: {is_headless})...")
    
    driver = setup_driver(headless=is_headless)
    
    try:
        driver.get(CNJ_URL)
        print("Página carregada, aguardando renderização...")
        
        # Aguarda um elemento chave do Qlik Sense carregar (canvas ou grid)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "qv-grid-object-scroll-area"))
        )
        
        # Espera extra para garantir que os gráficos renderizaram
        time.sleep(10)
        
        # Tenta encontrar o elemento central para clicar com botão direito
        # Estratégia: Clicar no centro da tela onde geralmente fica o grid
        action = ActionChains(driver)
        
        print("Tentando exportar dados...")
        
        # Localiza um elemento de gráfico visível
        # Qlik usa classes genéricas, vamos tentar pegar um container de objeto
        charts = driver.find_elements(By.CLASS_NAME, "qv-object-content-container")
        
        if charts:
            print(f"Encontrados {len(charts)} gráficos. Tentando o primeiro...")
            target = charts[0]
            
            # Botão direito (Context Click)
            action.context_click(target).perform()
            time.sleep(2)
            
            # Procura opção "Exportar" ou "Exportar dados" no menu de contexto
            # O texto pode variar, vamos tentar procurar por texto visível
            menus = driver.find_elements(By.TAG_NAME, "li")
            export_btn = None
            for menu in menus:
                if "Exportar" in menu.text or "Export" in menu.text:
                    export_btn = menu
                    break
            
            if export_btn:
                print("Menu 'Exportar' encontrado, clicando...")
                export_btn.click()
                time.sleep(2)
                
                # Agora procura "Exportar dados" no submenu
                submenus = driver.find_elements(By.TAG_NAME, "li")
                data_btn = None
                for sub in submenus:
                    if "dados" in sub.text or "Data" in sub.text:
                        data_btn = sub
                        break
                
                if data_btn:
                    print("Opção 'Exportar dados' encontrada, clicando...")
                    data_btn.click()
                    
                    # Aguarda link de download aparecer na modal
                    print("Aguardando link de download...")
                    time.sleep(5) # Qlik processando
                    
                    # Tenta encontrar o link de clique aqui para baixar
                    # Geralmente é um link <a> com classe que indica download
                    download_link = WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Clique aqui"))
                    )
                    download_link.click()
                    
                    file_path = wait_for_download()
                    if file_path:
                        print(f"Arquivo baixado com sucesso: {file_path}")
                        return file_path
                    else:
                        print("Timeout esperando download arquivo.")
                else:
                    print("Opção 'Exportar dados' não encontrada no submenu")
            else:
                print("Menu de contexto 'Exportar' não encontrado")
        else:
            print("Nenhum gráfico encontrado na página")
            
    except Exception as e:
        print(f"Erro durante a extração: {e}")
        # Tira print do erro
        driver.save_screenshot("erro_extracao.png")
    finally:
        driver.quit()
    
    return None

def upload_to_gsheets(file_path):
    """Sobe os dados para o Google Sheets"""
    if not file_path:
        print("Nenhum arquivo para processar.")
        return

    print("Conectando ao Google Sheets...")
    
    try:
        # 1. Tenta pegar credenciais do ambiente (GitHub Actions)
        if "GCP_SERVICE_ACCOUNT" in os.environ:
            import json
            creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
            gc = gspread.service_account_from_dict(creds_dict)
        
        # 2. Tenta pegar de arquivo secrets.toml local (Streamlit)
        elif os.path.exists(".streamlit/secrets.toml"):
            import toml
            secrets = toml.load(".streamlit/secrets.toml")
            if "gcp_service_account" in secrets:
                creds_dict = dict(secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(creds_dict)
            else:
                gc = gspread.service_account()
        
        # 3. Fallback padrão gspread
        else:
            gc = gspread.service_account()
            
        sh = gc.open_by_key(SHEET_ID)
        
        print(f"Lendo arquivo Excel: {file_path}")
        df = pd.read_excel(file_path)
        
        # Limpeza básica (se houver linhas vazias)
        df = df.dropna(how='all')
        df = df.astype(str) # Converte tudo para string para evitar erros de JSON
        
        # Atualiza aba
        # Vamos criar ou atualizar uma aba chamada "Dados CNJ"
        NOME_ABA = "Dados_CNJ_Bot"
        
        try:
            ws = sh.worksheet(NOME_ABA)
            print(f"Atualizando aba existente '{NOME_ABA}'...")
            ws.clear()
        except:
            print(f"Criando nova aba '{NOME_ABA}'...")
            ws = sh.add_worksheet(title=NOME_ABA, rows=1000, cols=20)
            
        # Upload
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        
        # Formatação
        try:
            ws.freeze(rows=1)
            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
            print("Formatação (Freeze/Filter) aplicada.")
        except Exception as e_fmt:
            print(f"Erro ao formatar planilha: {e_fmt}")
        
        # Adiciona timestamp de atualização em uma célula auxiliar ou log
        try:
            log_ws = sh.worksheet("Log_Bot")
        except:
            log_ws = sh.add_worksheet(title="Log_Bot", rows=100, cols=2)
            
        from datetime import datetime
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Atualização realizada com sucesso"])
        
        print("Upload concluído com sucesso!")
        
    except Exception as e:
        print(f"Erro no upload para o Sheets: {e}")

if __name__ == "__main__":
    file = extract_cnj_data()
    if file:
        upload_to_gsheets(file)
    else:
        print("Falha na extração, upload cancelado.")
