import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ActionChains

CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"

chrome_options = Options()
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

try:
    driver.get(CNJ_URL)
    print("Aguardando página carregar...")
    time.sleep(15)
    
    # Tira screenshot
    driver.save_screenshot("cnj_page.png")
    print("Screenshot salvo: cnj_page.png")
    
    # Lista todos os elementos com diferentes classes
    classes_to_check = [
        "qv-object-content-container",
        "qv-object",
        "qv-gridcell",
        "qv-object-wrapper",
        "qv-object-qlik-table"
    ]
    
    for class_name in classes_to_check:
        elements = driver.find_elements(By.CLASS_NAME, class_name)
        print(f"\n{class_name}: {len(elements)} elementos")
        
        if elements and len(elements) > 0:
            print(f"  Primeiro elemento - Tag: {elements[0].tag_name}, Visível: {elements[0].is_displayed()}")
            print(f"  Texto: {elements[0].text[:100] if elements[0].text else 'Vazio'}")
    
    # Tenta encontrar tabelas especificamente
    tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"\n<table> tags: {len(tables)}")
    
    # Procura por elementos com data-qlik
    qlik_elements = driver.find_elements(By.XPATH, "//*[starts-with(@class, 'qv-')]")
    print(f"\nElementos com classe qv-*: {len(qlik_elements)}")
    
    input("Pressione Enter para fechar o navegador...")
    
finally:
    driver.quit()
