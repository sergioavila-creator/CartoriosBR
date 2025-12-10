import os
from supabase import create_client, Client
import toml

# IMPORTANTE: Credenciais devem estar em secrets.toml ou variáveis de ambiente
# NUNCA commitar credenciais no código!

def get_supabase_client() -> Client:
    """Retorna cliente Supabase autenticado
    
    Credenciais devem estar em:
    1. Variáveis de ambiente: SUPABASE_URL e SUPABASE_KEY
    2. Arquivo .streamlit/secrets.toml
    """
    url = None
    key = None
    
    # Tenta ler de variáveis de ambiente primeiro
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Tenta ler de secrets.toml se disponível (para Streamlit Cloud)
    if not url or not key:
        try:
            if os.path.exists(".streamlit/secrets.toml"):
                data = toml.load(".streamlit/secrets.toml")
                url = data.get("SUPABASE_URL", url)
                key = data.get("SUPABASE_KEY", key)
        except Exception:
            pass
    
    if not url or not key:
        raise ValueError(
            "Credenciais Supabase não encontradas! "
            "Configure SUPABASE_URL e SUPABASE_KEY em variáveis de ambiente "
            "ou em .streamlit/secrets.toml"
        )
        
    return create_client(url, key)
