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
    
    # Encontra todos os gráficos
    charts = driver.find_elements(By.CLASS_NAME, "qv-object-content-container")
    print(f"\nTotal de gráficos: {len(charts)}")
    
    # Analisa os primeiros 2 gráficos em detalhe
    for idx in [0, 1]:
        if idx < len(charts):
            chart = charts[idx]
            print(f"\n{'='*60}")
            print(f"GRÁFICO {idx} ({'SERVENTIAS' if idx == 0 else 'ARRECADACAO'})")
            print(f"{'='*60}")
            
            # Informações básicas
            print(f"Tag: {chart.tag_name}")
            print(f"Visível: {chart.is_displayed()}")
            print(f"Tamanho: {chart.size}")
            print(f"Localização: {chart.location}")
            
            # Classes
            classes = chart.get_attribute("class")
            print(f"\nClasses: {classes}")
            
            # ID
            elem_id = chart.get_attribute("id")
            print(f"ID: {elem_id}")
            
            # Data attributes
            for attr in ['data-qlik-type', 'data-tid', 'data-object-id']:
                val = chart.get_attribute(attr)
                if val:
                    print(f"{attr}: {val}")
            
            # Procura por elementos filhos importantes
            print("\nElementos filhos:")
            
            # Tabelas
            tables = chart.find_elements(By.TAG_NAME, "table")
            print(f"  - Tables: {len(tables)}")
            
            # Botões
            buttons = chart.find_elements(By.TAG_NAME, "button")
            print(f"  - Buttons: {len(buttons)}")
            for btn in buttons[:3]:  # Primeiros 3 botões
                print(f"    * {btn.get_attribute('class')} - '{btn.text}'")
            
            # Menus
            menus = chart.find_elements(By.CSS_SELECTOR, "[class*='menu']")
            print(f"  - Menus: {len(menus)}")
            
            # Export-related elements
            export_els = chart.find_elements(By.CSS_SELECTOR, "[class*='export'], [class*='Export']")
            print(f"  - Export elements: {len(export_els)}")
            
            # Texto visível (primeiros 200 chars)
            text = chart.text[:200] if chart.text else "(vazio)"
            print(f"\nTexto visível: {text}")
            
            # HTML interno (primeiros 500 chars)
            inner_html = chart.get_attribute('innerHTML')[:500]
            print(f"\nHTML (preview): {inner_html}...")
    
    print("\n" + "="*60)
    print("Pressione Enter para fechar...")
    input()
    
finally:
    driver.quit()
