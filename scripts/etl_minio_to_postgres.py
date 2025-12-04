import io
import pandas as pd
from minio import Minio
from sqlalchemy import create_engine, text

# ===============================
# CONFIGURAÇÃO DO MINIO
# ===============================
# Como o ETL roda no host, usamos localhost:9000
minio_client = Minio(
    "localhost:9000",
    access_key="admin",
    secret_key="admin12345",
    secure=False
)

BUCKET = "inmet-raw"

# ===============================
# CONFIGURAÇÃO DO POSTGRES
# ===============================
# Postgres está mapeado na porta 5432 do host
engine = create_engine("postgresql://postgres:postgres@localhost:5432/clima")

# Cria tabela se não existir
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS inmet_raw (
    id SERIAL PRIMARY KEY,
    device_name TEXT NOT NULL,
    ts TIMESTAMP NOT NULL,
    temp_ar DOUBLE PRECISION,
    umidade DOUBLE PRECISION,
    radiacao DOUBLE PRECISION,
    vento_vel DOUBLE PRECISION,
    precipitacao DOUBLE PRECISION,
    pressao DOUBLE PRECISION
);
"""

with engine.begin() as conn:
    conn.execute(text(CREATE_TABLE))
    print("📌 Tabela inmet_raw verificada/criada.")


# ===============================
# FUNÇÕES AUXILIARES
# ===============================

def load_csv_from_minio(obj_name: str) -> pd.DataFrame:
    """
    Baixa um CSV do MinIO e carrega em um DataFrame.
    Os CSVs foram gerados pela FastAPI com header:
    hora,temp_ar,umidade,radiacao,vento_vel,precipitacao,pressao
    """
    response = minio_client.get_object(BUCKET, obj_name)
    data = response.read()
    response.close()
    response.release_conn()

    df = pd.read_csv(
        io.BytesIO(data),
        sep=",",
        encoding="utf-8",
    )

    # garantir nomes sem espaços
    df.columns = [c.strip() for c in df.columns]
    return df


def insert_into_postgres(df: pd.DataFrame, device_name: str):
    """
    Normaliza o DataFrame e insere na tabela inmet_raw.
    """
    # coluna 'hora' é o timestamp ISO gerado lá no ThingsBoard
    if "hora" not in df.columns:
        raise ValueError("CSV não contém a coluna 'hora'.")

    df = df.rename(columns={"hora": "ts"})

    # Converte para datetime
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna(subset=["ts"])

    # Adiciona o device_name (Petrolina/Garanhuns)
    df["device_name"] = device_name

    # Garante só as colunas de interesse
    cols = [
        "device_name",
        "ts",
        "temp_ar",
        "umidade",
        "radiacao",
        "vento_vel",
        "precipitacao",
        "pressao",
    ]
    df = df[cols]

    # Insere no Postgres
    df.to_sql(
        "inmet_raw",
        engine,
        if_exists="append",
        index=False
    )

    print(f"✔ Inserido {len(df)} registros de {device_name}")


# ===============================
# MAIN
# ===============================

def main():
    print("\n🚀 Iniciando ETL MinIO → PostgreSQL\n")

    # Lista todos os objetos do bucket
    objetos = minio_client.list_objects(BUCKET, recursive=True)

    for obj in objetos:
        if not obj.object_name.endswith(".csv"):
            continue

        print(f"\n📥 Lendo arquivo: {obj.object_name}")

        df = load_csv_from_minio(obj.object_name)

        # Caminho no MinIO: inmet/<device>/<ano>/<mes>/arquivo.csv
        parts = obj.object_name.split("/")
        device_name = parts[1] if len(parts) > 1 else "DESCONHECIDO"

        insert_into_postgres(df, device_name)

    print("\n🎉 ETL concluído.\n")


if __name__ == "__main__":
    main()
