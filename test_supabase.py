import supabase_config
import sys

def test_connection():
    print("--- Teste de Conexão Supabase ---")
    
    try:
        # 1. Inicializa Cliente
        print("1. Inicializando cliente (lendo credenciais)...")
        client = supabase_config.get_supabase_client()
        print(f"   URL: {client.supabase_url}")
        print("   Cliente criado com sucesso.")
        
        # 2. Teste de Leitura (Tabela Arrecadacao)
        print("\n2. Testando leitura da tabela 'arrecadacao'...")
        try:
            # Tenta buscar apenas 1 registro para ver se a tabela existe e é acessível
            response = client.table("arrecadacao").select("count", count="exact").limit(1).execute()
            count = response.count
            print(f"   ✅ SUCESSO! Conexão estabelecida.")
            print(f"   Registros na tabela 'arrecadacao': {count}")
            
        except Exception as query_err:
            print(f"   ❌ Erro ao consultar tabela 'arrecadacao'.")
            print(f"   Detalhe: {query_err}")
            print("   (DICA: Verifique se você rodou o script SQL de criação das tabelas no Supabase)")

        # 3. Teste de Leitura (Tabela Serventias)
        print("\n3. Testando leitura da tabela 'serventias'...")
        try:
            response = client.table("serventias").select("count", count="exact").limit(1).execute()
            count = response.count
            print(f"   ✅ SUCESSO! Tabela 'serventias' acessível.")
            print(f"   Registros na tabela: {count}")
        except Exception as query_err:
            print(f"   ❌ Erro ao consultar tabela 'serventias'.")
            print(f"   Detalhe: {query_err}")

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO NA CONEXÃO:")
        print(f"{e}")
        print("\nVerifique seu arquivo supabase_config.py e .streamlit/secrets.toml")

if __name__ == "__main__":
    test_connection()
