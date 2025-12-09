"""
Utilitário para gerenciar tema (claro/escuro) da aplicação
"""
import streamlit as st
import toml
import os

def apply_theme():
    """
    Aplica o tema escolhido pelo usuário
    Lê do session_state e injeta CSS customizado
    """
    # Pega tema do session_state (padrão: dark)
    theme = st.session_state.get('theme', 'dark')
    
    if theme == 'dark':
        # CSS para modo escuro
        st.markdown("""
        <style>
            /* Força modo escuro */
            :root {
                --background-color: #0E1117;
                --secondary-background-color: #262730;
                --text-color: #FAFAFA;
                --primary-color: #4A9EFF;
            }
            
            /* Aplica cores */
            .stApp {
                background-color: var(--background-color);
                color: var(--text-color);
            }
            
            .stSidebar {
                background-color: var(--secondary-background-color);
            }
            
            /* Cards e containers */
            .element-container, .stMarkdown, .stDataFrame {
                color: var(--text-color);
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        # CSS para modo claro
        st.markdown("""
        <style>
            /* Força modo claro */
            :root {
                --background-color: #FFFFFF;
                --secondary-background-color: #F0F2F6;
                --text-color: #31333F;
                --primary-color: #004B8D;
            }
            
            .stApp {
                background-color: var(--background-color);
                color: var(--text-color);
            }
            
            .stSidebar {
                background-color: var(--secondary-background-color);
            }
        </style>
        """, unsafe_allow_html=True)

def get_theme():
    """Retorna o tema atual"""
    return st.session_state.get('theme', 'dark')

def set_theme(theme):
    """Define o tema (dark ou light)"""
    st.session_state.theme = theme
