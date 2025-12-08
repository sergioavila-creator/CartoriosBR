import pdfplumber
import pandas as pd
import re
import os
import time
import datetime
from unicodedata import normalize

# --- CONFIGURACOES GERAIS ---
# O script agora procura os PDFs dentro da subpasta "pdfs".
PASTA_PDFS = "pdfs" 
ARQUIVO_SAIDA = "Relatorio_Cartorios_V71_Final.xlsx"

# --- COLUNAS DO RELATORIO ---
COLUNAS_BRUTAS = [
    'cod', 'cidade', 'designacao', 'arquivo_origem', 'mes', 'ano',
    'RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 
    'Emolumentos', 'Funarpem', 'Gratuitos', 'Total',
    'gestor', 'cargo'
]

COLS_NUMERICAS = ['RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 
                  'Emolumentos', 'Funarpem', 'Gratuitos', 'Total']

# Lista de Municipios (100% ASCII - SEM ACENTOS)
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

# --- FUNCOES DE EXTRACAO E ANALISE ---

def normalizar_para_match(texto):
    """Remove acentos e converte para maiúsculas para comparação."""
    if not texto: return ""
    return normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').upper().strip()

def extrair_valores(linha):
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

def separar_cidade_designacao(texto_completo):
    """Separa o nome do município da designação do cartório."""
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

def processar_pdfs():
    """Função principal que processa os PDFs e gera as planilhas de análise."""
    inicio_total = time.time()

    print("#" * 70)
    print("   Sistema CartoriosRJ - Microsserviço de Análise (V71.0)")
    print("   Desenvolvido por: Sergio Avila")
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

        # ----------------------------------------------------
        # ANALISE 12 MESES (Média por Cartório)
        # ----------------------------------------------------
        df_analise = df_brutos.groupby(['cod', 'cidade', 'designacao'], as_index=False).agg({
            'RCPJ': 'mean', 'RCPN': 'mean', 'IT': 'mean', 'RI': 'mean', 'RTD': 'mean', 
            'Notas': 'mean', 'Protesto': 'mean', 'Emolumentos': 'mean', 'Funarpem': 'mean', 
            'Gratuitos': 'mean', 'Total': 'mean', 'gestor': 'last', 'cargo': 'last'
        })
        
        # ----------------------------------------------------
        # DISTRITOS (Filtro)
        # ----------------------------------------------------
        df_distritos = df_analise[df_analise['designacao'].apply(eh_distrito_valido)].copy()
        
        # ----------------------------------------------------
        # ANALISE POR CIDADE
        # ----------------------------------------------------
        
        # Média Mensal Total (Soma das médias dos cartórios)
        df_cidades_media = df_analise.groupby('cidade', as_index=False)['Total'].sum()
        df_cidades_media.rename(columns={'Total': 'Media Mensal Total (R$)'}, inplace=True)

        # Faturamento Acumulado Bruto (Soma de todos os registros brutos)
        df_cidades_acum = df_brutos.groupby('cidade', as_index=False)['Total'].sum()
        df_cidades_acum.rename(columns={'Total': 'Faturamento Acumulado Bruto (R$)'}, inplace=True)
        
        # Contagem de Serviços Únicos e Registros
        df_cidades_cont = df_analise.groupby('cidade').size().reset_index(name='Numero de Servicos Unicos')
        df_cidades_reg = df_brutos.groupby('cidade').size().reset_index(name='Total de Registros Mensais')

        # Merge final
        df_cidades = pd.merge(df_cidades_media, df_cidades_acum, on='cidade', how='left')
        df_cidades = pd.merge(df_cidades, df_cidades_cont, on='cidade', how='left')
        df_cidades = pd.merge(df_cidades, df_cidades_reg, on='cidade', how='left')
        df_cidades.sort_values(by='Media Mensal Total (R$)', ascending=False, inplace=True)
        
        # ----------------------------------------------------
        # GERAÇÃO DO ARQUIVO FINAL
        # ----------------------------------------------------
        
        # Salva em um arquivo Excel com múltiplas abas
        with pd.ExcelWriter(ARQUIVO_SAIDA, engine='openpyxl') as writer:
            df_brutos.to_excel(writer, index=False, sheet_name='Dados Brutos')
            df_analise.to_excel(writer, index=False, sheet_name='Analise 12 Meses')
            df_distritos.to_excel(writer, index=False, sheet_name='Distritos')
            df_cidades.to_excel(writer, index=False, sheet_name='Cidades') 
            
            # Ajusta a largura das colunas
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

        # Finaliza o timer
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

if __name__ == "__main__":
    processar_pdfs()