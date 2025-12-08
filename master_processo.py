#!/usr/bin/env python3
# master_processo.py — Orquestrador que integra Baixador v3 (com log) + Extrator v71
# Gerado a partir dos seus scripts: mantenho prints do extrator idênticos.

import os
import re
import time
import datetime
import requests
from urllib.parse import urljoin, urlparse
from datetime import date
from unicodedata import normalize

import pdfplumber
import pandas as pd

# ============================================================
# CONFIGURAÇÕES GLOBAIS (unificadas)
# ============================================================
OUTDIR = "pdfs"                      # pasta onde os PDFs serão salvos (usada por ambos)
LOGFILE_BAIXADOR = "log_baixador.log"  # log do baixador
ARQUIVO_SAIDA = "Relatorio_Cartorios_V71_Final.xlsx"  # arquivo gerado pelo extrator

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

# ============================================================
# ===================     BAIXADOR v3     =====================
# ============================================================

def log_error_baixador(msg: str):
    """Registra erro silenciosamente no log do baixador."""
    try:
        with open(LOGFILE_BAIXADOR, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except:
        pass

def safe_get(url):
    """Baixa HTML sem exibir erros no console (requests)."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log_error_baixador(f"[ERRO HTML] {url} — {e}")
        return ""

def extract_pdf_links(html, base=ROOT):
    """Extrator robusto — busca href= em HTML quebrado."""
    if not html:
        return []

    found = []
    seen = set()
    regex = re.compile(r'href\s*=\s*(["\']?)(?P<u>[^"\' >]+)', re.I)

    for m in regex.finditer(html):
        raw = m.group("u")
        if PDF_SUBSTR not in raw.lower():
            continue

        if raw.startswith("//"):
            url = "https:" + raw
        elif raw.startswith("/"):
            url = urljoin(base, raw)
        else:
            url = raw

        p = urlparse(url)
        clean = p.scheme + "://" + p.netloc + p.path
        if p.query:
            clean += "?" + p.query

        if clean not in seen:
            seen.add(clean)
            found.append(clean)

    return found

def extrair_mes_ano(url):
    nome = os.path.basename(url).lower()
    mes = None
    for nome_mes, numero in MESES.items():
        if nome_mes in nome:
            mes = numero
            break
    ano_m = re.search(r"20\d{2}", nome)
    ano = int(ano_m.group()) if ano_m else None
    return (mes, ano) if mes and ano else (None, None)

def download_stream(url, dest):
    """Download robusto com retries — erros só no log."""
    for attempt in range(1, RETRIES + 1):
        try:
            with requests.Session() as s:
                r = s.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    stream=True,
                    timeout=(TIMEOUT_CONNECT, TIMEOUT_READ)
                )
                r.raise_for_status()

                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            if os.path.getsize(dest) < MIN_PDF_BYTES:
                raise Exception("Arquivo muito pequeno")

            with open(dest, "rb") as f:
                if b"%PDF" not in f.read(10):
                    raise Exception("Assinatura PDF inválida")

            print(f"[OK] {os.path.basename(dest)}")
            return True

        except Exception as e:
            log_error_baixador(f"[DOWNLOAD ERRO {attempt}/{RETRIES}] {url} — {e}")
            time.sleep(1 + attempt * 2)

    log_error_baixador(f"[FALHA] {url}")
    return False

def microsservico_download():
    """Executa o processo de varredura + download (até 12 arquivos mais recentes)."""
    print("\n" + "="*70)
    print("INICIANDO: Microsserviço de Download (Coleta de PDFs)")
    print("="*70)

    os.makedirs(OUTDIR, exist_ok=True)
    print(f"[PASTA OK] Diretório '{OUTDIR}' verificado/criado.")

    # Página principal
    print("Carregando página principal...")
    html_main = safe_get(BASE_PAGE)
    if not html_main:
        print("[AVISO] Falha ao carregar a página principal. Verifique o log.")
        return 0
    links_main = extract_pdf_links(html_main)
    print(f"→ {len(links_main)} links encontrados na principal.")

    # Página ano anterior
    ano_ant = date.today().year - 1
    page_prev = f"{BASE_PAGE}/{ano_ant}"
    print(f"Carregando {ano_ant}...")
    html_prev = safe_get(page_prev)
    links_prev = []
    if html_prev:
        links_prev = extract_pdf_links(html_prev)
        print(f"→ {len(links_prev)} links encontrados em {ano_ant}.")
    else:
        print(f"[AVISO] Falha ao carregar a página de {ano_ant}. Continuando com o que foi encontrado.")

    # Combine e dedupe
    combined = []
    seen = set()
    for u in links_main + links_prev:
        if u not in seen:
            seen.add(u)
            combined.append(u)

    print(f"Total bruto de links: {len(combined)}")

    if not combined:
        return 0

    # Ordena por ano/mes quando possível
    def key(u):
        mes, ano = extrair_mes_ano(u)
        return ano * 100 + mes if mes and ano else 0

    combined.sort(key=key, reverse=True)

    print("\nBaixando até 12 arquivos (mais recentes)...\n")
    baixados_contador = 0
    meses_baixados = set()

    for url in combined:
        if baixados_contador >= 12:
            break

        mes, ano = extrair_mes_ano(url)
        if not mes or not ano:
            # opcional: ignorar links que não contêm mês/ano detectáveis
            continue

        chave = (ano, mes)
        if chave in meses_baixados:
            continue

        nome_arquivo_local = f"{ano} {mes:02d}.pdf"
        caminho_local = os.path.join(OUTDIR, nome_arquivo_local)

        if os.path.exists(caminho_local):
            print(f"[JA EXISTE] {nome_arquivo_local}")
            meses_baixados.add(chave)
            baixados_contador += 1
            continue

        print(f"[Baixando] {nome_arquivo_local}...", end=" ", flush=True)
        if download_stream(url, caminho_local):
            print("Sucesso.")
            meses_baixados.add(chave)
            baixados_contador += 1
        else:
            print("Falha.")

    if baixados_contador > 0:
        print(f"\n[DOWNLOAD CONCLUÍDO] Total de arquivos prontos para análise: {baixados_contador}")
    else:
        print("\n[AVISO] Nenhum arquivo baixado ou encontrado. Verifique a conexão ou logs.")

    print("="*70)
    return baixados_contador

# ============================================================
# ===================     EXTRATOR v71     =====================
# ============================================================
# NOTE: Mantive o código do extrator exatamente como você enviou,
# apenas garanti que ele use OUTDIR como PASTA_PDFS.

PASTA_PDFS = OUTDIR
ARQUIVO_SAIDA = ARQUIVO_SAIDA

COLUNAS_BRUTAS = [
    'cod', 'cidade', 'designacao', 'arquivo_origem', 'mes', 'ano',
    'RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 
    'Emolumentos', 'Funarpem', 'Gratuitos', 'Total',
    'gestor', 'cargo'
]

COLS_NUMERICAS = ['RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 
                  'Emolumentos', 'Funarpem', 'Gratuitos', 'Total']

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

def normalizar_para_match(texto):
    if not texto: return ""
    return normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

def extrair_valores(linha):
    valores_str = re.findall(r'[\d\.]+\,\d{2}', linha)
    valores_float = []
    for v in valores_str:
        v_limpo = v.replace('.', '').replace(',', '.')
        try:
            valores_float.append(float(v_limpo))
        except ValueError:
            pass
    return valores_float

def separar_cidade_designacao(texto_completo):
    if not texto_completo: return "", ""
    texto_norm = normalizar_para_match(texto_completo)
    municipios_ordenados = sorted(MUNICIPIOS_RJ, key=len, reverse=True)
    
    for municipio in municipios_ordenados:
        if texto_norm.startswith(municipio):
            designacao = texto_norm[len(municipio):].strip()
            if designacao.startswith("-"): designacao = designacao[1:].strip()
            return municipio, designacao
    return "OUTRA/VERIFICAR", texto_completo

def eh_distrito_valido(designacao):
    if not isinstance(designacao, str): return False
    texto = designacao.upper()
    if "DISTR" not in texto: return False
    match = re.search(r'(\d+).*?DISTR', texto)
    if match:
        try:
            return int(match.group(1)) >= 2
        except: return False
    return False

def processar_pdfs():
    """Função principal que processa os PDFs e gera as planilhas de análise."""
    inicio_total = time.time()

    print("#" * 70)
    print("   Sistema CartoriosRJ - Microsserviço de Análise (V71.0)")
    print("   Desenvolvido por: Sergio Ávila")
    print(f"   Data: {datetime.date.today().strftime('%d/%m/%Y')}")
    print("#" * 70 + "\n")

    # Garante que a pasta existe antes de tentar listar arquivos
    if not os.path.exists(PASTA_PDFS):
        print(f"[ERRO] A subpasta de PDFs '{PASTA_PDFS}' não foi encontrada.")
        print("Verifique se o seu script de download ('baixador.py') foi executado e criou a pasta.")
        input("Pressione ENTER para sair...")
        return
    
    dados_consolidados = []
    # Busca arquivos que se parecem com "YYYY MM.pdf" (Ex: 2025 10.pdf) dentro da subpasta
    arquivos_pdf = [f for f in os.listdir(PASTA_PDFS) if re.match(r'^\d{4}\s\d{2}\.pdf$', f.lower())]
    arquivos_pdf.sort(reverse=True) # Processa do mais recente para o mais antigo
    
    print("="*60)
    print(f"PROCESSANDO {len(arquivos_pdf)} ARQUIVOS ENCONTRADOS EM '{PASTA_PDFS}'...")
    print("="*60)

    for nome_arquivo in arquivos_pdf:
        caminho_completo = os.path.join(PASTA_PDFS, nome_arquivo) # Junta o nome da pasta com o nome do arquivo
        linhas_arquivo_atual = 0 
        
        # Extrai mês e ano do nome do arquivo (Ex: '2025 10.pdf' -> mes='10', ano='2025')
        match_data_arquivo = re.search(r'(\d{4})\s(\d{2})', nome_arquivo)
        if match_data_arquivo:
            ano_arquivo, mes_arquivo = match_data_arquivo.groups()
        else:
            ano_arquivo, mes_arquivo = "N/A", "N/A"
        
        try:
            with pdfplumber.open(caminho_completo) as pdf:
                # O mês/ano do arquivo será usado como fallback, mas tentamos extrair do PDF
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
                    
                    # Limpeza de texto para facilitar a extração
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
                                mes_atual, ano_atual = match_data.groups()

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
                                
                            cidade, designacao = separar_cidade_designacao(nome_full)

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
                                        dados_servico_atual['cargo'] = split_cond[1].strip()
                                else:
                                    dados_servico_atual['gestor'] = conteudo
                            except: pass

                        # Extração da Condição (Cargo)
                        if lendo_servico and re.search(r'^Condi..o do Gestor:', linha_limpa):
                            try:
                                partes = linha_limpa.split(":", 1)
                                dados_servico_atual['cargo'] = partes[1].strip()
                            except: pass

                        # Extração dos valores por atribuição
                        if lendo_servico:
                            for key_regex, nome_coluna in mapa_regex.items():
                                if re.search(key_regex, linha_limpa, re.IGNORECASE):
                                    valores = extrair_valores(linha_limpa)
                                    if valores:
                                        # O valor total do emolumento fica no final da linha
                                        dados_servico_atual[nome_coluna] = valores[-1]
                                    break
                        
                        # Fim de um serviço (Total Geral)
                        if lendo_servico and "Total Geral" in linha_limpa:
                            valores = extrair_valores(linha_limpa)
                            if len(valores) >= 1:
                                # O último valor é o Total Final
                                dados_servico_atual['Total'] = valores[-1]
                                
                                # Tentativa de capturar Emolumentos Totais, Funarpem e Gratuitos
                                if len(valores) >= 4:
                                    dados_servico_atual['Emolumentos'] = valores[-4] # Emolumentos antes do Funarpem/Reembolso
                                    dados_servico_atual['Funarpem'] = valores[-3]
                                    dados_servico_atual['Gratuitos'] = valores[-2]
                                    
                                dados_consolidados.append(dados_servico_atual.copy())
                                linhas_arquivo_atual += 1
                                lendo_servico = False
                                dados_servico_atual = {}

            status = f"OK ({linhas_arquivo_atual} linhas)" if linhas_arquivo_atual > 0 else "ZERO DADOS"
            print(f"[{status}] -> {nome_arquivo}")

        except Exception as e:
            print(f"[ERRO] Falha ao processar {nome_arquivo}: {e}")

    print("="*60)
    print("GERANDO PLANILHAS FINAIS...")
    print("="*60)

    if dados_consolidados:
        df_brutos = pd.DataFrame(dados_consolidados)
        df_brutos = df_brutos.reindex(columns=COLUNAS_BRUTAS)
        
        # Converte colunas numéricas
        for col in COLS_NUMERICAS:
            if col in df_brutos.columns:
                df_brutos[col] = pd.to_numeric(df_brutos[col], errors='coerce')

        # Limpeza e ordenação dos dados brutos
        df_brutos.drop_duplicates(subset=['cod', 'cidade', 'designacao', 'arquivo_origem', 'mes', 'ano', 'Total'], keep='first', inplace=True)
        print(f"Total de linhas consolidadas: {len(df_brutos)}")

        df_brutos.sort_values(by=['cidade', 'designacao', 'ano', 'mes'], inplace=True)

        # ANALISE 12 MESES (Média por Cartório)
        df_analise = df_brutos.groupby(['cod', 'cidade', 'designacao'], as_index=False).agg({
            'RCPJ': 'mean', 'RCPN': 'mean', 'IT': 'mean', 'RI': 'mean', 'RTD': 'mean', 
            'Notas': 'mean', 'Protesto': 'mean', 'Emolumentos': 'mean', 'Funarpem': 'mean', 
            'Gratuitos': 'mean', 'Total': 'mean', 'gestor': 'last', 'cargo': 'last'
        })
        
        # DISTRITOS (Filtro)
        df_distritos = df_analise[df_analise['designacao'].apply(eh_distrito_valido)].copy()
        
        # ANALISE POR CIDADE
        df_cidades_media = df_analise.groupby('cidade', as_index=False)['Total'].sum()
        df_cidades_media.rename(columns={'Total': 'Media Mensal Total (R$)'}, inplace=True)

        df_cidades_acum = df_brutos.groupby('cidade', as_index=False)['Total'].sum()
        df_cidades_acum.rename(columns={'Total': 'Faturamento Acumulado Bruto (R$)'}, inplace=True)
        
        df_cidades_cont = df_analise.groupby('cidade').size().reset_index(name='Numero de Servicos Unicos')
        df_cidades_reg = df_brutos.groupby('cidade').size().reset_index(name='Total de Registros Mensais')

        df_cidades = pd.merge(df_cidades_media, df_cidades_acum, on='cidade', how='left')
        df_cidades = pd.merge(df_cidades, df_cidades_cont, on='cidade', how='left')
        df_cidades = pd.merge(df_cidades, df_cidades_reg, on='cidade', how='left')
        df_cidades.sort_values(by='Media Mensal Total (R$)', ascending=False, inplace=True)
        
        # GERAÇÃO DO ARQUIVO FINAL
        with pd.ExcelWriter(ARQUIVO_SAIDA, engine='openpyxl') as writer:
            df_brutos.to_excel(writer, index=False, sheet_name='Dados Brutos')
            df_analise.to_excel(writer, index=False, sheet_name='Analise 12 Meses')
            df_distritos.to_excel(writer, index=False, sheet_name='Distritos')
            df_cidades.to_excel(writer, index=False, sheet_name='Cidades') 
            
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    col_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value:
                                val_len = len(str(cell.value))
                                if val_len > max_length: max_length = val_len
                        except: pass
                    width = min(max_length + 2, 60)
                    worksheet.column_dimensions[col_letter].width = width

        fim_total = time.time()
        tempo_total = fim_total - inicio_total
        mins, segs = divmod(tempo_total, 60)

        print(f"\nSUCESSO! Arquivo gerado: {ARQUIVO_SAIDA}")
        print(f"Tempo total de execucao: {int(mins)}m {int(segs)}s")
        input("Pressione ENTER para sair...")
    else:
        fim_total = time.time()
        tempo_total = fim_total - inicio_total
        mins, segs = divmod(tempo_total, 60)
        
        print(f"Nenhum dado extraido. Verifique se os PDFs estão na subpasta '{PASTA_PDFS}'.")
        print(f"Tempo total de execucao: {int(mins)}m {int(segs)}s")
        input("Pressione ENTER para sair...")

# ============================================================
# ======================   ORQUESTRADOR   =====================
# ============================================================

def main():
    inicio_total = time.time()
    
    print("#" * 70)
    print("      Sistema CartoriosRJ - Orquestrador Microsserviços")
    print(f"     Sergio Ávila - Versão: 77.0 (Bundle integrado)")
    print(f"     em: {datetime.date.today().strftime('%d/%m/%Y')}")
    print("#" * 70)
    
    total_baixados = microsservico_download()
    
    if total_baixados > 0:
        # chama o extrator (mantém todos os prints do extrator original)
        processar_pdfs()
    else:
        print("\n[PROCESSO INTERROMPIDO] Download falhou ou não encontrou novos PDFs. Análise ignorada.")
    
    fim_total = time.time()
    tempo_total = fim_total - inicio_total
    mins, segs = divmod(tempo_total, 60)
    
    print("\n" + "#"*70)
    print(f"PROCESSO CONCLUÍDO. Tempo total da aplicação: {int(mins)}m {int(segs)}s")
    print("#"*70)
    input("Pressione ENTER para sair...")

if __name__ == "__main__":
    main()
