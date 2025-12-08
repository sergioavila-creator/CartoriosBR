import gspread
import streamlit as st
import os

# Mock streamlit secrets if running standalone
if not hasattr(st, "secrets"):
    import toml
    try:
        st.secrets = toml.load(".streamlit/secrets.toml")
    except Exception as e:
        print(f"Error loading secrets: {e}")

try:
    print("Testing GSheets Connection...")
    
    if st and hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
         # Use dict directly
         creds = dict(st.secrets["gcp_service_account"])
         print(f"Using credentials from secrets: project_id={creds.get('project_id')}")
         gc = gspread.service_account_from_dict(creds)
    else:
         print("Using default service_account()")
         gc = gspread.service_account()
    
    sheet_id = st.secrets["SHEET_ID"]
    print(f"Opening Sheet ID: {sheet_id}")
    
    sh = gc.open_by_key(sheet_id)
    print(f"Successfully opened: {sh.title}")
    
    ws = sh.sheet1
    print(f"Reading first cell: {ws.acell('A1').value}")
    
except Exception as e:
    import traceback
    print("ERROR:")
    print(traceback.format_exc())
