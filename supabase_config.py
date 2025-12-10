import os
from supabase import create_client, Client
import toml

# IMPORTANTE: Credenciais devem estar em secrets.toml ou variáveis de ambiente
# NUNCA commitar credenciais no código!

def get_supabase_client() -> Client:
    """Retorna cliente Supabase autenticado"""
    # Tenta ler de variáveis de ambiente primeiro
    url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
    key = os.environ.get("SUPABASE_KEY", SUPABASE_KEY)
    
    # Tenta ler de secrets.toml se disponível (para Streamlit Cloud)
    try:
        if os.path.exists(".streamlit/secrets.toml"):
            data = toml.load(".streamlit/secrets.toml")
            if "SUPABASE_URL" in data:
                url = data["SUPABASE_URL"]
            if "SUPABASE_KEY" in data:
                key = data["SUPABASE_KEY"]
    except:
        pass
        
    return create_client(url, key)
