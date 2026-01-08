"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          API ECOFIN V5.1                                     ║
║                                                                              ║
║  API REST com FastAPI                                                       ║
║  Motor validado 100% + Otimizador completo                                 ║
║  Storage: In-Memory (sem database externo)                                 ║
║  Endpoints: /clientes, /cliente/{id}, /otimizar                            ║
║                                                                              ║
║  Versão: 5.1.0 (2025-01-07)                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import hashlib
import json

# Imports do motor
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos
from otimizador import Otimizador

app = FastAPI(
    title="EcoFin API",
    description="API para otimização de financiamentos imobiliários",
    version="5.1.0"
)

# ============================================
# IN-MEMORY STORAGE
# ============================================

class InMemoryStorage:
    """Storage simples em memória"""
    def __init__(self):
        self.clientes = {}
    
    def criar(self, cliente_data: Dict) -> Dict:
        cliente_id = cliente_data['id']
        cliente_data['data_cadastro'] = datetime.now().isoformat()
        self.clientes[cliente_id] = cliente_data
        return cliente_data
    
    def listar_todos(self) -> List[Dict]:
        return list(self.clientes.values())
    
    def buscar_por_id(self, cliente_id: str) -> Optional[Dict]:
        return self.clientes.get(cliente_id)
    
    def atualizar(self, cliente_id: str, dados: Dict) -> bool:
        if cliente_id in self.clientes:
            self.clientes[cliente_id].update(dados)
            return True
        return False
    
    def deletar(self, cliente_id: str) -> bool:
        if cliente_id in self.clientes:
            del self.clientes[cliente_id]
            return True
        return False

storage = InMemoryStorage()

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
# SCHEMAS PYDANTIC
# ============================================

class FinanciamentoData(BaseModel):
    """Dados do financiamento"""
    saldo_devedor: float = Field(..., gt=0, description="Saldo devedor atual")
    taxa_nominal: float = Field(..., gt=0, lt=1, description="Taxa nominal anual (ex: 0.12 para 12%)")
    prazo_restante: int = Field(..., gt=0, le=720, description="Prazo restante em meses")
    sistema: str = Field("PRICE", description="Sistema de amortização: PRICE ou SAC")
    tr_mensal: float = Field(0.0015, description="TR mensal (ex: 0.0015 para 0.15%)")
    seguro_mensal: float = Field(50, description="Seguro mensal em R$")
    taxa_admin_mensal: float = Field(25, description="Taxa de administração mensal em R$")

class RecursosData(BaseModel):
    """Recursos disponíveis"""
    valor_fgts: float = Field(0, ge=0, description="Saldo FGTS disponível")
    capacidade_extra: float = Field(0, ge=0, description="Capacidade de amortização extra mensal")
    tem_reserva_emergencia: bool = Field(False, description="Possui reserva de emergência")
    trabalha_clt: bool = Field(False, description="Trabalha com CLT")

class ClienteCreate(BaseModel):
    """Dados para criar cliente"""
    nome: str = Field(..., min_length=3)
    email: Optional[str] = None
    whatsapp: str = Field(..., min_length=10)
    banco: str = Field(..., min_length=3)
    financiamento: FinanciamentoData
    recursos: RecursosData
    objetivo: str = Field("economia", description="Objetivo: 'economia' ou 'prazo'")

class OtimizacaoRequest(BaseModel):
    """Request para otimização"""
    financiamento: FinanciamentoData
    recursos: RecursosData
    objetivo: str = Field("economia")

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def decimal_to_float(obj):
    """Converte Decimal para float recursivamente"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj

def estrategia_to_dict(estrategia) -> Dict:
    """Converte objeto Estrategia para dict"""
    if not estrategia:
        return None
    
    return decimal_to_float({
        'fgts_usado': estrategia.fgts_usado,
        'fgtsUsado': estrategia.fgts_usado,
        'amortizacao_mensal': estrategia.amortizacao_mensal,
        'amortMensal': estrategia.amortizacao_mensal,
        'duracao_amortizacao': estrategia.duracao_amortizacao,
        'duracao': estrategia.duracao_amortizacao,
        'total_pago': estrategia.total_pago,
        'totalPago': estrategia.total_pago,
        'total_juros': estrategia.total_juros,
        'totalJuros': estrategia.total_juros,
        'prazo_meses': estrategia.prazo_meses,
        'prazoMeses': estrategia.prazo_meses,
        'economia': estrategia.economia,
        'reducao_prazo': estrategia.reducao_prazo,
        'reducaoPrazo': estrategia.reducao_prazo,
        'viabilidade': estrategia.viabilidade,
        'roi': estrategia.roi,
        'score': estrategia.score,
        'investimento_total': estrategia.investimento_total,
        'investimentoTotal': estrategia.investimento_total
    })

# ============================================
# ROTAS
# ============================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "EcoFin API",
        "version": "5.1.0",
        "motor": "validado 100%",
        "otimizador": "875 cenários",
        "storage": "in-memory",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "5.1.0",
        "clientes_cadastrados": len(storage.clientes)
    }

# ============================================
# CRUD CLIENTES
# ============================================

@app.post("/cliente", status_code=status.HTTP_201_CREATED)
@app.post("/otimizar", status_code=status.HTTP_201_CREATED)
async def criar_cliente(cliente: ClienteCreate):
    """
    Cria novo cliente e calcula estratégia otimizada
    
    ATENÇÃO: Este endpoint aceita AMBOS os nomes:
    - POST /cliente (preferido)
    - POST /otimizar (compatibilidade com index.html)
    """
    try:
        # Gerar ID único
        cliente_id = hashlib.md5(
            f"{cliente.nome}{cliente.whatsapp}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Calcular estratégia otimizada
        config = ConfiguracaoFinanciamento(
            saldo_devedor=Decimal(str(cliente.financiamento.saldo_devedor)),
            taxa_anual=Decimal(str(cliente.financiamento.taxa_nominal)),
            prazo_meses=cliente.financiamento.prazo_restante,
            sistema=cliente.financiamento.sistema,
            tr_mensal=Decimal(str(cliente.financiamento.tr_mensal)),
            seguro_mensal=Decimal(str(cliente.financiamento.seguro_mensal)),
            taxa_admin_mensal=Decimal(str(cliente.financiamento.taxa_admin_mensal))
        )
        
        recursos = Recursos(
            valor_fgts=Decimal(str(cliente.recursos.valor_fgts)),
            capacidade_extra_mensal=Decimal(str(cliente.recursos.capacidade_extra)),
            tem_reserva_emergencia=cliente.recursos.tem_reserva_emergencia,
            trabalha_clt=cliente.recursos.trabalha_clt
        )
        
        motor = MotorEcoFin(config)
        otimizador = Otimizador(motor, recursos)
        estrategia = otimizador.otimizar(cliente.objetivo)
        
        # Preparar dados para salvar (ambos os formatos)
        cliente_data = {
            'id': cliente_id,
            'nome': cliente.nome,
            'email': cliente.email or "",
            'whatsapp': cliente.whatsapp,
            'banco': cliente.banco,
            'objetivo': cliente.objetivo,
            
            # Snake_case (padrão API)
            'saldo_devedor': cliente.financiamento.saldo_devedor,
            'taxa_nominal': cliente.financiamento.taxa_nominal,
            'prazo_restante': cliente.financiamento.prazo_restante,
            'sistema': cliente.financiamento.sistema,
            'tr_mensal': cliente.financiamento.tr_mensal,
            'seguro_mensal': cliente.financiamento.seguro_mensal,
            'taxa_admin_mensal': cliente.financiamento.taxa_admin_mensal,
            'valor_fgts': cliente.recursos.valor_fgts,
            'capacidade_extra': cliente.recursos.capacidade_extra,
            'tem_reserva_emergencia': cliente.recursos.tem_reserva_emergencia,
            'trabalha_clt': cliente.recursos.trabalha_clt,
            
            # CamelCase (compatibilidade painel)
            'saldoDevedor': cliente.financiamento.saldo_devedor,
            'taxaNominal': cliente.financiamento.taxa_nominal,
            'prazoRestante': cliente.financiamento.prazo_restante,
            'taxaAdm': cliente.financiamento.taxa_admin_mensal,
            'seguroMensal': cliente.financiamento.seguro_mensal,
            'valorFGTS': cliente.recursos.valor_fgts,
            'capacidadeExtra': cliente.recursos.capacidade_extra,
        }
        
        # Adicionar estratégia
        if estrategia:
            cliente_data['economia'] = float(estrategia.economia)
            cliente_data['estrategia'] = estrategia_to_dict(estrategia)
        
        # Salvar
        storage.criar(cliente_data)
        
        return {
            "status": "success",
            "message": "Cliente criado com sucesso",
            "cliente_id": cliente_id,
            "estrategia": estrategia_to_dict(estrategia) if estrategia else None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar cliente: {str(e)}"
        )

@app.get("/clientes")
async def listar_clientes():
    """Lista todos os clientes cadastrados"""
    try:
        clientes = storage.listar_todos()
        
        return {
            "status": "success",
            "total": len(clientes),
            "clientes": clientes
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar clientes: {str(e)}"
        )

@app.get("/cliente/{cliente_id}")
async def buscar_cliente(cliente_id: str):
    """Busca cliente específico por ID"""
    try:
        cliente = storage.buscar_por_id(cliente_id)
        
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {cliente_id} não encontrado"
            )
        
        return {
            "status": "success",
            "cliente": cliente
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar cliente: {str(e)}"
        )

@app.put("/cliente/{cliente_id}")
async def atualizar_cliente(cliente_id: str, dados: Dict):
    """Atualiza cliente"""
    try:
        sucesso = storage.atualizar(cliente_id, dados)
        
        if not sucesso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        
        return {
            "status": "success",
            "message": "Cliente atualizado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar: {str(e)}"
        )

@app.delete("/cliente/{cliente_id}")
async def deletar_cliente(cliente_id: str):
    """Deleta cliente"""
    try:
        sucesso = storage.deletar(cliente_id)
        
        if not sucesso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
        
        return {
            "status": "success",
            "message": "Cliente deletado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar: {str(e)}"
        )

# ============================================
# SIMULAÇÃO RÁPIDA
# ============================================

@app.get("/simular")
async def simular(
    saldo_devedor: float,
    taxa_anual: float,
    prazo_meses: int,
    sistema: str = "PRICE",
    fgts: float = 0,
    amort_mensal: float = 0,
    duracao: int = 999
):
    """Simulação rápida sem otimização"""
    try:
        config = ConfiguracaoFinanciamento(
            saldo_devedor=Decimal(str(saldo_devedor)),
            taxa_anual=Decimal(str(taxa_anual)),
            prazo_meses=prazo_meses,
            sistema=sistema
        )
        
        motor = MotorEcoFin(config)
        resultado = motor.simular_completo(
            Decimal(str(fgts)),
            Decimal(str(amort_mensal)),
            duracao
        )
        
        return {
            "status": "success",
            "resultado": decimal_to_float({
                'total_pago': resultado['total_pago'],
                'total_juros': resultado['total_juros'],
                'prazo_meses': resultado['prazo_meses'],
                'total_amortizado': resultado['total_amortizado']
            })
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao simular: {str(e)}"
        )

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
