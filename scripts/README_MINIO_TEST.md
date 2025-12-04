# Como Testar o Notebook 02 com Dados do MinIO

Este guia explica como criar dados de teste no MinIO para validar se o notebook 02 consegue ler dados do MinIO corretamente.

## Passo 1: Fazer Upload de Dados de Teste

Execute o script `upload_test_minio.py` para criar arquivos de teste no MinIO:

```bash
# Se estiver rodando no host (Windows/Mac/Linux)
python scripts/upload_test_minio.py

# Se estiver rodando dentro do container
docker exec -it jupyter-uva python /home/jovyan/work/scripts/upload_test_minio.py
```

O script irá:
- Conectar ao MinIO
- Criar o bucket `inmet-raw` se não existir
- Gerar 5 dias de dados de teste (120 arquivos JSON por estação)
- Fazer upload de arquivos simulando dados das estações:
  - `INMET_Petrolina`
  - `INMET_Garanhuns`

## Passo 2: Testar no Notebook 02

1. Abra o notebook `notebooks/02_modelagem_kmeans.ipynb`
2. Na célula **2.1** (Carregamento dos Dados do MinIO), configure:
   ```python
   USAR_MINIO = True  # Mude para False para usar arquivos CSV locais
   ```
3. Execute as células do notebook normalmente

## Estrutura dos Dados no MinIO

Os arquivos são salvos no formato:
```
inmet/
  ├── INMET_Petrolina/
  │   └── 2024/
  │       └── 01/
  │           ├── 20240101_000000.json
  │           ├── 20240101_010000.json
  │           └── ...
  └── INMET_Garanhuns/
      └── 2024/
          └── 01/
              ├── 20240101_000000.json
              └── ...
```

Cada arquivo JSON contém:
```json
{
  "device_name": "INMET_Petrolina",
  "received_at": "2024-01-01T00:00:00",
  "data": {
    "ts": 1704067200000,
    "values": {
      "temp_ar": 25.3,
      "umidade": 65.2,
      "radiacao": 120.5,
      "vento_vel": 2.1,
      "precipitacao": 0.0,
      "pressao": 950.5
    }
  }
}
```

## Verificar Dados no MinIO

Você pode verificar os dados usando a API do FastAPI:

```bash
# Listar arquivos
curl http://localhost:8000/minio/files

# Estatísticas
curl http://localhost:8000/minio/stats
```

Ou acesse o painel web do MinIO em: http://localhost:9001
- Usuário: `admin`
- Senha: `admin12345`

## Notas

- Os dados de teste são simulados e não representam dados reais
- O script gera dados para 5 dias (120 horas por estação = 240 arquivos no total)
- Se precisar de mais dados, modifique a variável `num_days` no script

