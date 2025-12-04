# 🍇 AVD - Pipeline de BI Climático para Viticultura 

## 1. Introdução e Objetivo

Este projeto implementa um pipeline de Business Intelligence (BI) para análise e visualização de dados meteorológicos do INMET (Instituto Nacional de Meteorologia), focando no estado de Pernambuco, com ênfase no **Vale do São Francisco**.

O objetivo central é aplicar técnicas de **Agrupamento (Clustering) K-Means** para identificar **Padrões Climáticos Chave** durante fases críticas da videira, como a floração e a maturação, utilizando dados agregados de temperatura, umidade e radiação solar. O resultado deste agrupamento deve ser visualizado em dashboards interativos (ThingsBoard/Trendz).

## 2. Membros do Projeto

| Nome | Usuário |
| :--- | :--- |
| Lisa Matubara | `lm` |
| Luziane Santos | `lps` |
| Maria Júlia Peixoto | `mjpo` |
| Matheus Velame | `mvp2` |
| Paulo Rago | `prcr` |
| Thaís Aguiar | `thcba` |

* **Disciplina:** Análise e Visualização de Dados - 2025.2
* **Instituição:** CESAR School

## 3. Arquitetura do Pipeline

A solução é baseada em contêineres Docker e orquestrada via Docker Compose, abrangendo as seguintes camadas:

| Serviço | Função Principal | Porta |
| :--- | :--- | :--- |
| **FastAPI** | Interface de ingestão dos dados brutos do INMET e integração com MinIO/S3. | `8060` |
| **MinIO/S3** | Armazenamento de dados brutos e modelos. | - |
| **Snowflake** | Estruturação de dados tratados (Simulado por `SQLite`/`PostgreSQL` em ambiente local). | - |
| **Jupyter Notebook** | Ambiente de limpeza, agregação de features e modelagem K-Means. | `8888` |
| **MLFlow** | Registro e versionamento do modelo de K-Means e artefatos. | `5000` |
| **Trendz Analytics** | Visualização dos dados e dashboards interativos. | `8888` |

**Fluxo Geral:**

1. Os dados brutos do INMET são ingeridos e salvos no S3/MinIO.
2. Os dados são estruturados no Snowflake .
3. O Jupyter Notebook lê a base estruturada, aplica o K-Means e registra o modelo no MLFlow.
4. O dashboard no ThingsBoard/Trendz consome os resultados do agrupamento para gerar visualizações de padrões climáticos.

## 4. Estrutura do Repositório

| Caminho | Descrição |
| :--- | :--- |
| `docker-compose.yml` | Orquestração dos contêineres da infraestrutura. |
| `fastapi/` | Camada de ingestão de dados (API). |
| `jupyterlab/` | Dockerfile e configs do ambiente Jupyter. |
| `mlflow/` | Configuração e armazenamento de experimentos. |
| `notebooks/` | Notebooks de tratamento, modelagem e visualização. |
| `sql_scripts/` | Scripts SQL de estruturação e consultas (DML/DDL). |
| `reports/` | **Local de entrega do Relatório Técnico em PDF**. |
| `trendz/` | Dashboards e configurações exportadas. |

## 5. Instruções de Execução

Siga os passos abaixo para levantar a infraestrutura, executar o pipeline e visualizar o dashboard:

### 5.1. Pré-requisitos

* Docker e Docker Compose instalados.
* Conexão estável com a internet.

### 5.2. Configurar Variáveis de Ambiente

1.  Crie o arquivo `.env` na pasta `fastapi/` com as credenciais do ThingsBoard:
    ```bash
    cd fastapi
    cp .env.example .env
    ```
    
    Edite o arquivo `.env` e configure:
    ```env
    THINGSBOARD_URL=http://thingsboard:9090
    THINGSBOARD_TENANT_USER=tenant@thingsboard.org
    THINGSBOARD_TENANT_PASSWORD=tenant
    THINGSBOARD_DEVICE_ID_PETROLINA=<SEU_DEVICE_ID_PETROLINA>
    THINGSBOARD_DEVICE_ID_GARANHUNS=<SEU_DEVICE_ID_GARANHUNS>
    ```
    
    > **Nota:** Você precisará obter os Device IDs após criar os dispositivos no ThingsBoard (veja seção 5.2.1).

2.  Volte para a raiz do projeto:
    ```bash
    cd ..
    ```

### 5.2.1. Configurar ThingsBoard

1.  Acesse o ThingsBoard em `http://localhost:8090` (aguarde o serviço inicializar completamente).
2.  Faça login com as credenciais padrão:
    - Usuário: `tenant@thingsboard.org`
    - Senha: `tenant`
3.  Crie dois dispositivos:
    - **INMET_Petrolina**
    - **INMET_Garanhuns**
4.  Para cada dispositivo:
    - Vá em **Details** → copie o **Device ID** e cole no arquivo `.env` do FastAPI.
    - Copie o **Access Token** do dispositivo (será usado pelo script loader).

### 5.3. Subir a Infraestrutura

1.  Na raiz do projeto, construa as imagens e suba todos os serviços:
    ```bash
    docker-compose up -d --build
    ```
    
    Este comando sobe os seguintes serviços:
    - **fastapi** – API em `http://localhost:8000`
    - **jupyterlab** – ambiente de notebooks em `http://localhost:8888`
    - **thingsboard** – plataforma IoT em `http://localhost:8090`
    - **thingsboard-postgres** – banco usado pelo ThingsBoard
    - **minio** – armazenamento S3-compatível em `http://localhost:9001`
    - **mlflow** – registro de modelos em `http://localhost:5000`
    - **tb-loader** – carrega CSVs tratados e envia para o ThingsBoard
    - **inmet-ingest** – chama a API FastAPI para ler dados do ThingsBoard e salvar no MinIO

### 5.4. Execução do Pipeline

1.  Acesse o Jupyter Notebook (porta `8888`): `http://localhost:8888`
2.  Execute o notebook **`01_tratamento_dados_inmet.ipynb`** para:
    * Carregar dados brutos (do `/data/raw`).
    * Limpar nulos (interpolação) e salvar dados tratados (no `/data/processed`).
3.  **Carregamento Automático para ThingsBoard:**
    * O serviço `tb-loader` no Docker Compose automaticamente detecta os CSVs tratados e envia para o ThingsBoard.
    * Você pode verificar os logs: `docker-compose logs tb-loader`
    * Ou executar manualmente: `docker-compose run --rm tb-loader python send_inmet_to_tb.py`
4.  **Ingestão de Dados do ThingsBoard para MinIO:**
    * Após o `tb-loader` finalizar, o serviço `inmet-ingest` automaticamente chama a API FastAPI.
    * A API busca a telemetria do ThingsBoard e salva como CSV no MinIO.
    * Endpoint manual: `POST http://localhost:8000/ingest/inmet`
5.  **[ETAPA MANUAL: Carregamento para o Banco de Dados]**
    * Execute os scripts SQL em `sql_scripts/` para criar o schema no Snowflake (ou Postgres/SQLite).
    * Use o FastAPI ou um script auxiliar no Jupyter para carregar os dados tratados (CSV em `/data/processed`) para a tabela do Snowflake.
6.  Execute o notebook **`02_modelagem_kmeans.ipynb`** para:
    * Ler os dados estruturados do Snowflake.
    * Tratar Outliers e Aggregar features (Semanal).
    * Treinar e registrar o modelo K-Means no MLFlow (`http://localhost:5000`).

### 5.5. Endpoints da API FastAPI

Principais endpoints disponíveis:

- `GET /` – Informações da API e lista de endpoints
- `GET /health` – Health check
- `POST /ingest/inmet` – Busca telemetria do ThingsBoard e salva no MinIO
- `POST /webhook/inmet/{device_name}` – Recebe telemetria do ThingsBoard via webhook
- `GET /minio/files` – Lista arquivos no MinIO
- `GET /minio/stats` – Estatísticas dos dados no MinIO
- `GET /api/dados-processados` – Lista dados processados disponíveis
- `GET /api/dados-processados/{cidade}/{ano}` – Obtém dados tratados específicos
- `GET /api/dados-agregados/clusters` – Obtém dados agregados com clusters
- `POST /api/modelo/predict` – Faz predição de cluster para novos dados

### 5.6. Visualização do Dashboard

1.  Acesse o ThingsBoard em `http://localhost:8090`
2.  Navegue até os dispositivos **INMET_Petrolina** e **INMET_Garanhuns** para visualizar a telemetria em tempo real.
3.  Importe o dashboard de agrupamento (arquivos em `trendz/`) se disponível.
4.  O dashboard deve exibir:
    * A distribuição das semanas nos clusters identificados.
    * Gráficos de dispersão coloridos por cluster para variáveis-chave (e.g., Temperatura vs. Umidade).
    * Painéis com as médias de cada grupo climático.

## 6. Resultados e Conclusões

* **Relatório Técnico:** O relatório final em PDF, contendo a arquitetura, metodologia, resultados e conclusões, será salvo no diretório `/reports/` antes da entrega.