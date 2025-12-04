from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime, timezone
from pathlib import Path
import io
import json
import os
import pandas as pd
import pickle
from typing import Optional, List, Any, Dict
import requests
from dotenv import load_dotenv

from minio import Minio
from minio.error import S3Error

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()

app = FastAPI(
    title="API Clima Uva Vale do São Francisco",
    description="API para receber dados do ThingsBoard e gerenciar pipeline de dados climáticos",
    version="0.3.0",
)

# ============================
# CORS
# ============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================
# CONFIGURAÇÃO DO MINIO
# ============================
# Se estiver em docker-compose, normalmente o serviço é "minio:9000"
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin12345")
MINIO_USE_SSL = os.getenv("MINIO_USE_SSL", "false").lower() == "true"
RAW_BUCKET = "inmet-raw"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_USE_SSL,
)

# Garante que o bucket existe
try:
    if not minio_client.bucket_exists(RAW_BUCKET):
        minio_client.make_bucket(RAW_BUCKET)
except Exception:
    pass  # Bucket pode já existir ou erro de conexão inicial

# ============================
# CONFIGURAÇÃO DO THINGSBOARD
# ============================
THINGSBOARD_URL = os.getenv("THINGSBOARD_URL", "http://thingsboard:9090")
THINGSBOARD_DEVICE_ID_PETROLINA = os.getenv("THINGSBOARD_DEVICE_ID_PETROLINA", "")
THINGSBOARD_DEVICE_ID_GARANHUNS = os.getenv("THINGSBOARD_DEVICE_ID_GARANHUNS", "")
THINGSBOARD_TENANT_USER = os.getenv("THINGSBOARD_TENANT_USER", "tenant@thingsboard.org")
THINGSBOARD_TENANT_PASSWORD = os.getenv("THINGSBOARD_TENANT_PASSWORD", "tenant")

# ============================
# CONFIGURAÇÃO DE DADOS PROCESSADOS
# ============================
# Caminho para dados processados (compartilhado via volume)
DATA_PROCESSED_PATH = Path("/app/data/processed")


# ============================
# HEALTHCHECK
# ============================

@app.get("/")
async def root():
    """Endpoint raiz com informações da API."""
    return {
        "message": "API Clima Uva Vale do São Francisco está rodando.",
        "endpoints": [
            "/health",
            "/ingest/inmet",
            "/webhook/inmet/{device_name}",
            "/minio/files",
            "/api/dados-processados"
        ],
    }

@app.get("/health")
def health_check():
    """Endpoint simples para testar se a API está no ar."""
    return {
        "status": "ok",
        "message": "API rodando!",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================
# WEBHOOK DO THINGSBOARD
# ============================

@app.post("/webhook/inmet/{device_name}")
async def receive_from_thingsboard(device_name: str, request: Request):
    """
    Recebe telemetria do ThingsBoard e salva no MinIO (bucket inmet-raw)
    em formato JSON, organizado por: inmet/<device>/<ano>/<mes>/YYYYMMDD_HHMMSS.json

    Formatos aceitos (payload vindo da Rule Chain):

    1) Objeto único:
       {
         "ts": 1234567890000,
         "values": { ... }
       }

    2) Lista de objetos:
       [
         {"ts": 1234567890000, "values": { ... }},
         ...
       ]
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Metadados adicionados pela API
    data_to_save = {
        "device_name": device_name,
        "received_at": datetime.utcnow().isoformat(),
        "data": body,
    }

    # ============================
    # 1) Descobrir o timestamp correto
    # ============================
    ts_ms = None

    # Caso 1: payload é um único objeto
    if isinstance(body, dict) and "ts" in body:
        ts_ms = body["ts"]

    # Caso 2: payload é uma lista de objetos
    elif isinstance(body, list) and body and isinstance(body[0], dict) and "ts" in body[0]:
        ts_ms = body[0]["ts"]

    # Converter para datetime
    if ts_ms is not None:
        try:
            ts_int = int(ts_ms)
            ts_dt = datetime.utcfromtimestamp(ts_int / 1000.0)
        except Exception:
            ts_dt = datetime.utcnow()
    else:
        # Se não veio timestamp, usa horário de recebimento
        ts_dt = datetime.utcnow()

    # ============================
    # 2) Montar o path com base NO ts
    # ============================
    # inmet/<device>/<ano>/<mes>/YYYYMMDD_HHMMSS.json
    object_name = (
        f"inmet/{device_name}/"
        f"{ts_dt.year}/{ts_dt.month:02d}/"
        f"{ts_dt.strftime('%Y%m%d_%H%M%S')}.json"
    )

    data_bytes = json.dumps(data_to_save, indent=2).encode("utf-8")
    data_stream = io.BytesIO(data_bytes)

    try:
        minio_client.put_object(
            RAW_BUCKET,
            object_name,
            data_stream,
            length=len(data_bytes),
            content_type="application/json",
        )
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no MinIO: {e}")

    return {
        "status": "ok",
        "bucket": RAW_BUCKET,
        "object": object_name,
        "device": device_name,
        "timestamp": data_to_save["received_at"],
    }


# ============================
# LISTAGEM DE ARQUIVOS
# ============================

@app.get("/minio/files")
def listar_arquivos_minio(prefix: str = ""):
    """
    Lista os arquivos armazenados no bucket inmet-raw do MinIO.
    Use 'prefix' para filtrar (ex: prefix=inmet/INMET_Petrolina).
    """
    try:
        objetos = minio_client.list_objects(RAW_BUCKET, prefix=prefix, recursive=True)
        arquivos = []

        for obj in objetos:
            arquivos.append(
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat()
                    if obj.last_modified
                    else None,
                }
            )

        return {
            "bucket": RAW_BUCKET,
            "prefix": prefix,
            "total": len(arquivos),
            "arquivos": arquivos,
        }
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar objetos: {e}")


@app.get("/minio/download/{path:path}")
def download_arquivo_minio(path: str):
    """
    Baixa um arquivo específico do MinIO.
    Exemplo: /minio/download/inmet/INMET_Petrolina/2024/01/20240101_120000.json
    """
    try:
        response = minio_client.get_object(RAW_BUCKET, path)
        content = response.read()

        if path.endswith(".json"):
            return json.loads(content)
        else:
            return {"content": content.decode("utf-8")}
    except S3Error as e:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {e}")


@app.get("/minio/stats")
def estatisticas_minio():
    """
    Retorna estatísticas sobre os dados armazenados no MinIO.
    """
    try:
        objetos = list(minio_client.list_objects(RAW_BUCKET, recursive=True))

        total_size = sum(obj.size for obj in objetos)
        devices = {}

        for obj in objetos:
            # Extrair device do path (inmet/<device>/...)
            parts = obj.object_name.split("/")
            if len(parts) >= 2 and parts[0] == "inmet":
                device = parts[1]
                devices[device] = devices.get(device, 0) + 1

        return {
            "bucket": RAW_BUCKET,
            "total_arquivos": len(objetos),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "devices": devices,
        }
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {e}")


# ============================
# UPLOAD MANUAL (para testes)
# ============================

@app.post("/upload-csv")
async def upload_csv_manual(file: UploadFile = File(...)):
    """
    Upload manual de CSV para testes.
    Salva no MinIO em: uploads/<filename>
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .csv")

    try:
        file_bytes = await file.read()
        data_stream = io.BytesIO(file_bytes)
        size = len(file_bytes)

        object_name = f"uploads/{file.filename}"

        minio_client.put_object(
            RAW_BUCKET,
            object_name,
            data_stream,
            length=size,
            content_type="text/csv",
        )

        return {
            "message": "Arquivo enviado com sucesso para o MinIO.",
            "bucket": RAW_BUCKET,
            "object_name": object_name,
            "size_bytes": size,
        }

    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no MinIO: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {e}")


# ============================
# ENDPOINTS DE DADOS PROCESSADOS
# ============================

@app.get("/api/dados-processados")
def listar_dados_processados():
    """
    Lista todos os arquivos de dados processados disponíveis.
    """
    try:
        arquivos = list(DATA_PROCESSED_PATH.glob("*.csv"))
        arquivos_info = []
        
        for arquivo in sorted(arquivos):
            try:
                # Ler apenas metadados do CSV
                df = pd.read_csv(arquivo, nrows=0)
                arquivos_info.append({
                    "nome": arquivo.name,
                    "caminho": str(arquivo),
                    "colunas": list(df.columns),
                    "tamanho_bytes": arquivo.stat().st_size,
                })
            except Exception:
                arquivos_info.append({
                    "nome": arquivo.name,
                    "caminho": str(arquivo),
                    "colunas": [],
                    "tamanho_bytes": arquivo.stat().st_size,
                })
        
        return {
            "total": len(arquivos_info),
            "arquivos": arquivos_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {e}")


@app.get("/api/dados-processados/{cidade}/{ano}")
def obter_dados_tratados(cidade: str, ano: int, limit: Optional[int] = Query(None, ge=1, le=10000)):
    """
    Obtém dados tratados de uma cidade e ano específicos.
    
    - **cidade**: petrolina ou garanhuns
    - **ano**: 2020, 2021, 2022, 2023, ou 2024
    - **limit**: Número máximo de registros a retornar (opcional, padrão: todos)
    """
    cidade_lower = cidade.lower()
    arquivo = DATA_PROCESSED_PATH / f"{cidade_lower}_{ano}_tratado.csv"
    
    if not arquivo.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Arquivo não encontrado para {cidade} em {ano}"
        )
    
    try:
        df = pd.read_csv(arquivo, index_col=0, parse_dates=True)
        
        if limit:
            df = df.head(limit)
        
        # Converter para JSON
        df_reset = df.reset_index()
        df_reset['datetime'] = df_reset['datetime'].astype(str)
        
        return {
            "cidade": cidade_lower,
            "ano": ano,
            "total_registros": len(df),
            "registros_retornados": len(df_reset),
            "periodo": {
                "inicio": str(df.index.min()),
                "fim": str(df.index.max())
            },
            "colunas": list(df.columns),
            "dados": df_reset.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {e}")


@app.get("/api/dados-agregados/clusters")
def obter_dados_clustered(
    limit: Optional[int] = Query(None, ge=1, le=10000),
    cluster: Optional[int] = Query(None, description="Filtrar por cluster específico")
):
    """
    Obtém dados agregados semanais com clusters do modelo K-Means.
    
    - **limit**: Número máximo de registros (opcional)
    - **cluster**: Filtrar por cluster específico (opcional)
    """
    arquivo = DATA_PROCESSED_PATH / "dados_semanais_clustered.csv"
    
    if not arquivo.exists():
        raise HTTPException(
            status_code=404,
            detail="Arquivo de dados agregados não encontrado. Execute o notebook de modelagem primeiro."
        )
    
    try:
        df = pd.read_csv(arquivo)
        
        # Filtrar por cluster se especificado
        if cluster is not None:
            if 'cluster' not in df.columns:
                raise HTTPException(status_code=400, detail="Coluna 'cluster' não encontrada")
            df = df[df['cluster'] == cluster]
        
        # Limitar resultados
        if limit:
            df = df.head(limit)
        
        # Converter para JSON
        if 'data_semana' in df.columns:
            df['data_semana'] = pd.to_datetime(df['data_semana']).astype(str)
        
        return {
            "total_registros": len(df),
            "registros_retornados": len(df),
            "filtro_cluster": cluster,
            "colunas": list(df.columns),
            "dados": df.to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler dados agregados: {e}")


@app.get("/api/modelo/info")
def obter_info_modelo():
    """
    Retorna informações sobre o modelo K-Means salvo.
    """
    modelo_path = DATA_PROCESSED_PATH / "modelos_backup" / "kmeans_model.pkl"
    scaler_path = DATA_PROCESSED_PATH / "modelos_backup" / "scaler.pkl"
    
    info = {
        "modelo_disponivel": modelo_path.exists(),
        "scaler_disponivel": scaler_path.exists(),
    }
    
    if modelo_path.exists():
        try:
            with open(modelo_path, 'rb') as f:
                modelo = pickle.load(f)
            info["modelo"] = {
                "n_clusters": modelo.n_clusters if hasattr(modelo, 'n_clusters') else None,
                "tipo": type(modelo).__name__,
            }
        except Exception as e:
            info["erro_modelo"] = str(e)
    
    return info


@app.post("/api/modelo/predict")
async def prever_cluster(request: Request):
    """
    Faz predição de cluster para novos dados climáticos.
    
    Body esperado (JSON):
    {
        "temp_ar": 25.5,
        "umidade": 70.0,
        "vento_vel": 2.5,
        "pressao": 970.5,
        "radiacao": 500.0  // opcional
    }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
    
    modelo_path = DATA_PROCESSED_PATH / "modelos_backup" / "kmeans_model.pkl"
    scaler_path = DATA_PROCESSED_PATH / "modelos_backup" / "scaler.pkl"
    
    if not modelo_path.exists() or not scaler_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Modelo não encontrado. Execute o notebook de modelagem primeiro."
        )
    
    try:
        # Carregar modelo e scaler
        with open(modelo_path, 'rb') as f:
            modelo = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        
        # Preparar dados
        features = ['temp_ar', 'umidade', 'vento_vel', 'pressao']
        if 'radiacao' in body:
            features.append('radiacao')
        
        # Verificar se todas as features estão presentes
        missing = [f for f in features if f not in body]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Features faltando: {missing}"
            )
        
        # Criar array de features
        X = [[body[f] for f in features]]
        
        # Normalizar
        X_scaled = scaler.transform(X)
        
        # Predizer
        cluster = modelo.predict(X_scaled)[0]
        
        return {
            "cluster_predito": int(cluster),
            "features_usadas": features,
            "dados_entrada": body,
            "dados_normalizados": X_scaled[0].tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer predição: {e}")


@app.get("/api/dados-processados/{cidade}/{ano}/download")
def download_dados_tratados(cidade: str, ano: int):
    """
    Faz download do arquivo CSV completo de dados tratados.
    """
    cidade_lower = cidade.lower()
    arquivo = DATA_PROCESSED_PATH / f"{cidade_lower}_{ano}_tratado.csv"
    
    if not arquivo.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Arquivo não encontrado para {cidade} em {ano}"
        )
    
    def generate():
        with open(arquivo, 'rb') as f:
            yield from f
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={cidade_lower}_{ano}_tratado.csv"
        }
    )


# ============================
# THINGSBOARD HELPERS (lógica do machine-learning-project)
# ============================

def get_thingsboard_token() -> str:
    """
    Autentica como tenant user e retorna JWT token.
    """
    url = f"{THINGSBOARD_URL}/api/auth/login"
    payload = {
        "username": THINGSBOARD_TENANT_USER,
        "password": THINGSBOARD_TENANT_PASSWORD,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha ao autenticar no ThingsBoard: {resp.status_code} {resp.text}",
            )

        data = resp.json()
        token = data.get("token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ThingsBoard login não retornou um token.",
            )

        return token
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao conectar ao ThingsBoard: {e}",
        )


def fetch_thingsboard_telemetry(token: str, device_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Busca dados de telemetria completos do ThingsBoard para um dispositivo INMET.
    
    Variáveis esperadas: temp_ar, umidade, vento_vel, precipitacao, pressao, radiacao
    """
    url = f"{THINGSBOARD_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"

    END_TS = 2_000_000_000_000  # Timestamp futuro grande

    params = {
        "keys": "temp_ar,umidade,vento_vel,precipitacao,pressao,radiacao",
        "startTs": 0,
        "endTs": END_TS,
        "limit": 100000,  # Limite alto para pegar todos os dados
        "agg": "NONE",
        "interval": 0,
    }

    headers = {"X-Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Falha ao buscar telemetria do ThingsBoard (status={resp.status_code}): {resp.text}",
            )

        data = resp.json()
        if not isinstance(data, dict) or not data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Resposta de telemetria do ThingsBoard está vazia ou inválida.",
            )

        return data
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar telemetria: {e}",
        )


def telemetry_to_dataframe(data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
    """
    Converte JSON de timeseries do ThingsBoard em um pandas DataFrame.
    
    Formato de entrada:
    {
      "temp_ar":   [ {"ts": 123, "value": "25.5"}, {"ts": 124, "value": "26.0"}, ... ],
      "umidade":  [ {"ts": 123, "value": "70.0"}, {"ts": 124, "value": "72.0"}, ... ],
      ...
    }
    
    Merge todas as séries por 'ts' para que cada linha corresponda a um timestamp.
    """
    df: pd.DataFrame | None = None

    for key, series in data.items():
        if not series:
            # Sem dados para esta chave
            continue

        key_df = pd.DataFrame(series)[["ts", "value"]]
        # Converter valores numéricos
        key_df["value"] = pd.to_numeric(key_df["value"], errors="coerce")
        key_df = key_df.rename(columns={"value": key})

        if df is None:
            df = key_df
        else:
            df = df.merge(key_df, on="ts", how="outer")

    if df is None or df.empty:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nenhum dado de telemetria pôde ser convertido para DataFrame.",
        )

    # Ordenar por timestamp e resetar índice
    df = df.sort_values("ts").reset_index(drop=True)

    return df


def upload_dataframe_to_minio(df: pd.DataFrame, device_name: str) -> str:
    """
    Serializa DataFrame para CSV em memória e faz upload para MinIO.
    Retorna a chave S3 usada.
    """
    # Gerar chave
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    object_name = f"inmet/{device_name}/telemetry/inmet_telemetry_{now_utc}.csv"

    # Serializar para CSV (em memória)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    body = buffer.getvalue().encode("utf-8")

    try:
        minio_client.put_object(
            RAW_BUCKET,
            object_name,
            io.BytesIO(body),
            length=len(body),
            content_type="text/csv",
        )
        return object_name
    except S3Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao fazer upload para MinIO: {e}",
        )


# ============================
# ENDPOINT DE INGESTÃO DO THINGSBOARD
# ============================

@app.post("/ingest/inmet")
async def ingest_inmet():
    """
    Busca telemetria completa do ThingsBoard para ambos os dispositivos INMET
    (Petrolina e Garanhuns) e armazena como CSV no MinIO.
    """
    results = []

    devices = [
        ("INMET_Petrolina", THINGSBOARD_DEVICE_ID_PETROLINA),
        ("INMET_Garanhuns", THINGSBOARD_DEVICE_ID_GARANHUNS),
    ]

    try:
        token = get_thingsboard_token()

        for device_name, device_id in devices:
            if not device_id:
                results.append({
                    "device": device_name,
                    "status": "skipped",
                    "message": f"Device ID não configurado para {device_name}",
                })
                continue

            try:
                # Buscar telemetria
                tb_data = fetch_thingsboard_telemetry(token, device_id)
                df = telemetry_to_dataframe(tb_data)
                
                # Upload para MinIO
                s3_key = upload_dataframe_to_minio(df, device_name)

                results.append({
                    "device": device_name,
                    "status": "success",
                    "s3_key": s3_key,
                    "rows": int(len(df)),
                })
            except HTTPException:
                raise  # Re-lançar erros HTTP
            except Exception as exc:
                results.append({
                    "device": device_name,
                    "status": "error",
                    "message": str(exc),
                })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Ingestão de telemetria INMET concluída.",
                "results": results,
            },
        )
    except HTTPException:
        raise  # Re-lançar erros HTTP
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado durante ingestão: {exc}",
        )
