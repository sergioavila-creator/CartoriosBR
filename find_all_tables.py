import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"

chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

try:
    driver.get(CNJ_URL)
    print("Aguardando página carregar...")
    time.sleep(15)
    
    # Procura por TODAS as possíveis tabelas
    selectors = [
        ("qv-st", By.CLASS_NAME),
        ("table", By.TAG_NAME),
        (".qv-object-content-container", By.CSS_SELECTOR),
        ("[class*='table']", By.CSS_SELECTOR),
        ("[class*='qv-']", By.CSS_SELECTOR)
    ]
    
    for selector, by_type in selectors:
        elements = driver.find_elements(by_type, selector)
        print(f"\n{selector}: {len(elements)} elementos")
        
        # Mostra detalhes dos primeiros 3
        for i, el in enumerate(elements[:3]):
            if el.is_displayed():
                print(f"  [{i}] Visível, Classes: {el.get_attribute('class')[:80]}")
    
    print("\n" + "="*60)
    input("Pressione Enter para fechar...")
    
finally:
    driver.quit()
