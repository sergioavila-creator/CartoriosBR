"""
Utilitário para normalização de CNS (Código Nacional de Serventia)
Formato padrão: 6 dígitos numéricos com zeros à esquerda
Exemplo: "00.005-9" → "000059"
"""

def normalize_cns(cns_value):
    """
    Normaliza CNS para formato padrão: 6 dígitos com zeros à esquerda
    
    Args:
        cns_value: String ou número representando o CNS
        
    Returns:
        String com 6 dígitos (ex: "000059")
    """
    if cns_value is None or cns_value == '':
        return ''
    
    # Converte para string e remove caracteres não numéricos
    cns_str = str(cns_value)
    cns_clean = ''.join(filter(str.isdigit, cns_str))
    
    # Adiciona zeros à esquerda para completar 6 dígitos
    cns_normalized = cns_clean.zfill(6)
    
    return cns_normalized

def normalize_cns_column(df, column_name='CNS'):
    """
    Normaliza coluna CNS em um DataFrame pandas
    
    Args:
        df: pandas DataFrame
        column_name: Nome da coluna CNS (padrão: 'CNS')
        
    Returns:
        DataFrame com coluna CNS normalizada
    """
    if column_name in df.columns:
        df[column_name] = df[column_name].apply(normalize_cns)
    return df
