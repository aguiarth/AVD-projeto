"""
Script para limpar telemetria de dispositivos no ThingsBoard.
Use este script se precisar apagar dados enviados anteriormente.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

THINGSBOARD_URL = os.getenv("THINGSBOARD_URL", "http://thingsboard:9090")
THINGSBOARD_TENANT_USER = os.getenv("THINGSBOARD_TENANT_USER", "tenant@thingsboard.org")
THINGSBOARD_TENANT_PASSWORD = os.getenv("THINGSBOARD_TENANT_PASSWORD", "tenant")
THINGSBOARD_DEVICE_ID_PETROLINA = os.getenv("THINGSBOARD_DEVICE_ID_PETROLINA", "")
THINGSBOARD_DEVICE_ID_GARANHUNS = os.getenv("THINGSBOARD_DEVICE_ID_GARANHUNS", "")


def get_thingsboard_token():
    """Autentica e retorna token JWT."""
    url = f"{THINGSBOARD_URL}/api/auth/login"
    payload = {
        "username": THINGSBOARD_TENANT_USER,
        "password": THINGSBOARD_TENANT_PASSWORD,
    }
    
    resp = requests.post(url, json=payload, timeout=10)
    if resp.status_code != 200:
        print(f"❌ Erro ao autenticar: {resp.status_code} {resp.text}")
        return None
    
    data = resp.json()
    return data.get("token")


def deletar_telemetria(device_id: str, device_name: str, token: str):
    """Deleta toda a telemetria de um dispositivo."""
    if not device_id:
        print(f"⚠️  Device ID não configurado para {device_name}. Pulando.")
        return False
    
    url = f"{THINGSBOARD_URL}/api/plugins/telemetry/DEVICE/{device_id}/timeseries/delete"
    
    # Deletar todas as chaves de telemetria
    keys = [
        "temp_ar", "umidade", "vento_vel", "precipitacao", 
        "pressao", "radiacao", "vento_dir"
    ]
    
    params = {
        "keys": ",".join(keys),
        "startTs": 0,
        "endTs": 9999999999999,  # Timestamp futuro grande
    }
    
    headers = {"X-Authorization": f"Bearer {token}"}
    
    try:
        resp = requests.delete(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 200:
            print(f"✅ Telemetria deletada para {device_name}")
            return True
        else:
            print(f"❌ Erro ao deletar telemetria de {device_name}: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Exceção ao deletar telemetria de {device_name}: {e}")
        return False


def main():
    print("=" * 60)
    print("🗑️  Limpando telemetria do ThingsBoard")
    print("=" * 60)
    
    token = get_thingsboard_token()
    if not token:
        print("❌ Não foi possível autenticar no ThingsBoard")
        return
    
    print("✅ Autenticado com sucesso\n")
    
    # Deletar telemetria de ambos os dispositivos
    devices = [
        ("INMET_Petrolina", THINGSBOARD_DEVICE_ID_PETROLINA),
        ("INMET_Garanhuns", THINGSBOARD_DEVICE_ID_GARANHUNS),
    ]
    
    for device_name, device_id in devices:
        if device_id:
            deletar_telemetria(device_id, device_name, token)
        else:
            print(f"⚠️  Device ID não configurado para {device_name}")
    
    print("\n" + "=" * 60)
    print("🎉 Processo finalizado!")
    print("=" * 60)


if __name__ == "__main__":
    main()

