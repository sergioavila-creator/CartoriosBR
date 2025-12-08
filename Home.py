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
        
        st.write("")
        
        # Botão de Atualização Geral
        if st.button("🔄 Atualizar Todas as Bases", type="primary", use_container_width=True):
            import subprocess
            import sys
            import os
            
            status_box = st.status("🚀 Atualizando todas as bases de dados...", expanded=True)
            
            scripts = [
                ("Municípios IBGE", "extrair_municipios_ibge.py"),
                ("Justiça Aberta CNJ", "extrair_cnj_analytics.py"),
                ("Cadastro CNJ", "update_cnj_registry.py"),
                ("Receita TJRJ", "update_tjrj_revenue.py")
            ]
            
            results = []
            for nome, script in scripts:
                status_box.write(f"📥 Atualizando {nome}...")
                try:
                    result = subprocess.run(
                        [sys.executable, script],
                        capture_output=True,
                        text=True,
                        cwd=os.getcwd(),
                        timeout=300  # 5 minutos por script
                    )
                    
                    if result.returncode == 0:
                        results.append((nome, "✅", "Sucesso"))
                        status_box.write(f"✅ {nome} concluído")
                    else:
                        results.append((nome, "❌", "Erro"))
                        status_box.write(f"❌ {nome} falhou")
                except Exception as e:
                    results.append((nome, "❌", str(e)))
                    status_box.write(f"❌ {nome} erro: {str(e)[:50]}")
            
            # Resumo final
            sucessos = sum(1 for _, status, _ in results if status == "✅")
            total = len(results)
            
            if sucessos == total:
                status_box.update(label=f"✅ Todas as {total} bases atualizadas!", state="complete", expanded=False)
                st.balloons()
            else:
                status_box.update(label=f"⚠️ {sucessos}/{total} bases atualizadas", state="error", expanded=True)
            
            # Tabela de resultados
            with st.expander("📊 Detalhes da Atualização"):
                import pandas as pd
                df_results = pd.DataFrame(results, columns=["Base", "Status", "Mensagem"])
                st.dataframe(df_results, use_container_width=True, hide_index=True)

# ============================================================================
# MAIN CONTENT
# ============================================================================

st.markdown("""
## Bem-vindo ao Sistema de Inteligência 📊

**O sistema integra os dados da API de cadastro CNJ e do Relatorio de Receitas Extrajudiciais do TJRJ.**

Para acessar as funcionalidades completas, faça login na barra lateral.

### 📍 Módulos Disponíveis
""")

col1, col2, col3, col4 = st.columns(4)

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
    ### ⚖️ Justiça Aberta CNJ
    
    **Analytics e Consolidação**
    - Painéis do Justiça em Números
    - Monitoramento de Arquivos CSV
    - Upload e Consolidação de Bases
    - Integração com Google Sheets
    - **Requer Login**
    """)

with col3:
    st.markdown("""
    ### 💰 Receita TJRJ
    
    **Análise Financeira Extrajudicial**
    - Dados de faturamento e produtividade
    - Análise por atribuição e cidade
    - Comparativos de mercado
    - Detalhamento por serventia
    - **Requer Login**
    """)

with col4:
    st.markdown("""
    ### 🏙️ Municípios IBGE
    
    **Base Oficial de Municípios**
    - Dados completos do Brasil
    - API oficial do IBGE
    - Filtros por Região e Estado
    - Atualização automática
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
