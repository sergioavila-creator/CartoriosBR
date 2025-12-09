import os
from supabase import create_client, Client
import toml

# Configuração Hardcoded (Migrar para secrets.toml em produção)
# Project Ref extraído do JWT: ezshmkwbzfqffdlloyrwn
SUPABASE_URL = "https://ezshmkwbzfqffdloyrwn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6c2hta3diemZxZmZkbG95cnduIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTMxMDAyOCwiZXhwIjoyMDgwODg2MDI4fQ.9x8JcpAh6L7WACG0QgCNYGycESFVoWycv3WEDvIWhtU"

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
