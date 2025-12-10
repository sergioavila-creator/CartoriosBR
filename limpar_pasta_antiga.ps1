# Script para limpar a pasta antiga do OneDrive (exceto .venv)
# O .venv pode ser apagado manualmente depois se desejar

$pasta_antiga = "c:\Users\avila\OneDrive\Escritorio\site CartoiosRJ"

Write-Host "Removendo arquivos da pasta antiga (exceto .venv)..." -ForegroundColor Yellow

# Remover arquivos Python
Get-ChildItem -Path $pasta_antiga -Filter *.py -Recurse | Where-Object { $_.FullName -notlike "*\.venv\*" } | Remove-Item -Force -Verbose

# Remover pastas principais (exceto .venv)
$pastas_remover = @("pages", ".git", ".github", ".streamlit", "__pycache__", "dados_debug", "downloads_cnj", ".devcontainer")

foreach ($pasta in $pastas_remover) {
    $caminho = Join-Path $pasta_antiga $pasta
    if (Test-Path $caminho) {
        Write-Host "Removendo $pasta..." -ForegroundColor Green
        Remove-Item -Path $caminho -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Remover outros arquivos (logs, CSVs, etc.)
Get-ChildItem -Path $pasta_antiga -File | Where-Object { $_.Extension -in @('.log', '.csv', '.txt', '.json', '.png', '.pdf', '.ico', '.ps1', '.toml', '.xml', '.xlsx', '.html') } | Remove-Item -Force -Verbose

Write-Host ""
Write-Host "Limpeza concluida!" -ForegroundColor Cyan
Write-Host "A pasta .venv foi mantida. Voce pode apaga-la manualmente depois se desejar." -ForegroundColor Yellow
Write-Host ""
Write-Host "Para apagar tudo (incluindo .venv), execute:" -ForegroundColor White
Write-Host 'Remove-Item -Path "c:\Users\avila\OneDrive\Escritorio\site CartoiosRJ" -Recurse -Force' -ForegroundColor Gray
