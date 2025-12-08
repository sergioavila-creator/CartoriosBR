import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import glob
import sys
from datetime import datetime

# Adiciona o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import auth_utils

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="Justiça Aberta CNJ - Cartórios BR",
    page_icon="⚖️",
    layout="wide"
)

# ============================================================================
# VERIFICAÇÃO DE AUTENTICAÇÃO
# ============================================================================
if not auth_utils.check_password():
    st.warning("⚠️ Acesso restrito. Por favor, faça login na página inicial.")
    st.stop()

# ============================================================================
# CONSTANTES
# ============================================================================
NEW_SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"
WORKSHEET_NAME = "Consolidado"

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
    if st.button("🔄 Atualizar Justiça Aberta", use_container_width=True):
        import subprocess
        
        status_box = st.status("🚀 Iniciando atualização automática...", expanded=True)
        try:
            status_box.write("Iniciando motor de extração (Selenium)...")
            # Executa o script como subserviço para isolar o ambiente
            result = subprocess.run(
                [sys.executable, "extrair_cnj_analytics.py"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(__file__)) # Raiz do projeto
            )
            
            if result.returncode == 0:
                status_box.update(label="✅ Atualização concluída!", state="complete", expanded=False)
                st.success("Dados atualizados com sucesso! A planilha foi populada.")
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

# ============================================================================
# FUNÇÕES
# ============================================================================
def autenticar_google_sheets():
    """Autentica com Google Sheets usando st.secrets"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    return gspread.authorize(credentials)

def enviar_para_sheets(df):
    """Envia dados para a nova planilha"""
    try:
        gc = autenticar_google_sheets()
        sh = gc.open_by_key(NEW_SHEET_ID)
        
        try:
            ws = sh.worksheet(WORKSHEET_NAME)
            ws.clear()
        except:
            ws = sh.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=50)
            
        # Adiciona coluna de controle
        df_export = df.copy()
        df_export.insert(0, 'data_upload', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # Converte tipos complexos p/ string para evitar erro de JSON
        df_export = df_export.astype(str)
        
        # Prepara lista de listas
        dados = [df_export.columns.values.tolist()] + df_export.values.tolist()
        
        ws.update(dados, value_input_option='RAW')
        
        # Formatação: Congelar Topo e Filtro
        try:
            ws.freeze(rows=1)
            ws.set_basic_filter(1, 1, len(df_export)+1, len(df_export.columns))
        except Exception as e_fmt:
            print(f"Aviso de formatação: {e_fmt}")
            
        return True, len(df_export)
        
    except Exception as e:
        return False, str(e)

# ============================================================================
# INTERFACE
# ============================================================================
st.title("⚖️ Justiça Aberta CNJ")
st.markdown("Consolidação de dados do painel Justiça em Números (Analytics CNJ).")

col_left, col_right = st.columns([1, 2])

df_final = pd.DataFrame()

with col_left:
    st.subheader("1. Fontes de Dados")
    
    # Opção 1: Arquivos Locais (do Servidor)
    local_csvs = glob.glob("*.csv")
    use_local = st.checkbox(f"Usar CSVs locais ({len(local_csvs)} encontrados)", value=True if local_csvs else False)
    
    selected_local = []
    if use_local and local_csvs:
        selected_local = st.multiselect("Selecionar arquivos locais:", local_csvs, default=local_csvs)
        
    # Opção 2: Upload
    st.write("")
    uploaded_files = st.file_uploader("Carregar arquivos do computador", type=['csv', 'xlsx'], accept_multiple_files=True)

    # Processamento
    dfs_list = []
    
    # Lê locais
    if match_local := selected_local:
        for f in match_local:
            try:
                df = pd.read_csv(f)
                df['origem_arquivo'] = f
                dfs_list.append(df)
            except Exception as e:
                st.error(f"Erro ao ler {f}: {e}")
                
    # Lê uploads
    if uploaded_files:
        for f in uploaded_files:
            try:
                if f.name.endswith('.xlsx'):
                     df = pd.read_excel(f)
                else:
                     df = pd.read_csv(f)
                df['origem_arquivo'] = f.name
                dfs_list.append(df)
            except Exception as e:
                st.error(f"Erro ao ler upload {f.name}: {e}")
    
    if dfs_list:
        df_final = pd.concat(dfs_list, ignore_index=True)
        st.success(f"✅ {len(df_final)} linhas carregadas de {len(dfs_list)} arquivos.")
    else:
        st.info("👈 Selecione ou carregue arquivos CSV/Excel para começar.")

with col_right:
    st.subheader("2. Visualização e Envio")
    
    if not df_final.empty:
        # Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros", len(df_final))
        c2.metric("Colunas", len(df_final.columns))
        c3.metric("Arquivos", df_final['origem_arquivo'].nunique() if 'origem_arquivo' in df_final.columns else 1)
        
        # Preview
        st.dataframe(df_final.head(100), use_container_width=True, height=400)
        
        st.divider()
        st.markdown(f"### 🚀 Enviar para Google Sheets")
        st.markdown(f"**Destino:** Planilha ID `{NEW_SHEET_ID}`")
        
        if st.button("📤 Enviar Dados Consolidados", type="primary", use_container_width=True):
            with st.spinner("Enviando dados..."):
                sucesso, msg = enviar_para_sheets(df_final)
                if sucesso:
                    st.balloons()
                    st.success(f"Sucesso! {msg} linhas enviadas para a aba '{WORKSHEET_NAME}'.")
                    st.markdown(f"[🔗 Abrir Planilha](https://docs.google.com/spreadsheets/d/{NEW_SHEET_ID})")
                else:
                    st.error(f"Falha no envio: {msg}")
    else:
        st.warning("Nenhum dado carregado para visualização.")
