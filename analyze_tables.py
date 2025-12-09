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

output_file = "table_analysis.txt"

try:
    with open(output_file, "w", encoding="utf-8") as f:
        driver.get(CNJ_URL)
        f.write("Aguardando página carregar...\n")
        time.sleep(15)
        
        # Encontra todos os gráficos
        charts = driver.find_elements(By.CLASS_NAME, "qv-object-content-container")
        f.write(f"\nTotal de gráficos: {len(charts)}\n")
        
        # Analisa os primeiros 2 gráficos
        for idx in [0, 1]:
            if idx < len(charts):
                chart = charts[idx]
                f.write(f"\n{'='*60}\n")
                f.write(f"GRÁFICO {idx} ({'SERVENTIAS' if idx == 0 else 'ARRECADACAO'})\n")
                f.write(f"{'='*60}\n")
                
                # Classes
                classes = chart.get_attribute("class")
                f.write(f"Classes: {classes}\n")
                
                # Procura por atributos data-*
                for attr in ['data-qlik-type', 'data-tid', 'data-object-id', 'data-qv-object-id']:
                    val = chart.get_attribute(attr)
                    if val:
                        f.write(f"{attr}: {val}\n")
                
                # Procura elementos importantes
                f.write("\nElementos filhos:\n")
                
                # Tabelas
                tables = chart.find_elements(By.TAG_NAME, "table")
                f.write(f"  Tables: {len(tables)}\n")
                
                # Botões
                buttons = chart.find_elements(By.TAG_NAME, "button")
                f.write(f"  Buttons: {len(buttons)}\n")
                
                # Procura por elementos com "export" no class
                export_els = chart.find_elements(By.CSS_SELECTOR, "[class*='export'], [class*='Export'], [class*='download'], [class*='Download']")
                f.write(f"  Export/Download elements: {len(export_els)}\n")
                for el in export_els:
                    f.write(f"    - {el.tag_name}: {el.get_attribute('class')}\n")
                
                # HTML interno (primeiros 1000 chars)
                inner_html = chart.get_attribute('innerHTML')[:1000]
                f.write(f"\nHTML (preview):\n{inner_html}\n...\n")
        
        f.write("\n" + "="*60 + "\n")
        f.write("Análise completa!\n")
    
    print(f"Análise salva em: {output_file}")
    
finally:
    driver.quit()
