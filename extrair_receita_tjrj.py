import cloud_processo
import sys

if __name__ == "__main__":
    from logging_utils import print_start_log, print_end_log
    
    start_time = print_start_log("Extração Receitas TJRJ")
    
    try:
        # Chama a função principal do módulo cloud_processo
        # Passa None como request, pois não é uma requisição HTTP real
        res = cloud_processo.cloud_main(None)
        print(f"Resultado: {res}")
        print_end_log(start_time, success=True)
        sys.exit(0)
    except Exception as e:
        print(f"Erro fatal: {e}")
        print_end_log(start_time, success=False, error_msg=str(e))
        sys.exit(1)
