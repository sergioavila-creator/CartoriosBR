import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_cnj")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")
# Desabilita detecção de automação
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

# Remove indicadores de webdriver
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    '''
})

try:
    driver.get(CNJ_URL)
    print("Aguardando página carregar...")
    time.sleep(15)
    
    # Procura botões
    export_buttons = driver.find_elements(
        By.XPATH, 
        "//*[contains(text(), 'Exportar dados em .csv')]"
    )
    
    print(f"\nTotal de botões: {len(export_buttons)}")
    
    # Tenta com ActionChains (clique mais "humano")
    actions = ActionChains(driver)
    
    for i, btn in enumerate(export_buttons):
        try:
            if btn.is_displayed():
                print(f"\n>>> Botão {i}: Usando ActionChains (clique humano)...")
                
                # Scroll suave
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                time.sleep(2)
                
                # Move mouse até o elemento e clica
                actions.move_to_element(btn).pause(0.5).click().perform()
                print(f"Clicou! Aguardando 35 segundos...")
                time.sleep(35)
                
                # Verifica arquivos
                files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.csv') or f.endswith('.xlsx')]
                print(f"Arquivos baixados: {len(files)}")
                if files:
                    print(f"  ✓ SUCESSO: {files[-1]}")
                else:
                    print(f"  ✗ Nenhum arquivo")
        except Exception as e:
            print(f"  ✗ Erro: {e}")
    
    print("\n" + "="*60)
    all_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith(('.csv', '.xlsx'))]
    print(f"Total final: {len(all_files)} arquivos")
    for f in all_files:
        print(f"  - {f}")
    
    input("\nPressione Enter para fechar...")
    
finally:
    driver.quit()
