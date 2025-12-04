# 🚀 Como Rodar o Projeto AVD

Este guia passo a passo vai te ajudar a subir toda a infraestrutura e executar o pipeline completo.

## 📋 Pré-requisitos

- **Docker Desktop** instalado e rodando
- **Docker Compose** (vem com Docker Desktop)
- **Conexão com internet** (para baixar imagens)

## 🔧 Passo 1: Configurar Variáveis de Ambiente

### 1.1. Renomear arquivo de ambiente

O projeto já tem um arquivo `env.env` na pasta `fastapi/`. Renomeie para `.env`:

**No PowerShell (Windows):**
```powershell
cd AVD-projeto\fastapi
Rename-Item env.env .env
cd ..
```

**No Linux/Mac:**
```bash
cd AVD-projeto/fastapi
mv env.env .env
cd ..
```

### 1.2. Editar o arquivo `.env`

Abra o arquivo `fastapi/.env` e configure os Device IDs (você vai obter isso depois de criar os dispositivos no ThingsBoard):

```env
THINGSBOARD_URL=http://thingsboard:9090
THINGSBOARD_TENANT_USER=tenant@thingsboard.org
THINGSBOARD_TENANT_PASSWORD=tenant
THINGSBOARD_DEVICE_ID_PETROLINA=<VOCÊ_VAI_PREENCHER_DEPOIS>
THINGSBOARD_DEVICE_ID_GARANHUNS=<VOCÊ_VAI_PREENCHER_DEPOIS>
```

> **Nota:** Por enquanto, deixe os Device IDs vazios ou com valores temporários. Você vai preenchê-los no Passo 3.

## 🐳 Passo 2: Subir os Serviços

Na raiz do projeto (`AVD-projeto`), execute:

```powershell
docker-compose up -d --build
```

Este comando vai:
- Construir as imagens necessárias
- Subir todos os serviços em segundo plano
- Criar a rede Docker para comunicação entre serviços

**Serviços que serão iniciados:**
- ✅ FastAPI (porta 8000)
- ✅ JupyterLab (porta 8888)
- ✅ ThingsBoard (porta 8090)
- ✅ ThingsBoard PostgreSQL (porta 5434)
- ✅ MinIO (portas 9000 e 9001)
- ✅ MLFlow (porta 5000)
- ✅ tb-loader (executa uma vez e finaliza)
- ✅ inmet-ingest (executa após tb-loader)

### Verificar se está tudo rodando

```powershell
docker-compose ps
```

Você deve ver todos os serviços com status "Up" ou "running".

### Ver logs (opcional)

Se quiser acompanhar os logs em tempo real:

```powershell
docker-compose logs -f
```

Para ver logs de um serviço específico:

```powershell
docker-compose logs -f fastapi
docker-compose logs -f thingsboard
docker-compose logs -f tb-loader
```

## 🌐 Passo 3: Configurar ThingsBoard

### 3.1. Aguardar inicialização

Aguarde cerca de **1-2 minutos** para o ThingsBoard inicializar completamente. Você pode verificar os logs:

```powershell
docker-compose logs -f thingsboard
```

Quando aparecer algo como "Started ThingsBoardApplication", está pronto.

### 3.2. Acessar ThingsBoard

1. Abra o navegador e acesse: **http://localhost:8090**
2. Faça login com:
   - **Usuário:** `tenant@thingsboard.org`
   - **Senha:** `tenant`

### 3.3. Criar Dispositivos

1. No menu lateral, clique em **Devices** → **Add new device**
2. Crie o primeiro dispositivo:
   - **Name:** `INMET_Petrolina`
   - Clique em **Add**
3. Crie o segundo dispositivo:
   - **Name:** `INMET_Garanhuns`
   - Clique em **Add**

### 3.4. Obter Device IDs e Access Tokens

Para cada dispositivo criado:

1. Clique no dispositivo (ex: `INMET_Petrolina`)
2. Vá na aba **Details**
3. Copie o **Device ID** (um UUID longo, ex: `37f2e300-d093-11f0-8a69-fbf8c35e0488`)
4. Copie o **Access Token** (ex: `KqtPqGEvNa372lyyctey`)

### 3.5. Atualizar arquivo `.env`

Edite o arquivo `fastapi/.env` e cole os Device IDs:

```env
THINGSBOARD_DEVICE_ID_PETROLINA=37f2e300-d093-11f0-8a69-fbf8c35e0488
THINGSBOARD_DEVICE_ID_GARANHUNS=outro-uuid-aqui
```

**Importante:** Se você alterou o `.env`, precisa reiniciar o FastAPI:

```powershell
docker-compose restart fastapi
```

### 3.6. Configurar Tokens no Docker Compose (opcional)

Se quiser que o `tb-loader` use tokens específicos, você pode:

1. Criar um arquivo `.env` na **raiz** do projeto:
```env
THINGSBOARD_DEVICE_ACCESS_TOKEN_PETROLINA=KqtPqGEvNa372lyyctey
THINGSBOARD_DEVICE_ACCESS_TOKEN_GARANHUNS=C4dThEy9BtBgco99L3WL
```

2. Ou editar diretamente no `docker-compose.yml` (não recomendado para produção)

## 📊 Passo 4: Executar o Pipeline

### 4.1. Enviar Dados para ThingsBoard

O serviço `tb-loader` já deve ter executado automaticamente. Para executar manualmente:

```powershell
docker-compose run --rm tb-loader python send_inmet_to_tb.py
```

Este script vai:
- Ler todos os CSVs tratados em `data/processed/*_tratado.csv`
- Enviar os dados para o ThingsBoard via API
- Mostrar progresso no console

### 4.2. Ingerir Dados do ThingsBoard para MinIO

Após o `tb-loader` finalizar, o serviço `inmet-ingest` executa automaticamente. Para executar manualmente:

**Opção 1: Via API (recomendado)**
```powershell
curl -X POST http://localhost:8000/ingest/inmet
```

**Opção 2: Via Docker**
```powershell
docker-compose run --rm inmet-ingest
```

Este processo vai:
- Autenticar no ThingsBoard
- Buscar toda a telemetria dos dispositivos
- Converter para DataFrame
- Salvar como CSV no MinIO

### 4.3. Verificar Dados no MinIO

1. Acesse o MinIO Console: **http://localhost:9001**
2. Login:
   - **Usuário:** `admin`
   - **Senha:** `admin12345`
3. Navegue até o bucket `inmet-raw`
4. Você verá os arquivos organizados por dispositivo e data

## 🔬 Passo 5: Trabalhar com Jupyter Notebooks

### 5.1. Acessar JupyterLab

1. Abra: **http://localhost:8888**
2. Não precisa de token (configurado sem autenticação)

### 5.2. Executar Notebooks

1. **`01_tratamento_dados_inmet.ipynb`**
   - Carrega dados brutos de `data/raw/`
   - Limpa e trata os dados
   - Salva em `data/processed/`

2. **`02_modelagem_kmeans.ipynb`**
   - Lê dados tratados
   - Aplica agregação semanal
   - Treina modelo K-Means
   - Registra no MLFlow

## 📈 Passo 6: Visualizar Resultados

### 6.1. ThingsBoard

- Acesse: **http://localhost:8090**
- Navegue até os dispositivos `INMET_Petrolina` e `INMET_Garanhuns`
- Veja a telemetria em tempo real
- Crie dashboards personalizados

### 6.2. MLFlow

- Acesse: **http://localhost:5000**
- Veja experimentos e modelos registrados
- Compare métricas de diferentes execuções

### 6.3. API FastAPI

- Documentação interativa: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**
- Listar dados processados: **http://localhost:8000/api/dados-processados**

## 🛠️ Comandos Úteis

### Parar todos os serviços
```powershell
docker-compose down
```

### Parar e remover volumes (limpar dados)
```powershell
docker-compose down -v
```

### Reiniciar um serviço específico
```powershell
docker-compose restart fastapi
docker-compose restart thingsboard
```

### Ver logs de um serviço
```powershell
docker-compose logs -f fastapi
docker-compose logs -f thingsboard
docker-compose logs -f tb-loader
```

### Executar comando dentro de um container
```powershell
docker-compose exec fastapi bash
docker-compose exec jupyterlab bash
```

## ❓ Troubleshooting

### ThingsBoard não inicia
- Aguarde mais tempo (pode levar 2-3 minutos)
- Verifique logs: `docker-compose logs thingsboard`
- Verifique se o PostgreSQL está rodando: `docker-compose ps thingsboard-postgres`

### FastAPI não conecta ao ThingsBoard
- Verifique se o `.env` está correto
- Verifique se os Device IDs estão corretos
- Reinicie o FastAPI: `docker-compose restart fastapi`

### tb-loader não encontra CSVs
- Verifique se os arquivos existem: `ls data/processed/*_tratado.csv`
- Verifique o caminho no script: deve ser `/data/processed` dentro do container

### Erro de permissão no MinIO
- Verifique as credenciais: `admin` / `admin12345`
- Verifique se o bucket `inmet-raw` existe

## ✅ Checklist Final

- [ ] Docker Desktop rodando
- [ ] Arquivo `fastapi/.env` configurado
- [ ] Todos os serviços rodando (`docker-compose ps`)
- [ ] ThingsBoard acessível em http://localhost:8090
- [ ] Dispositivos criados no ThingsBoard
- [ ] Device IDs atualizados no `.env`
- [ ] Dados enviados para ThingsBoard (tb-loader executado)
- [ ] Dados ingeridos no MinIO (inmet-ingest executado)
- [ ] JupyterLab acessível em http://localhost:8888
- [ ] MLFlow acessível em http://localhost:5000

---

**Pronto!** Seu projeto está rodando. 🎉

Para mais detalhes, consulte o `README.md` principal.

