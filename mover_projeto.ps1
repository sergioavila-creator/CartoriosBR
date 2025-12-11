# Script para mover o projeto CartoriosRJ para fora do OneDrive
# Isso melhora a performance ao evitar sincronizacao constante

$origem = "g:\Meu Drive\dev\CartoriosBR"
$destino = "c:\dev\cartoriosbr"

Write-Host "=== Movendo projeto CartoriosBR ===" -ForegroundColor Cyan
Write-Host "Origem: $origem" -ForegroundColor Yellow
Write-Host "Destino: $destino" -ForegroundColor Yellow
Write-Host ""

# Criar diretorio de destino se nao existir
if (-not (Test-Path "c:\dev")) {
    Write-Host "Criando diretorio c:\dev..." -ForegroundColor Green
    New-Item -ItemType Directory -Path "c:\dev" -Force | Out-Null
}

# Verificar se o destino ja existe
if (Test-Path $destino) {
    Write-Host "AVISO: O destino $destino ja existe!" -ForegroundColor Red
    $resposta = Read-Host "Deseja sobrescrever? (S/N)"
    if ($resposta -ne "S" -and $resposta -ne "s") {
        Write-Host "Operacao cancelada." -ForegroundColor Yellow
        exit
    }
    Remove-Item -Path $destino -Recurse -Force
}

# Copiar todo o projeto (incluindo .git)
Write-Host "Copiando arquivos..." -ForegroundColor Green
Copy-Item -Path $origem -Destination $destino -Recurse -Force

Write-Host "Verificando integridade..." -ForegroundColor Green

# Verificar se o .git foi copiado
if (Test-Path "$destino\.git") {
    Write-Host "[OK] Repositorio Git copiado com sucesso" -ForegroundColor Green
}
else {
    Write-Host "[ERRO] Repositorio Git nao foi copiado!" -ForegroundColor Red
    exit
}

# Verificar se pastas principais existem
$pastas_principais = @("pages", ".streamlit", ".git")
$tudo_ok = $true

foreach ($pasta in $pastas_principais) {
    if (Test-Path "$destino\$pasta") {
        Write-Host "[OK] $pasta" -ForegroundColor Green
    }
    else {
        Write-Host "[ERRO] $pasta NAO ENCONTRADA!" -ForegroundColor Red
        $tudo_ok = $false
    }
}

# Contar arquivos Python
$arquivos_py = (Get-ChildItem -Path $destino -Filter *.py -Recurse).Count
Write-Host "[OK] Encontrados $arquivos_py arquivos Python" -ForegroundColor Green

if ($tudo_ok) {
    Write-Host ""
    Write-Host "=== Migracao concluida com sucesso! ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Proximos passos:" -ForegroundColor Yellow
    Write-Host "1. Abra o Antigravity e adicione o novo workspace: $destino" -ForegroundColor White
    Write-Host "2. Verifique se tudo esta funcionando corretamente" -ForegroundColor White
    Write-Host "3. Depois de confirmar, voce pode deletar a pasta original do OneDrive" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANTE: NAO delete a pasta original ainda! Confirme primeiro que tudo funciona." -ForegroundColor Red
}
else {
    Write-Host ""
    Write-Host "ERRO: Alguns arquivos nao foram copiados corretamente!" -ForegroundColor Red
    Write-Host "Verifique manualmente antes de prosseguir." -ForegroundColor Red
}
