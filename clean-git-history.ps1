# Script para limpar credenciais do histórico Git
# ATENÇÃO: Este script reescreve o histórico Git - faça backup antes!

Write-Host "=== Limpeza de Credenciais do Histórico Git ===" -ForegroundColor Yellow
Write-Host ""

# Arquivos a remover do histórico
$filesToRemove = @(
    "cartoriosrj-4ebd8df5339e.json",
    "supabase_config.py"
)

Write-Host "Arquivos que serão removidos do histórico:" -ForegroundColor Cyan
$filesToRemove | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

# Backup do repositório
Write-Host "1. Criando backup..." -ForegroundColor Green
$backupPath = "..\CartoriosBR-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item -Path "." -Destination $backupPath -Recurse -Force
Write-Host "   Backup criado em: $backupPath" -ForegroundColor Gray
Write-Host ""

# Limpar histórico usando git filter-branch
Write-Host "2. Limpando histórico Git..." -ForegroundColor Green
Write-Host "   Isso pode demorar alguns minutos..." -ForegroundColor Gray

git filter-branch --force --index-filter `
    "git rm --cached --ignore-unmatch cartoriosrj-4ebd8df5339e.json" `
    --prune-empty --tag-name-filter cat -- --all

Write-Host ""
Write-Host "3. Limpando referências antigas..." -ForegroundColor Green
Remove-Item -Path ".git/refs/original/" -Recurse -Force -ErrorAction SilentlyContinue
git reflog expire --expire=now --all
git gc --prune=now --aggressive

Write-Host ""
Write-Host "=== Limpeza Concluída ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "PRÓXIMOS PASSOS OBRIGATÓRIOS:" -ForegroundColor Red
Write-Host "1. Force push: git push origin --force --all" -ForegroundColor White
Write-Host "2. Revogar credenciais antigas no Supabase e Google Cloud" -ForegroundColor White
Write-Host "3. Gerar novas credenciais" -ForegroundColor White
Write-Host "4. Atualizar .streamlit/secrets.toml com novas credenciais" -ForegroundColor White
