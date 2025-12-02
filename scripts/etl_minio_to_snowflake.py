"""
ETL: MinIO → Snowflake

Este script:
1. Lê arquivos JSON do MinIO (bucket inmet-raw)
2. Consolida os dados em DataFrames
3. Envia para o Snowflake

Estrutura do Snowflake esperada:
- Database: CLIMA_UVA
- Schema: INMET
- Tabela: TELEMETRIA_RAW
"""

import json
import pandas as pd
from minio import Minio
from minio.error import S3Error
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from datetime import datetime
from pathlib import Path
import io

# ============================
# CONFIGURAÇÕES MINIO
# ============================
MINIO_ENDPOINT = "localhost:9000"  # ou "minio:9000" se rodar no container
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

# ============================
# CONFIGURAÇÕES SNOWFLAKE
# ============================
SNOWFLAKE_CONFIG = {
    "account": "SEU_ACCOUNT.snowflakecomputing.com",
    "user": "SEU_USUARIO",
    "password": "SUA_SENHA",
    "warehouse": "COMPUTE_WH",
    "database": "CLIMA_UVA",
    "schema": "INMET",
    "role": "ACCOUNTADMIN",  # Ajuste conforme seu role
}


def conectar_snowflake():
    """Estabelece conexão com o Snowflake"""
    try:
        conn = snowflake.connector.connect(
            account=SNOWFLAKE_CONFIG["account"],
            user=SNOWFLAKE_CONFIG["user"],
            password=SNOWFLAKE_CONFIG["password"],
            warehouse=SNOWFLAKE_CONFIG["warehouse"],
            database=SNOWFLAKE_CONFIG["database"],
            schema=SNOWFLAKE_CONFIG["schema"],
            role=SNOWFLAKE_CONFIG["role"],
        )
        print("✅ Conectado ao Snowflake")
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar no Snowflake: {e}")
        raise


def criar_tabela_se_nao_existe(conn):
    """
    Cria a tabela TELEMETRIA_RAW no Snowflake se não existir
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS TELEMETRIA_RAW (
        ID NUMBER AUTOINCREMENT PRIMARY KEY,
        DEVICE_NAME VARCHAR(100),
        TIMESTAMP_MS BIGINT,
        DATETIME_UTC TIMESTAMP_NTZ,
        TEMP_AR FLOAT,
        UMIDADE FLOAT,
        VENTO_VEL FLOAT,
        PRECIPITACAO FLOAT,
        PRESSAO FLOAT,
        RADIACAO FLOAT,
        RECEIVED_AT TIMESTAMP_NTZ,
        CREATED_AT TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
    );
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        print("✅ Tabela TELEMETRIA_RAW verificada/criada")
        cursor.close()
    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        raise


def ler_json_do_minio(object_name: str) -> dict:
    """Lê um arquivo JSON do MinIO"""
    try:
        response = minio_client.get_object(RAW_BUCKET, object_name)
        content = response.read()
        return json.loads(content)
    except Exception as e:
        print(f"❌ Erro ao ler {object_name}: {e}")
        return None


def processar_arquivo_json(data: dict) -> pd.DataFrame:
    """
    Converte dados JSON do ThingsBoard para DataFrame
    
    Estrutura esperada:
    {
        "device_name": "petrolina",
        "received_at": "2024-01-01T10:00:00",
        "data": {
            "ts": 1704106800000,
            "values": {
                "temp_ar": 25.5,
                "umidade": 70.0,
                ...
            }
        }
    }
    """
    try:
        device_name = data.get("device_name")
        received_at = data.get("received_at")
        telemetry_data = data.get("data", {})
        
        ts = telemetry_data.get("ts")
        values = telemetry_data.get("values", {})
        
        # Converter timestamp ms para datetime
        if ts:
            datetime_utc = pd.to_datetime(ts, unit='ms')
        else:
            datetime_utc = None
        
        # Criar registro
        record = {
            "DEVICE_NAME": device_name,
            "TIMESTAMP_MS": ts,
            "DATETIME_UTC": datetime_utc,
            "TEMP_AR": values.get("temp_ar"),
            "UMIDADE": values.get("umidade"),
            "VENTO_VEL": values.get("vento_vel"),
            "PRECIPITACAO": values.get("precipitacao"),
            "PRESSAO": values.get("pressao"),
            "RADIACAO": values.get("radiacao"),
            "RECEIVED_AT": pd.to_datetime(received_at) if received_at else None,
        }
        
        return pd.DataFrame([record])
    
    except Exception as e:
        print(f"❌ Erro ao processar dados: {e}")
        return pd.DataFrame()


def listar_arquivos_nao_processados(prefix: str = "inmet/") -> list:
    """
    Lista arquivos JSON no MinIO que ainda não foram processados.
    
    Para controlar o que já foi processado, você pode:
    1. Mover arquivos processados para outra pasta
    2. Adicionar uma tabela de controle no Snowflake
    3. Usar metadados do MinIO
    
    Por simplicidade, este exemplo processa todos os arquivos.
    """
    try:
        objetos = minio_client.list_objects(RAW_BUCKET, prefix=prefix, recursive=True)
        arquivos_json = [obj.object_name for obj in objetos if obj.object_name.endswith('.json')]
        return arquivos_json
    except S3Error as e:
        print(f"❌ Erro ao listar objetos: {e}")
        return []


def enviar_para_snowflake(conn, df: pd.DataFrame):
    """Envia DataFrame para o Snowflake usando write_pandas"""
    if df.empty:
        print("⚠️  DataFrame vazio, nada para enviar")
        return
    
    try:
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name="TELEMETRIA_RAW",
            database=SNOWFLAKE_CONFIG["database"],
            schema=SNOWFLAKE_CONFIG["schema"],
            auto_create_table=False,  # Já criamos a tabela antes
        )
        
        if success:
            print(f"✅ {nrows} registros enviados para Snowflake em {nchunks} chunks")
        else:
            print(f"❌ Falha ao enviar dados")
    
    except Exception as e:
        print(f"❌ Erro ao enviar para Snowflake: {e}")
        raise


def processar_lote(arquivos: list, batch_size: int = 100) -> pd.DataFrame:
    """
    Processa um lote de arquivos JSON e retorna DataFrame consolidado
    """
    dfs = []
    
    for i, arquivo in enumerate(arquivos[:batch_size], 1):
        print(f"📄 Processando {i}/{min(len(arquivos), batch_size)}: {arquivo}")
        
        data = ler_json_do_minio(arquivo)
        if data:
            df = processar_arquivo_json(data)
            if not df.empty:
                dfs.append(df)
    
    if dfs:
        df_final = pd.concat(dfs, ignore_index=True)
        return df_final
    else:
        return pd.DataFrame()


def main():
    """
    Função principal do ETL
    """
    print("=" * 60)
    print("🚀 Iniciando ETL: MinIO → Snowflake")
    print("=" * 60)
    
    # 1. Conectar ao Snowflake
    conn = conectar_snowflake()
    
    # 2. Garantir que a tabela existe
    criar_tabela_se_nao_existe(conn)
    
    # 3. Listar arquivos a processar
    print("\n📂 Listando arquivos no MinIO...")
    arquivos = listar_arquivos_nao_processados(prefix="inmet/")
    
    if not arquivos:
        print("⚠️  Nenhum arquivo encontrado para processar")
        conn.close()
        return
    
    print(f"✅ Encontrados {len(arquivos)} arquivos\n")
    
    # 4. Processar em lotes
    BATCH_SIZE = 100  # Ajuste conforme necessário
    total_processados = 0
    
    for i in range(0, len(arquivos), BATCH_SIZE):
        lote = arquivos[i:i + BATCH_SIZE]
        print(f"\n📦 Processando lote {i//BATCH_SIZE + 1} ({len(lote)} arquivos)...")
        
        df = processar_lote(lote)
        
        if not df.empty:
            enviar_para_snowflake(conn, df)
            total_processados += len(df)
        
        print(f"✅ Lote concluído. Total processado até agora: {total_processados} registros\n")
    
    # 5. Fechar conexão
    conn.close()
    
    print("=" * 60)
    print(f"🎉 ETL finalizado! Total de registros processados: {total_processados}")
    print("=" * 60)


if __name__ == "__main__":
    main()