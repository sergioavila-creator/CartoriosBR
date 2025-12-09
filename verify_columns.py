import gspread
import os
import toml
import pandas as pd
import json

SHEET_ID = "1Cx_ceynq_Y_pFKRUtFyHkLEJIvBvlWFjGo5LuOAvW-Y"

def check_columns():
    try:
        # Autenticação
        if os.path.exists(".streamlit/secrets.toml"):
            secrets = toml.load(".streamlit/secrets.toml")
            if "gcp_service_account" in secrets:
                creds_dict = dict(secrets["gcp_service_account"])
                gc = gspread.service_account_from_dict(creds_dict)
            else:
                gc = gspread.service_account()
        else:
            gc = gspread.service_account()
            
        sh = gc.open_by_key(SHEET_ID)
        
        # Check Arrecadacao
        try:
            ws = sh.worksheet("Arrecadacao")
            print(f"--- Columns in 'Arrecadacao' ---")
            header = ws.row_values(1)
            print(header)
            for col in header:
                print(f"'{col}'")
                if "Valor" in col:
                    print(f"  -> HEX: {col.encode('utf-8').hex()}")
        except Exception as e:
            print(f"Error accessing Arrecadacao: {e}")

    except Exception as e:
        print(f"Authentication error: {e}")

if __name__ == "__main__":
    check_columns()
