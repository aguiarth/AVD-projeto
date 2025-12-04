import requests
import pandas as pd
import time
from pathlib import Path

# ============================
# CONFIGURAÇÕES
# ============================

# Se rodar NO HOST (fora do Docker), use a porta mapeada:
THINGSBOARD_URL = "http://localhost:8090"
# Se um dia rodar DENTRO DE UM CONTAINER na mesma rede do TB,
# provavelmente será algo como: "http://thingsboard:8080"

# Tokens dos devices no ThingsBoard
DEVICES = {
    "INMET_Petrolina": "KqtPqGEvNa372lyyctey",
    "INMET_Garanhuns": "C4dThEy9BtBgco99L3WL",
}

# Caminho base para os CSVs
BASE_PROCESSED = Path("./data/processed")



def enviar_telemetria(token: str, payload: dict) -> bool:
    """Envia telemetria para o ThingsBoard."""
    url = f"{THINGSBOARD_URL}/api/v1/{token}/telemetry"

    try:
        resp = requests.post(url, json=payload, timeout=5)

        if resp.status_code == 200:
            return True
        else:
            print(f"❌ Erro {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção ao enviar: {e}")
        return False


def processar_csv_para_thingsboard(csv_path: Path, device_token: str, device_name: str):
    """
    Lê um CSV tratado e envia linha por linha para o ThingsBoard.
    Assume que o índice do CSV é um datetime (timestamp da medição).
    """
    print(f"\n📤 Processando: {csv_path.name}")
    print(f"   Device: {device_name}")

    # Ler CSV com datetime como índice
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

    total = len(df)
    enviados = 0
    erros = 0

    for idx, row in df.iterrows():
        # idx é um Timestamp do pandas → converter para ms
        ts = int(idx.timestamp() * 1000)  # ThingsBoard usa timestamp em ms

        payload = {
            "ts": ts,
            "values": {
                "temp_ar": float(row.get("temp_ar", 0)),
                "umidade": float(row.get("umidade", 0)),
                "vento_vel": float(row.get("vento_vel", 0)),
                "precipitacao": float(row.get("precipitacao", 0)),
                "pressao": float(row.get("pressao", 0)),
            },
        }

        # Adicionar radiação se existir
        if "radiacao" in row and pd.notna(row["radiacao"]):
            payload["values"]["radiacao"] = float(row["radiacao"])

        # Enviar
        if enviar_telemetria(device_token, payload):
            enviados += 1
            if enviados % 100 == 0:
                print(f"   ✅ {enviados}/{total} registros enviados...")
        else:
            erros += 1

        # Pequeno delay para não sobrecarregar
        time.sleep(0.01)

    print(f"\n✅ Finalizado: {csv_path.name}")
    print(f"   Total: {total} | Enviados: {enviados} | Erros: {erros}\n")


def main():
    """
    Processa todos os CSVs tratados e envia para o ThingsBoard.
    """
    print("=" * 60)
    print("🚀 Iniciando envio de dados INMET para ThingsBoard")
    print("=" * 60)

    if not BASE_PROCESSED.exists():
         print(f"❌ Pasta não encontrada: {BASE_PROCESSED}")
         return


    # Listar todos os CSVs tratados
    csvs = sorted(BASE_PROCESSED.glob("*_tratado.csv"))
    
    # Listar todos os CSVs RAW
    csvs = sorted(BASE_PROCESSED.glob("*.csv"))
    
    if not csvs:
        # print(f"❌ Nenhum CSV encontrado em {BASE_PROCESSED}")
        print(f"❌ Nenhum CSV encontrado em {BASE_PROCESSED}")
        return

    print(f"📂 Encontrados {len(csvs)} arquivos\n")

    # Processar cada CSV
    for csv_path in csvs:
        # Identificar a cidade pelo nome do arquivo
        nome = csv_path.stem.lower()  # ex: "petrolina_2024_tratado"

        if "petrolina" in nome:
            device_name = "INMET_Petrolina"
        elif "garanhuns" in nome:
            device_name = "INMET_Garanhuns"
        else:
            print(f"⚠️  Cidade não identificada no nome: {csv_path.name}")
            continue

        # Verificar o token
        token = DEVICES.get(device_name)
        if not token:
            print(f"⚠️  Token não configurado para {device_name}. Pulando {csv_path.name}")
            continue

        # Processar e enviar
        processar_csv_para_thingsboard(csv_path, token, device_name)

    print("=" * 60)
    print("🎉 Processo finalizado!")
    print("=" * 60)


if __name__ == "__main__":
    main()