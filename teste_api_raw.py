"""
Teste detalhado da API CNJ - Imprime resposta RAW
"""
from zeep import Client
from zeep.transports import Transport
from requests import Session
import sys

# Redireciona output
log_file = open('teste_api_raw.txt', 'w', encoding='utf-8')
sys.stdout = log_file

print("=" * 70)
print("TESTE RAW API CNJ")
print("=" * 70)

# Inicializa cliente
print("\n[1] Inicializando cliente SOAP...")
session = Session()
session.timeout = 30
transport = Transport(session=session)
client = Client("https://www.cnj.jus.br/corregedoria/ws/extraJudicial.php?wsdl", transport=transport)
print("✓ Cliente inicializado")

# Teste com diferentes parâmetros
testes = [
    {"dt_inicio": "01/01/2024", "dt_final": "31/12/2024", "ind_uf": "RJ"},
    {"dt_inicio": "01/01/2023", "dt_final": "31/12/2023", "ind_uf": "RJ"},
    {"dt_inicio": "01/01/2020", "dt_final": "31/12/2020", "ind_uf": "SP"},
    {"dt_inicio": "01/06/2024", "dt_final": "30/06/2024", "ind_uf": "RJ"},
]

for i, params in enumerate(testes, 1):
    print(f"\n{'=' * 70}")
    print(f"[{i}] TESTE {i}/4")
    print(f"{'=' * 70}")
    print(f"Parâmetros: {params}")
    
    try:
        print("\nChamando API...")
        response = client.service.servico(**params)
        
        print(f"\n✓ API respondeu!")
        print(f"Tipo da resposta: {type(response)}")
        print(f"Tamanho: {len(str(response))} caracteres")
        
        # Imprime resposta completa
        print(f"\nRESPOSTA COMPLETA:")
        print("-" * 70)
        print(response)
        print("-" * 70)
        
        # Tenta acessar como objeto
        if hasattr(response, 'serventias'):
            print(f"\n✓ Tem campo 'serventias'")
            print(f"Conteúdo: {response.serventias[:500] if response.serventias else 'VAZIO'}")
        else:
            print(f"\n✗ NÃO tem campo 'serventias'")
        
        # Verifica se é string
        if isinstance(response, str):
            print(f"\n✓ É string")
            if len(response.strip()) == 0:
                print("  ⚠ String VAZIA")
            elif response.strip().startswith('<'):
                print("  ✓ Parece XML")
                print(f"  Primeiros 300 caracteres:")
                print(f"  {response[:300]}")
            else:
                print(f"  ⚠ Não parece XML")
                print(f"  Conteúdo: {response[:200]}")
        
    except Exception as e:
        print(f"\n✗ ERRO: {type(e).__name__}: {e}")

print(f"\n{'=' * 70}")
print("TESTES CONCLUÍDOS")
print(f"{'=' * 70}")

log_file.close()
print("Resultados salvos em teste_api_raw.txt", file=sys.__stdout__)
