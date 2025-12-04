# 🌦️ AVD - Pipeline de BI Climático

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-Academic-lightgrey.svg)

**Pipeline completo de Business Intelligence para análise e visualização de dados meteorológicos do INMET**

[📋 Índice](#-índice) • [🚀 Início Rápido](#-início-rápido) • [📚 Documentação](#-documentação) • [🤝 Equipe](#-equipe)

</div>

---

## 📋 Índice

1. [Introdução e Objetivo](#1-introdução-e-objetivo)
2. [Membros do Projeto](#2-membros-do-projeto)
3. [Arquitetura do Pipeline](#3-arquitetura-do-pipeline)
4. [Estrutura do Repositório](#4-estrutura-do-repositório)
5. [Tecnologias Utilizadas](#5-tecnologias-utilizadas)
6. [Requisitos e Dependências](#6-requisitos-e-dependências)
7. [Instalação e Configuração](#7-instalação-e-configuração)
8. [Instruções de Execução](#8-instruções-de-execução)
9. [Notebooks do Projeto](#9-notebooks-do-projeto)
10. [Scripts Auxiliares](#10-scripts-auxiliares)
11. [Troubleshooting](#11-troubleshooting)
12. [Resultados e Conclusões](#12-resultados-e-conclusões)

---

## 1. Introdução e Objetivo

Este projeto implementa um **pipeline completo de Business Intelligence (BI)** para análise e visualização de dados meteorológicos do **INMET (Instituto Nacional de Meteorologia)**, focando no estado de **Pernambuco**, com ênfase nas estações de **Petrolina** e **Garanhuns**.

### 🎯 Objetivo Central

Aplicar técnicas de **Agrupamento (Clustering) K-Means** para identificar **Padrões Climáticos Chave** utilizando dados agregados de temperatura, umidade, radiação solar, precipitação e pressão atmosférica. O resultado deste agrupamento é visualizado em dashboards interativos no **ThingsBoard**.

### 📊 Dados Processados

- **Período:** 2020 a 2024
- **Estações:** Petrolina (A307) e Garanhuns (A322)
- **Frequência:** Dados horários
- **Variáveis:** Temperatura, Umidade, Radiação, Vento, Precipitação, Pressão

---

## 2. Membros do Projeto

| Nome | Usuário |
| :--- | :--- |
| Lisa Matubara | `lilymtbr` |
| Luziane Santos | `luzianes` |
| Maria Júlia Peixoto | `majupeixoto` |
| Matheus Velame | `MatheusVelame` |
| Paulo Rago | `paulo_rago` |
| Thaís Aguiar | `aguiarth` |

* **Disciplina:** Análise e Visualização de Dados - 2025.2  
* **Instituição:** CESAR School

---

## 3. Arquitetura do Pipeline

A solução é baseada em contêineres **Docker** e orquestrada via **Docker Compose**, abrangendo as seguintes camadas:

| Serviço | Função Principal | Porta | URL de Acesso |
| :--- | :--- | :--- | :--- |
| **JupyterLab** | Ambiente de análise, tratamento de dados e modelagem | `8888` | `http://localhost:8888` |
| **FastAPI** | Interface de ingestão dos dados brutos do INMET e integração com MinIO/S3 | `8000` | `http://localhost:8000` |
| **MinIO/S3** | Data Lake - Armazenamento de dados brutos e modelos | `9000` (API)<br>`9001` (Console) | `http://localhost:9001` |
| **PostgreSQL** | Data Warehouse - Banco de dados relacional para armazenamento estruturado | `5432` | `http://localhost:8085` (Adminer) |
| **Adminer** | Interface web para gerenciamento do PostgreSQL | `8085` | `http://localhost:8085` |
| **MLFlow** | Registro e versionamento do modelo de K-Means e artefatos | `5000` | `http://localhost:5000` |
| **ThingsBoard** | Plataforma IoT para visualização de dados e dashboards | `8090` | `http://localhost:8090` |

### 🔄 Fluxo Detalhado do Pipeline

```mermaid
graph TD
    A[Dados Limpos] --> B[send_inmet_to_tb.py]
    B --> C[ThingsBoard]
    C -->|Regra de Negócio| D[MinIO/S3]
    D -->|ETL| E[PostgreSQL]
    E -->|Extração| F[Jupyter Notebook]
    F -->|K-Means| G[MLFlow]
    F --> H[Modelos e Resultados]
    H --> C
```

#### Fluxo de Dados Detalhado

1. **Ingestão:** Os dados limpos são enviados ao ThingsBoard via script Python (`scripts/send_inmet_to_tb.py`).

2. **ThingsBoard → MinIO:** O ThingsBoard aplica uma **Regra de Negócio** para persistir os dados brutos no MinIO/S3 (Data Lake).

3. **MinIO → PostgreSQL:** A transferência do data lake (MinIO) para o data warehouse (PostgreSQL) é realizada através de um script de ETL dedicado (`scripts/etl_minio_to_postgres.py`).

4. **Modelagem:** O Jupyter Notebook extrai os dados estruturados diretamente do PostgreSQL para o Machine Learning (K-Means), que é rastreado pelo MLFlow.

5. **Visualização:** O ThingsBoard consome os resultados do agrupamento para gerar dashboards interativos.

---

## 4. Estrutura do Repositório

```
AVD-projeto-1/
├── data/
│   ├── raw/                    # Dados brutos do INMET (CSV)
│   │   ├── 2020/
│   │   ├── 2021/
│   │   ├── 2022/
│   │   ├── 2023/
│   │   └── 2024/
│   └── processed/               # Dados tratados (CSV)
│       ├── petrolina_*_tratado.csv
│       ├── garanhuns_*_tratado.csv
│       ├── dados_semanais_clustered.csv
│       ├── modelos_backup/      # Modelos ML salvos
│       ├── modelos_viticultura/ # Modelos específicos
│       └── temp_models/         # Modelos temporários
├── notebooks/
│   ├── 01_carregar_dados.ipynb          # Notebook exploratório
│   ├── 01_tratamento_dados_inmet.ipynb  # Processamento completo
│   └── 02_Modelagem.ipynb         # Modelagem e clustering
├── fastapi/
│   ├── main.py                  # API de ingestão
│   ├── requirements.txt         # Dependências FastAPI
│   └── Dockerfile               # Imagem Docker FastAPI
├── scripts/
│   ├── etl_minio_to_postgres.py    # ETL MinIO → PostgreSQL
│   ├── send_inmet_to_tb.py          # Envio de dados para ThingsBoard
│   ├── test_pipeline.py             # Testes do pipeline
├── mlflow/
│   └── artifacts/                # Artefatos dos modelos
├── minio/
│   └── data/                     # Dados armazenados no MinIO
├── thingsboard/
│   ├── data/                     # Banco de dados do ThingsBoard
│   └── logs/                     # Logs do ThingsBoard
├── docker-compose.yml            # Orquestração dos serviços
├── Dockerfile.jupyter            # Dockerfile do Jupyter
└── README.md                     # Este arquivo
```

---

## 5. Tecnologias Utilizadas

### 🐳 Infraestrutura e Containerização
- **Docker** (20.10+) - Containerização de aplicações
- **Docker Compose** (2.0+) - Orquestração de serviços

### 🔧 Backend e APIs
- **FastAPI** (0.100+) - Framework web moderno para APIs REST
- **Uvicorn** - Servidor ASGI de alta performance
- **Python 3.11** - Linguagem de programação principal

### 💾 Armazenamento de Dados
- **MinIO** - Data Lake - Armazenamento de objetos compatível com S3
- **PostgreSQL 15** - Data Warehouse - Banco de dados relacional
- **SQLAlchemy** - ORM para Python

### 📊 Análise de Dados e Machine Learning
- **Pandas** - Manipulação e análise de dados
- **NumPy** - Computação numérica
- **Scikit-learn** - Machine Learning (K-Means, StandardScaler)
- **JupyterLab** - Ambiente de desenvolvimento interativo

### 📈 Visualização
- **Matplotlib** - Visualizações estáticas
- **Seaborn** - Visualizações estatísticas avançadas

### 🔄 MLOps e Versionamento
- **MLFlow** (v2.7.1) - Gerenciamento do ciclo de vida de modelos
- **Git** - Controle de versão

### 🌐 IoT e Visualização
- **ThingsBoard** - Plataforma IoT para visualização e dashboards
- **Adminer** - Interface web para PostgreSQL

### 📡 Integração e Comunicação
- **Requests** - Cliente HTTP para Python
- **psycopg2-binary** - Adaptador PostgreSQL para Python
- **python-multipart** - Suporte para upload de arquivos

---

## 6. Requisitos e Dependências

### 📦 Dependências do FastAPI

Arquivo: `fastapi/requirements.txt`

```
fastapi
uvicorn[standard]
pandas
python-multipart
minio
requests
psycopg2-binary
sqlalchemy
```

### 📦 Dependências do JupyterLab

Instaladas via `Dockerfile.jupyter`:

```
minio
psycopg2-binary
sqlalchemy
```

### 📦 Dependências dos Notebooks

Bibliotecas Python utilizadas nos notebooks:

```python
# Análise de Dados
pandas
numpy

# Machine Learning
scikit-learn

# Visualização
matplotlib
seaborn

# Integração
minio
psycopg2-binary
sqlalchemy
requests
```
```

### 📦 Dependências dos Scripts

```python
# ETL e Processamento
pandas
minio
sqlalchemy
psycopg2-binary
```

# Comunicação
requests
```

---

## 7. Instalação e Configuração

### 7.1. Pré-requisitos

#### Linux / macOS

```bash
# Verificar versão do Docker
docker --version

# Verificar versão do Docker Compose
docker-compose --version

# Instalar Docker (se necessário)
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install docker.io docker-compose

# macOS (via Homebrew):
brew install docker docker-compose
```

#### Windows

```powershell
# Verificar versão do Docker
docker --version

# Verificar versão do Docker Compose
docker-compose --version

# Instalar Docker Desktop (inclui Docker Compose)
# Baixar de: https://www.docker.com/products/docker-desktop
```

### 7.2. Requisitos do Sistema

- **Docker** (versão 20.10 ou superior)
- **Docker Compose** (versão 2.0 ou superior)
- **Git** (para clonar o repositório)
- **8GB de RAM** (recomendado)
- **10GB de espaço em disco** (para dados e imagens)
- **Conexão estável com a internet** (para download de imagens Docker)

### 7.3. Clonagem do Repositório

#### Linux / macOS

```bash
git clone <git@github.com:aguiarth/AVD-projeto.git>
cd AVD-projeto
```

#### Windows (PowerShell)

```powershell
git clone <git@github.com:aguiarth/AVD-projeto.git>
cd AVD-projeto
```

#### Windows (CMD)

```cmd
git clone <git@github.com:aguiarth/AVD-projeto.git>
cd AVD-projeto
```

---

## 8. Instruções de Execução

### 8.1. Subir a Infraestrutura

#### Linux / macOS

```bash
# Construir as imagens e iniciar os serviços
docker-compose up -d --build

# Verificar se todos os serviços estão rodando
docker-compose ps
```

#### Windows (PowerShell)

```powershell
# Construir as imagens e iniciar os serviços
docker-compose up -d --build

# Verificar se todos os serviços estão rodando
docker-compose ps
```

#### Windows (CMD)

```cmd
docker-compose up -d --build
docker-compose ps
```

### 8.2. Verificar Status dos Serviços

Você deve ver todos os serviços com status `Up`:

- `jupyter-uva` (JupyterLab)
- `thingsboard` (ThingsBoard)
- `fastapi-clima` (FastAPI)
- `minio` (MinIO)
- `mlflow_server` (MLFlow)
- `postgres-avd` (PostgreSQL)
- `adminer-avd` (Adminer)

### 8.3. Acessar os Serviços

| Serviço | URL | Credenciais |
| :--- | :--- | :--- |
| **JupyterLab** | `http://localhost:8888` | Sem token |
| **FastAPI** | `http://localhost:8000` | - |
| **FastAPI Docs** | `http://localhost:8000/docs` | - |
| **MinIO Console** | `http://localhost:9001` | `admin` / `admin12345` |
| **MLFlow** | `http://localhost:5000` | - |
| **ThingsBoard** | `http://localhost:8090` | `tenant@thingsboard.org` / `tenant` |
| **Adminer** | `http://localhost:8085` | Sistema: `PostgreSQL`<br>Servidor: `postgres`<br>Usuário: `postgres`<br>Senha: `postgres`<br>Base de dados: `clima` |

### 8.4. Execução do Pipeline

#### Passo 1: Processamento dos Dados

1. **Acesse o JupyterLab:** `http://localhost:8888`

2. **Execute o notebook `01_tratamento_dados_inmet.ipynb`:**
   - Este notebook processa todos os arquivos CSV do INMET (2020-2024)
   - Aplica limpeza, interpolação temporal e tratamento de valores faltantes
   - Salva os dados tratados em `/data/processed/`

   **Variáveis processadas:**
   - Temperatura do ar (°C)
   - Umidade relativa (%)
   - Radiação global (kJ/m²) - quando disponível
   - Velocidade do vento (m/s)
   - Precipitação (mm)
   - Pressão atmosférica (mB)

3. **Para exploração rápida, use o notebook `01_carregar_dados.ipynb`:**
   - Permite visualizar e explorar um arquivo específico
   - Usa a mesma função de processamento do notebook principal

#### Passo 2: Modelagem K-Means

1. **Execute o notebook `02_Modelagem_KMeans.ipynb`:**
   - Carrega os dados estruturados diretamente do PostgreSQL
   - Agrega dados por semana
   - Trata outliers
   - Aplica normalização (StandardScaler)
   - Treina o modelo K-Means
   - Avalia o modelo (silhouette score)
   - Registra o modelo no MLFlow

   **Variáveis utilizadas na agregação semanal:**
   - Temperatura (média e desvio padrão)
   - Umidade (média e mínima)
   - Radiação (soma)
   - Precipitação (soma)
   - Pressão (média)
   
   *Nota: A velocidade do vento é processada nos dados brutos, mas não é utilizada na agregação semanal para o modelo K-Means.*

2. **Visualizar o modelo no MLFlow:**
   - Acesse `http://localhost:5000`
   - Navegue até o experimento "K-Means Clustering"
   - Visualize métricas, parâmetros e artefatos

#### Passo 3: Visualização no ThingsBoard

1. **Acesse o ThingsBoard:** `http://localhost:8090`
   - Credenciais padrão: `tenant@thingsboard.org` / `tenant`

2. **Configure dispositivos e dashboards:**
   - Crie dispositivos para cada estação (Petrolina, Garanhuns)
   - Configure uma **Regra de Negócio** no ThingsBoard para persistir dados no MinIO
   - Use o script `scripts/send_inmet_to_tb.py` para enviar dados limpos ao ThingsBoard
   - Execute o script `scripts/etl_minio_to_postgres.py` para transferir dados do MinIO para PostgreSQL
   - Crie dashboards para visualizar os clusters identificados

### 8.5. Executar Scripts Auxiliares

#### Linux / macOS

```bash
# Enviar dados limpos para ThingsBoard
python scripts/send_inmet_to_tb.py

# ETL MinIO → PostgreSQL (após ThingsBoard persistir no MinIO)
python scripts/etl_minio_to_postgres.py

# Testar pipeline
python scripts/test_pipeline.py
```

#### Windows (PowerShell)

```powershell
# Enviar dados limpos para ThingsBoard
python scripts/send_inmet_to_tb.py

# ETL MinIO → PostgreSQL (após ThingsBoard persistir no MinIO)
python scripts/etl_minio_to_postgres.py

# Testar pipeline
python scripts/test_pipeline.py
```

#### Windows (CMD)

```cmd
python scripts\send_inmet_to_tb.py
python scripts\etl_minio_to_postgres.py
python scripts\test_pipeline.py
```

---

## 9. Notebooks do Projeto

### 📓 `01_carregar_dados.ipynb`

**Propósito:** Notebook exploratório para visualização e análise rápida de dados.

**Funcionalidades:**
- Lista arquivos CSV disponíveis
- Processa um arquivo específico usando a função `processar_inmet()`
- Exibe estatísticas descritivas
- Verifica valores faltantes
- Visualiza amostras dos dados

**Quando usar:** Para exploração inicial dos dados ou análise de um arquivo específico.

### 📓 `01_tratamento_dados_inmet.ipynb`

**Propósito:** Processamento completo de todos os arquivos do INMET.

**Funcionalidades:**
- Processa todos os arquivos CSV (2020-2024, Petrolina e Garanhuns)
- Aplica função `processar_inmet()` padronizada
- Interpola valores faltantes usando método temporal
- Remove colunas 100% vazias (ex: radiação quando ausente)
- Cria features auxiliares (hora_num, mes)
- Salva dados tratados em CSV em `/data/processed/`

**Tratamento aplicado:**
- Conversão de vírgula para ponto decimal
- Padronização de formato de hora
- Criação de índice datetime
- Interpolação temporal de valores faltantes
- Preenchimento de bordas (ffill/bfill)

**Quando usar:** Para processar todos os dados e preparar para modelagem.

### 📓 `02_Modelagem_KMeans.ipynb`

**Propósito:** Modelagem de clustering para identificar padrões climáticos.

**Funcionalidades:**
- Extrai dados estruturados diretamente do PostgreSQL
- Agregação semanal dos dados horários
- Tratamento de outliers
- Normalização com StandardScaler
- Treinamento de K-Means
- Avaliação com silhouette score
- Visualização dos clusters
- Registro no MLFlow

**Variáveis utilizadas na agregação semanal:**
- Temperatura (média e desvio padrão)
- Umidade (média e mínima)
- Radiação (soma)
- Precipitação (soma)
- Pressão (média)

*Nota: A velocidade do vento é processada nos dados brutos, mas não é utilizada na agregação semanal para o modelo K-Means.*

**Quando usar:** Após o processamento dos dados, para identificar padrões climáticos.

---

## 10. Scripts Auxiliares

### 🔧 `scripts/etl_minio_to_postgres.py`

Script de ETL para transferir dados do Data Lake (MinIO) para o Data Warehouse (PostgreSQL). Este script deve ser executado após o ThingsBoard persistir os dados no MinIO através de sua Regra de Negócio.

**Uso:**

```bash
# Linux / macOS
python scripts/etl_minio_to_postgres.py

# Windows
python scripts\etl_minio_to_postgres.py
```

**Funcionalidades:**
- Conecta ao MinIO e lista arquivos CSV
- Carrega dados do MinIO (dados brutos persistidos pelo ThingsBoard)
- Cria tabela `inmet_raw` no PostgreSQL (se não existir)
- Insere dados na tabela `inmet_raw` do PostgreSQL
- Organiza dados por dispositivo (Petrolina/Garanhuns)

**Fluxo:**
1. Execute `send_inmet_to_tb.py` para enviar dados ao ThingsBoard
2. O ThingsBoard persiste dados brutos no MinIO via Regra de Negócio
3. Execute este script para transferir dados do MinIO para PostgreSQL
4. O Jupyter Notebook extrai dados do PostgreSQL para modelagem

### 🔧 `scripts/send_inmet_to_tb.py`

Script para enviar dados limpos processados para o ThingsBoard. Este é o primeiro passo do pipeline de dados.

**Uso:**

```bash
# Linux / macOS
python scripts/send_inmet_to_tb.py

# Windows
python scripts\send_inmet_to_tb.py
```

**Funcionalidades:**
- Lê CSVs tratados de `data/processed/`
- Envia telemetria linha por linha para o ThingsBoard
- Suporta múltiplos dispositivos (Petrolina, Garanhuns)
- Inclui delay para não sobrecarregar o ThingsBoard

**Configuração necessária:**
- Editar tokens dos dispositivos no dicionário `DEVICES`

**Fluxo:**
1. Este script envia dados limpos para o ThingsBoard
2. O ThingsBoard aplica uma Regra de Negócio para persistir dados brutos no MinIO
3. Execute `etl_minio_to_postgres.py` para transferir dados do MinIO para PostgreSQL

### 🔧 `scripts/test_pipeline.py`

Script de testes para validar o pipeline completo.

**Uso:**

```bash
# Linux / macOS
python scripts/test_pipeline.py

# Windows
python scripts\test_pipeline.py
```

---

## 11. Troubleshooting

### ❌ Problema: Serviços não iniciam

**Solução:**

#### Linux / macOS

```bash
# Verificar logs
docker-compose logs

# Reiniciar serviços
docker-compose restart

# Reconstruir imagens
docker-compose up -d --build --force-recreate
```

#### Windows (PowerShell)

```powershell
docker-compose logs
docker-compose restart
docker-compose up -d --build --force-recreate
```

#### Windows (CMD)

```cmd
docker-compose logs
docker-compose restart
docker-compose up -d --build --force-recreate
```

### ❌ Problema: Porta já em uso

**Solução:**
- Verifique se outra aplicação está usando a porta
- Altere a porta no `docker-compose.yml` se necessário
- Use `docker-compose down` antes de subir novamente

#### Linux / macOS

```bash
# Verificar processos usando a porta
sudo lsof -i :8888  # Para porta 8888
sudo netstat -tulpn | grep :8888

# Parar serviços
docker-compose down
```

#### Windows (PowerShell)

```powershell
# Verificar processos usando a porta
netstat -ano | findstr :8888

# Parar serviços
docker-compose down
```

### ❌ Problema: Erro ao processar dados

**Solução:**
- Verifique se os arquivos CSV estão em `/data/raw/` com a estrutura correta
- Confirme que o encoding é `latin1`
- Verifique os logs do Jupyter: `docker-compose logs jupyterlab`

#### Linux / macOS

```bash
docker-compose logs jupyterlab
```

#### Windows

```powershell
docker-compose logs jupyterlab
```

### ❌ Problema: PostgreSQL não conecta

**Solução:**
- Verifique se o serviço está rodando: `docker-compose ps postgres`
- Confirme credenciais: `postgres` / `postgres`
- Acesse via Adminer: `http://localhost:8085`
- Verifique a conexão no notebook: `postgresql://postgres:postgres@postgres:5432/clima`

### ❌ Problema: MLFlow não salva modelos

**Solução:**
- Verifique se o volume `./mlflow` está montado corretamente
- Confirme permissões de escrita no diretório
- Verifique logs: `docker-compose logs mlflow`

#### Linux / macOS

```bash
# Verificar permissões
ls -la mlflow/

# Ver logs
docker-compose logs mlflow
```

#### Windows

```powershell
docker-compose logs mlflow
```

### ❌ Problema: PostgreSQL não conecta

**Solução:**
- Verifique se o serviço está rodando: `docker-compose ps postgres`
- Confirme credenciais: `postgres` / `postgres`
- Acesse via Adminer: `http://localhost:8085`

### 🛠️ Comandos Úteis

#### Linux / macOS

```bash
# Parar todos os serviços
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Ver logs de um serviço específico
docker-compose logs -f jupyterlab

# Executar comando em um container
docker-compose exec jupyterlab bash

# Limpar recursos não utilizados
docker system prune -a

# Ver uso de recursos
docker stats
```

#### Windows (PowerShell)

```powershell
# Parar todos os serviços
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Ver logs de um serviço específico
docker-compose logs -f jupyterlab

# Executar comando em um container
docker-compose exec jupyterlab bash

# Limpar recursos não utilizados
docker system prune -a

# Ver uso de recursos
docker stats
```

#### Windows (CMD)

```cmd
docker-compose down
docker-compose down -v
docker-compose logs -f jupyterlab
docker-compose exec jupyterlab bash
docker system prune -a
docker stats
```

---

## 12. Resultados e Conclusões

### 📊 Dados Processados

- **Total de registros:** ~87.000 registros horários (por ano)
- **Período:** 2020-2024
- **Estações:** 2 (Petrolina e Garanhuns)
- **Variáveis climáticas:** 6 principais

### 🤖 Modelo K-Means

- **Método:** Clustering não-supervisionado
- **Features:** Agregações semanais de variáveis climáticas
- **Avaliação:** Silhouette score
- **Versionamento:** MLFlow

### 📈 Visualização

- **Plataforma:** ThingsBoard
- **Dashboards:** Padrões climáticos por cluster
- **Interatividade:** Filtros por período, estação e variável

### 📄 Relatório Técnico

O relatório final em PDF, contendo a arquitetura, metodologia, resultados e conclusões, será enviado junto da entrega.

---

## 📚 Referências

- [INMET - Instituto Nacional de Meteorologia](https://portal.inmet.gov.br/)
- [ThingsBoard - Documentação](https://thingsboard.io/docs/)
- [MLFlow - Documentação](https://www.mlflow.org/docs/latest/index.html)
- [Scikit-learn K-Means](https://scikit-learn.org/stable/modules/clustering.html#k-means)
- [FastAPI - Documentação](https://fastapi.tiangolo.com/)
- [Docker - Documentação](https://docs.docker.com/)
- [PostgreSQL - Documentação](https://www.postgresql.org/docs/)
- [MinIO - Documentação](https://min.io/docs/)

---

## 📝 Licença

Este projeto é desenvolvido para fins acadêmicos no contexto da disciplina de Análise e Visualização de Dados da CESAR School.

---

## 🤝 Equipe

Este é um projeto acadêmico desenvolvido pela equipe **Cobalto** ([ver membros](#2-membros-do-projeto)).

---

<div align="center">

**Desenvolvido com ❤️ pela equipe Cobalto**

[⬆ Voltar ao topo](#-avd---pipeline-de-bi-climático)

</div>
