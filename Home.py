"""
🏠 Sistema de Inteligência - Cartórios BR
Sistema de Inteligência para Análise de Cartórios do Brasil
"""

import streamlit as st
import auth_utils # Módulo de autenticação

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="Cartórios BR - Inteligência",
    page_icon="🏠",
    layout="wide"
)

# ============================================================================
# HEADER
# ============================================================================
col_logo, col_title = st.columns([1, 3])

with col_logo:
    st.image("logo_ribrj.png", width=200)

with col_title:
    st.title("Sistema de Inteligência - Cartórios BR")
    st.markdown("**Registro de Imóveis do Brasil - Análises Estratégicas**")

st.divider()

# ============================================================================
# SIDEBAR COM LOGIN
# ============================================================================
# Renderiza a sidebar de login importada do auth_utils
auth_utils.render_login_sidebar()

with st.sidebar:
    st.markdown("---")
    st.caption("v2.1 - Sistema Integrado API CNJ + TJRJ")
    
    # Botão de Limpar Cache (Admin)
    if auth_utils.check_password():
        st.divider()
        st.markdown("**Administração**")
        if st.button("🗑️ Limpar Cache"):
            st.cache_data.clear()
            st.success("Cache limpo! Recarregue (F5).")

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.markdown("""
## Bem-vindo ao Sistema de Inteligência 📊

**O sistema integra os dados da API de cadastro CNJ e do Relatorio de Receitas Extrajudiciais do TJRJ.**

Para acessar as funcionalidades completas, faça login na barra lateral.

### 📍 Módulos Disponíveis
""")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📋 Cadastro CNJ
    
    **Dados Cadastrais Oficiais**
    - Consulta direta à API do CNJ
    - Status das serventias em tempo real
    - Filtros por Estado e Data
    - Distribuição geográfica
    - **Requer Login**
    """)

with col2:
    st.markdown("""
    ### 💰 Receita TJRJ
    
    **Análise Financeira Extrajudicial**
    - Dados de faturamento e produtividade
    - Análise por atribuição e cidade
    - Comparativos de mercado
    - Detalhamento por serventia
    - **Requer Login**
    """)

with col3:
    st.markdown("""
    ### ⚖️ Justiça Aberta CNJ
    
    **Analytics e Consolidação**
    - Painéis do Justiça em Números
    - Monitoramento de Arquivos CSV
    - Upload e Consolidação de Bases
    - Integração com Google Sheets
    - **Requer Login**
    """)

st.divider()

# ============================================================================
# INFORMAÇÕES ADICIONAIS
# ============================================================================

with st.expander("ℹ️ Sobre o Sistema"):
    st.markdown("""
    ### Arquitetura de Integração
    
    Este sistema consolida dados de múltiplas fontes oficiais para oferecer uma visão unificada:
    
    1. **API do CNJ (SOAP)**: Conexão direta com o Conselho Nacional de Justiça para dados cadastrais fidedignos.
    2. **Processamento TJRJ**: Análise estruturada dos relatórios de receitas extrajudiciais.
    3. **Cloud Intelligence**: Armazenamento e processamento escalável de grandes volumes de dados.
    
    ### Segurança
    O acesso aos dados detalhados é restrito a usuários autorizados via autenticação segura com expiração automática de sessão (30 minutos).
    """)

with st.expander("🔄 Histórico de Versões"):
    st.markdown("""
    ### Versão 2.1 (Atual)
    - 🔒 Autenticação unificada com timeout
    - 🔄 Integração completa API CNJ + Streamlit
    - 📊 Módulo de Receita TJRJ renovado
    
    ### Versão 2.0
    - ✅ Lançamento do módulo CNJ
    """)

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.caption("© 2024 RIBRJ - Registro de Imóveis do Brasil | Desenvolvido com ❤️ para os Cartórios do Brasil")
