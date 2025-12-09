"""
Utilitário para detectar o locale do Google Sheets e retornar o separador correto para fórmulas.
"""

def detect_gsheets_locale(worksheet):
    """
    Detecta se o Google Sheets está configurado em inglês (vírgula) ou português/europeu (ponto-e-vírgula).
    
    Args:
        worksheet: Objeto worksheet do gspread
        
    Returns:
        str: ',' para inglês ou ';' para português/europeu
    """
    print("Detectando locale do Google Sheets...")
    try:
        # Usa uma célula temporária na última coluna disponível + 1
        # Pega o número de colunas atual para não exceder o grid
        num_cols = worksheet.col_count
        test_col = min(num_cols, 26)  # Usa no máximo coluna Z
        test_cell = f'{chr(64 + test_col)}1'
        
        # Testa inserindo uma fórmula simples com vírgula
        worksheet.update_acell(test_cell, '=IF(1>0,1,0)')
        test_result = worksheet.acell(test_cell).value
        
        if test_result == '1' or test_result == 1:
            separator = ','
            print("✓ Locale detectado: Inglês (separador: vírgula)")
        else:
            separator = ';'
            print("✓ Locale detectado: Português/Europeu (separador: ponto-e-vírgula)")
        
        # Limpa célula de teste
        worksheet.update_acell(test_cell, '')
        return separator
        
    except Exception as e:
        # Fallback: assume ponto-e-vírgula (mais comum no Brasil)
        print(f"⚠ Não foi possível detectar locale ({e}). Usando ponto-e-vírgula (padrão PT-BR)")
        return ';'


def build_formula(formula_template, separator):
    """
    Constrói uma fórmula substituindo o placeholder {SEP} pelo separador correto.
    
    Args:
        formula_template: String da fórmula com {SEP} como placeholder
        separator: ',' ou ';'
        
    Returns:
        str: Fórmula com separador correto
        
    Exemplo:
        >>> build_formula('=IF(A1>0{SEP}B1{SEP}0)', ';')
        '=IF(A1>0;B1;0)'
    """
    return formula_template.replace('{SEP}', separator)
