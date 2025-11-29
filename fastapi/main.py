from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd

from minio import Minio
from minio.error import S3Error
import io

app = FastAPI(
    title="API Clima Uva Vale do São Francisco",
    description="API para acessar dados climatológicos tratados do INMET",
    version="0.1.0",
)

# Liberar CORS (se depois quiser consumir de um frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Caminho para os CSVs tratados (usados no notebook)
BASE_PROC = Path("/app/data/processed")

# ============================
# CONFIGURAÇÃO DO MINIO
# ============================
MINIO_ENDPOINT = "minio:9000"          # nome do serviço no docker-compose
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

# Garante que o bucket de dados brutos exista
if not minio_client.bucket_exists(RAW_BUCKET):
    minio_client.make_bucket(RAW_BUCKET)


@app.get("/health")
def health_check():
    """Endpoint simples para testar se a API está no ar."""
    return {"status": "ok", "message": "API rodando!"}


@app.get("/datasets")
def listar_datasets():
    """Lista todos os arquivos CSV tratados disponíveis."""
    if not BASE_PROC.exists():
        raise HTTPException(status_code=500, detail="Pasta de dados não encontrada.")

    arquivos = sorted(BASE_PROC.glob("*_tratado.csv"))
    return {
        "quantidade": len(arquivos),
        "arquivos": [a.name for a in arquivos],
    }


@app.get("/datasets/{nome_arquivo}/head")
def mostrar_head(nome_arquivo: str, n: int = 5):
    """
    Devolve as primeiras linhas de um CSV tratado.
    Exemplo:
    /datasets/petrolina_2024_tratado.csv/head?n=10
    """
    caminho = BASE_PROC / nome_arquivo

    if not caminho.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    try:
        df = pd.read_csv(caminho, index_col=0, parse_dates=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler CSV: {e}")

    return {
        "arquivo": nome_arquivo,
        "linhas": len(df),
        "colunas": list(df.columns),
        "amostra": df.head(n).reset_index().to_dict(orient="records"),
    }


# ============================
# NOVOS ENDPOINTS: INMET BRUTO → MINIO
# ============================

@app.post("/upload-inmet")
async def upload_inmet_csv(file: UploadFile = File(...)):
    """
    Recebe um CSV bruto do INMET e envia para o bucket inmet-raw no MinIO.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .csv")

    try:
        # lê o arquivo inteiro em memória
        file_bytes = await file.read()
        data_stream = io.BytesIO(file_bytes)
        size = len(file_bytes)

        object_name = file.filename  # nome do objeto no MinIO

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


@app.get("/inmet-raw-files")
def listar_arquivos_brutos():
    """
    Lista os arquivos brutos armazenados no bucket inmet-raw do MinIO.
    """
    try:
        objetos = minio_client.list_objects(RAW_BUCKET, recursive=True)
        nomes = [obj.object_name for obj in objetos]
        return {"bucket": RAW_BUCKET, "arquivos": nomes}
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar objetos: {e}")
