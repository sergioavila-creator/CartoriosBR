"""
Script para baixar dados CNJ e salvar em CSV
"""
import sys
sys.path.insert(0, '.')

from cnj_api import CNJClient
import pandas as pd
from datetime import datetime

print("=" * 70)
print("DOWNLOAD DE DADOS CNJ")
print("=" * 70)

# Inicializa cliente
print("\n[1/3] Inicializando cliente CNJ...")
client = CNJClient(timeout=60)
print("✓ Cliente inicializado")

# Busca dados
print("\n[2/3] Buscando serventias ativas do RJ (2024)...")
print("  Período: 01/01/2024 a 31/12/2024")
print("  UF: RJ")
print("  Aguarde... (pode levar até 60 segundos)")

try:
    df = client.buscar_serventias_ativas("01/01/2024", "31/12/2024", "RJ")
    
    print(f"\n✓ Dados recebidos!")
    print(f"  Total de registros: {len(df)}")
    print(f"  Total de colunas: {len(df.columns)}")
    
    if not df.empty:
        # Salva em CSV
        print("\n[3/3] Salvando em CSV...")
        filename = f"cnj_dados_rj_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✓ Arquivo salvo: {filename}")
        
        # Mostra preview
        print(f"\nPrimeiras 5 colunas:")
        print(df.columns[:5].tolist())
        
        print(f"\nPrimeiros 3 registros:")
        print(df.head(3).to_string())
        
        print(f"\n{'=' * 70}")
        print("DOWNLOAD CONCLUÍDO COM SUCESSO!")
        print(f"Arquivo: {filename}")
        print(f"Registros: {len(df)}")
        print(f"{'=' * 70}")
    else:
        print("\n⚠ DataFrame vazio - API não retornou dados")
        
except Exception as e:
    print(f"\n✗ ERRO: {e}")
    import traceback
    traceback.print_exc()
