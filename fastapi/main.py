from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pathlib import Path
import io
import json

from minio import Minio
from minio.error import S3Error

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
MINIO_ENDPOINT = "minio:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "admin12345"
MINIO_USE_SSL = False
RAW_BUCKET = "inmet-raw"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_USE_SSL,
)

# Garante que o bucket existe
if not minio_client.bucket_exists(RAW_BUCKET):
    minio_client.make_bucket(RAW_BUCKET)


# ============================
# HEALTHCHECK
# ============================

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
