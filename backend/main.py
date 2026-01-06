"""
ECOFIN API - TESTE MÍNIMO DE CORS
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="EcoFin API - Teste CORS")

# CORS - PERMITIR TUDO
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # PERMITE TUDO
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "API funcionando com CORS liberado!",
        "version": "CORS-TEST"
    }

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "cors": "enabled",
        "message": "Se você está vendo isso, o CORS está funcionando!"
    }

@app.post("/api/teste")
def teste(data: dict):
    return {
        "success": True,
        "received": data,
        "message": "POST funcionou! CORS OK!"
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🚀 API TESTE CORS - INICIANDO")
    print("="*60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
