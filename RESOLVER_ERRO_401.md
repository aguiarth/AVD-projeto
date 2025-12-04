# 🔧 Como Resolver o Erro 401 no tb-loader

O erro 401 significa que os **Access Tokens** estão incorretos ou os dispositivos não existem no ThingsBoard.

## ✅ Solução Passo a Passo

### Passo 1: Acessar ThingsBoard

1. Abra o navegador: **http://localhost:8090**
2. Faça login:
   - Usuário: `tenant@thingsboard.org`
   - Senha: `tenant`

### Passo 2: Criar os Dispositivos (se ainda não criou)

1. No menu lateral, clique em **Devices** → **Add new device**
2. Crie o primeiro dispositivo:
   - **Name:** `INMET_Petrolina`
   - Clique em **Add**
3. Crie o segundo dispositivo:
   - **Name:** `INMET_Garanhuns`
   - Clique em **Add**

### Passo 3: Obter os Access Tokens

Para cada dispositivo:

1. Clique no dispositivo (ex: `INMET_Petrolina`)
2. Vá na aba **Details** (ou clique no ícone de engrenagem)
3. Role até a seção **Credentials**
4. Copie o **Access Token** (ex: `KqtPqGEvNa372lyyctey`)

### Passo 4: Atualizar os Tokens

Você tem **duas opções**:

#### Opção A: Criar arquivo `.env` na raiz do projeto (RECOMENDADO)

1. Crie um arquivo `.env` na raiz do projeto (`AVD-projeto/.env`):

```env
THINGSBOARD_DEVICE_ACCESS_TOKEN_PETROLINA=seu_token_petrolina_aqui
THINGSBOARD_DEVICE_ACCESS_TOKEN_GARANHUNS=seu_token_garanhuns_aqui
```

2. Substitua pelos tokens reais que você copiou do ThingsBoard

#### Opção B: Editar docker-compose.yml diretamente

1. Abra `docker-compose.yml`
2. Encontre a seção `tb-loader` (linha ~115)
3. Substitua os valores padrão pelos tokens reais:

```yaml
environment:
  THINGSBOARD_DEVICE_ACCESS_TOKEN_PETROLINA: seu_token_real_aqui
  THINGSBOARD_DEVICE_ACCESS_TOKEN_GARANHUNS: seu_token_real_aqui
```

### Passo 5: Executar o tb-loader manualmente

Depois de atualizar os tokens, execute manualmente (o container automático pode não instalar dependências corretamente):

**No PowerShell:**
```powershell
docker-compose run --rm tb-loader sh -c "pip install --no-cache-dir -r /app/requirements.txt && python /app/send_inmet_to_tb.py"
```

**Ou use o script auxiliar:**
```powershell
.\scripts\executar_tb_loader.ps1
```

**No Linux/Mac:**
```bash
docker-compose run --rm tb-loader sh -c "pip install --no-cache-dir -r /app/requirements.txt && python /app/send_inmet_to_tb.py"
```

**Ou use o script auxiliar:**
```bash
bash scripts/executar_tb_loader.sh
```

> **Nota:** O container `tb-loader` executa uma vez e finaliza, por isso não aparecem logs com `docker-compose logs -f`. Execute manualmente para ver os logs em tempo real.

## 🔍 Verificar se Funcionou

Depois de atualizar os tokens, verifique os logs:

```powershell
docker-compose logs -f tb-loader
```

Você deve ver mensagens como:
```
✅ {enviados}/{total} registros enviados...
```

Ao invés de:
```
❌ Erro 401: ...
```

## 💡 Dica

Se você ainda não criou os dispositivos no ThingsBoard, o erro 401 é esperado. Siga os passos acima para criar os dispositivos primeiro.

## 📝 Nota sobre Device IDs vs Access Tokens

- **Device ID**: UUID usado pela API FastAPI para buscar telemetria (vai no arquivo `fastapi/.env`)
- **Access Token**: Token usado pelo script `send_inmet_to_tb.py` para enviar telemetria (vai no `docker-compose.yml` ou `.env` da raiz)

Ambos são diferentes e ambos são necessários!

