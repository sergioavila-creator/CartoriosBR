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
    
    # Botão de alternância de tema
    st.markdown("**⚙️ Preferências**")
    
    # Detecta preferência do sistema via JavaScript (apenas na primeira vez)
    if 'theme' not in st.session_state:
        # Injeta JavaScript para detectar preferência do sistema
        st.markdown("""
        <script>
            const darkModePreference = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const theme = darkModePreference ? 'dark' : 'light';
            // Envia para Streamlit via query params (workaround)
            console.log('System theme preference:', theme);
        </script>
        """, unsafe_allow_html=True)
        
        # Por padrão, assume dark (será sobrescrito se sistema preferir light)
        st.session_state.theme = 'dark'
        st.session_state.theme_source = 'system'
    
    # Toggle de tema
    col1, col2 = st.columns([3, 1])
    with col1:
        theme_label = "Modo Escuro"
        if st.session_state.get('theme_source') == 'system':
            theme_label += " (Sistema)"
        st.write(theme_label)
    with col2:
        theme_toggle = st.checkbox("", value=st.session_state.theme == 'dark', key='theme_toggle', label_visibility='collapsed')
    
    # Se usuário mudou o toggle, marca como preferência manual
    if theme_toggle != (st.session_state.theme == 'dark'):
        st.session_state.theme = 'dark' if theme_toggle else 'light'
        st.session_state.theme_source = 'manual'
        st.info(f"🎨 Tema alterado para **{'Escuro' if theme_toggle else 'Claro'}**. Recarregue a página (F5) para aplicar.")
    
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
                ("Municípios IBGE", "extrair_municipios_ibge.py", []),
                ("Justiça Aberta CNJ - Download", "extrair_cnj_analytics.py", ["--action", "download"]),
                ("Justiça Aberta CNJ - Processar", "extrair_cnj_analytics.py", ["--action", "process"]),
                ("Cadastro CNJ", "extrair_cadastro_cnj.py", []),
                ("Receita TJRJ", "extrair_receita_tjrj.py", [])
            ]
            
            results = []
            for nome, script, args in scripts:
                status_box.write(f"📥 Atualizando {nome}...")
                try:
                    status_box.write(f"📥 Atualizando {nome} (Aguarde, processo em execução)...")
                    
                    # Cria container para logs
                    with status_box.expander(f"📜 Logs em tempo real: {nome}", expanded=True):
                        log_placeholder = st.empty()
                        
                    # Prepara ambiente para output sem buffer e modo VISUAL (não headless) para evitar bloqueio
                    env = os.environ.copy()
                    env["PYTHONUNBUFFERED"] = "1"
                    env["HEADLESS"] = "false"
                    
                    # Monta comando com argumentos
                    cmd = [sys.executable, "-u", script] + args
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, # Erros também vão para o stdout
                        text=True,
                        cwd=os.getcwd(),
                        env=env
                    )
                    
                    full_log = ""
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            full_log += line
                            # Atualiza logs visualmente (exibindo as últimas linhas para performance)
                            log_placeholder.code(full_log[-3000:], language="text")

                    if process.returncode == 0:
                        results.append((nome, "✅", "Sucesso"))
                        status_box.write(f"✅ {nome} concluído com sucesso!")
                    else:
                        results.append((nome, "❌", "Erro (Código de saída não zero)"))
                        status_box.write(f"❌ {nome} falhou. Verifique os logs acima.")
                        
                except Exception as e:
                    results.append((nome, "❌", str(e)))
                    status_box.write(f"❌ {nome} erro de execução: {str(e)[:100]}")
            
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
