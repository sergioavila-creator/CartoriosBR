import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_cnj")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")

prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

try:
    driver.get(CNJ_URL)
    print("Aguardando página carregar...")
    time.sleep(15)
    
    # Procura TODOS os botões "Exportar dados em .csv"
    export_buttons = driver.find_elements(
        By.XPATH, 
        "//*[contains(text(), 'Exportar dados em .csv')]"
    )
    
    print(f"\nTotal de botões 'Exportar dados em .csv': {len(export_buttons)}")
    
    # Lista todos os botões encontrados
    for i, btn in enumerate(export_buttons):
        try:
            visible = btn.is_displayed()
            parent = btn.find_element(By.XPATH, "..")
            print(f"  [{i}] Visível: {visible}, Parent: {parent.tag_name}")
        except:
            print(f"  [{i}] (erro ao inspecionar)")
    
    # Tenta clicar em CADA botão sequencialmente
    for i, btn in enumerate(export_buttons):
        try:
            if btn.is_displayed():
                print(f"\n>>> Clicando no botão {i}...")
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", btn)
                print(f"Clicou! Aguardando 30 segundos...")
                time.sleep(30)
                
                # Verifica se arquivo apareceu
                files = os.listdir(DOWNLOAD_DIR)
                csv_files = [f for f in files if f.endswith('.csv')]
                print(f"Arquivos CSV no diretório: {len(csv_files)}")
                if csv_files:
                    print(f"  ✓ SUCESSO: {csv_files[-1]}")
                else:
                    print(f"  ✗ Nenhum arquivo baixado")
        except Exception as e:
            print(f"  ✗ Erro: {e}")
    
    print("\n" + "="*60)
    print("Resultado final:")
    all_files = os.listdir(DOWNLOAD_DIR)
    print(f"Total de arquivos: {len(all_files)}")
    for f in all_files:
        print(f"  - {f}")
    
    input("\nPressione Enter para fechar...")
    
finally:
    driver.quit()
