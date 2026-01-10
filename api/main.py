"""
API EcoFin - Com CORS Ultra Configurado
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import os
import sys
import traceback

# ============================================
# TENTAR IMPORTAR MOTOR E OTIMIZADOR
# ============================================

MOTOR_DISPONIVEL = False
OTIMIZADOR_DISPONIVEL = False
IMPORT_ERRORS = []

try:
    from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos
    MOTOR_DISPONIVEL = True
    print("✅ Motor EcoFin importado com sucesso!")
except Exception as e:
    IMPORT_ERRORS.append(f"❌ Erro ao importar motor_ecofin: {str(e)}")
    print(f"❌ Erro ao importar motor_ecofin: {str(e)}")
    traceback.print_exc()

try:
    from otimizador import SuperOtimizador
    OTIMIZADOR_DISPONIVEL = True
    print("✅ Otimizador importado com sucesso!")
except Exception as e:
    IMPORT_ERRORS.append(f"❌ Erro ao importar otimizador: {str(e)}")
    print(f"❌ Erro ao importar otimizador: {str(e)}")
    traceback.print_exc()

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(
    title="EcoFin API",
    description="API para otimização de financiamentos imobiliários",
    version="6.0.1"
)

# ============================================
# CORS - ULTRA CONFIGURADO
# ============================================

# Lista de origens permitidas
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    "https://app.meuecofin.com.br",
    "https://meuecofin.com.br",
    "https://ecofin-app-production.vercel.app",
    "*"  # Permitir todas (temporário para debug)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ============================================
# HEALTHCHECK
# ============================================

@app.get("/")
async def root():
    """Root endpoint com informações de debug"""
    return {
        "message": "EcoFin API está rodando!",
        "status": "online",
        "version": "6.0.1",
        "motor_disponivel": MOTOR_DISPONIVEL,
        "otimizador_disponivel": OTIMIZADOR_DISPONIVEL,
        "import_errors": IMPORT_ERRORS if IMPORT_ERRORS else None,
        "cors_configured": True,
        "allowed_origins": origins,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """Healthcheck endpoint"""
    status_motor = "ok" if MOTOR_DISPONIVEL else "error"
    status_otimizador = "ok" if OTIMIZADOR_DISPONIVEL else "error"
    
    return {
        "status": "healthy",
        "service": "EcoFin API",
        "version": "6.0.1",
        "checks": {
            "api": "ok",
            "motor": status_motor,
            "otimizador": status_otimizador,
            "cors": "ok"
        },
        "errors": IMPORT_ERRORS if IMPORT_ERRORS else None,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================
# OPTIONS para CORS Preflight
# ============================================

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handler para requests OPTIONS (CORS preflight)"""
    return {"message": "OK"}

# ============================================
# STORAGE
# ============================================

class InMemoryStorage:
    def __init__(self):
        self.leads: Dict[str, Dict] = {}
    
    def create(self, lead_data: Dict) -> str:
        lead_id = str(uuid.uuid4())
        lead_data['id'] = lead_id
        lead_data['data_cadastro'] = datetime.utcnow().isoformat()
        lead_data['status'] = 'pendente'
        self.leads[lead_id] = lead_data
        return lead_id
    
    def get(self, lead_id: str) -> Optional[Dict]:
        return self.leads.get(lead_id)
    
    def list(self) -> List[Dict]:
        return list(self.leads.values())
    
    def update(self, lead_id: str, lead_data: Dict) -> bool:
        if lead_id in self.leads:
            self.leads[lead_id].update(lead_data)
            return True
        return False
    
    def delete(self, lead_id: str) -> bool:
        if lead_id in self.leads:
            del self.leads[lead_id]
            return True
        return False

storage = InMemoryStorage()

# ============================================
# ENDPOINTS BÁSICOS
# ============================================

@app.get("/leads")
async def listar_leads():
    """Lista todos os leads"""
    try:
        leads = storage.list()
        return leads
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar leads: {str(e)}"
        )

@app.get("/lead/{lead_id}")
async def buscar_lead(lead_id: str):
    """Busca lead por ID"""
    lead = storage.get(lead_id)
    
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} não encontrado"
        )
    
    return lead

@app.delete("/lead/{lead_id}")
async def deletar_lead(lead_id: str):
    """Deleta lead por ID"""
    sucesso = storage.delete(lead_id)
    
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} não encontrado"
        )
    
    return {
        'success': True,
        'message': f'Lead {lead_id} deletado com sucesso'
    }

# ============================================
# ENDPOINT OTIMIZAR (COM VALIDAÇÃO)
# ============================================

class DadosFinanciamento(BaseModel):
    saldo_devedor: float = Field(..., gt=0)
    taxa_anual: float = Field(..., gt=0, lt=1)
    prazo_meses: int = Field(..., gt=0)
    sistema: str = Field(default="PRICE")

class RecursosDisponiveis(BaseModel):
    valor_fgts: float = Field(default=0, ge=0)
    capacidade_extra_mensal: float = Field(default=0, ge=0)

class LeadCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    email: str = Field(...)
    telefone: Optional[str] = None
    dados_financiamento: DadosFinanciamento
    recursos_disponiveis: RecursosDisponiveis

@app.post("/otimizar", status_code=status.HTTP_200_OK)
async def otimizar_financiamento(lead_data: LeadCreate):
    """
    Endpoint de otimização
    Se motor/otimizador não estiverem disponíveis, retorna mock
    """
    
    print(f"📨 Recebendo lead: {lead_data.nome} ({lead_data.email})")
    
    if not MOTOR_DISPONIVEL or not OTIMIZADOR_DISPONIVEL:
        # Retornar resposta mock
        print("⚠️  Motor/Otimizador não disponível, retornando mock...")
        lead_dict = {
            'nome': lead_data.nome,
            'email': lead_data.email,
            'telefone': lead_data.telefone,
            'dados_financiamento': lead_data.dados_financiamento.dict(),
            'valor_fgts': lead_data.recursos_disponiveis.valor_fgts,
            'capacidade_extra_mensal': lead_data.recursos_disponiveis.capacidade_extra_mensal,
            'analise_otimizada': {
                'status': 'mock',
                'message': 'Motor/Otimizador não disponível. Retornando dados mock.',
                'errors': IMPORT_ERRORS,
                'melhor_geral': {
                    'economia_total': 100000,
                    'reducao_prazo': 120,
                    'roi': 5.5,
                    'viabilidade': 'ALTA',
                    'fgts_usado': lead_data.recursos_disponiveis.valor_fgts,
                    'amortizacao_mensal': lead_data.recursos_disponiveis.capacidade_extra_mensal,
                    'duracao_amortizacao': 60
                }
            }
        }
        
        lead_id = storage.create(lead_dict)
        storage.update(lead_id, {'status': 'concluido'})
        
        print(f"✅ Lead mock criado: {lead_id}")
        
        return {
            'success': True,
            'message': 'Lead criado (modo mock - motor não disponível)',
            'lead_id': lead_id,
            'lead': storage.get(lead_id)
        }
    
    # Implementação real quando motor estiver disponível
    try:
        print("🔧 Processando com motor real...")
        from decimal import Decimal
        
        config = ConfiguracaoFinanciamento(
            saldo_devedor=Decimal(str(lead_data.dados_financiamento.saldo_devedor)),
            taxa_anual=Decimal(str(lead_data.dados_financiamento.taxa_anual)),
            prazo_meses=lead_data.dados_financiamento.prazo_meses,
            sistema=lead_data.dados_financiamento.sistema
        )
        
        recursos = Recursos(
            valor_fgts=Decimal(str(lead_data.recursos_disponiveis.valor_fgts)),
            capacidade_extra_mensal=Decimal(str(lead_data.recursos_disponiveis.capacidade_extra_mensal))
        )
        
        print("🚀 Iniciando otimização...")
        otimizador = SuperOtimizador(
            config=config,
            recursos=recursos,
            passo_amortizacao=100
        )
        
        resultado = otimizador.otimizar()
        print("✅ Otimização concluída!")
        
        # Serializar resultado
        def serializar(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: serializar(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [serializar(item) for item in obj]
            return obj
        
        resultado_serializado = serializar(resultado)
        
        lead_dict = {
            'nome': lead_data.nome,
            'email': lead_data.email,
            'telefone': lead_data.telefone,
            'dados_financiamento': lead_data.dados_financiamento.dict(),
            'valor_fgts': lead_data.recursos_disponiveis.valor_fgts,
            'capacidade_extra_mensal': lead_data.recursos_disponiveis.capacidade_extra_mensal,
            'analise_otimizada': resultado_serializado
        }
        
        lead_id = storage.create(lead_dict)
        storage.update(lead_id, {'status': 'concluido'})
        
        print(f"✅ Lead real criado: {lead_id}")
        
        return {
            'success': True,
            'message': 'Análise realizada com sucesso!',
            'lead_id': lead_id,
            'lead': storage.get(lead_id)
        }
        
    except Exception as e:
        print(f"❌ Erro ao processar: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar otimização: {str(e)}"
        )

# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("🚀 EcoFin API v6.0.1 iniciada!")
    print("=" * 60)
    print(f"Motor disponível: {MOTOR_DISPONIVEL}")
    print(f"Otimizador disponível: {OTIMIZADOR_DISPONIVEL}")
    print(f"CORS configurado: ✅")
    print(f"Origens permitidas: {origins}")
    if IMPORT_ERRORS:
        print("⚠️  Erros de import:")
        for error in IMPORT_ERRORS:
            print(f"   {error}")
    print("=" * 60)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
