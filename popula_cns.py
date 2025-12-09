import os
import pandas as pd
import gspread
import cloud_processo
from logging_utils import print_start_log, print_end_log
import sys

def main():
    start_time = print_start_log("Serviço Independente: População de CNS")
    
    try:
        # 1. Conectar ao Google Sheets
        print("Conectando ao Google Sheets...")
        if "GCP_SERVICE_ACCOUNT" in os.environ:
             import json
             creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
             gc = gspread.service_account_from_dict(creds_dict)
        else:
             gc = gspread.service_account()
        
        # ID da Planilha TJRJ (Prioridade: Env Var -> Hardcoded)
        SHEET_ID = os.environ.get('SHEET_ID', '1SkxwQoAnNpcNBg1niLpaRaMs79h8rp143NPgsr1EAXo') 
        print(f"Abrindo planilha ID: {SHEET_ID}")
        sh = gc.open_by_key(SHEET_ID)
        
        # 2. Ler Dados Brutos Atuais
        print("Lendo aba 'Dados Brutos' (buscando por nome aproximado)...")
        ws = None
        target_name = "Dados Brutos"
        
        all_worksheets = sh.worksheets()
        for s in all_worksheets:
            # Compara removendo espaços extras e ignorando case
            if s.title.strip().upper() == target_name.upper():
                ws = s
                print(f"   -> Encontrada aba: '{s.title}'")
                break
        
        if not ws:
            print(f"❌ Erro: Aba '{target_name}' não encontrada!")
            print("   Abas disponíveis (Raw):")
            for s in all_worksheets:
                print(f"   - '{s.title}' (len={len(s.title)})")
            return

        data = ws.get_all_records()
        df_brutos = pd.DataFrame(data)
        
        if df_brutos.empty:
            print("Aba 'Dados Brutos' está vazia.")
            sys.exit(0)
            
        print(f"Lidas {len(df_brutos)} linhas.")
        
        # 3. Remover CNS antigo se existir (para forçar re-mapeamento)
        if 'CNS' in df_brutos.columns:
            df_brutos.drop(columns=['CNS'], inplace=True)
            
        # 4. Executar Enriquecimento
        df_enriquecido = cloud_processo.enrich_tjrj_with_cns(df_brutos)
        
        # 5. Salvar de volta
        print("Salvando dados enriquecidos...")
        
        # Snapshot de Debug
        from logging_utils import save_debug_snapshot
        save_debug_snapshot(df_enriquecido, "tjrj_cns_enriquecido")
        
        ws.clear()
        ws.update([df_enriquecido.columns.values.tolist()] + df_enriquecido.astype(str).values.tolist(), value_input_option='USER_ENTERED')
        
        print("✅ Dados atualizados com sucesso na aba 'Dados Brutos'.")
        print_end_log(start_time, success=True)
        
    except Exception as e:
        print(f"Erro: {e}")
        print_end_log(start_time, success=False, error_msg=str(e))

if __name__ == "__main__":
    main()
