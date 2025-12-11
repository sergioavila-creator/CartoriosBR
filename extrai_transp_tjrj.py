import os
import time
import datetime
import re
from urllib.parse import urljoin, urlparse
from datetime import date
from unicodedata import normalize

# --- NOVAS DEPENDÊNCIAS DE REDE (Recomendadas para Google Cloud Functions) ---
import urllib.request
import urllib.error
import requests # O requests é estável no GCF, mas vamos manter o urllib para o core
import json
import io
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- BIBLIOTECAS DE ANALISE E GOOGLE SHEETS ---
import pdfplumber
import pandas as pd
# Biblioteca para Google Sheets: requer 'pip install gspread'
import gspread 
try:
    import streamlit as st
except ImportError:
    st = None

# ####################################################################
# CONFIGURAÇÕES GERAIS (Cloud)
# ####################################################################

# ID da sua planilha Google (substitua pelo ID da sua planilha!)
# Tenta pegar de var de ambiente OU dos segredos do Streamlit
GOOGLE_SHEET_ID = os.environ.get('SHEET_ID')
try:
    if not GOOGLE_SHEET_ID and st and hasattr(st, "secrets") and "SHEET_ID" in st.secrets:
        GOOGLE_SHEET_ID = st.secrets["SHEET_ID"]
except Exception:
    pass # Ignora erro se não houver secrets (comum no GitHub Actions)

if not GOOGLE_SHEET_ID:
    # Fallback para o ID conhecido (extraído do st.secrets anteriormente se necessário, ou mantido hardcoded se for seguro)
    GOOGLE_SHEET_ID = '1_BXjFfmKM_K0ZHpcU8qiEWYQm4weZeekg8E2CbOiQfE' # ID da planilha de Receita atualizado

# --- CONFIGURAÇÕES DO BAIXADOR ---
BASE_PAGE = "https://www.tjrj.jus.br/transparencia/relatorio-de-receita-cartoraria-extrajudicial"
ROOT = "https://www.tjrj.jus.br"
PDF_SUBSTR = "documents/d/guest/receita"

RETRIES = 3
TIMEOUT_CONNECT = 20
TIMEOUT_READ = 120
MIN_PDF_BYTES = 1500

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12
}

# --- CONFIGURAÇÕES DO EXTRATOR ---
# Colunas que serão exportadas para o Google Sheets
COLUNAS_BRUTAS = [
    'cod', 'cidade', 'designacao', 'arquivo_origem', 'mes', 'ano',
    'RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 
    'Emolumentos', 'Funarpem', 'Gratuitos', 'Total',
    'gestor', 'cargo'
]

# ####################################################################
# FUNÇÕES DE UTILIDADE E REDE (Adaptadas para Cloud)
# ####################################################################

# Funções otimizadas com requests
def safe_get(url):
    """Baixa HTML usando requests (mais robusto)."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT_CONNECT, verify=False)
        response.encoding = 'utf-8' # Força UTF-8
        return response.text
    except Exception as e:
        print(f"[ERRO REDE] Falha ao carregar {url}: {e}")
        return ""

def download_file(url: str):
    """Baixa arquivo usando requests."""
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT_READ, verify=False)
            if r.status_code == 200:
                content = r.content
                if len(content) < MIN_PDF_BYTES:
                     print(f"[AVISO] Arquivo pequeno em {url}.")
                     return None
                return content
            else:
                 print(f"[ERRO HTTP] {r.status_code} em {url}")
        except Exception as e:
            print(f"[DOWNLOAD ERRO {attempt}/{RETRIES}] {url} - {e}")
            time.sleep(1 + attempt * 2)

    return None

def extrair_mes_ano(url: str):
    """Tenta extrair o mês e ano do nome do arquivo na URL."""
    nome_arquivo = url.split('/')[-1].lower()
    
    match = re.search(r'(' + '|'.join(MESES.keys()) + r')[\W_]*(\d{4})', nome_arquivo)
    
    if match:
        mes_nome_bruto = match.group(1)
        ano = int(match.group(2))
        mes = MESES.get(mes_nome_bruto.replace('ç', 'c'))
        return mes, ano
    
    return 0, 0

def extract_pdf_links(html, base=ROOT):
    """Extrator robusto baseado no baixa.py."""
    if not html:
        return []

    found = []
    seen = set()

    # Regex do baixa.py: busca qualquer href
    regex = re.compile(r'href\s*=\s*(["\']?)(?P<u>[^"\' >]+)', re.I)

    for m in regex.finditer(html):
        raw = m.group("u")

        # Filtro pelo substring específico
        if PDF_SUBSTR not in raw.lower():
            continue

        if raw.startswith("//"):
            url = "https:" + raw
        elif raw.startswith("/"):
            url = urljoin(base, raw)
        else:
            url = raw

        # Limpeza da URL
        p = urlparse(url)
        clean = p.scheme + "://" + p.netloc + p.path
        if p.query:
            clean += "?" + p.query

        if clean not in seen:
            seen.add(clean)
            found.append(clean)
            
    print(f"[DEBUG] extrair_pdf_links encontrou {len(found)} links.")
    return found

# Lista de Municipios (100% ASCII - SEM ACENTOS) - Mantida do extrator.py
MUNICIPIOS_RJ = [
    "ANGRA DOS REIS", "APERIBE", "ARARUAMA", "AREAL", "ARMACAO DOS BUZIOS",
    "ARRAIAL DO CABO", "BARRA DO PIRAI", "BARRA MANSA", "BELFORD ROXO", "BOM JARDIM",
    "BOM JESUS DO ITABAPOANA", "CABO FRIO", "CACHOEIRAS DE MACACU", "CAMBUCI", "CAMPOS DOS GOYTACAZES",
    "CANTAGALO", "CARAPEBUS", "CARDOSO MOREIRA", "CARMO", "CASIMIRO DE ABREU", "COMENDADOR LEVY GASPARIAN",
    "CONCEICAO DE MACABU", "CORDEIRO", "DUAS BARRAS", "DUQUE DE CAXIAS",
    "ENGENHEIRO PAULO DE FRONTIN", "GUAPIMIRIM", "IGUABA GRANDE", "ITABORAI", "ITAGUAI",
    "ITALVA", "ITAOCARA", "ITAPERUNA", "ITATIAIA", "JAPERI", "LAJE DO MURIAE", "MACAE",
    "MACUCO", "MAGE", "MANGARATIBA", "MARICA", "MENDES", "MESQUITA", "MIGUEL PEREIRA",
    "MIRACEMA", "NATIVIDADE", "NILOPOLIS", "NITEROI", "NOVA FRIBURGO", "NOVA IGUACU",
    "PARACAMBI", "PARAIBA DO SUL", "PARATY", "PATY DO ALFERES", "PETROPOLIS",
    "PINHEIRAL", "PIRAI", "PORCIUNCULA", "PORTO REAL", "QUATIS", "QUEIMADOS", "QUISSAMA",
    "RESENDE", "RIO BONITO", "RIO CLARO", "RIO DAS FLORES", "RIO DAS OSTRAS", "RIO DE JANEIRO",
    "SANTA MARIA MADALENA", "SANTO ANTONIO DE PADUA", "SAO FIDELIS",
    "SAO FRANCISCO DE ITABAPOANA", "SAO GONCALO",
    "SAO JOAO DA BARRA", "SAO JOAO DE MERITI",
    "SAO JOSE DE UBA", "SAO JOSE DO VALE DO RIO PRETO",
    "SAO PEDRO DA ALDEIA", "SAO SEBASTIAO DO ALTO",
    "SAPUCAIA", "SAQUAREMA", "SEROPEDICA", "SILVA JARDIM", "SUMIDOURO", "TANGUA",
    "TERESOPOLIS", "TRAJANO DE MORAES", "TRES RIOS", "VALENCA",
    "VARRE-SAI", "VASSOURAS", "VOLTA REDONDA", "CAPITAL"
]

def extrator_normalizar_para_match(texto):
    if not texto: return ""
    return normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

def extrator_extrair_valores(linha):
    """Extrai valores numéricos formatados em BRL (ponto como milhar, vírgula como decimal)."""
    valores_str = re.findall(r'[\d\.]+\,\d{2}', linha)
    valores_float = []
    for v in valores_str:
        v_limpo = v.replace('.', '').replace(',', '.')
        try:
            valores_float.append(float(v_limpo))
        except ValueError:
            pass
    return valores_float

def extrator_separar_cidade_designacao(texto_completo):
    """Separa o nome do município da designação do cartório."""
    if not texto_completo: return "", ""
    texto_norm = extrator_normalizar_para_match(texto_completo)
    municipios_ordenados = sorted(MUNICIPIOS_RJ, key=len, reverse=True)
    
    for municipio in municipios_ordenados:
        if texto_norm.startswith(municipio):
            designacao = texto_norm[len(municipio):].strip()
            if designacao.startswith("-"): designacao = designacao[1:].strip()
            return municipio, designacao
    return "OUTRA/VERIFICAR", texto_completo

def processar_pdf_content(pdf_bytes: bytes, nome_arquivo: str):
    """Processa o conteúdo binário de um PDF usando a lógica do extrator.py."""
    dados_servicos = []
    
    # Tenta extrair mês/ano do nome do arquivo fornecido
    match_data_arquivo = re.search(r'(\d{4})_(\d{2})', nome_arquivo)
    if match_data_arquivo:
        ano_arquivo = int(match_data_arquivo.group(1))
        mes_arquivo = int(match_data_arquivo.group(2))
    else:
        ano_final, mes_final = 0, 0
    
    try:
        # Usa pdfplumber para abrir o arquivo a partir dos bytes (encapsulados em BytesIO)
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            mes_atual = mes_arquivo
            ano_atual = ano_arquivo
            
            # Regex para mapear colunas (RCPJ, RCPN, etc.)
            mapa_regex = {
                r'Civil das Pessoas Jur.dicas': "RCPJ",
                r'Civil das Pessoas Naturais': "RCPN",
                r'Interdi..es e Tutelas': "IT",
                r'Of.cios e Atos do Registro de Im.veis': "RI",
                r'T.tulos e Documentos': "RTD",
                r'Of.cios e Atos de Notas': "Notas",
                r'Tabelionatos de Protesto de T.tulos': "Protesto"
            }

            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if not texto: continue
                
                # Limpeza de texto para facilitar a extração (Lógica do extrator.py)
                texto_reparado = re.sub(r'[^\S\n]+', ' ', texto) 
                texto_reparado = re.sub(r'(\S)(Servi.o:)', r'\1\n\2', texto_reparado)
                texto_reparado = re.sub(r'(\S)(Total Geral)', r'\1\n\2', texto_reparado)
                texto_reparado = re.sub(r'(\S)(Gestor do Servi.o:)', r'\1\n\2', texto_reparado)
                
                for key_regex in mapa_regex.keys():
                    texto_reparado = re.sub(rf'(\S)({key_regex})', r'\1\n\2', texto_reparado, flags=re.IGNORECASE)

                linhas = texto_reparado.split('\n')
                dados_servico_atual = {}
                lendo_servico = False
                
                for linha in linhas:
                    linha_limpa = linha.strip()

                    # Tentativa de extrair data do cabeçalho da página
                    if "Per" in linha and "/" in linha and len(linha) < 50:
                        match_data = re.search(r'(\d{1,2})\s*/\s*(\d{4})', linha)
                        if match_data:
                            mes_atual = int(match_data.group(1))
                            ano_atual = int(match_data.group(2))

                    # Início de um novo serviço
                    if re.match(r'^Servi.o:', linha_limpa):
                        if lendo_servico: pass 
                        partes = linha_limpa.split(":", 1)
                        texto_completo = partes[1].strip() if len(partes) > 1 else ""
                        match_cod = re.search(r'^(\d+)\s*-\s*(.*)', texto_completo)
                        
                        if match_cod:
                            cod_servico = match_cod.group(1).strip()
                            nome_full = match_cod.group(2).strip()
                        else:
                            cod_servico = texto_completo.split(' ')[0] if texto_completo else "N/A"
                            nome_full = texto_completo
                            
                        cidade, designacao = extrator_separar_cidade_designacao(nome_full)

                        # Inicializa os dados do serviço
                        dados_servico_atual = {col: None for col in COLUNAS_BRUTAS}
                        dados_servico_atual['cod'] = cod_servico 
                        dados_servico_atual['cidade'] = cidade
                        dados_servico_atual['designacao'] = designacao
                        dados_servico_atual['mes'] = mes_atual
                        dados_servico_atual['ano'] = ano_atual
                        dados_servico_atual['arquivo_origem'] = nome_arquivo
                        dados_servico_atual['gestor'] = "NAO IDENTIFICADO"
                        dados_servico_atual['cargo'] = "NAO IDENTIFICADO"
                        lendo_servico = True
                    
                    # Extração do Gestor
                    if lendo_servico and re.search(r'Gestor do Servi.o:', linha_limpa):
                        try:
                            partes = linha_limpa.split(":", 1)
                            conteudo = partes[1].strip() if len(partes) > 1 else ""
                            if re.search(r'Condi..o do Gestor', conteudo):
                                split_cond = re.split(r'Condi..o do Gestor:?', conteudo)
                                dados_servico_atual['gestor'] = split_cond[0].strip()
                                if len(split_cond) > 1:
                                    cargo_temp = split_cond[1].strip()
                                    if "Delegat" in cargo_temp: cargo_temp = "Titular"
                                    dados_servico_atual['cargo'] = cargo_temp
                            else:
                                dados_servico_atual['gestor'] = conteudo
                        except: pass

                    # Extração da Condição (Cargo)
                    if lendo_servico and re.search(r'^Condi..o do Gestor:', linha_limpa):
                        try:
                            partes = linha_limpa.split(":", 1)
                            cargo_temp = partes[1].strip()
                            if "Delegat" in cargo_temp: cargo_temp = "Titular"
                            dados_servico_atual['cargo'] = cargo_temp
                        except: pass

                    # Extração dos valores por atribuição
                    if lendo_servico:
                        for key_regex, nome_coluna in mapa_regex.items():
                            if re.search(key_regex, linha_limpa, re.IGNORECASE):
                                valores = extrator_extrair_valores(linha_limpa)
                                if valores:
                                    # O valor total do emolumento fica no final da linha
                                    dados_servico_atual[nome_coluna] = valores[-1]
                                break
                    
                    # Fim de um serviço (Total Geral)
                    if lendo_servico and "Total Geral" in linha_limpa:
                        valores = extrator_extrair_valores(linha_limpa)
                        if len(valores) >= 1:
                            # O último valor é o Total Final
                            dados_servico_atual['Total'] = valores[-1]
                            
                            # Tentativa de capturar Emolumentos Totais, Funarpem e Gratuitos
                            if len(valores) >= 4:
                                dados_servico_atual['Emolumentos'] = valores[-4] # Emolumentos
                                dados_servico_atual['Funarpem'] = valores[-3]
                                dados_servico_atual['Gratuitos'] = valores[-2]
                                
                            dados_servicos.append(dados_servico_atual.copy())
                            lendo_servico = False
                            dados_servico_atual = {}

    except Exception as e:
        print(f"[ERRO PDF] Falha ao processar {nome_arquivo}: {e}")
        import traceback
        print(traceback.format_exc())
        
    return dados_servicos

# ####################################################################
# GOOGLE SHEETS API (Nova Funcionalidade)
# ####################################################################

def eh_distrito_valido(designacao):
    """Verifica se a designação se refere a um RCPN de Distrito (a partir do 2º)."""
    if not isinstance(designacao, str): return False
    texto = designacao.upper()
    if "DISTR" not in texto: return False
    match = re.search(r'(\d+).*?DISTR', texto)
    if match:
        try:
            # Consideramos Distritos a partir do 2º.
            return int(match.group(1)) >= 2
        except: return False
    return False

# ####################################################################
# GOOGLE SHEETS API (Nova Funcionalidade)
# ####################################################################

def exportar_para_sheets(df_brutos: pd.DataFrame, df_analise: pd.DataFrame, df_distritos: pd.DataFrame, df_cidades: pd.DataFrame):
    """Autentica no Google Sheets e envia os dados para as abas."""
    print("Iniciando exportação para o Google Sheets (4 abas)...")
    
    try:
        if "GCP_SERVICE_ACCOUNT" in os.environ:
             import json
             creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
             gc = gspread.service_account_from_dict(creds_dict)
        elif st and hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
             gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        else:
             gc = gspread.service_account()
        
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        
        def enviar_aba(df, nome_aba, col_inicial_format=None, col_final_format=None):
            ws = get_or_create_worksheet(sh, nome_aba, rows=len(df)+50, cols=len(df.columns)+5)
            df = df.fillna(0.0) # Previne NaN
            values = [df.columns.values.tolist()] + df.values.tolist()
            ws.clear()
            ws.update(values, value_input_option='USER_ENTERED')
            print(f"SUCESSO: {len(df)} linhas exportadas para '{nome_aba}'.")
            
            # Congela a primeira linha (cabeçalho)
            try:
                ws.freeze(rows=1)
            except Exception as e:
                print(f"   [AVISO] Falha ao congelar painéis em {nome_aba}: {e}")

            # Filtro Automático (AutoFilter)
            try:
                # Define o intervalo total: A1 até (UltimaColuna)(UltimaLinha)
                # Ex: set_basic_filter(1, 1, 100, 5) -> Linha 1, Col 1 até Linha 100, Col 5
                ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
            except Exception as e:
                print(f"   [AVISO] Falha ao criar filtro em {nome_aba}: {e}")

            # Formatação de Número (Se colunas definidas)
            if col_inicial_format and col_final_format:
                try:
                    # Ex: G2:Q100
                    range_sq = f"{col_inicial_format}2:{col_final_format}{len(df)+1}"
                    ws.format(range_sq, {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}})
                    print(f"   -> Formatado intervalo {range_sq}")
                except Exception as e:
                    print(f"   [AVISO] Não foi possível formatar {nome_aba}: {e}")

        # Helper para criar aba se nao existir
        def get_or_create_worksheet(spreadsheet, title, rows=100, cols=20):
            try:
                return spreadsheet.worksheet(title)
            except gspread.exceptions.WorksheetNotFound:
                print(f"Aba '{title}' não encontrada. Criando...")
                return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

        # Exporta as 4 abas com formatação
        # Dados Brutos: G a Q
        enviar_aba(df_brutos, "Dados Brutos", "G", "Q")
        
        # Análise 12 Meses: D a N
        enviar_aba(df_analise, "Análise 12 Meses", "D", "N")
        
        # Distritos: D a N
        enviar_aba(df_distritos, "Distritos", "D", "N")
        
        # Cidades: B a E
        enviar_aba(df_cidades, "Cidades", "B", "E")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"[ERRO GSHEETS] Falha na autenticação ou escrita: {e}")
        print(traceback.format_exc())
        return False


# ####################################################################
# LOG DE EXECUÇÃO (Google Sheets)
# ####################################################################
def log_execution(status, message, elapsed_time=0):
    """Registra a execução na aba 'Log Execucoes'."""
    try:
        print(f"[LOG] Registrando execução: {status} - {message}")
        
        # Autenticação
        if "GCP_SERVICE_ACCOUNT" in os.environ:
             import json
             creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
             if "private_key" in creds_dict:
                 creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
             gc = gspread.service_account_from_dict(creds_dict)
        elif st and hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
             creds_dict = dict(st.secrets["gcp_service_account"])
             if "private_key" in creds_dict:
                 creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
             gc = gspread.service_account_from_dict(creds_dict)
        else:
             gc = gspread.service_account()
        
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
        
        try:
            ws = sh.worksheet("Log Execucoes")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title="Log Execucoes", rows=1000, cols=5)
            ws.append_row(["Data Hora", "Status", "Tempo (s)", "Mensagem", "Detalhes"])
            
        timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ws.append_row([timestamp, status, round(elapsed_time, 2), message, "Cloud Function/Streamlit"])
        print("[LOG] Sucesso ao salvar log.")
        
    except Exception as e:
        print(f"[LOG ERROR] Falha ao salvar log de execução: {e}")

# ####################################################################
# ORQUESTRADOR PRINCIPAL (master_processo.py main)
# ####################################################################

def cloud_main(request, run_enrichment=True):
    """
    Função principal que será executada pelo Google Cloud Functions (GCF).
    """
    inicio_total = time.time()
    dados_consolidados = []
    
    print("#"*70)
    print("      Sistema CartoriosRJ - Orquestrador Cloud (V80.6 - Refinado)")
    print(f"      Iniciado em: {datetime.date.today().strftime('%d/%m/%Y')}")
    print(f"      [PARAM] run_enrichment = {run_enrichment}")
    print("#"*70)
    
    # 1. Obter lista de links dos PDFs
    html_main = safe_get(BASE_PAGE)
    links_totais = extract_pdf_links(html_main)
    
    ano_ant = date.today().year - 1
    html_prev = safe_get(f"{BASE_PAGE}/{ano_ant}")
    links_prev = extract_pdf_links(html_prev)
    
    combined_links = list(dict.fromkeys(links_totais + links_prev))
    combined_links.sort(key=lambda url: extrair_mes_ano(url)[1] * 100 + extrair_mes_ano(url)[0], reverse=True)
    
    print(f"[INFO] Total de links detectados: {len(combined_links)}")

    # 2. Loop de Download e Extração
    for i, url in enumerate(combined_links[:12]): # Limita aos 12 mais recentes
        mes, ano = extrair_mes_ano(url)
        nome_arquivo = f"{ano}_{mes:02d}.pdf"
        
        print(f"Processando {nome_arquivo}...", end=" ")
        
        pdf_bytes = download_file(url)
        
        if pdf_bytes:
            dados_servicos = processar_pdf_content(pdf_bytes, nome_arquivo)
            qtd = len(dados_servicos)
            if qtd > 0:
                print(f"OK ({qtd} linhas)")
                dados_consolidados.extend(dados_servicos)
            else:
                print(f"ZERO DADOS")
            
        if i >= 11: break

    # 3. Análise (Pandas)
    if not dados_consolidados:
        print("[ERRO] Nenhuma dado extraído dos PDFs. Análise finalizada.")
    if not dados_consolidados:
        print("[ERRO] Nenhuma dado extraído dos PDFs. Análise finalizada.")
        log_execution("ERRO", "Nenhum dado extraído dos PDFs", time.time() - inicio_total)
        return 'Falha ao processar PDFs', 500

    df_brutos = pd.DataFrame(dados_consolidados)
    df_brutos = df_brutos.reindex(columns=COLUNAS_BRUTAS)
    
    # Converte colunas numéricas (importante filtrar apenas as que existem)
    cols_numericas = ['RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 'Emolumentos', 'Funarpem', 'Gratuitos', 'Total']
    for col in cols_numericas:
        if col in df_brutos.columns:
            df_brutos[col] = pd.to_numeric(df_brutos[col], errors='coerce')

    # Limpeza e ordenação dos dados brutos
    df_brutos.drop_duplicates(subset=['cod', 'cidade', 'designacao', 'arquivo_origem', 'mes', 'ano', 'Total'], keep='first', inplace=True)
    df_brutos.sort_values(by=['cidade', 'designacao', 'ano', 'mes'], inplace=True)

    # --- ANALISE 1 (Média por Cartório) ---
    df_analise = df_brutos.groupby(['cod', 'cidade', 'designacao'], as_index=False).agg({
        'RCPJ': 'mean', 'RCPN': 'mean', 'IT': 'mean', 'RI': 'mean', 'RTD': 'mean', 
        'Notas': 'mean', 'Protesto': 'mean', 'Emolumentos': 'mean', 'Funarpem': 'mean', 
        'Gratuitos': 'mean', 'Total': 'mean', 'gestor': 'last', 'cargo': 'last'
    })

    # Renomear para compatibilidade
    df_analise_compat = df_analise.copy()
    df_analise_compat.rename(columns={'Total': 'Media Mensal Total (R$)'}, inplace=True)

    # --- ANALISE 2 (Distritos) ---
    df_distritos = df_analise[df_analise['designacao'].apply(eh_distrito_valido)].copy()
    
    # --- ANALISE 3 (Cidades) ---
    # Média Mensal Total (Soma das médias dos cartórios da cidade)
    df_cidades_media = df_analise.groupby('cidade', as_index=False)['Total'].sum()
    df_cidades_media.rename(columns={'Total': 'Media Mensal Total (R$)'}, inplace=True)

    # Faturamento Acumulado Bruto
    df_cidades_acum = df_brutos.groupby('cidade', as_index=False)['Total'].sum()
    df_cidades_acum.rename(columns={'Total': 'Faturamento Acumulado Bruto (R$)'}, inplace=True)
    
    # Qtd Cartorios (Novo rótulo)
    df_cidades_cont = df_analise.groupby('cidade').size().reset_index(name='Qtd Cartorios')
    
    # Merge
    df_cidades = pd.merge(df_cidades_media, df_cidades_acum, on='cidade', how='left')
    df_cidades = pd.merge(df_cidades, df_cidades_cont, on='cidade', how='left')
    
    # Nova Coluna E: Média por cartório
    # Média por cartório = Media Mensal Total (B) / Qtd Cartorios (D)
    df_cidades['Média por cartório'] = df_cidades['Media Mensal Total (R$)'] / df_cidades['Qtd Cartorios']
    df_cidades['Média por cartório'] = df_cidades['Média por cartório'].round(2)
    
    # Ordenar colunas e linhas
    # A=cidade, B=Media Mensal, C=Fat Acum, D=Qtd Cart, E=Média por cartório
    cols_cidades = ['cidade', 'Media Mensal Total (R$)', 'Faturamento Acumulado Bruto (R$)', 'Qtd Cartorios', 'Média por cartório']
    df_cidades = df_cidades[cols_cidades]
    
    df_cidades.sort_values(by='Media Mensal Total (R$)', ascending=False, inplace=True)
    
    # 4. Snapshots de Debug (Solicitado pelo usuário)
    try:
        from logging_utils import save_debug_snapshot
        save_debug_snapshot(df_brutos, "tjrj_dados_brutos")
        save_debug_snapshot(df_analise_compat, "tjrj_analise_12m")
        save_debug_snapshot(df_distritos, "tjrj_distritos")
        save_debug_snapshot(df_cidades, "tjrj_cidades")
    except ImportError:
        print("[AVISO] logging_utils não encontrado para snapshots.")

    # 5. Exportação para Google Sheets
    exportar_para_sheets(df_brutos, df_analise_compat, df_distritos, df_cidades)

    fim_total = time.time()
    tempo_total = fim_total - inicio_total
    
    print(f"\n[SUCESSO] Processo Cloud concluído em {tempo_total:.2f} segundos.")
    print(f"\n[SUCESSO] Processo Cloud concluído em {tempo_total:.2f} segundos.")
    log_execution("SUCESSO", "Processo concluído", tempo_total)
    return 'Planilha atualizada com sucesso', 200

# ####################################################################
# SERVIÇO INDEPENDENTE: ENRIQUECIMENTO DE CNS
# ####################################################################

def enrich_tjrj_with_cns(df_brutos):
    """
    Serviço Independente de População de CNS.
    Recebe o DataFrame Bruto do TJRJ e adiciona a coluna CNS usando fuzzy matching
    com a base oficial do CNJ (Lista de Serventias).
    """
    print("\n[INFO] Iniciando Serviço de Enriquecimento de CNS...")
    
    # 1. Carregar Base de Conhecimento (Serventias CNJ)
    df_serventias = None
    try:
        # Tentar CSV local (cache)
        path_serventias_csv = os.path.join(os.getcwd(), "downloads", "serventias.csv")
        if os.path.exists(path_serventias_csv):
             try:
                 df_serventias = pd.read_csv(path_serventias_csv, dtype=str)
                 print("  -> Carregado de serventias.csv local")
             except: pass
        
        # Tentar Google Sheets se não achou local
        if df_serventias is None:
             if "GCP_SERVICE_ACCOUNT" in os.environ:
                  import json
                  creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
                  # Correção de chave privada
                  if "private_key" in creds_dict:
                      creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                  gc_map = gspread.service_account_from_dict(creds_dict)
             elif st and hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
                  # Converte AttrDict para dict mutável e sanitiza
                  creds_dict = dict(st.secrets["gcp_service_account"])
                  if "private_key" in creds_dict:
                      creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                  gc_map = gspread.service_account_from_dict(creds_dict)
             else:
                  gc_map = gspread.service_account()
             
             sh_map = gc_map.open_by_key("1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y")
             ws_map = sh_map.worksheet("Lista de Serventias")
             df_serventias = pd.DataFrame(ws_map.get_all_records())
             print("  -> Carregado do Google Sheets")
             
    except Exception as e:
        print(f"  [AVISO] Falha ao carregar base CNJ: {e}")
        return df_brutos # Retorna sem alterações em caso de erro

    if df_serventias is None or df_serventias.empty:
        return df_brutos

    try:
         # Função helper interna
         def normalize_name(name):
             if not isinstance(name, str): return ""
             return normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII').upper().strip()
         
         print(f"  [DEBUG] Colunas encontradas na base CNJ: {list(df_serventias.columns)}")
         
         # Identificar colunas
         col_nome = next((c for c in df_serventias.columns if 'nome' in c.lower() or 'denominacao' in c.lower() or 'denominação' in c.lower()), 'Denominação')
         col_municipio = next((c for c in df_serventias.columns if 'municipio' in c.lower() or 'cidade' in c.lower()), 'Município')
         col_cns = next((c for c in df_serventias.columns if 'cns' in c.lower()), 'CNS')
         col_gestor = next((c for c in df_serventias.columns if ('titular' in c.lower() or 'responsavel' in c.lower() or 'responsável' in c.lower()) and 'data' not in c.lower() and 'dat.' not in c.lower()), 'Titular')
         col_atribuicao = next((c for c in df_serventias.columns if 'atribuicao' in c.lower() or 'atribuição' in c.lower()), 'Atribuições')
         
         # Indexar Base CNJ
         cnj_map_nome = {}
         cnj_map_gestor = {}

         for _, row in df_serventias.iterrows():
             cns = str(row[col_cns]).strip()
             nome = normalize_name(row[col_nome])
             mun = normalize_name(row[col_municipio])
             gestor = normalize_name(row[col_gestor])
             atribs = str(row[col_atribuicao]).upper()
             
             cnj_map_nome[f"{mun}_{nome}"] = cns
             cnj_map_nome[nome] = cns
             
             if gestor:
                 if gestor not in cnj_map_gestor: cnj_map_gestor[gestor] = []
                 cnj_map_gestor[gestor].append({
                     'cns': cns,
                     'municipio': mun,
                     'atribuicoes': atribs,
                     'nome_cartorio': nome
                 })
         
         print(f"  -> Base indexada: {len(cnj_map_nome)} nomes, {len(cnj_map_gestor)} gestores.")

         # Lógica de Busca
         def find_cns(row):
             tjrj_mun = normalize_name(row['cidade'])
             tjrj_nome = normalize_name(row['designacao'])
             tjrj_gestor = normalize_name(row['gestor'])
             
             # 1. Match Exato (Mun + Nome)
             key_exact = f"{tjrj_mun}_{tjrj_nome}"
             if key_exact in cnj_map_nome: return cnj_map_nome[key_exact]
             
             # 2. Match Gestor (com Desambiguação de Atribuição)
             if tjrj_gestor and tjrj_gestor in cnj_map_gestor:
                 candidatos = cnj_map_gestor[tjrj_gestor]
                 # Filtra municipio
                 cand_mun = [c for c in candidatos if c['municipio'] == tjrj_mun]
                 if not cand_mun: cand_mun = candidatos # Fallback
                 
                 if len(cand_mun) == 1:
                     return cand_mun[0]['cns']
                 elif len(cand_mun) > 1:
                     # Desambiguação por Atribuição (Receita vs Atribuição CNJ)
                     pontuacao = []
                     cols_receita = ['RCPJ', 'RCPN', 'RI', 'RTD', 'Notas', 'Protesto']
                     atribuicoes_row = []
                     for c in cols_receita:
                         val = pd.to_numeric(row.get(c, 0), errors='coerce')
                         if val > 0: atribuicoes_row.append(c)
                     
                     for cand in cand_mun:
                         score = 0
                         cand_atribs = cand['atribuicoes']
                         for atrib_req in atribuicoes_row:
                             termos = [atrib_req]
                             if atrib_req == 'Notas': termos += ['TABELIE', 'NOTAS']
                             if atrib_req == 'RI': termos += ['REGISTRO DE IMOVEIS']
                             if atrib_req == 'RCPN': termos += ['CIVIL DAS PESSOAS NATURAIS']
                             if atrib_req == 'RCPJ': termos += ['CIVIL DAS PESSOAS JURIDICAS']
                             if atrib_req == 'RTD': termos += ['TITULOS E DOCUMENTOS']
                             
                             for t in termos:
                                 if t in cand_atribs: 
                                     score += 1
                                     break
                         
                         # Tie-breaker: Nome similar
                         from difflib import SequenceMatcher
                         ratio = SequenceMatcher(None, tjrj_nome, cand['nome_cartorio']).ratio()
                         score += ratio
                         pontuacao.append((score, cand['cns']))
                     
                     pontuacao.sort(key=lambda x: x[0], reverse=True)
                     if pontuacao: return pontuacao[0][1]

             # 3. Fuzzy Match Nome
             candidates = [k for k in cnj_map_nome.keys() if k.startswith(f"{tjrj_mun}_")]
             best_ratio = 0
             best_cns = None
             from difflib import SequenceMatcher
             for cand_key in candidates:
                 cand_nome_only = cand_key.replace(f"{tjrj_mun}_", "")
                 ratio = SequenceMatcher(None, tjrj_nome, cand_nome_only).ratio()
                 if ratio > 0.85 and ratio > best_ratio:
                     best_ratio = ratio
                     best_cns = cnj_map_nome[cand_key]
             if best_cns: return best_cns
             
             return "NAO_ENCONTRADO"

         df_brutos['CNS'] = df_brutos.apply(find_cns, axis=1)
         
         # Reordenar colunas
         cols = ['CNS'] + [c for c in df_brutos.columns if c != 'CNS']
         df_brutos = df_brutos[cols]
         
         # Hack: atualizar a lista global COLUNAS_BRUTAS se necessario
         # Mas aqui estamos retornando o DF modificado. O caller deve usar esse DF.
         
         # Função helper para fallback por código (reutilizável)
         def apply_code_fallback_step(df, step_name):
             """Aplica fallback por código e retorna quantidade recuperada"""
             if 'cod' not in df.columns:
                 return 0
             
             before_count = df[df['CNS'] != 'NAO_ENCONTRADO'].shape[0]
             
             # Cria mapeamento: cod -> CNS (apenas CNS válidos)
             cod_to_cns = df[df['CNS'] != 'NAO_ENCONTRADO'].groupby('cod')['CNS'].first().to_dict()
             
             # Função para aplicar fallback
             def apply_fallback(row):
                 if row['CNS'] == 'NAO_ENCONTRADO' and row['cod'] in cod_to_cns:
                     return cod_to_cns[row['cod']]
                 return row['CNS']
             
             # Aplica fallback
             df['CNS'] = df.apply(apply_fallback, axis=1)
             
             after_count = df[df['CNS'] != 'NAO_ENCONTRADO'].shape[0]
             recovered = after_count - before_count
             
             if recovered > 0:
                 print(f"  -> [{step_name}] Recuperados {recovered} via código")
             
             return recovered
         
         # Conta sucesso inicial (antes dos fallbacks)
         success_count = df_brutos['CNS'].ne('NAO_ENCONTRADO').sum()
         print(f"  -> Matching inicial: {success_count}/{len(df_brutos)} mapeados")
         
         # Fallback 1: Logo após matching principal
         apply_code_fallback_step(df_brutos, "Fallback 1")
         
         # Fallback 2: Após fallback por código inicial
         apply_code_fallback_step(df_brutos, "Fallback 2")
         
         
         # Passo Avançado: Matching por Atribuições Únicas
         # Para NAO_ENCONTRADO restantes, tenta match por combinação única de atribuições
         print("  -> Aplicando matching por atribuições únicas...")
         
         nao_encontrados = df_brutos[df_brutos['CNS'] == 'NAO_ENCONTRADO'].copy()
         
         if len(nao_encontrados) > 0 and 'cidade' in df_brutos.columns:
             # IMPORTANTE: Filtra CNS já usados (mapeados anteriormente)
             cns_ja_usados = set(df_brutos[df_brutos['CNS'] != 'NAO_ENCONTRADO']['CNS'].unique())
             print(f"  -> CNS já mapeados: {len(cns_ja_usados)}")
             
             # Para cada NAO_ENCONTRADO, identifica suas atribuições (colunas com receita > 0)
             cols_receita = ['RCPJ', 'RCPN', 'RI', 'RTD', 'Notas', 'Protesto']
             
             for idx, row in nao_encontrados.iterrows():
                 cidade = row['cidade']
                 
                 # Identifica atribuições do registro TJRJ
                 atribs_tjrj = set()
                 for col in cols_receita:
                     if col in row.index:
                         val = pd.to_numeric(row[col], errors='coerce')
                         if pd.notna(val) and val > 0:
                             atribs_tjrj.add(col)
                 
                 if not atribs_tjrj:
                     continue  # Sem atribuições identificadas
                 
                 # Busca no CNJ cartórios da mesma cidade com as mesmas atribuições
                 # MAS APENAS OS QUE AINDA NÃO FORAM USADOS
                 candidatos_cnj = []
                 for _, cnj_row in df_serventias[df_serventias[col_municipio].str.upper().str.strip() == cidade.upper().strip()].iterrows():
                     cns_cand = str(cnj_row[col_cns]).strip()
                     
                     # FILTRO CRÍTICO: Ignora CNS já mapeados
                     if cns_cand in cns_ja_usados:
                         continue
                     
                     atribs_cnj_str = str(cnj_row[col_atribuicao]).upper()
                     
                     # Verifica se todas as atribuições do TJRJ estão no CNJ
                     match_count = 0
                     for atrib in atribs_tjrj:
                         termos_busca = [atrib]
                         if atrib == 'Notas': termos_busca += ['TABELIE', 'NOTAS']
                         if atrib == 'RI': termos_busca += ['REGISTRO DE IMOVEIS', 'IMOVEIS']
                         if atrib == 'RCPN': termos_busca += ['CIVIL DAS PESSOAS NATURAIS', 'PESSOAS NATURAIS']
                         if atrib == 'RCPJ': termos_busca += ['CIVIL DAS PESSOAS JURIDICAS', 'PESSOAS JURIDICAS']
                         if atrib == 'RTD': termos_busca += ['TITULOS E DOCUMENTOS']
                         if atrib == 'Protesto': termos_busca += ['PROTESTO']
                         
                         if any(termo in atribs_cnj_str for termo in termos_busca):
                             match_count += 1
                     
                     # Se todas as atribuições batem, é candidato
                     if match_count == len(atribs_tjrj):
                         candidatos_cnj.append(cns_cand)
                 
                 # Se há exatamente 1 candidato (único), atribui o CNS
                 if len(candidatos_cnj) == 1:
                     df_brutos.at[idx, 'CNS'] = candidatos_cnj[0]
         
         # Conta recuperados por atribuição
         recovered_attr = df_brutos[df_brutos['CNS'] != 'NAO_ENCONTRADO'].shape[0] - success_count
         if recovered_attr > 0:
             print(f"  -> Recuperados {recovered_attr} registros via atribuições únicas!")
         
         # Fallback 3: Após matching por atribuições
         apply_code_fallback_step(df_brutos, "Fallback 3")
         
         
         # Log Detalhado: NAO_ENCONTRADO com comparação CNJ
         nao_encontrados_final = df_brutos[df_brutos['CNS'] == 'NAO_ENCONTRADO']
         
         if len(nao_encontrados_final) > 0:
             print(f"\n  [LOG DETALHADO - NAO_ENCONTRADO: {len(nao_encontrados_final)} registros]")
             
             # Agrupa por cidade para log mais organizado
             cidades_nao_encontradas = nao_encontrados_final.groupby('cidade')
             
             for cidade, grupo in cidades_nao_encontradas:
                 print(f"\n  Cidade: {cidade}")
                 print(f"  -> TJRJ não mapeados: {len(grupo)}")
                 
                 # Mostra os registros TJRJ não encontrados
                 for idx, row in grupo.head(3).iterrows():  # Limita a 3 por cidade
                     print(f"     * Cod {row.get('cod', 'N/A')}: {row['designacao']} - Gestor: {row.get('gestor', 'N/A')}")
                     
                     # Atribuições
                     atribs = []
                     for col in ['RCPJ', 'RCPN', 'RI', 'RTD', 'Notas', 'Protesto']:
                         if col in row.index:
                             val = pd.to_numeric(row[col], errors='coerce')
                             if pd.notna(val) and val > 0:
                                 atribs.append(col)
                     if atribs:
                         print(f"       Atrib: {', '.join(atribs)}")
                 
                 if len(grupo) > 3:
                     print(f"     ... e mais {len(grupo) - 3} registros")
                 
                 # Mostra cartórios CNJ disponíveis na mesma cidade
                 cnj_cidade = df_serventias[df_serventias[col_municipio].str.upper().str.strip() == cidade.upper().strip()]
                 cns_ja_usados = set(df_brutos[df_brutos['CNS'] != 'NAO_ENCONTRADO']['CNS'].unique())
                 cnj_disponiveis = cnj_cidade[~cnj_cidade[col_cns].isin(cns_ja_usados)]
                 
                 print(f"  -> CNJ disponíveis (não mapeados): {len(cnj_disponiveis)}")
                 for idx, cnj_row in cnj_disponiveis.head(3).iterrows():
                     print(f"     * CNS {cnj_row[col_cns]}: {cnj_row[col_nome]}")
                     print(f"       Atrib: {cnj_row[col_atribuicao]}")
                     print(f"       Resp: {cnj_row[col_gestor]}")
                 
                 if len(cnj_disponiveis) > 3:
                     print(f"     ... e mais {len(cnj_disponiveis) - 3} cartórios")
         
         # Estatísticas Finais: Comparação CNJ vs TJRJ
         print("\n  [ESTATÍSTICAS CNJ vs TJRJ]")
         
         # Total de cartórios ativos no CNJ (RJ)
         cnj_rj_ativos = df_serventias[
             (df_serventias[col_municipio].str.contains('RIO DE JANEIRO|NITER', case=False, na=False)) |
             (df_serventias['UF'] == 'RJ')
         ]
         total_cnj_rj = len(cnj_rj_ativos)
         
         # Total de cartórios únicos com receita no TJRJ
         if 'cod' in df_brutos.columns:
             total_tjrj_unicos = df_brutos['cod'].nunique()
         else:
             total_tjrj_unicos = len(df_brutos.groupby(['cidade', 'designacao']))
         
         # Cartórios mapeados com sucesso
         cns_mapeados_unicos = df_brutos[df_brutos['CNS'] != 'NAO_ENCONTRADO']['CNS'].nunique()
         
         print(f"  -> Cartórios ativos CNJ (RJ): {total_cnj_rj}")
         print(f"  -> Cartórios com receita TJRJ: {total_tjrj_unicos}")
         print(f"  -> CNS mapeados (distintos): {cns_mapeados_unicos}")
         print(f"  -> Cobertura: {(cns_mapeados_unicos/total_tjrj_unicos*100):.1f}%")
         
         success_count = df_brutos['CNS'].ne('NAO_ENCONTRADO').sum()
         print(f"\n  -> Enriquecimento concluído: {success_count}/{len(df_brutos)} mapeados.")
         return df_brutos

    except Exception as e:
        print(f"[ERRO ENRIQUECIMENTO] {e}")
        import traceback
        traceback.print_exc()
        return df_brutos

if __name__ == "__main__":
    # Esta seção é apenas para teste local no ambiente Python puro
    # Em produção, o Google Cloud Functions chamará a função cloud_main(request)
    cloud_main(None)
