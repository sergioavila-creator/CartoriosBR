import gspread
import os
import json
import toml

SECTION_ID = "1SkxwQoAnNpcNBg1niLpaRaMs79h8rp143NPgsr1weZeekg8E2CbOiQfE"

def get_gspread_client():
    """Authenticates with Google Sheets using available credentials."""
    print("Connecting to Google Sheets...")
    
    # 1. Try environment variable (GitHub Actions/Cloud)
    if "GCP_SERVICE_ACCOUNT" in os.environ:
        try:
            creds_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
            return gspread.service_account_from_dict(creds_dict)
        except Exception as e:
            print(f"Error loading from env: {e}")

    # 2. Try local secrets.toml (Streamlit)
    if os.path.exists(".streamlit/secrets.toml"):
        try:
            secrets = toml.load(".streamlit/secrets.toml")
            if "gcp_service_account" in secrets:
                creds_dict = dict(secrets["gcp_service_account"])
                return gspread.service_account_from_dict(creds_dict)
        except Exception as e:
            print(f"Error loading from secrets.toml: {e}")

    # 3. Fallback to default gspread (looks for service_account.json)
    try:
        return gspread.service_account()
    except Exception as e:
        print(f"Error with default service_account: {e}")
        return None

def format_sheet():
    gc = get_gspread_client()
    if not gc:
        print("Failed to authenticate.")
        return

    try:
        # Try to find the sheet in openall() list to avoid 404 on ID issues
        print("Listing sheets...")
        sheets = gc.openall()
        target_sh = None
        for s in sheets:
            # Match by explicit title as fallback for ID issues
            if s.title == "API CNJ Cartorios":
                target_sh = s
                print(f"Found sheet by title: {s.title} (ID: {s.id})")
                break
            
            # Check if ID matches
            if s.id.strip() == SECTION_ID.strip():
                target_sh = s
                break
        
        if not target_sh:
            print(f"Sheet 'API CNJ Cartorios' or ID {SECTION_ID} not found.")
            print("Available sheets:")
            for s in sheets:
                print(f"- {s.title} ({s.id})")
            return

        sh = target_sh
        print(f"Opened spreadsheet: {sh.title}")
        
        # Access the first worksheet
        ws = sh.sheet1
        print(f"Targeting worksheet: {ws.title}")

        # 1. Freeze the first row
        print("Freezing the first row...")
        ws.freeze(rows=1)
        
        # 2. Enable Auto-Filter
        num_rows = ws.row_count
        num_cols = ws.col_count
        ws.set_basic_filter(1, 1, num_rows, num_cols)
        print("Auto-filter enabled.")

        print("Formatting applied successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    format_sheet()
