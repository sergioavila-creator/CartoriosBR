"""
Diagnóstico da API CNJ
Testa conectividade e resposta da API
"""
import requests
from zeep import Client
from zeep.transports import Transport
from requests import Session
import xml.etree.ElementTree as ET
import sys

# Redireciona output para arquivo
log_file = open('diagnostico_resultado.txt', 'w', encoding='utf-8')
sys.stdout = log_file

print("=" * 60)
print("DIAGNÓSTICO API CNJ - Serventias Extrajudiciais")
print("=" * 60)

# Teste 1: Verificar se o WSDL está acessível
print("\n[1/4] Testando acesso ao WSDL...")
wsdl_url = "https://www.cnj.jus.br/corregedoria/ws/extraJudicial.php?wsdl"

try:
    response = requests.get(wsdl_url, timeout=10)
    if response.status_code == 200:
        print(f"✓ WSDL acessível (Status: {response.status_code})")
        print(f"  Tamanho: {len(response.content)} bytes")
    else:
        print(f"✗ WSDL retornou status: {response.status_code}")
except Exception as e:
    print(f"✗ Erro ao acessar WSDL: {e}")
    exit(1)

# Teste 2: Inicializar cliente SOAP
print("\n[2/4] Inicializando cliente SOAP...")
try:
    session = Session()
    session.timeout = 30
    transport = Transport(session=session)
    client = Client(wsdl_url, transport=transport)
    print("✓ Cliente SOAP inicializado")
    
    # Lista operações disponíveis
    print("\n  Operações disponíveis:")
    for service in client.wsdl.services.values():
        for port in service.ports.values():
            for operation in port.binding._operations.values():
                print(f"    - {operation.name}")
except Exception as e:
    print(f"✗ Erro ao inicializar cliente: {e}")
    exit(1)

# Teste 3: Fazer chamada real à API
print("\n[3/4] Testando chamada à API (período curto)...")
print("  Parâmetros:")
print("    dt_inicio: 01/12/2024")
print("    dt_final: 08/12/2024")
print("    ind_uf: RJ")
print("\n  Aguardando resposta (timeout: 30s)...")

try:
    response = client.service.servico(
        dt_inicio="01/12/2024",
        dt_final="08/12/2024",
        ind_uf="RJ"
    )
    print("✓ API respondeu!")
    
    # Teste 4: Analisar resposta
    print("\n[4/4] Analisando resposta...")
    
    if hasattr(response, 'serventias'):
        xml_data = response.serventias
        print(f"  Tipo de resposta: {type(xml_data)}")
        print(f"  Tamanho: {len(str(xml_data))} caracteres")
        
        if xml_data and len(str(xml_data).strip()) > 0:
            print("\n  Conteúdo XML (primeiros 500 caracteres):")
            print("  " + "-" * 56)
            print(f"  {str(xml_data)[:500]}")
            print("  " + "-" * 56)
            
            # Tentar parsear XML
            try:
                root = ET.fromstring(xml_data)
                serventias = root.findall('.//serventia')
                print(f"\n  ✓ XML parseado com sucesso!")
                print(f"  ✓ Serventias encontradas: {len(serventias)}")
                
                if len(serventias) > 0:
                    print(f"\n  Exemplo de serventia (primeira):")
                    for child in serventias[0]:
                        print(f"    {child.tag}: {child.text}")
                else:
                    print("\n  ⚠ XML válido mas sem serventias no período")
                    print("    Isso pode significar:")
                    print("    - Período sem dados disponíveis")
                    print("    - API retorna vazio para RJ neste período")
                    
            except ET.ParseError as e:
                print(f"\n  ✗ Erro ao parsear XML: {e}")
                print("    A resposta não está em formato XML válido")
        else:
            print("\n  ⚠ Resposta vazia")
            print("    A API respondeu mas não retornou dados")
    else:
        print(f"  ⚠ Resposta sem campo 'serventias'")
        print(f"  Estrutura da resposta: {dir(response)}")
        
except requests.exceptions.ReadTimeout:
    print("✗ TIMEOUT - API não respondeu em 30 segundos")
    print("  A API está muito lenta ou sobrecarregada")
except Exception as e:
    print(f"✗ Erro na chamada: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("DIAGNÓSTICO CONCLUÍDO")
print("=" * 60)
