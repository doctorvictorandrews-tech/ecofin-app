"""
API EcoFin - Versão Mínima para Teste
Apenas endpoints básicos para validar deploy
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

app = FastAPI(title="EcoFin API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# HEALTHCHECK - PRIORIDADE MÁXIMA
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "EcoFin API está funcionando!",
        "status": "online",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "port": os.environ.get("PORT", "unknown")
    }

@app.get("/health")
async def health():
    """Healthcheck endpoint"""
    return {
        "status": "healthy",
        "service": "EcoFin API",
        "checks": {
            "api": "ok",
            "timestamp": datetime.utcnow().isoformat()
        }
    }

@app.get("/test")
async def test():
    """Endpoint de teste"""
    return {"message": "API está respondendo!", "ok": True}

# ============================================
# ENDPOINTS TEMPORÁRIOS (mock)
# ============================================

@app.get("/leads")
async def get_leads():
    """Retorna lista vazia por enquanto"""
    return []

@app.get("/lead/{lead_id}")
async def get_lead(lead_id: str):
    """Retorna lead mock"""
    return {
        "id": lead_id,
        "nome": "Teste",
        "email": "teste@teste.com",
        "status": "pendente",
        "message": "Esta é uma API de teste. Adicione os endpoints reais depois."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
