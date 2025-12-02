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

### 5.2. Subir a Infraestrutura

1.  [Clone este repositório](https://docs.github.com/pt/repositories/creating-and-managing-repositories/creating-a-new-repository) e entre na raiz do projeto:
    ```bash
    cd avd-projeto
    ```
2.  Construa as imagens e suba todos os serviços definidos no `docker-compose.yml`:
    ```bash
    docker-compose up -d --build
    ```

### 5.3. Execução do Pipeline

1.  Acesse o Jupyter Notebook (porta `8888`): `http://localhost:8888`
2.  Execute o notebook **`01_tratamento_dados_inmet.ipynb`** para:
    * Carregar dados brutos (do `/data/raw`).
    * Limpar nulos (interpolação) e salvar dados tratados (no `/data/processed`).
3.  **[ETAPA MANUAL: Carregamento para o Banco de Dados]**
    * Execute os scripts SQL em `sql_scripts/` para criar o schema no Snowflake (ou Postres/SQLite).
    * Use o FastAPI (`main.py`) ou um script auxiliar no Jupyter para carregar os dados tratados (CSV em `/data/processed`) para a tabela do Snowflake.
4.  Execute o notebook **`02_modelagem_kmeans.ipynb`** para:
    * Ler os dados estruturados do Snowflake.
    * Tratar Outliers e Aggregar features (Semanal).
    * Treinar e registrar o modelo K-Means no MLFlow (`http://localhost:5000`).

### 5.4. Visualização do Dashboard

1.  Acesse o Trendz Analytics (porta `8888` - pode ser a mesma do Jupyter se o `docker-compose.yml` for diferente): `http://localhost:8888`
2.  Importe o dashboard de agrupamento (arquivos em `trendz/`).
3.  O dashboard deve exibir:
    * A distribuição das semanas nos clusters identificados.
    * Gráficos de dispersão coloridos por cluster para variáveis-chave (e.g., Temperatura vs. Umidade).
    * Painéis com as médias de cada grupo climático.

## 6. Resultados e Conclusões

* **Relatório Técnico:** O relatório final em PDF, contendo a arquitetura, metodologia, resultados e conclusões, será salvo no diretório `/reports/` antes da entrega.