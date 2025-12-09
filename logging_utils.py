"""
Utilitário para adicionar timestamps em logs de scripts.
"""
from datetime import datetime
from functools import wraps

def log_execution_time(func):
    """
    Decorator para adicionar timestamps de início e fim em funções.
    
    Uso:
        @log_execution_time
        def minha_funcao():
            # código
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"⏰ Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📝 Função: {func.__name__}")
        print(f"{'='*60}\n")
        
        try:
            result = func(*args, **kwargs)
            
            end_time = datetime.now()
            duration = end_time - start_time
            print(f"\n{'='*60}")
            print(f"✅ Sucesso!")
            print(f"⏰ Fim: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Duração: {duration}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time
            print(f"\n{'='*60}")
            print(f"❌ Erro: {e}")
            print(f"⏰ Fim: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Duração até erro: {duration}")
            print(f"{'='*60}\n")
            raise
    
    return wrapper


def print_start_log(script_name="Script"):
    """Imprime log de início padronizado."""
    start_time = datetime.now()
    print(f"\n{'='*60}")
    print(f"⏰ Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 {script_name}")
    print(f"{'='*60}\n")
    return start_time


def print_end_log(start_time, success=True, error_msg=None):
    """Imprime log de fim padronizado."""
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"\n{'='*60}")
    if success:
        print(f"✅ Concluído com sucesso!")
    else:
        print(f"❌ Erro: {error_msg}")
    print(f"⏱️  Duração: {duration}")
    print(f"{'='*60}\n")


def save_debug_snapshot(df, name_prefix):
    """
    Salva um snapshot do DataFrame em CSV na pasta 'dados_debug'.
    Útil para debug do assistente AI.
    """
    try:
        import os
        import pandas as pd
        
        # Cria pasta se não existir
        debug_dir = os.path.join(os.getcwd(), "dados_debug")
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        # Nome do arquivo com timestamp simples (YYYY-MM-DD) para não lotar, 
        # ou overwrite se preferir sempre o último. O user pediu "ultimas alterações".
        # Vamos usar apenas o nome_prefix.csv para manter sempre o state mais RECENTE.
        filename = f"{name_prefix}.csv"
        filepath = os.path.join(debug_dir, filename)
        
        df.to_csv(filepath, index=False, sep=';', encoding='utf-8')
        print(f"📸 Snapshot de debug salvo: {filepath}")
        
    except Exception as e:
        print(f"⚠️ Falha ao salvar snapshot de debug: {e}")
