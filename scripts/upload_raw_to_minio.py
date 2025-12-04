import os
from pathlib import Path
from minio import Minio
from minio.error import S3Error

# --- CONFIGURAÇÃO DO MINIO (de acordo com docker-compose.yml) ---
# Usamos 'minio:9000' porque é o nome do serviço no Docker
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "admin12345"
RAW_BUCKET = "inmet-raw"
# Prefixo para organizar os arquivos brutos dentro do bucket (Camada Raw/Landing)
RAW_PREFIX = "raw/" 

# Caminho local (host) que contém os dados a serem subidos
BASE_DIR_RAW = Path("./data/raw") 

def upload_raw_data():
    """Conecta ao MinIO e sobe todos os CSVs brutos da pasta ./data/raw"""
    print("Conectando ao MinIO...")
    try:
        # Nota: Se este script for executado FORA do contêiner Docker, 
        # você pode precisar alterar o MINIO_ENDPOINT para "localhost:9000"
        minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
    except Exception as e:
        print(f"❌ Erro ao conectar ao MinIO. Verifique se o serviço está no ar: {e}")
        return

    # Garante que o bucket existe
    if not minio_client.bucket_exists(RAW_BUCKET):
        print(f"Criando bucket: {RAW_BUCKET}")
        minio_client.make_bucket(RAW_BUCKET)

    print(f"Buscando arquivos CSV em {BASE_DIR_RAW}...")
    
    # Busca todos os CSVs recursivamente (espera-se que estejam em ./data/raw/<ano>/)
    csv_files = list(BASE_DIR_RAW.glob("**/*.CSV"))
    
    if not csv_files:
        print("❌ Nenhum arquivo CSV encontrado. Certifique-se de que os dados brutos estão na pasta.")
        return

    uploaded_count = 0
    for file_path in csv_files:
        # Cria o nome do objeto no MinIO, mantendo a estrutura de pastas
        # Ex: file_path.parts[2:] pega a partir de '2020/...'
        object_path_parts = file_path.parts[2:] 
        object_name = RAW_PREFIX + "/".join(object_path_parts)
        
        print(f"   ▶️ Subindo {file_path.name} para {RAW_BUCKET}/{object_name}")

        try:
            with open(file_path, 'rb') as file_data:
                file_stat = os.stat(file_path)
                minio_client.put_object(
                    RAW_BUCKET,
                    object_name,
                    file_data,
                    file_stat.st_size,
                    content_type="text/csv",
                )
            uploaded_count += 1
            print("   ✅ Upload Concluído.")

        except S3Error as e:
            print(f"   ❌ Erro S3 no upload: {e}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

    print("-" * 50)
    print(f"🎉 Processo Finalizado. Total de arquivos subidos: {uploaded_count}/{len(csv_files)}")

if __name__ == '__main__':
    upload_raw_data()