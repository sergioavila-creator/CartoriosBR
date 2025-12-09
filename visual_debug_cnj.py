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
    
    driver.save_screenshot("step1_page_loaded.png")
    print("Screenshot 1: Página carregada")
    
    # Procura botão exportar
    export_elements = driver.find_elements(
        By.XPATH, 
        "//*[contains(text(), 'Exportar dados em .csv')]"
    )
    
    print(f"\nEncontrados {len(export_elements)} botões 'Exportar dados em .csv'")
    
    if export_elements:
        # Clica no primeiro
        btn = export_elements[0]
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(1)
        
        driver.save_screenshot("step2_before_click.png")
        print("Screenshot 2: Antes de clicar")
        
        driver.execute_script("arguments[0].click();", btn)
        print("Clicou em 'Exportar dados em .csv'")
        time.sleep(3)
        
        driver.save_screenshot("step3_after_click.png")
        print("Screenshot 3: Depois de clicar")
        
        # Procura por qualquer link ou botão que possa ser o download
        possible_download_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'Clique') or contains(text(), 'Download') or contains(text(), 'Baixar') or contains(@href, '.csv') or contains(@href, '.xlsx')]"
        )
        
        print(f"\nPossíveis elementos de download encontrados: {len(possible_download_elements)}")
        for i, el in enumerate(possible_download_elements[:5]):
            try:
                if el.is_displayed():
                    print(f"  [{i}] {el.tag_name}: {el.text[:50] if el.text else el.get_attribute('href')}")
            except:
                pass
        
        if possible_download_elements:
            print(f"\nClicando no primeiro elemento visível...")
            for el in possible_download_elements:
                try:
                    if el.is_displayed():
                        driver.execute_script("arguments[0].click();", el)
                        print(f"Clicou em: {el.text[:50] if el.text else 'link'}")
                        time.sleep(3)
                        driver.save_screenshot("step4_after_download_click.png")
                        print("Screenshot 4: Depois de clicar no download")
                        break
                except:
                    continue
        
        time.sleep(5)
        
        # Verifica arquivos
        files = os.listdir(DOWNLOAD_DIR)
        print(f"\nArquivos no diretório: {len(files)}")
        for f in files:
            print(f"  - {f}")
    
    print("\n" + "="*60)
    print("Screenshots salvos:")
    for f in ["step1_page_loaded.png", "step2_before_click.png", "step3_after_click.png", "step4_after_download_click.png"]:
        if os.path.exists(f):
            print(f"  - {f}")
    
    input("\nPressione Enter para fechar...")
    
finally:
    driver.quit()
