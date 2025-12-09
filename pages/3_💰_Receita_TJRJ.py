"""
Dashboard de Inteligência - Cartórios BR
Sistema de análise e visualização de receitas dos cartórios do Rio de Janeiro
"""

# ============================================================================
# IMPORTS E CONFIGURAÇÕES INICIAIS
# ============================================================================
import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import cloud_processo
import traceback
import base64
import sys
import contextlib
import os
import subprocess
import importlib

# Força reload do módulo cloud_processo para pegar mudanças
importlib.reload(cloud_processo)

# Adiciona diretório pai
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import auth_utils # Módulo de autenticação

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="Cartórios BR - Receita", 
    page_icon="💰", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ============================================================================
# VERIFICAÇÃO DE AUTENTICAÇÃO
# ============================================================================
if not auth_utils.check_password():
    st.warning("⚠️ Acesso restrito. Por favor, faça login na página inicial.")
    st.stop()

# CSS Customizado
st.markdown("""
    <style>
        /* Sidebar toggle button */
        [data-testid="stSidebarCollapseButton"] {
            display: block !important;
            opacity: 1 !important;
            color: #003366 !important;
            background-color: rgba(0, 51, 102, 0.05);
            border-radius: 4px;
        }
        [data-testid="stSidebarCollapseButton"] svg {
            fill: #003366 !important;
        }
        
        /* Plotly modebar - sempre visível e destacado */
        .modebar-container {
            opacity: 1 !important;
            display: block !important;
        }
        
        .modebar {
            opacity: 1 !important;
            background-color: rgba(0, 51, 102, 0.1) !important;
            border-radius: 8px !important;
            padding: 4px 8px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        
        .modebar-btn {
            opacity: 1 !important;
            background-color: white !important;
            border-radius: 4px !important;
            margin: 2px !important;
            padding: 4px !important;
        }
        
        .modebar-btn:hover {
            background-color: #003366 !important;
        }
        
        .modebar-btn svg {
            fill: #003366 !important;
        }
        
        .modebar-btn:hover svg {
            fill: white !important;
        }
        
        /* Multiselect compacto quando desabilitado */
        div[data-baseweb="select"] div[data-baseweb="tag"] {
            max-height: 32px !important;
            overflow: hidden !important;
        }
        
        /* Oculta pills extras quando desabilitado */
        div[aria-disabled="true"] div[data-baseweb="tag"]:nth-child(n+4) {
            display: none !important;
        }
        
        /* Adiciona "..." quando há muitos itens */
        div[aria-disabled="true"] div[data-baseweb="select"] > div:first-child::after {
            content: "..." !important;
            color: #666 !important;
            margin-left: 4px !important;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================================================
RIBRJ_COLORS = ['#003366', '#0055A4', '#CA9E26', '#407BFF', '#82A6FF', '#E6C86E']

ATTRIBUTION_COLOR_MAP = {
    'RI': '#003366', 
    'RCPN': '#CA9E26',
    'Emolumentos RCPN': '#E6C86E', 
    'Funarpem': '#B8860B',         
    'Notas': '#0055A4',
    'Protesto': '#407BFF',
    'RCPJ': '#82A6FF',
    'IT': '#A3C4FF',
    'RTD': '#2E4C80'
}

ATTRIBUTION_MAPPING = {
    'RCPJ': ['RCPJ'],
    'IT': ['IT'],
    'RI': ['RI'],
    'RTD': ['RTD'],
    'Notas': ['Notas'],
    'Protesto': ['Protesto'],
    'RCPN': ['RCPN']  # Usa coluna RCPN agregada (já inclui Emolumentos + Funarpem)
}

ATTRIBUTIONS_LIST = ['RCPJ', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 'RCPN']

NUMERIC_COLUMNS = [
    'RCPJ', 'RCPN', 'IT', 'RI', 'RTD', 'Notas', 'Protesto', 
    'Emolumentos', 'Funarpem', 'Gratuitos', 'Media Mensal Total (R$)'
]

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def format_br_currency(val):
    """Formata valor para padrão brasileiro (R$ 1.234,56)"""
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def clean_currency(x):
    """Converte string brasileira para float (1.234,56 -> 1234.56)"""
    if not isinstance(x, str): 
        return x
    if not x.strip(): 
        return 0.0
    clean = x.replace('.', '').replace(',', '.')
    try:
        return float(clean)
    except ValueError:
        return 0.0

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================
@st.cache_data(ttl=60)  # Cache de 1 minuto para facilitar testes
def load_data():
    """Carrega dados da planilha Google Sheets com cache de 10 minutos"""
    try:
        # Autenticação robusta (compatível com Cloud e Local)
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        elif "GCP_SERVICE_ACCOUNT" in os.environ:
            import json
            creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
            gc = gspread.service_account_from_dict(creds_dict)
        else:
            gc = gspread.service_account()

        sh = gc.open_by_key(cloud_processo.GOOGLE_SHEET_ID)
        
        try:
            worksheet = sh.worksheet("Análise 12 Meses")
            rows = worksheet.get_all_values()
            
            if len(rows) < 2:
                return pd.DataFrame()
                
            # Processa headers e dados
            header = [h.strip() for h in rows[0]]
            data = rows[1:]
            df = pd.DataFrame(data, columns=header)
            
            # Limpeza de dados
            df = df.drop_duplicates()
            
            # Remove linhas de totalização
            if 'cidade' in df.columns:
                df = df[~df['cidade'].astype(str).str.contains('Total', case=False, na=False)]
            if 'designacao' in df.columns:
                df = df[~df['designacao'].astype(str).str.contains('Total', case=False, na=False)]
            
            # Converte colunas numéricas
            for col in NUMERIC_COLUMNS:
                if col in df.columns:
                    df[col] = df[col].apply(clean_currency)
            
            # Substitui "Responsavel pelo Expediente" por "R.E." na coluna cargo
            if 'cargo' in df.columns:
                df['cargo'] = df['cargo'].astype(str).str.replace('Responsavel pelo Expediente', 'R.E.', case=False, regex=False)
                df['cargo'] = df['cargo'].str.replace('Responsável pelo Expediente', 'R.E.', case=False, regex=False)
            
            return df
            
        except gspread.exceptions.WorksheetNotFound:
            st.warning("A conexão foi feita, mas as abas de dados ainda não existem. Por favor, faça a atualização inicial.")
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao conectar com a base de dados: {e}")
        return pd.DataFrame()

# ============================================================================
# CONSOLE DE LOG
# ============================================================================
class StreamlitConsole:
    """Captura prints e exibe no Streamlit em tempo real"""
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.buffer = []

    def write(self, text):
        self.buffer.append(text)
        self.placeholder.code("".join(self.buffer), language="bash")
        sys.__stdout__.write(text)

    def flush(self):
        sys.__stdout__.flush()

# ============================================================================
# PROCESSAMENTO DE DADOS
# ============================================================================
def apply_filters(df, cities, roles):
    """Aplica filtros de cidade e cargo ao dataframe"""
    if not cities:
        return pd.DataFrame(columns=df.columns)
    
    mask = df["cidade"].isin(cities)
    
    if 'cargo' in df.columns and roles:
        mask = mask & df["cargo"].isin(roles)
    
    return df[mask].copy()

def calculate_attribution_data(df_filtered, attributions):
    """Prepara dados para o gráfico de atribuições"""
    data = []
    for attr in attributions:
        if attr == 'RCPN':
            # Verifica se existe coluna RCPN agregada
            if 'RCPN' in df_filtered.columns:
                # Usa a coluna agregada diretamente
                val = df_filtered['RCPN'].sum()
                if val > 0:
                    data.append({'Atribuicao': 'RCPN', 'Detalhe': 'RCPN', 'Valor': val})
            else:
                # Se não existe RCPN agregada, faz o breakdown
                if 'Emolumentos' in df_filtered.columns:
                    val = df_filtered['Emolumentos'].sum()
                    if val > 0: 
                        data.append({'Atribuicao': 'RCPN', 'Detalhe': 'Emolumentos RCPN', 'Valor': val})
                if 'Funarpem' in df_filtered.columns:
                    val_f = df_filtered['Funarpem'].sum()
                    if val_f > 0: 
                        data.append({'Atribuicao': 'RCPN', 'Detalhe': 'Funarpem', 'Valor': val_f})
        else:
            if attr in df_filtered.columns:
                val = df_filtered[attr].sum()
                if val > 0: 
                    data.append({'Atribuicao': attr, 'Detalhe': attr, 'Valor': val})
    
    return pd.DataFrame(data)

def calculate_dynamic_total(df_filtered, attributions):
    """Calcula total baseado nas atribuições selecionadas"""
    cols_to_sum = []
    for attr in attributions:
        if attr in ATTRIBUTION_MAPPING:
            for c in ATTRIBUTION_MAPPING[attr]:
                if c in df_filtered.columns:
                    cols_to_sum.append(c)
    
    if not cols_to_sum:
        return 0
    return df_filtered[cols_to_sum].sum(axis=1)

# ============================================================================
# SIDEBAR - ADMINISTRAÇÃO
# ============================================================================
with st.sidebar:
    col_logo, _ = st.columns([1, 0.1])
    with col_logo:
        st.image("logo_ribrj.png", width=250)
    
    st.markdown("---")
    st.subheader("Administração")
    
    if st.button("🔄 Atualizar Dados Agora"):
        st.info("Iniciando processo... Acompanhe o log abaixo.")
        log_placeholder = st.empty()
        with contextlib.redirect_stdout(StreamlitConsole(log_placeholder)):
            with st.spinner("Processando..."):
                try:
                    # Executa update SEM enriquecimento (run_enrichment=False)
                    msg, code = cloud_processo.cloud_main(None, run_enrichment=False)
                    if code == 200:
                        st.success(msg)
                        st.cache_data.clear()
                    else:
                        st.error(f"Erro: {msg}")
                except Exception as e:
                    st.error(f"Erro crítico: {e}")
                    st.code(traceback.format_exc())
    
    if st.button("🧬 Popular CNS (TJRJ + CNJ)"):
        st.info("Iniciando enriquecimento de CNS...")
        log_placeholder = st.empty()
        
        # Como popula_cns.py tem sys.exit, usamos subprocess para segurança
        cmd = [sys.executable, "popula_cns.py"]
        
        try:
            # Força encoding UTF-8 para evitar erro no Windows (cp1252 vs utf-8)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            # Injeta credenciais do Streamlit Secrets no ambiente do subprocesso
            if "gcp_service_account" in st.secrets:
                import json
                # Converte o objeto de configuração (AttrDict) para dict padrão antes de serializar
                creds = dict(st.secrets["gcp_service_account"])
                env["GCP_SERVICE_ACCOUNT"] = json.dumps(creds)
            
            # Injeta ID da Planilha se existir nos secrets
            # Injeta ID da Planilha se existir nos secrets ou usa o do cloud_processo
            env["SHEET_ID"] = cloud_processo.GOOGLE_SHEET_ID
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                bufsize=1,
                env=env
            )
            
            full_log = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    full_log.append(line)
                    log_placeholder.code("".join(full_log))
            
            if process.returncode == 0:
                st.success("Enriquecimento concluído com sucesso!")
                st.cache_data.clear()
            else:
                st.error("Falha ao popular CNS.")
                
        except Exception as e:
            st.error(f"Erro ao executar script: {e}")
    

    
    st.divider()
    url_planilha = f"https://docs.google.com/spreadsheets/d/{cloud_processo.GOOGLE_SHEET_ID}"
    
    try:
        with open("icon_sheets.png", "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        
        st.markdown(f'''
            <a href="{url_planilha}" target="_blank" style="text-decoration: none;">
                <div style="
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    width: 100%; 
                    padding: 0.5rem; 
                    border: 1px solid #d0d7de; 
                    border-radius: 8px; 
                    background-color: #ffffff; 
                    color: #24292f; 
                    font-weight: 500;
                    transition: 0.3s;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <img src="data:image/png;base64,{img_b64}" style="width: 24px; height: 24px; margin-right: 10px;">
                    Abrir Planilha
                </div>
            </a>
        ''', unsafe_allow_html=True)
    except Exception:
        st.link_button("📊 Abrir Planilha no Google Sheets", url_planilha)

# ============================================================================
# MAIN - DASHBOARD
# ============================================================================
st.title("💰 Receita TJRJ - Análise Extrajudicial")

with st.spinner('Buscando dados atualizados na nuvem...'):
    df = load_data()

if not df.empty:
    # --- CONFIGURAÇÃO DE ABAS ---
    tab_geral, tab_cidades = st.tabs(["Painel Geral", "🏙️ Cidades"])

    # ========================================================================
    # ABA 2: CIDADES (Relatório Solicitado)
    # ========================================================================
    with tab_cidades:
        st.subheader("Relatório por Cidade")
        st.markdown("Selecione uma cidade na tabela para filtrar o Painel Geral.")
        
        col_total_name = "Media Mensal Total (R$)"
        
        if col_total_name in df.columns:
            # Agrupa dados
            # 1. Receita Média Total por Cidade (Soma das médias dos cartórios da cidade)
            # 2. Quantidade de Cartórios
            df_cidades = df.groupby("cidade").agg({
                col_total_name: 'sum',
                'cidade': 'count'
            }).rename(columns={'cidade': 'Qtd Cartórios'}).reset_index()
            
            df_cidades.rename(columns={col_total_name: 'Receita Total Média'}, inplace=True)
            
            # Ordenação: Menor para Maior (Ascending)
            df_cidades = df_cidades.sort_values('Receita Total Média', ascending=True)
            
            # Formatação para exibição (mas mantemos dados brutos para ordenação interna se possível, 
            # mas o st.dataframe permite formatar via column_config, o que é melhor)
            
            # Configuração da Coluna de Seleção
            event = st.dataframe(
                df_cidades,
                column_config={
                    "Receita Total Média": st.column_config.NumberColumn(
                        "Receita Total Média",
                        format="R$ %.2f",
                        width="medium" # Ajuste de largura
                    ),
                    "cidade": st.column_config.TextColumn(
                        "Cidade",
                        width="large" # Garante espaço para nomes longos
                    ),
                    "Qtd Cartórios": st.column_config.NumberColumn(
                        "Qtd Cartórios",
                        width="small" # Coluna estreita para número pequeno
                    )
                },
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Lógica de Seleção
            if len(event.selection["rows"]) > 0:
                selected_index = event.selection["rows"][0]
                # Pega a cidade correspondente ao índice visualizado (atenção à ordenação)
                selected_city = df_cidades.iloc[selected_index]["cidade"]
                
                # Atualiza o filtro da outra aba via Session State
                # A chave do multiselect abaixo será 'filtro_cidades_main'
                st.session_state['filtro_cidades_main'] = [selected_city]
                st.success(f"✅ Cidade **{selected_city}** selecionada! Vá para a aba **Painel Geral** para ver os detalhes.")
                
        else:
            st.error("Coluna de Receita não encontrada para gerar o relatório.")

    # ========================================================================
    # ABA 1: PAINEL GERAL (Dashboard Original)
    # ========================================================================
    with tab_geral:
        # --- FILTROS E MÉTRICAS ---
        col1, col2, col3, col_filtros = st.columns([0.8, 0.8, 0.8, 3])
        
        with col_filtros:
            f_col1, f_col2, f_col3 = st.columns(3)
            
            # Filtro de Cidades
            with f_col1:
                usar_todas = st.checkbox("Todas Cidades", value=True)
                opcoes_cidades = sorted(df["cidade"].unique())
                
                if usar_todas:
                    cidades_selecionadas = opcoes_cidades
                    st.caption(f"✓ Todas ({len(opcoes_cidades)} cidades)")
                    # Se marcou 'Todas', limpamos a seleção específica do session state para evitar conflito visual
                    if 'filtro_cidades_main' in st.session_state and st.session_state['filtro_cidades_main'] != opcoes_cidades:
                         # Opcional: manter sincronia
                         pass
                else:
                    # Widget Multiselect com KEY para ser controlado pela outra aba
                    cidades_selecionadas = st.multiselect(
                        "Cidades", 
                        options=opcoes_cidades, 
                        label_visibility="collapsed", 
                        placeholder="Cidades...",
                        key='filtro_cidades_main' # CHAVE IMPORTANTE PARA INTERATIVIDADE
                    )
            
            # Filtro de Atribuições
            with f_col2:
                usar_todas_attr = st.checkbox("Todas Atribuições", value=True)
                
                if usar_todas_attr:
                    atribuicoes_selecionadas = ATTRIBUTIONS_LIST
                    st.caption(f"✓ Todas ({len(ATTRIBUTIONS_LIST)} atribuições)")
                else:
                    atribuicoes_selecionadas = st.multiselect("Atribuições", options=ATTRIBUTIONS_LIST, 
                                                             label_visibility="collapsed", placeholder="Atribuições...")
            
            # Filtro de Cargos
            with f_col3:
                if 'cargo' in df.columns:
                    opcoes_cargos = sorted([c for c in df["cargo"].dropna().unique() if str(c).strip() != ''])
                    if not opcoes_cargos: 
                        opcoes_cargos = ["N/A"]
                    
                    usar_todos_cargos = st.checkbox("Todos Cargos", value=True)
                    
                    if usar_todos_cargos:
                        cargos_selecionados = opcoes_cargos
                        st.caption(f"✓ Todos ({len(opcoes_cargos)} cargos)")
                    else:
                        cargos_selecionados = st.multiselect("Cargos", options=opcoes_cargos, 
                                                            label_visibility="collapsed", placeholder="Cargos...")
                else:
                    st.warning("Sem dados de Cargo")
                    cargos_selecionados = []
        
        # Aplica filtros
        if not cidades_selecionadas:
            df_filtered = pd.DataFrame(columns=df.columns)
            if not usar_todas: 
                st.caption("👈 Selecione cidades.")
        else:
            df_filtered = apply_filters(df, cidades_selecionadas, cargos_selecionados)
        
        # Calcula métricas
        col_total = "Media Mensal Total (R$)"
        df_filtered['Total_Calculado'] = calculate_dynamic_total(df_filtered, atribuicoes_selecionadas)
        
        faturamento_mensal = df_filtered[col_total].sum() if col_total in df_filtered.columns else 0
        media_por_cartorio = df_filtered[col_total].mean() if col_total in df_filtered.columns and len(df_filtered) > 0 else 0
        
        # Exibe métricas
        col1.metric("Faturamento Mensal Médio", format_br_currency(faturamento_mensal))
        col2.metric("Média Mensal por Cartório", format_br_currency(media_por_cartorio))
        col3.metric("Cartórios Listados", len(df_filtered))
        
        st.divider()
        
        # --- GRÁFICOS ---
        # Prepara dados para gráfico de atribuições
        df_sun = calculate_attribution_data(df_filtered, atribuicoes_selecionadas)
        
        # Define layout condicional
        mostrar_grafico_cidade = df_filtered['cidade'].nunique() > 1
        mostrar_grafico_cargo = ('cargo' in df_filtered.columns and 
                                 df_filtered['cargo'].nunique() > 1 and
                                 usar_todas and usar_todas_attr and usar_todos_cargos)
        
        if mostrar_grafico_cargo:
            # Layout com 3 gráficos na primeira linha (Cidade | Atribuição | Cargo)
            r1_c1, r1_c2, r1_c3 = st.columns(3)
            container_cidade = r1_c1
            container_atribuicao = r1_c2
            container_cargo = r1_c3
            st.divider()
            container_cartorio = st.container()
        elif mostrar_grafico_cidade:
            # Layout padrão: Linha 1 (Cidade | Atribuição), Linha 2 (Cartório)
            r1_c1, r1_c2 = st.columns(2)
            container_cidade = r1_c1
            container_atribuicao = r1_c2
            container_cargo = None
            st.divider()
            container_cartorio = st.container()
        else:
            # Layout cidade única: Linha 1 (Atribuição | Cartório)
            container_cidade = None
            container_cargo = None
            r1_c1, r1_c2 = st.columns(2)
            container_atribuicao = r1_c1
            container_cartorio = r1_c2
        
        # Gráfico 1: Receita por Cidade
        if container_cidade:
            with container_cidade:
                st.subheader("Receita por Cidade")
                fig1 = px.pie(
                    df_filtered, 
                    values='Total_Calculado', 
                    names="cidade",
                    hole=0.4,
                    color_discrete_sequence=RIBRJ_COLORS
                )
                fig1.update_layout(separators=",.", margin=dict(t=20, b=20, l=10, r=10))
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': True})
        
        # Gráfico 2: Receita por Atribuição
        with container_atribuicao:
            st.subheader("Receita por Atribuição")
            
            if not df_sun.empty:
                fig2 = px.pie(
                    df_sun,
                    values='Valor',
                    names='Detalhe',
                    color='Detalhe',
                    color_discrete_map=ATTRIBUTION_COLOR_MAP,
                    hole=0.5
                )
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                fig2.update_layout(separators=",.", showlegend=True, margin=dict(t=20, b=20, l=10, r=10))
                st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': True})
            else:
                st.info("Selecione o desejado nos filtros acima.")
        
        # Gráfico 3: Receita por Cargo (quando sem filtros)
        if container_cargo:
            with container_cargo:
                st.subheader("Receita por Cargo")
                
                if 'cargo' in df_filtered.columns:
                    # Agrupa por cargo
                    df_cargo = df_filtered.groupby('cargo')[col_total].sum().reset_index()
                    df_cargo = df_cargo[df_cargo[col_total] > 0]
                    
                    if not df_cargo.empty:
                        fig_cargo = px.pie(
                            df_cargo,
                            values=col_total,
                            names='cargo',
                            hole=0.5,
                            color_discrete_sequence=RIBRJ_COLORS
                        )
                        fig_cargo.update_traces(textposition='inside', textinfo='percent+label')
                        fig_cargo.update_layout(separators=",.", showlegend=True, margin=dict(t=20, b=20, l=10, r=10))
                        st.plotly_chart(fig_cargo, use_container_width=True, config={'displayModeBar': True})
                    else:
                        st.info("Sem dados de cargo para exibir.")
                else:
                    st.info("Coluna 'cargo' não disponível.")
        
        # Gráfico 3: Receita por Cartório
        with container_cartorio:
            st.subheader("Receita por Cartório")
            
            df_filtered = df_filtered.copy()
            df_filtered['Cartorio'] = (
                df_filtered['cidade'] + " - " + 
                df_filtered['designacao'] + 
                " (" + df_filtered[col_total].apply(format_br_currency) + ")"
            )
            
            fig3 = px.pie(
                df_filtered, 
                values=col_total, 
                names="Cartorio",
                hole=0.4,
                color_discrete_sequence=RIBRJ_COLORS
            )
            fig3.update_layout(separators=",.", margin=dict(t=20, b=20, l=10, r=10))
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': True})
        
        # --- TABELA DE DETALHAMENTO ---
        st.divider()
        st.subheader("Detalhamento")
        
        # Ordena por cidade alfabeticamente
        df_display = df_filtered.sort_values('cidade') if 'cidade' in df_filtered.columns else df_filtered
        
        # Renomeia Total_Calculado para Media Mensal
        df_display = df_display.copy()
        if 'Total_Calculado' in df_display.columns:
            df_display.rename(columns={'Total_Calculado': 'Media Mensal'}, inplace=True)
        
        # Remove primeira coluna se ela vier antes de 'cod' (geralmente índice ou vazia)
        if len(df_display.columns) > 0 and 'cod' in df_display.columns:
            cod_index = df_display.columns.get_loc('cod')
            if cod_index > 0:
                # Remove todas as colunas antes de 'cod'
                cols_before_cod = df_display.columns[:cod_index].tolist()
                df_display = df_display.drop(columns=cols_before_cod)
        
        # Remove colunas vazias ou sem nome
        cols_to_remove = [col for col in df_display.columns if 
                          col == '' or 
                          str(col).lower().startswith('unnamed') or 
                          df_display[col].isna().all()]
        df_display = df_display.drop(columns=cols_to_remove, errors='ignore')
        
        # Remove coluna Media Mensal Total (R$) se existir
        cols_to_hide = [col_total]
        df_display = df_display.drop(columns=[c for c in cols_to_hide if c in df_display.columns])
        
        # Aplica formatação
        styled_df = df_display.style.format(decimal=",", thousands=".", precision=2)
        
        if 'Media Mensal' in df_display.columns:
            # Negrito APENAS no cabeçalho (header)
            styled_df = styled_df.set_table_styles([
                {'selector': 'th.col_heading.level0.col' + str(df_display.columns.get_loc('Media Mensal')),
                 'props': [('font-weight', 'bold')]}
            ])
        
        st.dataframe(
            styled_df,
            use_container_width=True
        )
        
        # Botão de Download
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar dados filtrados (CSV)", csv, "dados_filtrados.csv", "text/csv", key='download-csv')

else:
    st.warning("A planilha parece estar vazia ou inacessível no momento.")
