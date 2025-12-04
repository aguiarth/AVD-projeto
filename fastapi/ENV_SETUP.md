# Configuração de Variáveis de Ambiente

## Arquivo `.env` na pasta `fastapi/`

Crie um arquivo `.env` na pasta `fastapi/` com o seguinte conteúdo:

```env
# ============================
# CONFIGURAÇÃO DO THINGSBOARD
# ============================
THINGSBOARD_URL=http://thingsboard:9090
THINGSBOARD_TENANT_USER=tenant@thingsboard.org
THINGSBOARD_TENANT_PASSWORD=tenant
THINGSBOARD_DEVICE_ID_PETROLINA=
THINGSBOARD_DEVICE_ID_GARANHUNS=

# ============================
# CONFIGURAÇÃO DO MINIO (opcional, valores padrão já configurados)
# ============================
# MINIO_ENDPOINT=minio:9000
# MINIO_ACCESS_KEY=admin
# MINIO_SECRET_KEY=admin12345
# MINIO_USE_SSL=false
```

## Como obter os Device IDs

1. Acesse o ThingsBoard em `http://localhost:8090`
2. Faça login com `tenant@thingsboard.org` / `tenant`
3. Crie os dispositivos:
   - **INMET_Petrolina**
   - **INMET_Garanhuns**
4. Para cada dispositivo:
   - Vá em **Details**
   - Copie o **Device ID** (UUID) e cole no `.env`
   - Copie o **Access Token** (será usado pelo script `send_inmet_to_tb.py`)

## Variáveis de Ambiente do Docker Compose

O `docker-compose.yml` também usa variáveis de ambiente opcionais para os tokens de acesso:

```bash
# Opcional: definir no arquivo .env na raiz do projeto ou exportar antes de rodar docker-compose
export THINGSBOARD_DEVICE_ACCESS_TOKEN_PETROLINA="seu_token_aqui"
export THINGSBOARD_DEVICE_ACCESS_TOKEN_GARANHUNS="seu_token_aqui"
```

Ou adicione ao `docker-compose.yml` diretamente (não recomendado para produção).


