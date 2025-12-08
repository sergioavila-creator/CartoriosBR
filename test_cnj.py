"""
Script de teste para API CNJ
"""
from cnj_api import CNJClient
from datetime import datetime

print("=== Teste API CNJ ===\n")

try:
    print("1. Inicializando cliente...")
    client = CNJClient()
    print("✓ Cliente inicializado\n")
    
    print("2. Testando consulta de serventias ativas...")
    print("   Período: 01/01/2024 a 31/12/2024")
    print("   UF: RJ\n")
    
    df = client.buscar_serventias_ativas("01/01/2024", "31/12/2024", "RJ")
    
    print(f"✓ Consulta concluída!")
    print(f"   Registros retornados: {len(df)}")
    
    if not df.empty:
        print(f"\n3. Colunas disponíveis:")
        for col in df.columns:
            print(f"   - {col}")
        
        print(f"\n4. Primeiros 3 registros:")
        print(df.head(3).to_string())
    else:
        print("\n⚠ DataFrame vazio - API retornou sem dados")
        print("   Possíveis causas:")
        print("   - Período sem serventias ativas")
        print("   - Formato de resposta diferente do esperado")
        print("   - API temporariamente indisponível")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
