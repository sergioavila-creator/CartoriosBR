from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ActionChains

# Configurações
CNJ_URL = "https://paineisanalytics.cnj.jus.br/single/?appid=6ae52b4b-f6fb-4e06-8f8a-19c0656b1408&sheet=8413120e-2be0-4713-ae80-8152be891d36&lang=pt-BR&opt=ctxmenu,currsel"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads_cnj")
SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y" 

def setup_driver(headless=True):
    """Configura o driver do Chrome"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=2560,1440")
    
    # CRÍTICO: Desabilita detecção de automação
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Configurar downloads automáticos
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
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver

def wait_for_download(timeout=120, ignore_files=None):
    """Aguarda o download terminar - robusto com lista de ignorados"""
    print("Aguardando download (pode demorar até 2 minutos)...")
    if ignore_files is None: ignore_files = []
    
    seconds = 0
    while seconds < timeout:
        current_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.csv")) + glob.glob(os.path.join(DOWNLOAD_DIR, "*.xlsx"))
        new_files = [f for f in current_files if f not in ignore_files]
        
        if new_files:
            if not glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload")):
                return max(new_files, key=os.path.getmtime)
        
        if seconds % 10 == 0 and seconds > 0:
            print(f"  ... {seconds}s aguardando...")
        
        time.sleep(1)
        seconds += 1
    return None

def close_modals(driver):
    try:
        actions = ActionChains(driver)
        actions.send_keys(Keys.ESCAPE).perform()
    except: pass

def identify_and_rename_file(file_path):
    """Lê o cabeçalho e identifica se é Arrecadação ou Serventias"""
    try:
        # Fallback 1: Verificar pelo NOME do arquivo original (confiança alta se vier do Qlik)
        filename = os.path.basename(file_path).lower()
        if "arrecadacao" in filename or "arrecadação" in filename:
             print(f"Identificado pelo nome do arquivo: {filename} -> arrecadacao")
             return "arrecadacao"
        if "serventias" in filename or "serventia" in filename:
             print(f"Identificado pelo nome do arquivo: {filename} -> serventias")
             return "serventias"

        # Fallback 2: Identificação por conteúdo
        df = read_csv_robust(file_path)
        if df is None: return None
        
        cols = [c.lower() for c in df.columns]
        str_cols = str(cols)
        print(f"Colunas encontradas para identificação: {str_cols[:200]}...") # Debug
        
        # Critérios de identificação
        if "valor arrecada" in str_cols or "arrecadacao" in str_cols or "total arrecadado" in str_cols:
            return "arrecadacao"
        elif "instala" in str_cols or "denominac" in str_cols or "uf" in cols or "municipio" in cols:
            return "serventias"
        
        return "unknown"
    except Exception as e:
        print(f"Erro ao identificar arquivo: {e}")
        return None

def extract_cnj_data():
    """Executa a extração dos dados (Download All & Identify)"""
    is_headless = os.environ.get("HEADLESS", "true").lower() == "true"
    print(f"Iniciando extração (Headless: {is_headless})...")
    
    driver = setup_driver(headless=is_headless)
    downloaded_files = {}
    
    try:
        driver.get(CNJ_URL)
        print("Página carregada, aguardando renderização...")
        # (Removido sleep fixo de 45s - agora confiamos no WebDriverWait)
        
        button_xpath = "//*[@title='Exportar dados em .csv' or contains(@title, 'Exportar') or contains(text(), 'Exportar')]"
        
        try:
            wait = WebDriverWait(driver, 60)
            wait.until(EC.presence_of_all_elements_located((By.XPATH, button_xpath)))
            print("Botões de exportação detectados!")
        except:
            print("ERRO: Botões de exportação não apareceram após 60 segundos")
            driver.save_screenshot("debug_no_buttons.png")
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            export_buttons = []
        
        actions = ActionChains(driver)
        
        # 1. Encontrar botões (Mesmo XPath do Wait)
        export_buttons = driver.find_elements(By.XPATH, button_xpath)
        print(f"Total de botões encontrados: {len(export_buttons)}")
        
        processed_files = [] 
        
        # 2. Iterar sobre botões (sem saber qual é qual)
        for idx, btn in enumerate(export_buttons):
            print(f"\n--- Tentando Botão {idx} ---")
            try:
                # Verificação inteligente do tipo de botão antes de clicar
                btn_title = btn.get_attribute("title") or ""
                btn_text = btn.text or ""
                
                # Se o usuário pediu pra ignorar XLS, vamos ignorar explicitamente
                if "xls" in btn_title.lower() or "excel" in btn_title.lower() or "xls" in btn_text.lower():
                    print(f"Skipping button {idx} (Excel detected: {btn_title} / {btn_text})")
                    continue
                
                # Se já baixamos os 2 arquivos nescessários, podemos parar (otimização)
                if len(downloaded_files) >= 2:
                    print("Já temos os dois arquivos (Serventias e Arrecadação). Encerrando busca.")
                    break

                # Scroll e Clique
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(1)
                actions.move_to_element(btn).pause(0.5).click().perform()
                
                # Aguarda novo arquivo
                file_path = wait_for_download(timeout=90, ignore_files=processed_files)
                
                if file_path:
                    print(f"Download detectado: {os.path.basename(file_path)}")
                    
                    # Identificar conteúdo
                    file_type = identify_and_rename_file(file_path)
                    print(f"Conteúdo identificado como: {file_type}")
                    
                    if file_type in ["arrecadacao", "serventias"]:
                         # PRESERVAR EXTENSÃO ORIGINAL
                         _, ext = os.path.splitext(file_path)
                         if not ext: ext = ".csv" # Fallback
                         
                         new_name = f"{file_type}{ext}"
                         new_path = os.path.join(DOWNLOAD_DIR, new_name)
                         
                         # Rotação de Backup (Mantém 2 versões)
                         if os.path.exists(new_path):
                             backup_name = f"{file_type}_backup{ext}"
                             backup_path = os.path.join(DOWNLOAD_DIR, backup_name)
                             if os.path.exists(backup_path):
                                 os.remove(backup_path)
                             try:
                                 os.rename(new_path, backup_path)
                                 print(f"Backup criado: {backup_name}")
                             except: pass
                         
                         shutil.move(file_path, new_path)
                         downloaded_files[file_type] = new_path
                         processed_files.append(new_path)
                         print(f"Arquivo salvo e catalogado: {new_name}")
                    else:
                        print(f"Arquivo ignorado: {file_type}")
                        processed_files.append(file_path)
                        
                else:
                    print(f"Timeout no botão {idx}")
                    
            except Exception as e:
                print(f"Erro ao processar botão {idx}: {e}")
            
            close_modals(driver)
            time.sleep(2)
            
    except Exception as e:
        print(f"Erro geral durante a extração: {e}")
    finally:
        driver.quit()
    
    return downloaded_files

def read_csv_robust(file_path):
    """Lê CSV tentando diferentes separadores e encodings"""
    if not file_path or not os.path.exists(file_path): return None
    
    # Tenta ler como CSV
    if file_path.lower().endswith('.csv'):
        separators = [';', ',', '\t']
        encodings = ['utf-8', 'latin1', 'utf-16', 'mbcs'] # mbcs ajuda no Windows
        
        # 1. Tentativa com engine python (mais tolerante)
        for enc in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, encoding=enc, sep=sep, on_bad_lines='skip', engine='python')
                    if len(df.columns) > 1:
                        return df
                except: continue
        
        # 2. Última tentativa: deixar o pandas adivinhar
        try:
            return pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='skip')
        except: return None

    # Tenta ler como Excel
    elif file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
        try:
             return pd.read_excel(file_path)
        except: return None
    
    return None

def normalize_cns(val):
    """Normaliza CNS para 6 dígitos numéricos"""
    import re
    if pd.isna(val): return ""
    s = str(val)
    nums = re.sub(r'[^0-9]', '', s)
    if not nums: return ""
    return nums.zfill(6)

def upload_sheet_df(sh, df, tab_name):
    """Sobe um DataFrame para uma aba com suporte a chunks"""
    print(f"Subindo {len(df)} linhas para '{tab_name}'...")
    try:
        try:
            ws = sh.worksheet(tab_name)
            ws.clear()
            # Garante que a aba tem linhas suficientes
            ws.resize(rows=len(df) + 500)
        except:
            ws = sh.add_worksheet(title=tab_name, rows=len(df)+500, cols=len(df.columns)+5)
            
        df_str = df.astype(str)
        
        # Cabeçalho
        ws.update([df_str.columns.values.tolist()])
        
        # Chunking para evitar erro 500 do Google (aumentado para 50k)
        CHUNK_SIZE = 50000 
        data = df_str.values.tolist()
        
        for i in range(0, len(data), CHUNK_SIZE):
            chunk = data[i:i + CHUNK_SIZE]
            start_row = i + 2  # +2 porque linha 1 é header e índice começa em 1
            end_row = start_row + len(chunk) - 1
            print(f"  Enviando lote {i} a {i+len(chunk)} (linhas {start_row}-{end_row})...")
            
            # Retry robusto com múltiplas tentativas
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # Usa update com range específico em vez de append
                    # Isso garante que os dados vão para as linhas corretas
                    range_name = f'A{start_row}:{chr(65 + len(df.columns) - 1)}{end_row}'
                    ws.update(range_name=range_name, values=chunk, value_input_option='USER_ENTERED')
                    time.sleep(0.5)  # Pausa entre lotes bem-sucedidos
                    break  # Sucesso, sai do loop de retry
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3  # Backoff exponencial: 3s, 6s, 9s, 12s, 15s
                        print(f"  ⚠ Erro no lote {i} (tentativa {attempt + 1}/{max_retries}): {e}")
                        print(f"  Aguardando {wait_time}s antes de tentar novamente...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ❌ FALHA CRÍTICA no lote {i} após {max_retries} tentativas!")
                        raise  # Re-lança exceção após todas as tentativas
        
        try:
            ws.freeze(rows=1)
        except: pass
        print(f"Upload '{tab_name}' concluído.")
    except Exception as e:
        print(f"Erro no upload '{tab_name}': {e}")

def sync_to_supabase(df_arrecadacao, df_serventias):
    """Sincroniza dados com Supabase após upload no Sheets"""
    try:
        from supabase_config import get_supabase_client
        
        print("\n🔄 Verificando Supabase...")
        supabase = get_supabase_client()
        
        # Se Supabase não está configurado, pula a sincronização
        if supabase is None:
            print("ℹ️ Supabase não configurado. Sincronização ignorada.")
            return
        
        # 1. Limpa tabela arrecadacao
        print("Limpando tabela arrecadacao...")
        try:
            supabase.table('arrecadacao').delete().neq('id', 0).execute()
        except Exception as e:
            print(f"⚠️ Aviso ao limpar tabela arrecadacao (pode estar vazia ou não existir): {e}")

        # 2. Insere dados em lotes (Supabase tem limite de 1000 por request)
        if df_arrecadacao is not None and not df_arrecadacao.empty:
            # Garante tipos de dados compatíveis com SQL
            df_sync = df_arrecadacao.copy()
            
            # Converte datas para string ISO (YYYY-MM-DD)
            date_cols = ['Dat. inicio periodo', 'Dat. final periodo']
            for col in date_cols:
                if col in df_sync.columns:
                    df_sync[col] = pd.to_datetime(df_sync[col], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            
            # Renomeia colunas para snake_case (padrao SQL)
            rename_map = {
                'CNS': 'cns',
                'Dat. inicio periodo': 'dat_inicio_periodo',
                'Dat. final periodo': 'dat_final_periodo',
                'Quantidade de atos praticados': 'quantidade_atos',
                'Valor arrecadação': 'valor_arrecadacao',
                'Valor custeio': 'valor_custeio',
                'Valor repasse': 'valor_repasse',
                'Estado': 'estado',
                'Município': 'municipio',
                'Atribuição': 'atribuicao',
                'Semestre': 'semestre',
                'Delegatário': 'delegatario',
                'Líquido': 'liquido',
                'Indice_Eficiencia': 'indice_eficiencia',
                'Indice_Repasses': 'indice_repasses',
                'Ano': 'ano',
                'Semestre_Num': 'semestre_num'
            }
            # Filtra apenas colunas que existem no map + map
            cols_to_keep = [c for c in df_sync.columns if c in rename_map]
            df_sync = df_sync[cols_to_keep].rename(columns=rename_map)
            
            # Remove NaNs (Supabase não gosta de NaN JSON)
            df_sync = df_sync.where(pd.notnull(df_sync), None)
            
            print(f"Inserindo {len(df_sync)} registros em 'arrecadacao'...")
            BATCH_SIZE = 1000
            records = df_sync.to_dict('records')
            
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                try:
                    supabase.table('arrecadacao').insert(batch).execute()
                    if i % 10000 == 0:
                        print(f"  ✓ Lote {i//BATCH_SIZE + 1}/{(len(records)//BATCH_SIZE) + 1}")
                except Exception as e:
                    print(f"  ❌ Erro no lote {i}: {e}")
        
        # 3. Atualiza serventias
        if df_serventias is not None and not df_serventias.empty:
            print("Atualizando serventias...")
            try:
                supabase.table('serventias').delete().neq('id', 0).execute()
                
                df_serv_sync = df_serventias.copy()
                rename_serv = {
                    'CNS': 'cns',
                    'Nome': 'nome', # Ajustar conforme nome real da coluna
                    'UF': 'uf',
                    'Município': 'municipio',
                    'Atribuição': 'atribuicao'
                }
                # Tenta mapear o que der
                cols_serv = [c for c in df_serv_sync.columns if c in rename_serv]
                # Se não tiver 'Nome', tenta achar coluna parecida
                if 'Nome' not in df_serv_sync.columns:
                     # Procura coluna de nome
                     for c in df_serv_sync.columns:
                         if 'nome' in c.lower() or 'serventia' in c.lower():
                             rename_serv[c] = 'nome'
                             break
                
                df_serv_sync = df_serv_sync.rename(columns=rename_serv)
                # Mantém apenas colunas alvo
                target_cols = ['cns', 'nome', 'uf', 'municipio', 'atribuicao']
                current_cols = [c for c in df_serv_sync.columns if c in target_cols]
                df_serv_sync = df_serv_sync[current_cols]
                
                df_serv_sync = df_serv_sync.where(pd.notnull(df_serv_sync), None)
                
                serventias_records = df_serv_sync.to_dict('records')
                # Batch também para serventias
                for i in range(0, len(serventias_records), BATCH_SIZE):
                    batch = serventias_records[i:i + BATCH_SIZE]
                    supabase.table('serventias').insert(batch).execute()
                    
                print("✓ Serventias atualizadas")
            except Exception as e:
                print(f"⚠️ Erro ao atualizar serventias: {e}")

        print("✅ Sincronização com Supabase concluída!")
        
    except Exception as e:
        print(f"❌ Erro geral ao sincronizar com Supabase: {e}")
        print("  (Verifique se as tabelas foram criadas no Supabase e se as chaves estão corretas)")

def upload_to_gsheets(files_dict):
    """ETL Completo: Normaliza, Cruza e Sobe"""
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
        
        # 1. Leitura e Preparação
        df_serv = None
        df_arr = None
        
        if 'serventias' in files_dict:
            df_serv = read_csv_robust(files_dict['serventias'])
            if df_serv is not None:
                # Normalização de Colunas (Case Insensitive)
                df_serv.columns = [c.strip() for c in df_serv.columns]
                
                # Mapa de renomeação para garantir padrão
                rename_map_serv = {}
                for col in df_serv.columns:
                    c_lower = col.lower()
                    if c_lower == 'cns': rename_map_serv[col] = 'CNS'
                    elif c_lower == 'uf': rename_map_serv[col] = 'UF'
                    elif c_lower in ['cidade', 'municipio', 'município']: rename_map_serv[col] = 'Município'
                
                if rename_map_serv:
                    df_serv.rename(columns=rename_map_serv, inplace=True)
                
                if 'CNS' in df_serv.columns:
                    print("Normalizando CNS Serventias...")
                    df_serv['CNS_Raw'] = df_serv['CNS'] # Backup
                    df_serv['CNS'] = df_serv['CNS'].apply(normalize_cns)
                    upload_sheet_df(sh, df_serv, "Lista de Serventias")
            
        if 'arrecadacao' in files_dict:
            df_arr = read_csv_robust(files_dict['arrecadacao'])
            if df_arr is not None:
                # Normalização de Colunas Arrecadação
                df_arr.columns = [c.strip() for c in df_arr.columns]
                for col in df_arr.columns:
                    if col.lower() == 'cns':
                        df_arr.rename(columns={col: 'CNS'}, inplace=True)
                        break
                ws_arr = sh.worksheet("Arrecadacao")
                ws_serv = sh.worksheet("Lista de Serventias")
                
                # Identifica estrutura das colunas em ambas as abas
                header_arr = ws_arr.row_values(1)
                header_serv = ws_serv.row_values(1)
                
                # Encontra CNS em Arrecadacao
                try:
                    cns_col_idx = header_arr.index('CNS') + 1
                    cns_col_letter = chr(64 + cns_col_idx)
                except ValueError:
                    print("ERRO: Coluna CNS não encontrada em Arrecadacao")
                    cns_col_idx = None
                
                # Encontra colunas em Lista de Serventias
                try:
                    serv_cns_col = header_serv.index('CNS') + 1
                    serv_uf_col = next((i+1 for i, c in enumerate(header_serv) if c in ['UF', 'Estado']), None)
                    serv_mun_col = next((i+1 for i, c in enumerate(header_serv) if c in ['Município', 'Cidade']), None)
                    
                    print(f"Estrutura Lista de Serventias: CNS=col{serv_cns_col}, UF=col{serv_uf_col}, Município=col{serv_mun_col}")
                except:
                    print("ERRO: Estrutura de Lista de Serventias não reconhecida")
                    serv_cns_col = None
                
                if cns_col_idx and serv_cns_col:
                    from gsheets_locale_utils import detect_gsheets_locale
                    separator = detect_gsheets_locale(ws_arr)
                    
                    # Identifica colunas de valores para cálculo de índices
                    val_arr_col = next((i+1 for i, c in enumerate(header_arr) if 'arrecadação' in c.lower() and 'valor' in c.lower()), None)
                    val_cust_col = next((i+1 for i, c in enumerate(header_arr) if 'custeio' in c.lower() and 'valor' in c.lower()), None)
                    val_rep_col = next((i+1 for i, c in enumerate(header_arr) if 'repasse' in c.lower() and 'valor' in c.lower()), None)
                    
                    # Adiciona cabeçalhos para novas colunas
                    num_cols = len(header_arr)
                    new_headers = ['Estado', 'Município', 'Delegatário', 'Líquido', 'Indice_Eficiencia', 'Indice_Repasses']
                    
                    # Prepara fórmulas APENAS para a primeira linha de dados (linha 2)
                    num_rows = len(df_arr)
                    
                    # Converte números de coluna para letras
                    serv_cns_letter = chr(64 + serv_cns_col)
                    serv_uf_letter = chr(64 + serv_uf_col) if serv_uf_col else None
                    serv_mun_letter = chr(64 + serv_mun_col) if serv_mun_col else None
                    
                    # VLOOKUP para Estado (coluna H = 8 em Lista de Serventias)
                    if serv_uf_letter:
                        estado_formula = f'=IFERROR(VLOOKUP({cns_col_letter}2{separator}\'Lista de Serventias\'!A:O{separator}{serv_uf_col}{separator}0){separator}"")'
                    else:
                        estado_formula = ''
                    
                    # VLOOKUP para Município (coluna I = 9 em Lista de Serventias)
                    if serv_mun_letter:
                        municipio_formula = f'=IFERROR(VLOOKUP({cns_col_letter}2{separator}\'Lista de Serventias\'!A:O{separator}{serv_mun_col}{separator}0){separator}"")'
                    else:
                        municipio_formula = ''
                    
                    # Delegatário = E - G (Arrecadação - Repasse)
                    if val_arr_col and val_rep_col:
                        arr_letter = chr(64 + val_arr_col)
                        rep_letter = chr(64 + val_rep_col)
                        delegatario_formula = f'={arr_letter}2-{rep_letter}2'
                    else:
                        delegatario_formula = ''
                    
                    # Líquido = Delegatário - F (Delegatário - Custeio)
                    # Delegatário está na coluna atual + 2 (depois de Estado e Município)
                    delegatario_col_letter = chr(65 + num_cols + 2)
                    if val_cust_col:
                        cust_letter = chr(64 + val_cust_col)
                        liquido_formula = f'={delegatario_col_letter}2-{cust_letter}2'
                    else:
                        liquido_formula = ''
                    
                    # Índice Eficiência = F / Delegatário (Custeio / Delegatário)
                    if val_cust_col and delegatario_formula:
                        efic_formula = f'=IF({delegatario_col_letter}2>0{separator}{cust_letter}2/{delegatario_col_letter}2{separator}0)'
                    else:
                        efic_formula = ''
                    
                    # Índice Repasses = G / E (Repasse / Arrecadação)
                    if val_arr_col and val_rep_col:
                        repasses_formula = f'=IF({arr_letter}2>0{separator}{rep_letter}2/{arr_letter}2{separator}0)'
                    else:
                        repasses_formula = ''
                    
                    # Monta dados: cabeçalho + primeira linha de fórmulas
                    data_to_insert = [
                        new_headers,
                        [estado_formula, municipio_formula, delegatario_formula, liquido_formula, efic_formula, repasses_formula]
                    ]
                    
                    # Insere cabeçalho e primeira linha
                    first_col_letter = chr(65 + num_cols)
                    last_col_letter = chr(65 + num_cols + 5)  # 6 colunas agora
                    ws_arr.update(data_to_insert, f'{first_col_letter}1:{last_col_letter}2', value_input_option='USER_ENTERED')
                    print("Cabeçalhos e fórmulas base inseridos.")
                    
                    # Copia a linha 2 para todas as linhas restantes usando copyPaste
                    print(f"Copiando fórmulas para {num_rows} linhas...")
                    
                    # Usa batch_update com copyPaste request
                    copy_paste_request = {
                        'copyPaste': {
                            'source': {
                                'sheetId': ws_arr.id,
                                'startRowIndex': 1,  # Linha 2 (0-indexed)
                                'endRowIndex': 2,
                                'startColumnIndex': num_cols,
                                'endColumnIndex': num_cols + 6  # 6 colunas: Estado, Município, Delegatário, Líquido, Efic, Repasses
                            },
                            'destination': {
                                'sheetId': ws_arr.id,
                                'startRowIndex': 2,  # Linha 3 em diante
                                'endRowIndex': num_rows + 1,
                                'startColumnIndex': num_cols,
                                'endColumnIndex': num_cols + 6
                            },
                            'pasteType': 'PASTE_NORMAL'
                        }
                    }
                    
                    # Remove filtros antes de copiar (evita erro com linhas filtradas)
                    clear_filter_request = {
                        'clearBasicFilter': {
                            'sheetId': ws_arr.id
                        }
                    }
                    
                    # Executa: limpa filtro + copia fórmulas
                    sh.batch_update({'requests': [clear_filter_request, copy_paste_request]})
                    print("Fórmulas copiadas com sucesso!")
                    
                    print("Fórmulas de enriquecimento adicionadas com sucesso!")
                    
                    # ========================================================================
                    # OTIMIZAÇÃO: Converte fórmulas para valores (melhora performance)
                    # ========================================================================
                    print("\nConvertendo fórmulas para valores (otimização de performance)...")
                    
                    # 1. Documenta as fórmulas antes de converter
                    formula_docs = [
                        ['Coluna', 'Fórmula', 'Descrição'],
                        ['Estado', estado_formula, 'VLOOKUP do Estado na Lista de Serventias usando CNS'],
                        ['Município', municipio_formula, 'VLOOKUP do Município na Lista de Serventias usando CNS'],
                        ['Delegatário', delegatario_formula, 'Arrecadação - Repasse (E - G)'],
                        ['Líquido', liquido_formula, 'Delegatário - Custeio (Delegatário - F)'],
                        ['Indice_Eficiencia', efic_formula, 'Custeio / Delegatário (F / Delegatário)'],
                        ['Indice_Repasses', repasses_formula, 'Repasse / Arrecadação (G / E)']
                    ]
                    
                    try:
                        ws_formulas = sh.worksheet("Formulas_Documentacao")
                        ws_formulas.clear()
                    except:
                        ws_formulas = sh.add_worksheet(title="Formulas_Documentacao", rows=20, cols=3)
                    
                    ws_formulas.update(formula_docs, value_input_option='USER_ENTERED')
                    print("✓ Fórmulas documentadas na aba 'Formulas_Documentacao'")
                    
                    # 2. Copia valores das colunas com fórmulas
                    # Usa copyPaste com PASTE_VALUES para converter fórmulas em valores
                    copy_values_request = {
                        'copyPaste': {
                            'source': {
                                'sheetId': ws_arr.id,
                                'startRowIndex': 1,  # Linha 2 em diante (pula header)
                                'endRowIndex': num_rows + 1,
                                'startColumnIndex': num_cols,
                                'endColumnIndex': num_cols + 6
                            },
                            'destination': {
                                'sheetId': ws_arr.id,
                                'startRowIndex': 1,
                                'endRowIndex': num_rows + 1,
                                'startColumnIndex': num_cols,
                                'endColumnIndex': num_cols + 6
                            },
                            'pasteType': 'PASTE_VALUES'  # Apenas valores, sem fórmulas
                        }
                    }
                    
                    sh.batch_update({'requests': [copy_values_request]})
                    print("✓ Fórmulas convertidas para valores (planilha mais rápida!)")
                    
                    # ========================================================================
                    # PRÉ-PROCESSAMENTO: Adiciona colunas auxiliares para performance
                    # ========================================================================
                    print("\nAdicionando colunas de pré-processamento...")
                    
                    # Lê dados atuais da aba Arrecadacao
                    data_arr = ws_arr.get_all_records()
                    df_proc = pd.DataFrame(data_arr)
                    
                    # Adiciona colunas Ano e Semestre_Num
                    if 'Semestre' in df_proc.columns:
                        df_proc['Ano'] = df_proc['Semestre'].astype(str).str.extract(r'(\d{4})').fillna(0).astype(int)
                        df_proc['Semestre_Num'] = df_proc['Semestre'].astype(str).str.extract(r'(\d)S').fillna(0).astype(int)
                        print("✓ Colunas Ano e Semestre_Num adicionadas")
                    
                    # Atualiza a aba com as novas colunas
                    ws_arr.clear()
                    df_proc_str = df_proc.astype(str)
                    ws_arr.update([df_proc_str.columns.values.tolist()] + df_proc_str.values.tolist(), value_input_option='USER_ENTERED')
                    print("✓ Aba Arrecadacao atualizada com colunas processadas")
                    
                    # ========================================================================
                    # ABAS AGREGADAS: Cria abas pré-filtradas para performance
                    # ========================================================================
                    print("\nCriando abas agregadas...")
                    
                    # Converte colunas numéricas
                    numeric_cols = ['Valor arrecadação', 'Valor custeio', 'Valor repasse', 'Delegatário', 'Quantidade de atos praticados']
                    for col in numeric_cols:
                        if col in df_proc.columns:
                            df_proc[col] = pd.to_numeric(df_proc[col], errors='coerce').fillna(0)
                    
                    # 1. Agregado Total (por Semestre)
                    df_total = df_proc.groupby(['Semestre', 'Ano', 'Semestre_Num']).agg({
                        'Valor arrecadação': 'sum',
                        'Valor custeio': 'sum',
                        'Valor repasse': 'sum',
                        'Delegatário': 'sum',
                        'Quantidade de atos praticados': 'sum',
                        'CNS': 'count'  # Conta serventias
                    }).reset_index()
                    df_total.rename(columns={'CNS': 'Qtd_Serventias'}, inplace=True)
                    df_total = df_total.sort_values(['Ano', 'Semestre_Num'])
                    
                    try:
                        ws_total = sh.worksheet("Agregado_Total")
                        ws_total.clear()
                    except:
                        ws_total = sh.add_worksheet(title="Agregado_Total", rows=100, cols=10)
                    
                    ws_total.update([df_total.columns.values.tolist()] + df_total.astype(str).values.tolist())
                    print("✓ Aba 'Agregado_Total' criada")
                    
                    # 2. Agregado RJ (apenas Rio de Janeiro)
                    if 'Estado' in df_proc.columns:
                        df_rj = df_proc[df_proc['Estado'].astype(str).str.upper() == 'RJ'].copy()
                        if not df_rj.empty:
                            df_rj_agg = df_rj.groupby(['Semestre', 'Ano', 'Semestre_Num']).agg({
                                'Valor arrecadação': 'sum',
                                'Valor custeio': 'sum',
                                'Valor repasse': 'sum',
                                'Delegatário': 'sum',
                                'Quantidade de atos praticados': 'sum',
                                'CNS': 'count'
                            }).reset_index()
                            df_rj_agg.rename(columns={'CNS': 'Qtd_Serventias'}, inplace=True)
                            df_rj_agg = df_rj_agg.sort_values(['Ano', 'Semestre_Num'])
                            
                            try:
                                ws_rj = sh.worksheet("Agregado_RJ")
                                ws_rj.clear()
                            except:
                                ws_rj = sh.add_worksheet(title="Agregado_RJ", rows=100, cols=10)
                            
                            ws_rj.update([df_rj_agg.columns.values.tolist()] + df_rj_agg.astype(str).values.tolist())
                            print("✓ Aba 'Agregado_RJ' criada")
                    
                    # 3. Agregado por Atribuição
                    if 'Atribuição' in df_proc.columns:
                        atribuicoes = df_proc['Atribuição'].dropna().unique()
                        for atrib in atribuicoes:
                            atrib_str = str(atrib).strip()
                            if not atrib_str or atrib_str == 'nan':
                                continue
                            
                            # Nome seguro para aba (max 100 chars, sem caracteres especiais)
                            safe_name = f"Agr_{atrib_str[:30].replace('/', '_').replace(' ', '_')}"
                            
                            df_atrib = df_proc[df_proc['Atribuição'] == atrib].copy()
                            if not df_atrib.empty:
                                df_atrib_agg = df_atrib.groupby(['Semestre', 'Ano', 'Semestre_Num']).agg({
                                    'Valor arrecadação': 'sum',
                                    'Valor custeio': 'sum',
                                    'Valor repasse': 'sum',
                                    'Delegatário': 'sum',
                                    'Quantidade de atos praticados': 'sum',
                                    'CNS': 'count'
                                }).reset_index()
                                df_atrib_agg.rename(columns={'CNS': 'Qtd_Serventias'}, inplace=True)
                                df_atrib_agg['Atribuição'] = atrib_str
                                df_atrib_agg = df_atrib_agg.sort_values(['Ano', 'Semestre_Num'])
                                
                                try:
                                    ws_atrib = sh.worksheet(safe_name)
                                    ws_atrib.clear()
                                except:
                                    ws_atrib = sh.add_worksheet(title=safe_name, rows=100, cols=11)
                                
                                ws_atrib.update([df_atrib_agg.columns.values.tolist()] + df_atrib_agg.astype(str).values.tolist())
                                print(f"✓ Aba '{safe_name}' criada")
                    
                    print("\n✅ Todas as abas agregadas criadas com sucesso!")
                    
                    # Sincroniza com Supabase
                    sync_to_supabase(df_proc, df_serv)
        
        # Limpeza de abas legadas
        try:
            ws_adj = sh.worksheet("Arrecadacao_Ajustada")
            sh.del_worksheet(ws_adj)
            print("Aba legada 'Arrecadacao_Ajustada' removida.")
        except: pass
        
        try:
            log_ws = sh.worksheet("Log_Bot")
        except:
            log_ws = sh.add_worksheet(title="Log_Bot", rows=100, cols=2)
        from datetime import datetime
        log_ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"ETL Concluído. Arquivos: {list(files_dict.keys())}"])
        
        print("Processo finalizado com sucesso!")
        
    except Exception as e:
        print(f"Erro geral no GSheets: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Script CNJ Analytics")
    parser.add_argument("--action", choices=["download", "process", "full"], default="full", help="Ação a executar")
    args = parser.parse_args()
    
    # Log de início
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"⏰ Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    files_to_process = {}
    
    # 1. Fase de Download
    if args.action in ["download", "full"]:
        files_to_process = extract_cnj_data()
    
    # 2. Captura arquivos se for apenas processamento 
    # (ou se o download sobrescreveu files_to_process com o último tipo encontrado)
    if args.action == "process" or (args.action == "full" and not files_to_process):
        # Busca inteligente: prefere CSV, se não achar, tenta XLSX
        for key in ["arrecadacao", "serventias"]:
            # Tenta CSV primeiro
            path_csv = os.path.join(DOWNLOAD_DIR, f"{key}.csv")
            if os.path.exists(path_csv):
                files_to_process[key] = path_csv
                print(f"[{key}] Selecionado CSV: {path_csv}")
                continue
                
            # Tenta XLSX
            path_xlsx = os.path.join(DOWNLOAD_DIR, f"{key}.xlsx")
            if os.path.exists(path_xlsx):
                files_to_process[key] = path_xlsx
                print(f"[{key}] Selecionado XLSX: {path_xlsx}")
    
    # 3. Fase de Processamento/Upload
    if args.action in ["process", "full"] and files_to_process:
        upload_to_gsheets(files_to_process)
    elif args.action == "download":
        print("Download concluído. Processamento ignorado conforme solicitado.")
    else:
        print("Nenhum arquivo encontrado para processamento.")
    
    # Log de fim
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n{'='*60}")
    print(f"⏰ Fim: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Duração: {duration}")
    print(f"{'='*60}\n")
