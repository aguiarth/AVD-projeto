import os
import requests
import pandas as pd
import time
from pathlib import Path
from dotenv import load_dotenv

# ============================
# CARREGAR VARIÁVEIS DE AMBIENTE
# ============================
load_dotenv()

# ============================
# CONFIGURAÇÕES
# ============================

# URL do ThingsBoard (dentro do Docker usa o nome do serviço)
THINGSBOARD_URL = os.getenv("THINGSBOARD_URL", "http://thingsboard:9090")

# Tokens dos devices no ThingsBoard (via variáveis de ambiente)
DEVICES = {
    "INMET_Petrolina": os.getenv("THINGSBOARD_DEVICE_ACCESS_TOKEN_PETROLINA", "KqtPqGEvNa372lyyctey"),
    "INMET_Garanhuns": os.getenv("THINGSBOARD_DEVICE_ACCESS_TOKEN_GARANHUNS", "C4dThEy9BtBgco99L3WL"),
}

# Caminho base para os CSVs raw (dentro do container)
CSV_PATH = os.getenv("CSV_PATH", "/data/raw")
BASE_RAW = Path(CSV_PATH)


def enviar_telemetria(token: str, payload: dict) -> bool:
    """Envia telemetria para o ThingsBoard."""
    url = f"{THINGSBOARD_URL}/api/v1/{token}/telemetry"

    try:
        resp = requests.post(url, json=payload, timeout=10)

        if resp.status_code == 200:
            return True
        else:
            error_msg = resp.text[:200] if resp.text else "Sem detalhes"
            print(f"❌ Erro {resp.status_code}: {error_msg}")
            if resp.status_code == 401:
                print(f"   ⚠️  Token inválido ou dispositivo não existe: {token[:20]}...")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Exceção ao enviar: {e}")
        return False


def processar_csv_raw_para_thingsboard(csv_path: Path, device_token: str, device_name: str):
    """
    Lê um CSV raw do INMET e envia linha por linha para o ThingsBoard.
    O formato do INMET tem metadados nas primeiras linhas e dados começam na linha 9.
    """
    print(f"\n📤 Processando: {csv_path.name}")
    print(f"   Device: {device_name}")

    try:
        # Ler CSV raw do INMET (pula as 8 primeiras linhas de metadados)
        # Linha 9 é o cabeçalho, dados começam na linha 10
        # Tentar diferentes encodings
        encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    csv_path,
                    sep=";",
                    skiprows=8,
                    encoding=encoding,
                    on_bad_lines="skip"
                )
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if df is None:
            print(f"   ❌ Não foi possível ler o arquivo com nenhum encoding. Pulando.")
            return
        
        # Limpar nomes das colunas (remover espaços extras)
        df.columns = df.columns.str.strip()
        
        # Mapear colunas do INMET para variáveis do ThingsBoard
        # Usar busca parcial porque os nomes podem ter variações de encoding
        col_mapping = {}
        
        for col in df.columns:
            col_upper = col.upper()
            if "DATA" in col_upper and "HORA" not in col_upper:
                col_mapping[col] = "data"
            elif "HORA" in col_upper and "UTC" in col_upper:
                col_mapping[col] = "hora"
            elif "PRECIPIT" in col_upper and "TOTAL" in col_upper:
                col_mapping[col] = "precipitacao"
            elif "PRESSAO" in col_upper and "NIVEL" in col_upper and "HORARIA" in col_upper:
                col_mapping[col] = "pressao"
            elif "RADIACAO" in col_upper or "RADIAO" in col_upper:
                col_mapping[col] = "radiacao"
            elif "TEMPERATURA" in col_upper and "BULBO SECO" in col_upper and "HORARIA" in col_upper:
                col_mapping[col] = "temp_ar"
            elif "UMIDADE" in col_upper and "RELATIVA" in col_upper and "HORARIA" in col_upper:
                col_mapping[col] = "umidade"
            elif "VENTO" in col_upper and "VELOCIDADE" in col_upper and "HORARIA" in col_upper:
                col_mapping[col] = "vento_vel"
            elif "VENTO" in col_upper and "DIRE" in col_upper and "HORARIA" in col_upper:
                col_mapping[col] = "vento_dir"
        
        # Renomear colunas
        df = df.rename(columns=col_mapping)
        
        # Criar coluna datetime combinando Data e Hora UTC
        if "data" in df.columns and "hora" in df.columns:
            # Formato: "2024/01/01" e "0000 UTC"
            df["hora_clean"] = df["hora"].astype(str).str.replace(" UTC", "").str.zfill(4)
            df["datetime_str"] = df["data"].astype(str) + " " + df["hora_clean"].str[:2] + ":" + df["hora_clean"].str[2:]
            df["datetime"] = pd.to_datetime(df["datetime_str"], format="%Y/%m/%d %H:%M", errors="coerce")
        else:
            print(f"   ⚠️  Colunas Data ou Hora não encontradas. Pulando arquivo.")
            return
        
        # Remover linhas sem datetime válido
        df = df.dropna(subset=["datetime"])
        
        total = len(df)
        enviados = 0
        erros = 0

        # Função auxiliar para converter string com vírgula para float
        def str_to_float(value):
            """Converte string com vírgula (formato BR) para float."""
            if pd.isna(value):
                return None
            try:
                # Converter para string, substituir vírgula por ponto
                str_value = str(value).strip().replace(',', '.')
                return float(str_value)
            except (ValueError, AttributeError):
                return None

        for _, row in df.iterrows():
            # Converter datetime para timestamp em ms
            ts = int(row["datetime"].timestamp() * 1000)

            # Preparar payload com valores disponíveis
            payload = {
                "ts": ts,
                "values": {}
            }
            
            # Adicionar variáveis se existirem e não forem NaN
            if "temp_ar" in row:
                val = str_to_float(row["temp_ar"])
                if val is not None:
                    payload["values"]["temp_ar"] = val
            
            if "umidade" in row:
                val = str_to_float(row["umidade"])
                if val is not None:
                    payload["values"]["umidade"] = val
            
            if "vento_vel" in row:
                val = str_to_float(row["vento_vel"])
                if val is not None:
                    payload["values"]["vento_vel"] = val
            
            if "precipitacao" in row:
                val = str_to_float(row["precipitacao"])
                if val is not None:
                    payload["values"]["precipitacao"] = val
            
            if "pressao" in row:
                val = str_to_float(row["pressao"])
                if val is not None:
                    payload["values"]["pressao"] = val
            
            if "radiacao" in row:
                val = str_to_float(row["radiacao"])
                if val is not None:
                    payload["values"]["radiacao"] = val
            
            if "vento_dir" in row:
                val = str_to_float(row["vento_dir"])
                if val is not None:
                    payload["values"]["vento_dir"] = val

            # Enviar apenas se tiver pelo menos uma variável
            if payload["values"]:
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
        
    except Exception as e:
        print(f"   ❌ Erro ao processar {csv_path.name}: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Processa todos os CSVs raw do INMET e envia para o ThingsBoard.
    Os arquivos estão organizados por ano em subpastas: raw/2020/, raw/2021/, etc.
    """
    print("=" * 60)
    print("🚀 Iniciando envio de dados INMET RAW para ThingsBoard")
    print("=" * 60)

    if not BASE_RAW.exists():
        print(f"❌ Pasta não encontrada: {BASE_RAW}")
        return

    # Listar todos os CSVs raw (procurar em todas as subpastas de ano)
    csvs = []
    for ano_dir in sorted(BASE_RAW.glob("*")):
        if ano_dir.is_dir():
            csvs.extend(sorted(ano_dir.glob("*.CSV")))
            csvs.extend(sorted(ano_dir.glob("*.csv")))

    if not csvs:
        print(f"❌ Nenhum CSV encontrado em {BASE_RAW}")
        return

    print(f"📂 Encontrados {len(csvs)} arquivos\n")

    # Processar cada CSV
    for csv_path in csvs:
        # Identificar a cidade pelo nome do arquivo
        nome = csv_path.stem.upper()  # ex: "INMET_NE_PE_A307_PETROLINA_01-01-2024_A_31-12-2024"

        if "A307" in nome or "PETROLINA" in nome:
            device_name = "INMET_Petrolina"
        elif "A322" in nome or "GARANHUNS" in nome:
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
        processar_csv_raw_para_thingsboard(csv_path, token, device_name)

    print("=" * 60)
    print("🎉 Processo finalizado!")
    print("=" * 60)


if __name__ == "__main__":
    main()
