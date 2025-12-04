# Script PowerShell para executar o tb-loader manualmente
# Use este script após configurar os Access Tokens no ThingsBoard

Write-Host "🚀 Executando tb-loader..." -ForegroundColor Green
Write-Host ""

# Verificar se está no diretório correto
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Erro: Execute este script na raiz do projeto (onde está o docker-compose.yml)" -ForegroundColor Red
    exit 1
}

# Executar o tb-loader
Write-Host "📦 Instalando dependências e executando script..." -ForegroundColor Yellow
docker-compose run --rm tb-loader sh -c "pip install --no-cache-dir -r /app/requirements.txt && python /app/send_inmet_to_tb.py"

Write-Host ""
Write-Host "✅ Concluído!" -ForegroundColor Green

