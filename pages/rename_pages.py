
import os
import sys
import io

# Configure stdout to use UTF-8 encoding to handle emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Use dynamic path instead of hardcoded one
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".")

p1 = os.path.join(base, "2_💰_Receita_TJRJ.py")
p2 = os.path.join(base, "3_⚖️_Justica_Aberta_CNJ.py")

temp = os.path.join(base, "temp_swap.py")

t1 = os.path.join(base, "3_💰_Receita_TJRJ.py") # Receita vai para 3
t2 = os.path.join(base, "2_⚖️_Justica_Aberta_CNJ.py") # Justiça vai para 2

print("Iniciando renomeação segura...")

# 1. 2_Receita -> Temp
if os.path.exists(p1):
    try:
        os.rename(p1, temp)
        print(f"Renomeado: {os.path.basename(p1)} -> temp")
    except Exception as e:
        print(f"Erro ao mover p1: {e}")
else:
    print(f"Arquivo p1 não encontrado: {p1}")

# 2. 3_Justica -> 2_Justica
if os.path.exists(p2):
    try:
        os.rename(p2, t2)
        print(f"Renomeado: {os.path.basename(p2)} -> {os.path.basename(t2)}")
    except Exception as e:
        print(f"Erro ao mover p2: {e}")

# 3. Temp -> 3_Receita
if os.path.exists(temp):
    try:
        os.rename(temp, t1)
        print(f"Renomeado: temp -> {os.path.basename(t1)}")
    except Exception as e:
        print(f"Erro ao mover temp: {e}")

print("Concluído.")
