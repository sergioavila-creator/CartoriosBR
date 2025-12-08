import os
import glob

# Files to keep
keep = [
    "1_📋_Cadastro_CNJ.py",
    "2_💰_Receita_TJRJ.py"
]

# Navigate to pages directory
pages_dir = os.path.join(os.getcwd(), "pages")
print(f"Cleaning pages directory: {pages_dir}")

for filename in os.listdir(pages_dir):
    if filename.endswith(".py") and filename not in keep:
        file_path = os.path.join(pages_dir, filename)
        try:
            os.remove(file_path)
            print(f"Deleted: {filename}")
        except Exception as e:
            print(f"Error deleting {filename}: {e}")
            
print("Cleanup complete.")
