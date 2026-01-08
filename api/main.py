"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          API ECOFIN V4.1                                    ║
║                                                                              ║
║  API REST com FastAPI                                                       ║
║  Integração com motor validado 100%                                        ║
║  Campos corretos: taxa_admin e seguro                                      ║
║  Mapeamento flat + nested para compatibilidade                             ║
║                                                                              ║
║  Versão: 4.1.0 (2025-01-07)                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import hashlib
from sqlalchemy.orm import Session

# Imports do motor
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos
from otimizador import Otimizador

# Imports do database
from database import get_db, Cliente, ClienteRepository, init_db, testar_conexao

app = FastAPI(
    title="EcoFin API",
    description="API para otimização de financiamentos imobiliários",
    version="4.1.0"
)

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Inicializa banco de dados ao iniciar"""
    print("🚀 Iniciando EcoFin API...")
    
    if testar_conexao():
        init_db()
        print("✅ Banco de dados pronto!")
    else:
        print("⚠️  Aviso: Banco de dados não conectado. Verifique DATABASE_URL.")

# ============================================
# CORS
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.meuecofin.com.br",
        "https://meuecofin.com.br",
        "https://ecofin-app.vercel.app",
        "https://*.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "*"
    ],
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

def achar_dados_cliente(cliente: ClienteCreate) -> Dict:
    """
    Converte dados nested para flat (compatibilidade com painel)
    Mantém ambos os formatos
    """
    return {
        'nome': cliente.nome,
        'email': cliente.email or "",
        'whatsapp': cliente.whatsapp,
        'banco': cliente.banco,
        'objetivo': cliente.objetivo,
        'data': datetime.now().isoformat(),
        'status': 'pendente',
        
        # Dados do financiamento (flat para painel)
        'saldoDevedor': cliente.financiamento.saldo_devedor,
        'taxaNominal': cliente.financiamento.taxa_nominal,
        'taxaAnual': cliente.financiamento.taxa_nominal,  # Alias
        'prazoRestante': cliente.financiamento.prazo_restante,
        'sistema': cliente.financiamento.sistema,
        'tr': cliente.financiamento.tr_mensal * 100,  # Converter para %
        'taxaAdm': cliente.financiamento.taxa_admin_mensal,
        'seguroMensal': cliente.financiamento.seguro_mensal,
        
        # Dados dos recursos (flat para painel)
        'valorFGTS': cliente.recursos.valor_fgts,
        'capacidadeExtra': cliente.recursos.capacidade_extra,
        'temReserva': cliente.recursos.tem_reserva_emergencia,
        'trabalhaCLT': cliente.recursos.trabalha_clt,
        
        # Manter nested para compatibilidade com endpoint /otimizar
        'financiamento': {
            'saldo_devedor': cliente.financiamento.saldo_devedor,
            'taxa_nominal': cliente.financiamento.taxa_nominal,
            'prazo_restante': cliente.financiamento.prazo_restante,
            'sistema': cliente.financiamento.sistema,
            'tr_mensal': cliente.financiamento.tr_mensal,
            'seguro_mensal': cliente.financiamento.seguro_mensal,
            'taxa_admin_mensal': cliente.financiamento.taxa_admin_mensal
        },
        'recursos': {
            'valor_fgts': cliente.recursos.valor_fgts,
            'capacidade_extra': cliente.recursos.capacidade_extra,
            'tem_reserva_emergencia': cliente.recursos.tem_reserva_emergencia,
            'trabalha_clt': cliente.recursos.trabalha_clt
        }
    }

def decimal_to_float(obj):
    """Converte Decimal para float recursivamente"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj

# ============================================
# ROTAS
# ============================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "EcoFin API",
        "version": "4.1.0",
        "motor": "validado 100%",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "motor_version": "4.1.0"
    }

@app.post("/api/cliente", status_code=status.HTTP_201_CREATED)
async def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """Cria novo cliente e calcula estratégia otimizada"""
    try:
        repo = ClienteRepository(db)
        
        # Gerar ID único
        cliente_id = hashlib.md5(
            f"{cliente.nome}{datetime.now().isoformat()}".encode()
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
        
        # Preparar dados para salvar
        cliente_data = {
            'id': cliente_id,
            'nome': cliente.nome,
            'email': cliente.email,
            'whatsapp': cliente.whatsapp,
            'banco': cliente.banco,
            'objetivo': cliente.objetivo,
            
            # Financiamento
            'saldo_devedor': cliente.financiamento.saldo_devedor,
            'taxa_nominal': cliente.financiamento.taxa_nominal,
            'prazo_restante': cliente.financiamento.prazo_restante,
            'sistema': cliente.financiamento.sistema,
            'tr_mensal': cliente.financiamento.tr_mensal,
            'seguro_mensal': cliente.financiamento.seguro_mensal,
            'taxa_admin_mensal': cliente.financiamento.taxa_admin_mensal,
            
            # Recursos
            'valor_fgts': cliente.recursos.valor_fgts,
            'capacidade_extra': cliente.recursos.capacidade_extra,
            'tem_reserva_emergencia': cliente.recursos.tem_reserva_emergencia,
            'trabalha_clt': cliente.recursos.trabalha_clt,
        }
        
        # Adicionar estratégia se encontrada
        if estrategia:
            cliente_data.update({
                'fgts_usado': float(estrategia.fgts_usado),
                'amortizacao_mensal': float(estrategia.amortizacao_mensal),
                'duracao_amortizacao': estrategia.duracao_amortizacao,
                'economia': float(estrategia.economia),
                'reducao_prazo': estrategia.reducao_prazo,
                'roi': float(estrategia.roi),
                'viabilidade': estrategia.viabilidade,
            })
        
        # Salvar no banco
        cliente_salvo = repo.criar(cliente_data)
        
        return {
            "sucesso": True,
            "cliente_id": cliente_id,
            "cliente": cliente_salvo.to_dict(),
            "estrategia": {
                'fgts_usado': float(estrategia.fgts_usado) if estrategia else 0,
                'amortizacao_mensal': float(estrategia.amortizacao_mensal) if estrategia else 0,
                'duracao_amortizacao': estrategia.duracao_amortizacao if estrategia else 0,
                'economia': float(estrategia.economia) if estrategia else 0,
                'reducao_prazo': estrategia.reducao_prazo if estrategia else 0,
                'roi': float(estrategia.roi) if estrategia else 0,
                'viabilidade': estrategia.viabilidade if estrategia else 'BAIXA',
            } if estrategia else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar cliente: {str(e)}")

@app.get("/api/clientes")
async def listar_clientes():
    """Lista todos os clientes"""
    return {
        "sucesso": True,
        "clientes": storage.listar_clientes()
    }

@app.get("/api/cliente/{cliente_id}")
async def obter_cliente(cliente_id: str):
    """Obtém cliente específico"""
    cliente = storage.obter_cliente(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"sucesso": True, "cliente": cliente}

@app.put("/api/cliente/{cliente_id}")
async def atualizar_cliente(cliente_id: str, dados: Dict):
    """Atualiza cliente"""
    sucesso = storage.atualizar_cliente(cliente_id, dados)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"sucesso": True, "mensagem": "Cliente atualizado"}

@app.delete("/api/cliente/{cliente_id}")
async def deletar_cliente(cliente_id: str):
    """Deleta cliente"""
    sucesso = storage.deletar_cliente(cliente_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"sucesso": True, "mensagem": "Cliente deletado"}

@app.post("/api/otimizar")
async def otimizar(request: OtimizacaoRequest):
    """Otimiza estratégia de amortização"""
    try:
        # Criar configuração
        config = ConfiguracaoFinanciamento(
            saldo_devedor=Decimal(str(request.financiamento.saldo_devedor)),
            taxa_anual=Decimal(str(request.financiamento.taxa_nominal)),
            prazo_meses=request.financiamento.prazo_restante,
            sistema=request.financiamento.sistema,
            tr_mensal=Decimal(str(request.financiamento.tr_mensal)),
            seguro_mensal=Decimal(str(request.financiamento.seguro_mensal)),
            taxa_admin_mensal=Decimal(str(request.financiamento.taxa_admin_mensal))
        )
        
        # Criar recursos
        recursos = Recursos(
            valor_fgts=Decimal(str(request.recursos.valor_fgts)),
            capacidade_extra_mensal=Decimal(str(request.recursos.capacidade_extra)),
            tem_reserva_emergencia=request.recursos.tem_reserva_emergencia,
            trabalha_clt=request.recursos.trabalha_clt
        )
        
        # Otimizar
        motor = MotorEcoFin(config)
        otimizador = Otimizador(motor, recursos)
        estrategia = otimizador.otimizar(request.objetivo)
        
        if not estrategia:
            raise HTTPException(status_code=400, detail="Não foi possível encontrar estratégia viável")
        
        # Converter para dict
        resultado = decimal_to_float({
            'fgts_usado': estrategia.fgts_usado,
            'amortizacao_mensal': estrategia.amortizacao_mensal,
            'duracao_amortizacao': estrategia.duracao_amortizacao,
            'total_pago': estrategia.total_pago,
            'total_juros': estrategia.total_juros,
            'prazo_meses': estrategia.prazo_meses,
            'economia': estrategia.economia,
            'reducao_prazo': estrategia.reducao_prazo,
            'viabilidade': estrategia.viabilidade,
            'roi': estrategia.roi,
            'score': estrategia.score,
            'investimento_total': estrategia.investimento_total
        })
        
        return {
            "sucesso": True,
            "estrategia": resultado
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/simular")
async def simular(
    saldo_devedor: float,
    taxa_anual: float,
    prazo_meses: int,
    sistema: str = "PRICE",
    fgts: float = 0,
    amort_mensal: float = 0,
    duracao: int = 999
):
    """Simulação rápida"""
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
            "sucesso": True,
            "resultado": decimal_to_float({
                'total_pago': resultado['total_pago'],
                'total_juros': resultado['total_juros'],
                'prazo_meses': resultado['prazo_meses']
            })
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
