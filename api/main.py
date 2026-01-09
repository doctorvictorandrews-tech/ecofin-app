"""
API EcoFin - Versão Completa com Motor e Otimizador
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation
import uuid
import os

# Imports do motor
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos
from otimizador import SuperOtimizador

app = FastAPI(
    title="EcoFin API",
    description="API para otimização de financiamentos imobiliários",
    version="6.0.0"
)

# ============================================
# CORS
# ============================================

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
        "version": "6.0.0",
        "endpoints": ["/health", "/leads", "/lead/{id}", "/otimizar"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health():
    """Healthcheck endpoint"""
    return {
        "status": "healthy",
        "service": "EcoFin API",
        "version": "6.0.0",
        "checks": {
            "api": "ok",
            "storage": "ok",
            "motor": "ok",
            "otimizador": "ok"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================
# IN-MEMORY STORAGE
# ============================================

class InMemoryStorage:
    """Storage simples em memória"""
    
    def __init__(self):
        self.leads: Dict[str, Dict] = {}
    
    def create(self, lead_data: Dict) -> str:
        """Criar novo lead"""
        lead_id = str(uuid.uuid4())
        lead_data['id'] = lead_id
        lead_data['data_cadastro'] = datetime.utcnow().isoformat()
        lead_data['status'] = 'pendente'
        self.leads[lead_id] = lead_data
        return lead_id
    
    def get(self, lead_id: str) -> Optional[Dict]:
        """Buscar lead por ID"""
        return self.leads.get(lead_id)
    
    def list(self) -> List[Dict]:
        """Listar todos os leads"""
        return list(self.leads.values())
    
    def update(self, lead_id: str, lead_data: Dict) -> bool:
        """Atualizar lead"""
        if lead_id in self.leads:
            self.leads[lead_id].update(lead_data)
            return True
        return False
    
    def delete(self, lead_id: str) -> bool:
        """Deletar lead"""
        if lead_id in self.leads:
            del self.leads[lead_id]
            return True
        return False

# Instância global do storage
storage = InMemoryStorage()

# ============================================
# MODELS
# ============================================

class DadosFinanciamento(BaseModel):
    """Dados do financiamento"""
    saldo_devedor: float = Field(..., gt=0, description="Saldo devedor em R$")
    taxa_anual: float = Field(..., gt=0, lt=1, description="Taxa de juros anual (0.12 = 12%)")
    prazo_meses: int = Field(..., gt=0, description="Prazo em meses")
    sistema: str = Field(default="PRICE", description="Sistema de amortização")
    
    @field_validator('sistema')
    @classmethod
    def validate_sistema(cls, v):
        if v.upper() not in ['PRICE', 'SAC']:
            raise ValueError('Sistema deve ser PRICE ou SAC')
        return v.upper()

class RecursosDisponiveis(BaseModel):
    """Recursos disponíveis para amortização"""
    valor_fgts: float = Field(default=0, ge=0, description="Valor disponível no FGTS")
    capacidade_extra_mensal: float = Field(default=0, ge=0, description="Capacidade de amortização mensal")

class LeadCreate(BaseModel):
    """Dados para criar lead"""
    nome: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    telefone: Optional[str] = Field(None, max_length=20)
    dados_financiamento: DadosFinanciamento
    recursos_disponiveis: RecursosDisponiveis

class LeadResponse(BaseModel):
    """Resposta com dados do lead"""
    id: str
    nome: str
    email: str
    telefone: Optional[str]
    status: str
    data_cadastro: str
    dados_financiamento: Dict
    valor_fgts: float
    capacidade_extra_mensal: float
    analise_otimizada: Optional[Dict] = None

# ============================================
# HELPER FUNCTIONS
# ============================================

def converter_para_decimal(valor: Any) -> Decimal:
    """Converte valor para Decimal"""
    try:
        if isinstance(valor, Decimal):
            return valor
        if isinstance(valor, (int, float)):
            return Decimal(str(valor))
        if isinstance(valor, str):
            return Decimal(valor)
        raise InvalidOperation(f"Não foi possível converter {type(valor)} para Decimal")
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"Erro ao converter para Decimal: {e}")

def serializar_resultado(obj: Any) -> Any:
    """Serializa objetos Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: serializar_resultado(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serializar_resultado(item) for item in obj]
    return obj

# ============================================
# ENDPOINTS
# ============================================

@app.post("/otimizar", status_code=status.HTTP_200_OK)
async def otimizar_financiamento(lead_data: LeadCreate):
    """
    Recebe dados do lead, realiza análise e salva no storage
    """
    try:
        # 1. Criar configuração do financiamento
        config = ConfiguracaoFinanciamento(
            saldo_devedor=converter_para_decimal(lead_data.dados_financiamento.saldo_devedor),
            taxa_anual=converter_para_decimal(lead_data.dados_financiamento.taxa_anual),
            prazo_meses=lead_data.dados_financiamento.prazo_meses,
            sistema=lead_data.dados_financiamento.sistema
        )
        
        # 2. Criar recursos disponíveis
        recursos = Recursos(
            valor_fgts=converter_para_decimal(lead_data.recursos_disponiveis.valor_fgts),
            capacidade_extra_mensal=converter_para_decimal(lead_data.recursos_disponiveis.capacidade_extra_mensal)
        )
        
        # 3. Criar otimizador (passo R$ 100 para performance)
        otimizador = SuperOtimizador(
            configuracao=config,
            recursos=recursos,
            passo_amortizacao=100  # Granularidade média
        )
        
        # 4. Executar otimização
        resultado = otimizador.otimizar()
        
        # 5. Serializar resultado
        resultado_serializado = serializar_resultado(resultado)
        
        # 6. Preparar dados do lead
        lead_dict = {
            'nome': lead_data.nome,
            'email': lead_data.email,
            'telefone': lead_data.telefone,
            'dados_financiamento': {
                'saldo_devedor': lead_data.dados_financiamento.saldo_devedor,
                'taxa_anual': lead_data.dados_financiamento.taxa_anual,
                'prazo_meses': lead_data.dados_financiamento.prazo_meses,
                'sistema': lead_data.dados_financiamento.sistema
            },
            'valor_fgts': lead_data.recursos_disponiveis.valor_fgts,
            'capacidade_extra_mensal': lead_data.recursos_disponiveis.capacidade_extra_mensal,
            'analise_otimizada': resultado_serializado
        }
        
        # 7. Salvar no storage
        lead_id = storage.create(lead_dict)
        
        # 8. Atualizar status
        storage.update(lead_id, {'status': 'concluido'})
        
        # 9. Retornar resposta
        lead_salvo = storage.get(lead_id)
        
        return {
            'success': True,
            'message': 'Análise realizada com sucesso!',
            'lead_id': lead_id,
            'lead': lead_salvo
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro nos dados fornecidos: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar otimização: {str(e)}"
        )

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
    try:
        lead = storage.get(lead_id)
        
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lead {lead_id} não encontrado"
            )
        
        return lead
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar lead: {str(e)}"
        )

@app.delete("/lead/{lead_id}")
async def deletar_lead(lead_id: str):
    """Deleta lead por ID"""
    try:
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
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar lead: {str(e)}"
        )

# ============================================
# STARTUP
# ============================================

@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a API"""
    print("=" * 60)
    print("🚀 EcoFin API v6.0.0 iniciada com sucesso!")
    print("=" * 60)
    print(f"📊 Storage: In-Memory")
    print(f"🔧 Motor: V5 (corrigido)")
    print(f"🎯 Otimizador: V6 (exploração exaustiva)")
    print("=" * 60)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
