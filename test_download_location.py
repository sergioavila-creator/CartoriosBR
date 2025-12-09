import os
import time
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_cnj")

# Cria diretório de download
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")

# Configurar downloads
prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

try:
    print(f"Diretório de download configurado: {DOWNLOAD_DIR}")
    print(f"Diretório existe: {os.path.exists(DOWNLOAD_DIR)}")
    
    driver.get(CNJ_URL)
    print("\nAguardando página carregar...")
    time.sleep(15)
    
    # Procura primeiro botão de exportar
    export_elements = driver.find_elements(
        By.XPATH, 
        "//*[contains(text(), 'Exportar') or contains(text(), 'Export')]"
    )
    
    print(f"\nEncontrados {len(export_elements)} elementos com 'Exportar'")
    
    if len(export_elements) > 0:
        # Pega o primeiro elemento não vazio
        for idx, el in enumerate(export_elements):
            text = el.text.strip()
            if text:
                print(f"[{idx}] {text}")
                if idx == 1:  # Segundo elemento (índice 1)
                    print(f"\n>>> Clicando no elemento {idx}: {text}")
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(2)
                    break
        
        # Procura opção de dados
        data_options = driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'dados') or contains(text(), 'Excel')]"
        )
        
        visible_options = [el for el in data_options if el.is_displayed()]
        print(f"\nOpções de dados visíveis: {len(visible_options)}")
        
        if visible_options:
            print(f"Clicando na primeira opção: {visible_options[0].text[:50]}")
            driver.execute_script("arguments[0].click();", visible_options[0])
            print("Aguardando 5 segundos...")
            time.sleep(5)
            
            # Verifica arquivos no diretório
            print(f"\n=== Verificando downloads ===")
            print(f"Diretório: {DOWNLOAD_DIR}")
            all_files = os.listdir(DOWNLOAD_DIR)
            print(f"Arquivos encontrados: {len(all_files)}")
            for f in all_files:
                print(f"  - {f}")
            
            # Verifica também o diretório padrão do usuário
            default_download = os.path.join(os.path.expanduser("~"), "Downloads")
            print(f"\nDiretório padrão: {default_download}")
            recent_files = []
            for f in os.listdir(default_download):
                full_path = os.path.join(default_download, f)
                if os.path.isfile(full_path):
                    mtime = os.path.getmtime(full_path)
                    if time.time() - mtime < 60:  # Últimos 60 segundos
                        recent_files.append(f)
            print(f"Arquivos recentes (último minuto): {len(recent_files)}")
            for f in recent_files:
                print(f"  - {f}")
    
    print("\n" + "="*60)
    input("Pressione Enter para fechar...")
    
finally:
    driver.quit()
