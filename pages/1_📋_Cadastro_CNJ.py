"""
📋 Cadastro CNJ - Serventias Extrajudiciais
Interface completa para consulta, visualização e exportação (CSV/Google Sheets)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
import gspread
from google.oauth2.service_account import Credentials

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cnj_api import CNJClient
import auth_utils # Módulo de autenticação

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="Cadastro CNJ - Cartórios BR",
    page_icon="📋",
    layout="wide"
)

# ============================================================================
# VERIFICAÇÃO DE AUTENTICAÇÃO
# ============================================================================
# Se não estiver logado, interrompe a execução e pede login na Home
if not auth_utils.check_password():
    st.warning("⚠️ Acesso restrito. Por favor, faça login na página inicial.")
    st.stop()

# ============================================================================
# CONSTANTES E CONFIGURAÇÕES
# ============================================================================
SHEET_ID = "1SkxwQoAnNpcNBg1niLpaRaMs79h8rp143NPgsr1EAXo"
WORKSHEET_NAME = "Dados CNJ"
RIBRJ_COLORS = ['#003366', '#0055A4', '#CA9E26', '#407BFF', '#82A6FF', '#E6C86E']

# Estados do Brasil
ESTADOS_BRASIL = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
    "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
    "RS", "RO", "RR", "SC", "SP", "SE", "TO"
]

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def autenticar_google_sheets():
    """Autentica com Google Sheets usando st.secrets"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Prepara credenciais (suporte a st.secrets e env var)
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        # Converte AttrDict para dict normal para ser mutável
        creds_dict = dict(st.secrets["gcp_service_account"])
    elif "GCP_SERVICE_ACCOUNT" in os.environ:
        import json
        creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    
    if creds_dict:
        # Correção de chave privada (comum erro de \n escapado)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scope
        )
        return gspread.authorize(credentials)
    else:
        # Fallback para default (local com gcloud auth)
        return gspread.service_account()

def salvar_em_sheets(df):
    """
    Salva DataFrame na Google Sheets.
    Regra: APAGA todo o conteúdo da aba e grava os novos dados.
    """
    try:
        gc = autenticar_google_sheets()
        sheet = gc.open_by_key(SHEET_ID)
        
        # Tenta pegar worksheet existente ou cria nova
        try:
            worksheet = sheet.worksheet(WORKSHEET_NAME)
            worksheet.clear()  # Limpa todo o conteúdo existente
        except:
            worksheet = sheet.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=50)
        
        # Prepara dados para salvar
        df_to_save = df.copy()
        # Adiciona timestamp da atualização na primeira coluna
        df_to_save.insert(0, 'data_atualizacao', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Converte para lista de listas (formato exigido pelo gspread)
        # Inclui o cabeçalho
        data_to_write = [df_to_save.columns.values.tolist()] + df_to_save.values.tolist()
        
        # Salva utilizando atualização em massa (mais rápido)
        worksheet.update(data_to_write, value_input_option='RAW')
        
        return True, len(df)
        
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=60) # Cache reduzido para 1 minuto
def load_data_from_sheets():
    """Carrega dados da planilha Google Sheets"""
    try:
        # DEBUG MODE ATIVADO
        st.write("🔧 DEBUG: Iniciando autenticação...")
        gc = autenticar_google_sheets()
        st.write("🔧 DEBUG: Autenticado. Abrindo planilha...")
        
        try:
            sh = gc.open_by_key(SHEET_ID)
            st.write(f"🔧 DEBUG: Planilha aberta. Buscando aba '{WORKSHEET_NAME}'...")
            
            try:
                worksheet = sh.worksheet(WORKSHEET_NAME)
                st.write(f"🔧 DEBUG: Aba '{WORKSHEET_NAME}' encontrada. Baixando dados...")
                
                # Lê todos os dados
                data = worksheet.get_all_records()
                st.write(f"🔧 DEBUG: Dados brutos: {len(data)} registros encontrados.")
                
                if not data:
                    st.warning(f"⚠️ A aba '{WORKSHEET_NAME}' existe mas está vazia.")
                    return pd.DataFrame()
                
                df = pd.DataFrame(data)
                st.write(f"🔧 DEBUG: DataFrame criado. Colunas: {df.columns.tolist()}")
                
                # Remove a coluna de metadata se existir
                if 'data_atualizacao' in df.columns:
                    df = df.drop(columns=['data_atual_atualizacao', 'data_atualizacao'], errors='ignore')
                
                # Garante que status_serventia seja string para comparações
                if 'status_serventia' in df.columns:
                    df['status_serventia'] = df['status_serventia'].astype(str)
                    # Remove .0 se tiver vindo como float (1.0 -> 1)
                    df['status_serventia'] = df['status_serventia'].str.replace(r'\.0$', '', regex=True)
                    
                return df
                
            except gspread.exceptions.WorksheetNotFound:
                st.error(f"❌ ERRO: Aba '{WORKSHEET_NAME}' NÃO encontrada na planilha.")
                return pd.DataFrame()
                
        except Exception as e:
             st.error(f"❌ ERRO ao abrir planilha: {e}")
             return pd.DataFrame()
            
    except Exception as e:
        st.error(f"❌ ERRO CRÍTICO ao carregar dados salvos: {e}")
        return pd.DataFrame()

# ============================================================================
# INTERFACE
# ============================================================================

st.title("📋 Cadastro CNJ - Serventias Extrajudiciais")
st.markdown("Consulta oficial ao cadastro do Conselho Nacional de Justiça")

with st.sidebar:
    st.image("logo_ribrj.png", width=250)
    st.markdown("---")
    
    # Botão de Recarregar Cache
    if st.button("🔄 Recarregar Dados Salvos"):
        load_data_from_sheets.clear()
        if 'cnj_dados' in st.session_state:
            del st.session_state['cnj_dados']
        st.rerun()

    st.subheader("Filtros")
    
    # Seleção de Estados com opção "Todo o Brasil"
    selecionar_todos = st.checkbox("🇧🇷 Todo o Brasil", value=False)
    
    if selecionar_todos:
        ufs_selecionadas = ESTADOS_BRASIL
        st.multiselect(
            "Estados",
            options=ESTADOS_BRASIL,
            default=ESTADOS_BRASIL,
            disabled=True,
            label_visibility="collapsed"
        )
    else:
        ufs_selecionadas = st.multiselect(
            "Estados",
            options=ESTADOS_BRASIL,
            default=["RJ"],
            label_visibility="collapsed",
            help="Selecione um ou mais estados"
        )
    
    if not ufs_selecionadas:
        st.warning("Selecione pelo menos um estado.")
    
    st.markdown("---")
    
    # Filtro de Datas
    st.markdown("**Período de Consulta**")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        dt_inicio = st.date_input("Data Inicial", value=datetime(2024, 1, 1))
    with col_d2:
        dt_final = st.date_input("Data Final", value=datetime(2024, 12, 31))
        
    st.markdown("---")
    # Botão de busca
    if st.button("🔍 Buscar Dados", type="primary", use_container_width=True):
        st.session_state['realizar_busca'] = True
    else:
        st.session_state.setdefault('realizar_busca', False)
        
    st.write("")
    st.markdown(f"""
        <a href="https://docs.google.com/spreadsheets/d/{SHEET_ID}" target="_blank" style="text-decoration: none;">
            <button style="
                width: 100%;
                padding: 0.5rem;
                background-color: white;
                color: #1f77b4;
                border: 1px solid #1f77b4;
                border-radius: 0.25rem;
                cursor: pointer;
                font-weight: bold;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;">
                📊 Abrir Planilha Google
            </button>
        </a>
        """, unsafe_allow_html=True)

# Lógica de Busca e Persistência
if st.session_state.get('realizar_busca') and ufs_selecionadas:
    # Se vai realizar busca nova, não faz nada aqui, deixa o bloco abaixo tratar
    pass

# Auto-carregamento inicial (se não houver dados em sessão)
if 'cnj_dados' not in st.session_state:
    with st.spinner("Carregando últimos dados salvos..."):
        df_saved = load_data_from_sheets()
        if not df_saved.empty:
            st.session_state['cnj_dados'] = df_saved
            # Tenta inferir filtros do dataframe carregado
            if 'uf' in df_saved.columns:
                ufs_loaded = df_saved['uf'].unique()
                st.session_state['cnj_filtros'] = f"Dados Carregados ({len(ufs_loaded)} estados)"
        else:
             st.session_state['cnj_dados'] = pd.DataFrame()

# Tratamento do clique do botão de busca
# Tratamento do clique do botão de busca
if st.session_state.get('realizar_busca'):
    st.session_state['realizar_busca'] = False # Reseta trigger
    
    try:
        total_ufs = len(ufs_selecionadas)
        dfs_result = []
        
        # --- PAINEL DE ACOMPANHAMENTO (EXECUÇÃO) ---
        with st.status("🚀 Processando consulta...", expanded=True) as status:
            st.write("📝 Inicializando parâmetros de busca...")
            dt_inicio_str = dt_inicio.strftime("%d/%m/%Y")
            dt_final_str = dt_final.strftime("%d/%m/%Y")
            st.write(f"📅 Período: {dt_inicio_str} a {dt_final_str}")
            
            # Loop por UF
            for i, uf in enumerate(ufs_selecionadas):
                start_time = datetime.now()
                st.write(f"🔄 **[{i+1}/{total_ufs}] Consultando {uf}...**")
                
                try:
                    # Instancia cliente novo para cada chamada
                    status.update(label=f"Consultando {uf}...", state="running")
                    client = CNJClient(timeout=60)
                    
                    # Busca dados
                    df_uf = client.buscar_serventias_ativas(dt_inicio_str, dt_final_str, uf)
                    
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    # Garante coluna UF
                    if not df_uf.empty:
                        registros = len(df_uf)
                        if 'uf' not in df_uf.columns:
                            df_uf['uf'] = uf
                        dfs_result.append(df_uf)
                        st.write(f"✅ {uf}: {registros} registros encontrados em {elapsed:.1f}s")
                    else:
                        st.write(f"⚠️ {uf}: Nenhum dado encontrado. ({elapsed:.1f}s)")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao consultar {uf}: {e}")
            
            st.write("---")
            st.write("📊 Consolidando resultados...")
            
            # Consolida e SALVA NO SESSION STATE
            if dfs_result:
                df_final = pd.concat(dfs_result, ignore_index=True)
                st.session_state['cnj_dados'] = df_final
                st.session_state['cnj_filtros'] = f"{len(ufs_selecionadas)} estados"
                
                st.write(f"🎉 **Total Final: {len(df_final)} registros.**")
                status.update(label="✅ Consulta Finalizada com Sucesso!", state="complete", expanded=False)
            else:
                st.session_state['cnj_dados'] = pd.DataFrame() # Vazio
                status.update(label="⚠️ Consulta Finalizada (Sem dados)", state="complete", expanded=True)
                st.warning("Nenhum dado encontrado para os filtros selecionados.")
            
    except Exception as e:
        st.error(f"Erro crítico na execução: {e}")
        st.exception(e)

# EXIBIÇÃO (Sempre que houver dados no session_state)
if 'cnj_dados' in st.session_state and not st.session_state['cnj_dados'].empty:
    df_raw = st.session_state['cnj_dados']
    
    # --- LAYOUT PRINCIPAL (Com Coluna à Direita para Filtros) ---
    col_main, col_filters_right = st.columns([4, 1.2])

    with col_filters_right:
        st.write("") # Spacer
        st.markdown("### 🔎 Filtros")
        
        # 1. Filtro de Estado (dos resultados)
        estados_disponiveis = sorted(df_raw['uf'].unique())
        sel_estados = st.multiselect("Estado", options=estados_disponiveis, default=estados_disponiveis)
        
        # 2. Filtro de Município (Dinâmico)
        if sel_estados:
            df_muni = df_raw[df_raw['uf'].isin(sel_estados)]
            municipios_disponiveis = sorted(df_muni['municipio'].unique())
        else:
            municipios_disponiveis = []
            
        sel_municipios = st.multiselect("Município", options=municipios_disponiveis, placeholder="Todos")
        
        # 3. Filtro de Atribuição
        if 'atribuicao' in df_raw.columns:
            # Separa todas as atribuições, pois podem vir separadas por vírgula
            all_attr_list = []
            for item in df_raw['atribuicao'].dropna():
                parts = [p.strip() for p in str(item).split(',')]
                all_attr_list.extend(parts)
            
            # Remove vazios e duplicatas, ordena
            unique_attrs = sorted(list(set([a for a in all_attr_list if a])))
            
            sel_atribuicao = st.multiselect("Atribuição", options=unique_attrs, placeholder="Todas")
        else:
            sel_atribuicao = []
        
        # 4. Filtro de Status
        status_opts = ["Todas", "Ativas", "Inativas"]
        sel_status = st.radio("Status", options=status_opts, index=0)
    
    # --- APLICAÇÃO DOS FILTROS ---
    df_filtered = df_raw.copy()
    
    # Filtro Estado
    if sel_estados:
        df_filtered = df_filtered[df_filtered['uf'].isin(sel_estados)]
    
    # Filtro Município
    if sel_municipios:
        df_filtered = df_filtered[df_filtered['municipio'].isin(sel_municipios)]
        
    # Filtro Atribuição
    if sel_atribuicao and 'atribuicao' in df_filtered.columns:
        # Filtra se TEM ALGUMA das atribuições selecionadas (lógica OR na seleção)
        # Ex: Se selecionar "Notas", traz tudo que tem "Notas" na string
        def check_attr(row_val):
            if not isinstance(row_val, str): return False
            row_parts = [r.strip() for r in row_val.split(',')]
            # Interseção entre o que tem na linha e o que foi selecionado
            return any(sel in row_parts for sel in sel_atribuicao)
            
        df_filtered = df_filtered[df_filtered['atribuicao'].apply(check_attr)]
        
    # Filtro Status
    if sel_status == "Ativas":
        if 'status_serventia' in df_filtered.columns:
             df_filtered = df_filtered[df_filtered['status_serventia'].astype(str) == '1']
        else:
             df_filtered = df_filtered[df_filtered['situacao'] == 'Ativa']
    elif sel_status == "Inativas":
        if 'status_serventia' in df_filtered.columns:
             df_filtered = df_filtered[df_filtered['status_serventia'].astype(str) != '1']
        else:
             df_filtered = df_filtered[df_filtered['situacao'] != 'Ativa']

    # --- EXIBIÇÃO NA COLUNA PRINCIPAL ---
    with col_main:
        st.success(f"✅ Consulta concluída! {len(df_filtered)} registros exibidos.")
        st.divider()
        
        # Calcula Contagens
        total_filtrado = len(df_filtered)
        
        # Contagem de Ativas
        if 'status_serventia' in df_filtered.columns:
            ativas = (df_filtered['status_serventia'].astype(str) == '1').sum()
        else:
            ativas = df_filtered['situacao'].value_counts().get('Ativa', 0)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", total_filtrado)
        m2.metric("Municípios", df_filtered['municipio'].nunique() if 'municipio' in df_filtered.columns else "-")
        m3.metric("Estados", df_filtered['uf'].nunique() if 'uf' in df_filtered.columns else "-")
        
        # Destaque visual para Ativas
        m4.metric("✅ Ativas", ativas, delta=f"{((ativas/total_filtrado)*100):.1f}%" if total_filtrado > 0 else None)
    
    # --- TABELA ---
    st.divider()
    st.subheader(f"Detalhamento dos Dados ({len(df_filtered)} registros)")
    st.dataframe(df_filtered, use_container_width=True, height=500)
    
    # --- INFO SOBRE ESTADOS FALTANTES ---
    total_esperado = len(ufs_selecionadas) if 'realizar_busca' in st.session_state else 0
    encontrados = df_raw['uf'].nunique()
    if encontrados < total_esperado and total_esperado > 0:
         with st.expander(f"⚠️ Atenção: Apenas {encontrados} de {total_esperado} estados retornaram dados"):
            st.warning("Alguns estados podem estar indisponíveis na API do CNJ no momento ou excederam o tempo de resposta.")
            st.write(f"Estados sem retorno: {set(ufs_selecionadas) - set(df_raw['uf'].unique())}")
    
    # --- AÇÕES (Download e Save) ---
    st.divider()
    ac1, ac2 = st.columns(2)
    
    with ac1:
        # Nome do arquivo CSV
        file_name = f"cnj_dados_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        csv_data = df_filtered.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Baixar Dados Filtrados (CSV)",
            data=csv_data,
            file_name=file_name,
            mime="text/csv",
            use_container_width=True
        )
        
    with ac2:
        if st.button("💾 Salvar Filtrados no Google Sheets", use_container_width=True):
            with st.spinner("Salvando dados filtrados na planilha..."):
                sucesso, msg = salvar_em_sheets(df_filtered)
                if sucesso:
                    st.success(f"Sucesso! {msg} linhas salvas na aba '{WORKSHEET_NAME}'.")
                    st.markdown(f"[🔗 Abrir Planilha](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
                else:
                    st.error(f"Erro ao salvar: {msg}")

elif 'cnj_dados' in st.session_state and st.session_state['cnj_dados'].empty:
    st.info("Nenhum dado para exibir.")
else:
    st.info("👈 Utilize a barra lateral para configurar e iniciar a busca.")
