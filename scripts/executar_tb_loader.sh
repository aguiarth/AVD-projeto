#!/bin/bash
# Script Bash para executar o tb-loader manualmente
# Use este script após configurar os Access Tokens no ThingsBoard

echo "🚀 Executando tb-loader..."
echo ""

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Erro: Execute este script na raiz do projeto (onde está o docker-compose.yml)"
    exit 1
fi

# Executar o tb-loader
echo "📦 Instalando dependências e executando script..."
docker-compose run --rm tb-loader sh -c "pip install --no-cache-dir -r /app/requirements.txt && python /app/send_inmet_to_tb.py"

echo ""
echo "✅ Concluído!"

