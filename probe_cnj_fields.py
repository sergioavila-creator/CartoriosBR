from cnj_api import CNJClient
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def probe_fields():
    client = CNJClient()
    # Try a range that definitely has data
    dt_inicio = "01/01/2024"
    dt_final = "31/01/2024"
    
    print(f"Querying {dt_inicio} to {dt_final}...")
    try:
        df = client.buscar_serventias_ativas(dt_inicio, dt_final, "RJ")
        
        if not df.empty:
            print(f"Found {len(df)} records.")
            print("Columns found:", df.columns.tolist())
            print("\nSample record (first one):")
            print(df.iloc[0].to_dict())
            
            # Check specifically for attribution-like fields
            attr_cols = [c for c in df.columns if 'atrib' in c.lower()]
            print("\nAttribution-related columns:", attr_cols)
            
            if 'atribuicao' in df.columns:
                non_null = df['atribuicao'].dropna().astype(str).str.strip().replace('', pd.NA).dropna()
                print(f"\nTotal 'atribuicao' values: {len(df['atribuicao'])}")
                print(f"Non-empty 'atribuicao' values: {len(non_null)}")
                if len(non_null) > 0:
                     print("Sample values:", non_null.head().tolist())
                else:
                     print("ALL values in 'atribuicao' are empty/None.")
            
        else:
            print("No records found in this period.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe_fields()
