import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import sys
import subprocess

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import auth_utils

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="Municípios IBGE - Cartórios BR",
    page_icon="🏙️",
    layout="wide"
)

# ============================================================================
# VERIFICAÇÃO DE AUTENTICAÇÃO
# ============================================================================
# TEMPORARIAMENTE DESATIVADO PARA HOMOLOGAÇÃO
# if not auth_utils.check_password():
#     st.warning("⚠️ Acesso restrito. Por favor, faça login na página inicial.")
#     st.stop()

# ============================================================================
# CONSTANTES
# ============================================================================
SHEET_ID = "1ktKGyouWoVVC3Vbp-amltr_rRJiZHZAFcp7GaUXmDmo"
WORKSHEET_NAME = "Municipios_IBGE"

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.markdown("### ⚙️ Administração")
    
    # Botão Abrir Planilha
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
                📊 Abrir Planilha
            </button>
        </a>
        """, unsafe_allow_html=True)
        
    st.write("")
    
    # Botão Atualizar Dados
    if st.button("🔄 Atualizar Municípios IBGE", use_container_width=True):
        status_box = st.status("🚀 Iniciando atualização...", expanded=True)
        try:
            status_box.write("Consultando API do IBGE...")
            result = subprocess.run(
                [sys.executable, "extrair_municipios_ibge.py"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(__file__))
            )
            
            if result.returncode == 0:
                status_box.update(label="✅ Atualização concluída!", state="complete", expanded=False)
                st.success("Dados atualizados com sucesso!")
                with st.expander("Ver logs da execução"):
                    st.code(result.stdout)
            else:
                status_box.update(label="❌ Falha na atualização", state="error", expanded=True)
                st.error("Ocorreu um erro durante a extração.")
                st.error(result.stderr)
        except Exception as e:
            status_box.update(label="❌ Erro crítico", state="error")
            st.error(f"Erro ao executar script: {str(e)}")

# ============================================================================
# FUNÇÕES
# ============================================================================
def load_data_from_sheets():
    """Carrega dados da planilha"""
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(credentials)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet(WORKSHEET_NAME)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# ============================================================================
# INTERFACE
# ============================================================================
st.title("🏙️ Municípios IBGE")
st.markdown("Base de dados oficial de municípios brasileiros do IBGE.")

# Carrega dados
with st.spinner("Carregando dados da planilha..."):
    df = load_data_from_sheets()

if not df.empty:
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Municípios", f"{len(df):,}")
    col2.metric("Estados", df['sigla_uf'].nunique() if 'sigla_uf' in df.columns else 0)
    col3.metric("Regiões", df['nome_regiao'].nunique() if 'nome_regiao' in df.columns else 0)
    
    if 'data_atualizacao' in df.columns and len(df) > 0:
        ultima_atualizacao = df['data_atualizacao'].iloc[0]
        col4.metric("Última Atualização", ultima_atualizacao.split()[0] if ' ' in str(ultima_atualizacao) else ultima_atualizacao)
    
    st.divider()
    
    # Layout com filtros
    col_main, col_filters = st.columns([4, 1.2])
    
    with col_filters:
        st.write("")
        st.markdown("### 🔎 Filtros")
        
        # Filtro por Região
        if 'nome_regiao' in df.columns:
            regioes = sorted(df['nome_regiao'].unique())
            regiao_selecionada = st.selectbox("Região", ["Todas"] + regioes)
            if regiao_selecionada != "Todas":
                df = df[df['nome_regiao'] == regiao_selecionada]
        
        # Filtro por UF
        if 'sigla_uf' in df.columns:
            ufs = sorted(df['sigla_uf'].unique())
            uf_selecionada = st.selectbox("Estado (UF)", ["Todos"] + ufs)
            if uf_selecionada != "Todos":
                df = df[df['sigla_uf'] == uf_selecionada]
        
        # Busca por nome
        busca = st.text_input("Buscar município")
        if busca:
            df = df[df['nome_municipio'].str.contains(busca, case=False, na=False)]
    
    with col_main:
        st.markdown(f"### 📋 Dados ({len(df)} registros)")
        st.dataframe(
            df,
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        # Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name="municipios_ibge.csv",
            mime="text/csv"
        )
else:
    st.info("👈 Clique em 'Atualizar Municípios IBGE' na barra lateral para carregar os dados.")
