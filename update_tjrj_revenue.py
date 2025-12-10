"""
Script para atualizar dados da Receita TJRJ
Wrapper para integração com o botão de atualização geral
"""
import extrai_transp_tjrj

def main():
    print("Iniciando atualização da Receita TJRJ...")
    try:
        extrai_transp_tjrj.cloud_main(None)
        print("Receita TJRJ atualizada com sucesso!")
    except Exception as e:
        print(f"Erro na atualização: {e}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
