"""
Script para fazer upload de arquivos de teste no MinIO
Simula dados que viriam do ThingsBoard para testar o notebook 02
"""

import json
from datetime import datetime, timedelta
from minio import Minio
from minio.error import S3Error
import io
import socket

# Configurações do MinIO
# Tentar detectar automaticamente o endpoint correto
# Tentar diferentes endpoints
possible_endpoints = [
    "minio:9000",      # Se rodar no container Docker
    "localhost:9000",  # Se rodar no host
]

MINIO_ENDPOINT = None
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "admin12345"
MINIO_USE_SSL = False
RAW_BUCKET = "inmet-raw"

# Testar qual endpoint funciona
print("🔍 Testando conexão com MinIO...")
for endpoint in possible_endpoints:
    try:
        host, port = endpoint.split(':')
        port = int(port)
        # Testar conexão TCP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            # Tentar conectar ao MinIO
            test_client = Minio(
                endpoint,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_USE_SSL,
            )
            # Testar se consegue listar buckets
            test_client.list_buckets()
            MINIO_ENDPOINT = endpoint
            print(f"✅ MinIO encontrado em: {endpoint}")
            break
    except Exception as e:
        print(f"   ❌ {endpoint}: {str(e)[:50]}...")
        continue

if MINIO_ENDPOINT is None:
    print("⚠️  Não foi possível conectar ao MinIO automaticamente.")
    print("   Usando 'localhost:9000' como padrão...")
    MINIO_ENDPOINT = "localhost:9000"

# Conectar ao MinIO
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_USE_SSL,
)

# Garantir que o bucket existe
if not minio_client.bucket_exists(RAW_BUCKET):
    minio_client.make_bucket(RAW_BUCKET)
    print(f"✅ Bucket '{RAW_BUCKET}' criado!")
else:
    print(f"✅ Bucket '{RAW_BUCKET}' já existe!")

# Criar alguns arquivos de teste
# Simulando dados de duas estações: INMET_Petrolina e INMET_Garanhuns
devices = ["INMET_Petrolina", "INMET_Garanhuns"]

# Criar dados para alguns dias de janeiro de 2024
base_date = datetime(2024, 1, 1, 0, 0, 0)
num_days = 5  # 5 dias de dados
hours_per_day = 24

print(f"\n📤 Fazendo upload de arquivos de teste...\n")

total_uploaded = 0

for device in devices:
    print(f"📡 Gerando dados para {device}...")
    
    for day in range(num_days):
        current_date = base_date + timedelta(days=day)
        
        for hour in range(hours_per_day):
            timestamp = current_date + timedelta(hours=hour)
            ts_ms = int(timestamp.timestamp() * 1000)
            
            # Simular dados climáticos realistas
            import random
            temp_base = 25.0 if "Petrolina" in device else 22.0
            temp_ar = round(temp_base + random.uniform(-3, 5) + (hour - 12) * 0.3, 1)
            umidade = round(random.uniform(50, 90), 1)
            radiacao = round(max(0, random.uniform(0, 1000) + (hour - 6) * 50 if 6 <= hour <= 18 else 0), 1)
            vento_vel = round(random.uniform(0.5, 4.0), 1)
            precipitacao = round(random.uniform(0, 2) if random.random() < 0.1 else 0, 1)
            pressao = round(random.uniform(940, 980), 1)
            
            # Criar payload no formato do ThingsBoard
            payload = {
                "ts": ts_ms,
                "values": {
                    "temp_ar": temp_ar,
                    "umidade": umidade,
                    "radiacao": radiacao,
                    "vento_vel": vento_vel,
                    "precipitacao": precipitacao,
                    "pressao": pressao
                }
            }
            
            # Formato que a API salva no MinIO
            data_to_save = {
                "device_name": device,
                "received_at": datetime.utcnow().isoformat(),
                "data": payload
            }
            
            # Montar path: inmet/<device>/<ano>/<mes>/YYYYMMDD_HHMMSS.json
            object_name = (
                f"inmet/{device}/"
                f"{timestamp.year}/{timestamp.month:02d}/"
                f"{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Fazer upload
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
                total_uploaded += 1
            except S3Error as e:
                print(f"   ❌ Erro ao fazer upload de {object_name}: {e}")
    
    print(f"   ✅ {device}: {num_days * hours_per_day} arquivos criados")

print(f"\n✅ Total de {total_uploaded} arquivos de teste enviados para o MinIO!")
print(f"   📂 Bucket: {RAW_BUCKET}")
print(f"   📅 Período: {base_date.strftime('%Y-%m-%d')} até {(base_date + timedelta(days=num_days-1)).strftime('%Y-%m-%d')}")
print(f"\n💡 Agora você pode testar o notebook 02 para ler esses dados do MinIO!")

