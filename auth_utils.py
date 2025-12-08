import streamlit as st
from datetime import datetime, timedelta

def check_password():
    """
    Verifica se o usuário está autenticado e se a sessão é válida (30 min).
    Retorna True se autenticado, False caso contrário.
    Se não autenticado, interrompe a execução (st.stop()) das páginas protegidas
    ou exibe o formulário de login (se chamado na Home sem sidebar=False).
    """

    # Configuração de timeout (30 minutos)
    TIMEOUT_MINUTES = 30

    # Inicializa estado se não existir
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    if 'login_time' not in st.session_state:
        st.session_state['login_time'] = None

    # Verifica se o tempo expirou
    if st.session_state['authentication_status']:
        if st.session_state['login_time']:
            elapsed_time = datetime.now() - st.session_state['login_time']
            if elapsed_time > timedelta(minutes=TIMEOUT_MINUTES):
                st.session_state['authentication_status'] = None
                st.session_state['login_time'] = None
                st.warning("Sessão expirada. Por favor, faça login novamente.")
                return False
        else:
            # Caso raro onde status é True mas não tem time (segurança reset)
            st.session_state['authentication_status'] = None
            return False

    # Se já autenticado e válido
    if st.session_state['authentication_status']:
        return True

    return False

def render_login_sidebar():
    """Renderiza o formulário de login na sidebar"""
    
    # Se já logado, mostra info de sessão e botão de logout
    if check_password():
        with st.sidebar:
            st.success(f"🔓 Logado como Admin")
            if st.button("Sair / Logout"):
                st.session_state['authentication_status'] = None
                st.session_state['login_time'] = None
                st.rerun()
        return

    # Se não logado, mostra form
    with st.sidebar:
        st.header("🔒 Acesso Restrito")
        
        # Pega a senha correta dos secrets ou usa default
        try:
            correct_password = st.secrets["general"]["password"]
        except:
            correct_password = "admin" # Fallback

        password_input = st.text_input("Senha de Acesso", type="password")
        
        if st.button("Entrar"):
            if password_input == correct_password:
                st.session_state['authentication_status'] = True
                st.session_state['login_time'] = datetime.now()
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Senha incorreta")
