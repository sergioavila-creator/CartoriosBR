import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import subprocess
import sys
import time

# Configuração da página
st.set_page_config(page_title="Justiça Aberta CNJ", page_icon="⚖️", layout="wide")

# Constantes
NEW_SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Administração")
    
    # Botão Abrir Planilha
    st.markdown(f"""
        <a href="https://docs.google.com/spreadsheets/d/{NEW_SHEET_ID}" target="_blank" style="text-decoration: none;">
            <button style="
                width: 100%;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;">
                📊 Abrir Planilha
            </button>
        </a>
    
        """, unsafe_allow_html=True)
        
    st.write("")
    
    # Função Helper para Executar Script
    def run_script_action(action_key, display_name):
        log_key = f'log_{action_key}'
        st.session_state[log_key] = [] 
        
        st.toast(f"🚀 Iniciando: {display_name}...")
        
        # Container para logs persistentes
        log_expander = st.sidebar.expander(f"📜 Log: {display_name}", expanded=True)
        log_container = log_expander.empty()
        
        def update_log(msg):
            if log_key not in st.session_state:
                st.session_state[log_key] = []
            st.session_state[log_key].append(msg)
            # Acumula logs
            full_log = "\n".join(st.session_state[log_key])
            log_container.text_area("Log de Execução", value=full_log, height=300)
            
        try:
            update_log(f"--- Iniciando {display_name} ---")
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["HEADLESS"] = "false"
            
            cmd = [sys.executable, "extrair_cnj_analytics.py", "--action", action_key]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8', # Force UTF-8 decoding
                bufsize=1,
                env=env
            )
            
            for line in process.stdout:
                update_log(line.strip())
            
            process.wait()
            
            # Botão de Download do Log Completo
            full_log_final = "\n".join(st.session_state[log_key])
            st.sidebar.download_button(
                label=f"📥 Baixar Log ({display_name})",
                data=full_log_final,
                file_name=f"log_{action_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            
            if process.returncode == 0:
                update_log("✅ Concluído!")
                st.success(f"{display_name} realizado com sucesso!")
                
                # Se for processamento, limpa cache e recarrega
                if action_key == "process":
                    st.cache_data.clear() 
                    time.sleep(2)
                    st.rerun()
            else:
                update_log("❌ Falha na execução")
                st.error("Ocorreu um erro durante a execução.")
        except Exception as e:
            update_log(f"❌ Erro crítico: {str(e)}")
            st.error(f"Erro ao executar script: {str(e)}")

    # Botões de Ação Separados
    col_a, col_b = st.columns(2)
    
    with col_a:
        if st.button("⬇️ 1. Baixar Dados (CNJ)", use_container_width=True, help="Apenas baixa os arquivos do site do CNJ"):
            run_script_action("download", "Download de Dados")
            
    with col_b:
        if st.button("⚙️ 2. Processar e Enviar", use_container_width=True, help="Lê os arquivos baixados, ajusta e envia para a planilha"):
            run_script_action("process", "Processamento e Envio")
            
    # Display Persistent Logs (Mostra todos os logs disponíveis)
    for key, title in [('log_download', 'Download'), ('log_process', 'Processamento')]:
        if key in st.session_state and st.session_state[key]:
            with st.sidebar.expander(f"📜 Log Anterior ({title})", expanded=False):
                st.code("\n".join(st.session_state[key]), language="text")
    
    st.divider()
    
    # Upload Manual de Lista de Serventias
    st.markdown("### 📤 Upload Manual - Lista de Serventias")
    st.caption("Baixe manualmente do Qlik e faça upload aqui")
    
    uploaded_file = st.file_uploader(
        "Selecione o arquivo CSV",
        type=['csv'],
        key="upload_serventias",
        help="Baixe a planilha 'Lista de Serventias' do Qlik Sense e faça upload aqui"
    )
    
    if uploaded_file is not None:
        if st.button("📊 Processar e Enviar", use_container_width=True, type="primary"):
            try:
                with st.spinner("Processando arquivo..."):
                    # Lê o CSV
                    try:
                        df = pd.read_csv(uploaded_file, encoding='utf-8', sep=';')
                    except:
                        df = pd.read_csv(uploaded_file, encoding='latin1', sep=';')
                    
                    if 'CNS' in df.columns:
                        try:
                            # Adiciona o diretório raiz ao path (parent do pages/)
                            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            if root_dir not in sys.path:
                                sys.path.insert(0, root_dir)
                            from cns_utils import normalize_cns_column
                            df = normalize_cns_column(df, 'CNS')
                            st.success("✅ CNS normalizado para 6 dígitos")
                        except Exception as e:
                            st.warning(f"⚠️ Não foi possível normalizar CNS: {e}")
                    
                    # Conecta ao Google Sheets
                    with st.spinner("Conectando ao Google Sheets..."):
                        import toml
                        secrets = toml.load(".streamlit/secrets.toml")
                        creds_dict = secrets["gcp_service_account"]
                        gc = gspread.service_account_from_dict(creds_dict)
                        sh = gc.open_by_key(NEW_SHEET_ID)
                    
                    # Atualiza aba
                    with st.spinner("Enviando dados para 'Lista de Serventias'..."):
                        try:
                            ws = sh.worksheet('Lista de Serventias')
                            ws.clear()
                        except:
                            ws = sh.add_worksheet(title='Lista de Serventias', rows=len(df)+100, cols=len(df.columns)+5)
                        
                        # Upload
                        data_to_write = [df.columns.values.tolist()] + df.values.tolist()
                        ws.update(data_to_write, value_input_option='USER_ENTERED')
                        
                        # Formatação
                        ws.freeze(rows=1)
                        try:
                            ws.set_basic_filter(1, 1, len(df)+1, len(df.columns))
                        except:
                            pass
                    
                    st.success(f"✅ Upload concluído! {len(df)} linhas enviadas para 'Lista de Serventias'")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")
                st.exception(e)

# ============================================================================
# FUNÇÕES
# ============================================================================

@st.cache_data(ttl=1800)  # Cache 30min
def carregar_dados():
    """Carrega dados: Tenta Supabase primeiro, faz fallback para Google Sheets"""
    
    # 1. Tenta carregar do Supabase (Mais rápido)
    try:
        from supabase_config import get_supabase_client
        supabase = get_supabase_client()
        
        # Se Supabase não está configurado, pula para Google Sheets
        if supabase is None:
            print("ℹ️ Supabase não configurado, usando Google Sheets")
            raise Exception("Supabase não configurado")
        
        # Query: seleciona colunas
        # Limitando a 500k registros (seu dataset é ~470k)
        response = supabase.table('arrecadacao').select('*').limit(500000).execute()
        data = response.data
        
        if data:
            df = pd.DataFrame(data)
            
            # Ajuste de nomes de colunas (Supabase snake_case -> Dashboard Original)
            clean_map = {
                'valor_arrecadacao': 'Valor arrecadação',
                'valor_custeio': 'Valor custeio',
                'valor_repasse': 'Valor repasse',
                'quantidade_atos': 'Quantidade de atos praticados',
                'dat_inicio_periodo': 'Dat. inicio periodo',
                'dat_final_periodo': 'Dat. final periodo',
                'estado': 'Estado',
                'municipio': 'Município',
                'delegatario': 'Delegatário',
                'liquido': 'Líquido',
                'indice_eficiencia': 'Indice_Eficiencia',
                'indice_repasses': 'Indice_Repasses',
                'atribuicao': 'Atribuição',
                'cns': 'CNS'
            }
            # Renomeia se existir
            df.rename(columns=clean_map, inplace=True)
            
            # Garante tipos numéricos
            num_cols = ['Valor arrecadação', 'Valor custeio', 'Valor repasse', 'Delegatário', 'Líquido']
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            print(f"✅ Dados carregados do Supabase: {len(df)} registros")
            return df
            
    except Exception as e:
        print(f"ℹ️ Usando Google Sheets (Supabase: {e})")
        # Fallback silencioso - mensagens de UI não podem estar em funções cacheadas

    # 2. Fallback: Google Sheets (Lento)
    try:
        import toml
        # Tenta carregar credenciais
        if os.path.exists(".streamlit/secrets.toml"):
             secrets = toml.load(".streamlit/secrets.toml")
             creds_dict = secrets["gcp_service_account"]
        else:
             # Tenta via env var se não tiver toml
             import json
             creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
             
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_key(NEW_SHEET_ID)
        
        # Tenta abas agregadas primeiro (Agregado_Total não serve para analise detalhada, mas ok)
        # Na verdade, precisamos da base cheia para os filtros. 
        # Vamos tentar 'Arrecadacao' direto.
        try:
            ws = sh.worksheet("Arrecadacao")
        except:
            time.sleep(1)
            ws = sh.worksheet("Arrecadacao")
            
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"❌ Erro crítico ao carregar dados: {e}")
        return pd.DataFrame()

def processar_dados(df):
    """Processa dados: converte datas, calcula semestres e índices"""
    if df.empty:
        return df
    
    # Converte colunas numéricas e normaliza negativos para positivos
    numeric_cols = ['Quantidade de atos praticados', 'Valor arrecadação', 'Valor custeio', 'Valor repasse']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
            # Normaliza valores negativos para positivos (abs)
            df[col] = df[col].abs()
    
    # Processa data final período
    # Tenta encontrar a coluna de data (pode ter nomes diferentes)
    date_col_candidates = ['Dat. final periodo', 'Dat. final período', 'Data final periodo', 'Data final período']
    date_col = None
    for candidate in date_col_candidates:
        if candidate in df.columns:
            date_col = candidate
            break
    
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Cria coluna Semestre (formato: 1S2010, 2S2024)
        df['Semestre'] = df[date_col].apply(
            lambda x: f"{'1S' if x.month <= 6 else '2S'}{x.year}" if pd.notna(x) else None
        )
        
        df['Ano'] = df[date_col].dt.year
    else:
        # Se não encontrou coluna de data, cria coluna Semestre vazia
        st.warning("⚠️ Coluna de data não encontrada. Análise temporal desabilitada.")
        df['Semestre'] = 'Sem Data'
        df['Ano'] = None
    
    # Calcula índices (com proteção contra divisão por zero)
    if 'Valor arrecadação' in df.columns and 'Valor custeio' in df.columns:
        df['Índice Eficiência (%)'] = df.apply(
            lambda row: (row['Valor custeio'] / row['Valor arrecadação']) if row['Valor arrecadação'] > 0 else 0,
            axis=1
        ).round(4)
    
    if 'Valor arrecadação' in df.columns and 'Valor repasse' in df.columns:
        df['Índice Repasses (%)'] = df.apply(
            lambda row: (row['Valor repasse'] / row['Valor arrecadação']) if row['Valor arrecadação'] > 0 else 0,
            axis=1
        ).round(4)
    
    return df

# ============================================================================
# INTERFACE
# ============================================================================
st.title("⚖️ Justiça Aberta CNJ - Dashboard de Arrecadação")
st.markdown("Análise semestral de arrecadação, custeio e repasses das serventias extrajudiciais")

# Carrega e processa dados
df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado disponível. Clique em 'Atualizar Justiça Aberta' para carregar os dados.")
    st.stop()

# Debug: Mostra colunas disponíveis
with st.expander("🔍 Debug: Colunas Disponíveis", expanded=False):
    st.write(f"Total de colunas: {len(df.columns)}")
    st.write("Colunas:", list(df.columns))
    if not df.empty:
        st.write("Exemplo (primeira linha):", df.iloc[0].to_dict())

df = processar_dados(df)

# ============================================================================
# LAYOUT: Filtros à direita
# ============================================================================
col_main, col_filtros = st.columns([3, 1])

with col_filtros:
    st.markdown("### 🔍 Filtros")
    
    # Verifica se colunas geográficas existem e têm dados válidos
    tem_estado = 'Estado' in df.columns and df['Estado'].notna().any() and df['Estado'].str.strip().ne('').any()
    tem_municipio = 'Município' in df.columns and df['Município'].notna().any() and df['Município'].str.strip().ne('').any()
    
    if not tem_estado and not tem_municipio:
        st.info("📍 **Filtros geográficos indisponíveis**\n\nClique em '🔄 Atualizar Justiça Aberta' para carregar Estado e Município.")
        estados_selecionados = []
        municipios_selecionados = []
    else:
        # Filtro Estado
        if tem_estado:
            estados_disponiveis = sorted([e for e in df['Estado'].dropna().unique() if str(e).strip()])
            usar_todos_estados = st.checkbox("Todos os Estados", value=True, key="todos_estados")
            
            if usar_todos_estados:
                estados_selecionados = estados_disponiveis
                if estados_disponiveis:
                    st.caption(f"✓ {len(estados_disponiveis)} estados")
            else:
                estados_selecionados = st.multiselect(
                    "Estados",
                    options=estados_disponiveis,
                    default=[],
                    key="filtro_estados"
                )
        else:
            estados_selecionados = []
        
        # Filtro Município (dependente de Estado)
        if tem_municipio:
            if estados_selecionados:
                df_filtrado_estado = df[df['Estado'].isin(estados_selecionados)]
                municipios_disponiveis = sorted([m for m in df_filtrado_estado['Município'].dropna().unique() if str(m).strip()])
            else:
                municipios_disponiveis = sorted([m for m in df['Município'].dropna().unique() if str(m).strip()])
            
            usar_todos_municipios = st.checkbox("Todos os Municípios", value=True, key="todos_municipios")
            
            if usar_todos_municipios:
                municipios_selecionados = municipios_disponiveis
                if municipios_disponiveis:
                    st.caption(f"✓ {len(municipios_disponiveis)} municípios")
            else:
                municipios_selecionados = st.multiselect(
                    "Municípios",
                    options=municipios_disponiveis,
                    default=[],
                    key="filtro_municipios"
                )
        else:
            municipios_selecionados = []
        
        st.markdown("---")
        
        # Filtro Atribuição
        atribuicoes_selecionadas = []
        if 'Atribuição' in df.columns:
            atribuicoes_disponiveis = sorted([a for a in df['Atribuição'].dropna().unique() if str(a).strip()])
            if atribuicoes_disponiveis:
                usar_todas_atribuicoes = st.checkbox("Todas as Atribuições", value=True, key="todas_atribuicoes")
                
                if usar_todas_atribuicoes:
                    atribuicoes_selecionadas = atribuicoes_disponiveis
                    st.caption(f"✓ {len(atribuicoes_disponiveis)} atribuições")
                else:
                    atribuicoes_selecionadas = st.multiselect(
                        "Atribuições",
                        options=atribuicoes_disponiveis,
                        default=[],
                        key="filtro_atribuicoes"
                    )
        
        # Filtro CNS (busca por texto)
        cns_filtro = st.text_input("🔍 Filtrar por CNS", placeholder="Digite o CNS...", key="filtro_cns")
    
    # Filtros adicionais (fora do bloco geográfico, sempre visíveis)
    if not tem_estado and not tem_municipio:
        st.markdown("---")
        
        # Filtro Atribuição
        atribuicoes_selecionadas = []
        if 'Atribuição' in df.columns:
            atribuicoes_disponiveis = sorted([a for a in df['Atribuição'].dropna().unique() if str(a).strip()])
            if atribuicoes_disponiveis:
                usar_todas_atribuicoes = st.checkbox("Todas as Atribuições", value=True, key="todas_atribuicoes")
                
                if usar_todas_atribuicoes:
                    atribuicoes_selecionadas = atribuicoes_disponiveis
                    st.caption(f"✓ {len(atribuicoes_disponiveis)} atribuições")
                else:
                    atribuicoes_selecionadas = st.multiselect(
                        "Atribuições",
                        options=atribuicoes_disponiveis,
                        default=[],
                        key="filtro_atribuicoes"
                    )
        
        # Filtro CNS (busca por texto)
        cns_filtro = st.text_input("🔍 Filtrar por CNS", placeholder="Digite o CNS...", key="filtro_cns")

# Aplica filtros
df_filtrado = df.copy()
if estados_selecionados and 'Estado' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['Estado'].isin(estados_selecionados)]
if municipios_selecionados and 'Município' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['Município'].isin(municipios_selecionados)]
if atribuicoes_selecionadas and 'Atribuição' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['Atribuição'].isin(atribuicoes_selecionadas)]
if cns_filtro and 'CNS' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['CNS'].astype(str).str.contains(cns_filtro, case=False, na=False)]

with col_main:
    # ============================================================================
    # MÉTRICAS PRINCIPAIS
    # ============================================================================
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    total_arrecadacao = df_filtrado['Valor arrecadação'].sum()
    total_custeio = df_filtrado['Valor custeio'].sum()
    total_repasses = df_filtrado['Valor repasse'].sum()
    
    # Calcula Delegatário total (se a coluna existir na planilha, senão calcula)
    if 'Delegatário' in df_filtrado.columns:
        # Converte para numérico (vem como string do Sheets)
        total_delegatario = pd.to_numeric(df_filtrado['Delegatário'], errors='coerce').sum()
    else:
        total_delegatario = total_arrecadacao - total_repasses
    
    # Calcula Líquido total
    total_liquido = total_delegatario - total_custeio
    
    # Índice de Eficiência GLOBAL: Total Custeio / Total Delegatário
    # (NÃO usar média das linhas, pois isso distorce por outliers)
    if total_delegatario > 0:
        media_eficiencia = total_custeio / total_delegatario
    else:
        media_eficiencia = 0
    
    # Índice de Repasses GLOBAL: Total Repasses / Total Arrecadação
    # (NÃO usar média das linhas, pois isso distorce por outliers)
    if total_arrecadacao > 0:
        media_repasses = total_repasses / total_arrecadacao
    else:
        media_repasses = 0
    
    # Formatação brasileira (vírgula como separador decimal)
    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def formatar_percentual(valor):
        # Valor vem como decimal (0.92 = 92%), então multiplica por 100
        return f"{(valor * 100):.2f}%".replace(".", ",")
    
    col1.metric("💰 Arrecadação Total", formatar_moeda(total_arrecadacao))
    col2.metric("💸 Custeio Total", formatar_moeda(total_custeio))
    col3.metric("📤 Repasses Total", formatar_moeda(total_repasses))
    col4.metric("🏦 Delegatário Total", formatar_moeda(total_delegatario))
    col5.metric("📊 Eficiência Média", formatar_percentual(media_eficiencia))
    col6.metric("📈 Repasses Médio", formatar_percentual(media_repasses))
    
    st.markdown("---")
    
    # ============================================================================
    # GRÁFICOS
    # ============================================================================
    
    # Prepara dados para gráficos semestrais
    # Não agrupa - cada linha já representa uma serventia em um semestre específico
    # Apenas ordena cronologicamente
    df_semestre = df_filtrado.copy()
    
    if 'Semestre' in df_semestre.columns and not df_semestre.empty:
        # Remove linhas sem semestre válido
        df_semestre = df_semestre[df_semestre['Semestre'].notna()]
        df_semestre = df_semestre[df_semestre['Semestre'].astype(str).str.strip() != '']
        
        if not df_semestre.empty:
            # Ordena semestres cronologicamente
            df_semestre['Ano'] = df_semestre['Semestre'].str.extract(r'(\d{4})').fillna(0).astype(int)
            df_semestre['Sem'] = df_semestre['Semestre'].str.extract(r'(\d)S').fillna(0).astype(int)
            df_semestre = df_semestre.sort_values(['Ano', 'Sem'])
    else:
        st.warning("Coluna 'Semestre' não encontrada ou dados vazios.")
    
    # Gráfico 1: Linhas - Valores por Semestre
    fig1 = go.Figure()
    
    fig1.add_trace(go.Scatter(
        name='Arrecadação',
        x=df_semestre['Semestre'],
        y=df_semestre['Valor arrecadação'],
        mode='lines+markers',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6)
    ))
    
    fig1.add_trace(go.Scatter(
        name='Custeio',
        x=df_semestre['Semestre'],
        y=df_semestre['Valor custeio'],
        mode='lines+markers',
        line=dict(color='#ff7f0e', width=2),
        marker=dict(size=6)
    ))
    
    fig1.add_trace(go.Scatter(
        name='Repasses',
        x=df_semestre['Semestre'],
        y=df_semestre['Valor repasse'],
        mode='lines+markers',
        line=dict(color='#2ca02c', width=2),
        marker=dict(size=6)
    ))
    
    fig1.update_layout(
        title="Evolução Semestral - Arrecadação, Custeio e Repasses",
        xaxis_title="Semestre",
        yaxis_title="Valor (R$)",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Gráfico 1B: Linhas - Médias Mensais por Semestre
    fig1b = go.Figure()
    
    # Calcula médias mensais (divide por 6 meses)
    df_semestre['Média Mensal Arrecadação'] = df_semestre['Valor arrecadação'] / 6
    df_semestre['Média Mensal Custeio'] = df_semestre['Valor custeio'] / 6
    df_semestre['Média Mensal Repasses'] = df_semestre['Valor repasse'] / 6
    
    fig1b.add_trace(go.Scatter(
        name='Arrecadação',
        x=df_semestre['Semestre'],
        y=df_semestre['Média Mensal Arrecadação'],
        mode='lines+markers',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6)
    ))
    
    fig1b.add_trace(go.Scatter(
        name='Custeio',
        x=df_semestre['Semestre'],
        y=df_semestre['Média Mensal Custeio'],
        mode='lines+markers',
        line=dict(color='#ff7f0e', width=2),
        marker=dict(size=6)
    ))
    
    fig1b.add_trace(go.Scatter(
        name='Repasses',
        x=df_semestre['Semestre'],
        y=df_semestre['Média Mensal Repasses'],
        mode='lines+markers',
        line=dict(color='#2ca02c', width=2),
        marker=dict(size=6)
    ))
    
    fig1b.update_layout(
        title="Médias Mensais por Semestre - Arrecadação, Custeio e Repasses",
        xaxis_title="Semestre",
        yaxis_title="Média Mensal (R$)",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig1b, use_container_width=True)
    
    # Gráfico 2: Linhas - Índices de Eficiência
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        name='Índice Eficiência (Custeio/Arrecadação)',
        x=df_semestre['Semestre'],
        y=df_semestre['Índice Eficiência (%)'],
        mode='lines+markers',
        line=dict(color='#d62728', width=2),
        marker=dict(size=8)
    ))
    
    fig2.add_trace(go.Scatter(
        name='Índice Repasses (Repasses/Arrecadação)',
        x=df_semestre['Semestre'],
        y=df_semestre['Índice Repasses (%)'],
        mode='lines+markers',
        line=dict(color='#9467bd', width=2),
        marker=dict(size=8)
    ))
    
    fig2.update_layout(
        title="Índices de Eficiência e Repasses (%)",
        xaxis_title="Semestre",
        yaxis_title="Percentual (%)",
        hovermode='x unified',
        height=400
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # ============================================================================
    # TABELA DETALHADA
    # ============================================================================
    st.markdown("### 📋 Dados Detalhados")
    
    # Seleciona colunas relevantes
    colunas_exibir = ['Semestre', 'Estado', 'Município', 'CNS', 
                      'Quantidade de atos praticados', 'Valor arrecadação', 
                      'Valor custeio', 'Valor repasse', 
                      'Índice Eficiência (%)', 'Índice Repasses (%)']
    
    # Filtra apenas colunas que existem
    colunas_exibir = [col for col in colunas_exibir if col in df_filtrado.columns]
    
    df_exibir = df_filtrado[colunas_exibir].sort_values('Semestre', ascending=False)
    
    st.dataframe(
        df_exibir,
        use_container_width=True,
        height=400,
        column_config={
            "Valor arrecadação": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor custeio": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor repasse": st.column_config.NumberColumn(format="R$ %.2f"),
            "Índice Eficiência (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Índice Repasses (%)": st.column_config.NumberColumn(format="%.2f%%"),
        }
    )
    
    # Estatísticas
    st.caption(f"📊 Exibindo {len(df_exibir)} registros de {len(df)} totais")
