#!/usr/bin/env python3
"""
Script de Teste - Verificação do Pipeline INMET

Este script testa todas as etapas do pipeline para garantir
que está tudo configurado corretamente.
"""

import requests
import json
from datetime import datetime

# Cores para output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"ℹ️  {text}")


# Configurações
THINGSBOARD_URL = "http://localhost:8090"
FASTAPI_URL = "http://localhost:8000"
MINIO_CONSOLE = "http://localhost:9001"

DEVICES = {
    "INMET_Petrolina": "Sg2x96EjqTz4cblrUwtzS",
    "INMET_Garanhuns": "J3nv6VcUL9xrSDuWXE9b",
}


def test_fastapi():
    """Testa se a FastAPI está respondendo"""
    print_header("Testando FastAPI")
    
    try:
        response = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("FastAPI está rodando")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"FastAPI retornou status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Não foi possível conectar na FastAPI")
        print_warning("Verifique se o container está rodando: docker ps")
        return False
    except Exception as e:
        print_error(f"Erro ao testar FastAPI: {e}")
        return False


def test_minio():
    """Testa se o MinIO está acessível"""
    print_header("Testando MinIO")
    
    try:
        response = requests.get(MINIO_CONSOLE, timeout=5)
        if response.status_code in [200, 403]:  # 403 é esperado sem autenticação
            print_success("MinIO está rodando")
            print_info(f"Console acessível em: {MINIO_CONSOLE}")
            return True
        else:
            print_error(f"MinIO retornou status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Não foi possível conectar no MinIO")
        print_warning("Verifique se o container está rodando: docker ps")
        return False
    except Exception as e:
        print_error(f"Erro ao testar MinIO: {e}")
        return False


def test_thingsboard():
    """Testa se o ThingsBoard está acessível"""
    print_header("Testando ThingsBoard")
    
    try:
        response = requests.get(f"{THINGSBOARD_URL}/api/noauth/configuration", timeout=5)
        if response.status_code == 200:
            print_success("ThingsBoard está rodando")
            return True
        else:
            print_error(f"ThingsBoard retornou status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Não foi possível conectar no ThingsBoard")
        print_warning("Verifique se o container está rodando: docker ps")
        return False
    except Exception as e:
        print_error(f"Erro ao testar ThingsBoard: {e}")
        return False


def test_thingsboard_telemetry():
    """Testa envio de telemetria para o ThingsBoard"""
    print_header("Testando Envio de Telemetria para ThingsBoard")
    
    for device_name, token in DEVICES.items():
        print_info(f"Testando device: {device_name}")
        
        url = f"{THINGSBOARD_URL}/api/v1/{token}/telemetry"
        
        payload = {
            "ts": int(datetime.now().timestamp() * 1000),
            "values": {
                "temp_ar": 25.5,
                "umidade": 70.0,
                "vento_vel": 2.5,
                "precipitacao": 0.0,
                "pressao": 970.5,
                "teste": True
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                print_success(f"{device_name}: Telemetria enviada com sucesso!")
            else:
                print_error(f"{device_name}: Erro {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print_error(f"{device_name}: Erro ao enviar - {e}")
            return False
    
    return True


def test_fastapi_webhook():
    """Testa o webhook da FastAPI diretamente"""
    print_header("Testando Webhook da FastAPI")
    
    for device_name in DEVICES.keys():
        print_info(f"Testando webhook para: {device_name}")
        
        url = f"{FASTAPI_URL}/webhook/inmet/{device_name}"
        
        payload = {
            "ts": int(datetime.now().timestamp() * 1000),
            "values": {
                "temp_ar": 25.5,
                "umidade": 70.0,
                "teste": True
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                result = response.json()
                print_success(f"{device_name}: Webhook funcionando!")
                print_info(f"Arquivo salvo: {result.get('object')}")
            else:
                print_error(f"{device_name}: Erro {response.status_code}")
                return False
        except Exception as e:
            print_error(f"{device_name}: Erro ao chamar webhook - {e}")
            return False
    
    return True


def test_minio_files():
    """Lista arquivos no MinIO via API"""
    print_header("Verificando Arquivos no MinIO")
    
    try:
        response = requests.get(f"{FASTAPI_URL}/minio/files", timeout=5)
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            print_success(f"MinIO acessível via API")
            print_info(f"Total de arquivos: {total}")
            
            if total > 0:
                print_info("Últimos 5 arquivos:")
                for arquivo in data.get("arquivos", [])[:5]:
                    print(f"  • {arquivo['name']} ({arquivo['size']} bytes)")
            return True
        else:
            print_error(f"Erro ao listar arquivos: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro ao acessar API do MinIO: {e}")
        return False


def test_minio_stats():
    """Mostra estatísticas do MinIO"""
    print_header("Estatísticas do MinIO")
    
    try:
        response = requests.get(f"{FASTAPI_URL}/minio/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Estatísticas recuperadas")
            print_info(f"Total de arquivos: {data.get('total_arquivos', 0)}")
            print_info(f"Tamanho total: {data.get('total_size_mb', 0)} MB")
            
            devices = data.get('devices', {})
            if devices:
                print_info("Arquivos por device:")
                for device, count in devices.items():
                    print(f"  • {device}: {count} arquivos")
            return True
        else:
            print_error(f"Erro ao obter estatísticas: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro ao acessar API: {e}")
        return False


def main():
    """Executa todos os testes"""
    print_header("🧪 TESTE DE CONFIGURAÇÃO DO PIPELINE INMET")
    print_info("Este script verifica se todos os serviços estão funcionando")
    
    results = {
        "FastAPI": test_fastapi(),
        "MinIO": test_minio(),
        "ThingsBoard": test_thingsboard(),
        "ThingsBoard Telemetry": test_thingsboard_telemetry(),
        "FastAPI Webhook": test_fastapi_webhook(),
        "MinIO Files": test_minio_files(),
        "MinIO Stats": test_minio_stats(),
    }
    
    # Resumo
    print_header("📊 RESUMO DOS TESTES")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        color = GREEN if result else RED
        print(f"{color}{status}{RESET} - {test_name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} testes passaram{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{'='*60}")
        print("🎉 TODOS OS TESTES PASSARAM!")
        print("Você está pronto para executar o pipeline completo!")
        print(f"{'='*60}{RESET}\n")
        
        print_info("Próximos passos:")
        print("  1. Configure o webhook no ThingsBoard")
        print("  2. Execute: python send_inmet_to_thingsboard.py")
        print("  3. Configure o Snowflake")
        print("  4. Execute: python etl_minio_to_snowflake.py")
    else:
        print(f"\n{RED}{'='*60}")
        print("⚠️  ALGUNS TESTES FALHARAM")
        print("Verifique os serviços que falharam antes de continuar")
        print(f"{'='*60}{RESET}\n")
        
        print_warning("Dicas de troubleshooting:")
        print("  • Verifique se todos os containers estão rodando: docker-compose ps")
        print("  • Veja os logs: docker-compose logs -f")
        print("  • Reinicie os serviços: docker-compose restart")


if __name__ == "__main__":
    main()