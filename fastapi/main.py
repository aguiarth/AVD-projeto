from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import pandas as pd

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
    Exemplo de uso:
    /datasets/petrolina_2024_tratado.csv/head?n=10
    """
    caminho = BASE_PROC / nome_arquivo

    if not caminho.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    try:
        df = pd.read_csv(caminho, index_col=0, parse_dates=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler CSV: {e}")

    # converter para json
    return {
        "arquivo": nome_arquivo,
        "linhas": len(df),
        "colunas": list(df.columns),
        "amostra": df.head(n).reset_index().to_dict(orient="records"),
    }
