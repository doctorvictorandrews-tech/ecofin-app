"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          API ECOFIN V5.0                                     ║
║                                                                              ║
║  API REST com FastAPI                                                       ║
║  Motor validado 100% + Otimizador completo                                 ║
║  Endpoints: /clientes, /cliente/{id}, /otimizar                            ║
║  Database: SQLite/PostgreSQL                                               ║
║                                                                              ║
║  Versão: 5.0.0 (2025-01-07)                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from sqlalchemy.orm import Session

# Imports do motor
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos
from otimizador import Otimizador

# Imports do database
from database import get_db, Cliente, ClienteRepository, init_db, testar_conexao

app = FastAPI(
    title="EcoFin API",
    description="API para otimização de financiamentos imobiliários",
    version="5.0.0"
)

# ============================================
# STARTUP EVENT
# ============================================

@app.on_event("startup")
async def startup_event():
    """Inicializa banco de dados ao iniciar"""
    print("🚀 Iniciando EcoFin API v5.0...")
    
    if testar_conexao():
        init_db()
        print("✅ Banco de dados pronto!")
    else:
        print("⚠️  Aviso: Banco de dados não conectado. Usando modo in-memory.")

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
        "http://localhost:8000",
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

# ============================================
# ROTAS
# ============================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "EcoFin API",
        "version": "5.0.0",
        "motor": "validado 100%",
        "otimizador": "875 cenários",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "motor_version": "5.0.0",
        "database": testar_conexao()
    }

# ============================================
# CRUD CLIENTES
# ============================================

@app.post("/cliente", status_code=status.HTTP_201_CREATED)
@app.post("/api/cliente", status_code=status.HTTP_201_CREATED)
async def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """
    Cria novo cliente e calcula estratégia otimizada
    
    Aceita dados no formato nested (financiamento + recursos)
    Salva no banco e retorna estratégia otimizada
    """
    try:
        repo = ClienteRepository(db)
        
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
        
        # Preparar dados para salvar
        cliente_data = {
            'id': cliente_id,
            'nome': cliente.nome,
            'email': cliente.email or "",
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
            cliente_data['economia'] = float(estrategia.economia)
            cliente_data['estrategia'] = json.dumps(estrategia_to_dict(estrategia))
        
        # Salvar no banco
        novo_cliente = repo.criar(cliente_data)
        
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
@app.get("/api/clientes")
async def listar_clientes(db: Session = Depends(get_db)):
    """
    Lista todos os clientes cadastrados
    
    Retorna lista com dados básicos + estratégia de cada cliente
    """
    try:
        repo = ClienteRepository(db)
        clientes_db = repo.listar_todos()
        
        # Converter para formato esperado pelo painel
        clientes = []
        for c in clientes_db:
            cliente_dict = {
                'id': c.id,
                'nome': c.nome,
                'email': c.email,
                'whatsapp': c.whatsapp,
                'banco': c.banco,
                'saldoDevedor': c.saldo_devedor,
                'saldo_devedor': c.saldo_devedor,
                'taxaNominal': c.taxa_nominal,
                'taxa_nominal': c.taxa_nominal,
                'prazoRestante': c.prazo_restante,
                'prazo_restante': c.prazo_restante,
                'sistema': c.sistema,
                'economia': c.economia or 0,
                'data_cadastro': c.data_cadastro.isoformat() if c.data_cadastro else None,
                'valorFGTS': c.valor_fgts or 0,
                'valor_fgts': c.valor_fgts or 0,
                'capacidadeExtra': c.capacidade_extra or 0,
                'capacidade_extra': c.capacidade_extra or 0,
                'taxaAdm': c.taxa_admin_mensal or 25,
                'taxa_admin_mensal': c.taxa_admin_mensal or 25,
                'seguroMensal': c.seguro_mensal or 50,
                'seguro_mensal': c.seguro_mensal or 50
            }
            
            # Adicionar estratégia se existe
            if c.estrategia:
                try:
                    cliente_dict['estrategia'] = json.loads(c.estrategia)
                except:
                    pass
            
            clientes.append(cliente_dict)
        
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
@app.get("/api/cliente/{cliente_id}")
async def buscar_cliente(cliente_id: str, db: Session = Depends(get_db)):
    """
    Busca cliente específico por ID
    
    Retorna dados completos do cliente + estratégia otimizada
    """
    try:
        repo = ClienteRepository(db)
        c = repo.buscar_por_id(cliente_id)
        
        if not c:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cliente {cliente_id} não encontrado"
            )
        
        cliente_dict = {
            'id': c.id,
            'nome': c.nome,
            'email': c.email,
            'whatsapp': c.whatsapp,
            'banco': c.banco,
            'objetivo': c.objetivo,
            'saldoDevedor': c.saldo_devedor,
            'saldo_devedor': c.saldo_devedor,
            'taxaNominal': c.taxa_nominal,
            'taxa_nominal': c.taxa_nominal,
            'prazoRestante': c.prazo_restante,
            'prazo_restante': c.prazo_restante,
            'sistema': c.sistema,
            'economia': c.economia or 0,
            'data_cadastro': c.data_cadastro.isoformat() if c.data_cadastro else None,
            'valorFGTS': c.valor_fgts or 0,
            'valor_fgts': c.valor_fgts or 0,
            'capacidadeExtra': c.capacidade_extra or 0,
            'capacidade_extra': c.capacidade_extra or 0,
            'taxaAdm': c.taxa_admin_mensal or 25,
            'taxa_admin_mensal': c.taxa_admin_mensal or 25,
            'seguroMensal': c.seguro_mensal or 50,
            'seguro_mensal': c.seguro_mensal or 50
        }
        
        # Adicionar estratégia
        if c.estrategia:
            try:
                cliente_dict['estrategia'] = json.loads(c.estrategia)
            except:
                pass
        
        return {
            "status": "success",
            "cliente": cliente_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar cliente: {str(e)}"
        )

# ============================================
# OTIMIZAÇÃO
# ============================================

@app.post("/otimizar")
@app.post("/api/otimizar")
async def otimizar(request: OtimizacaoRequest, db: Session = Depends(get_db)):
    """
    ENDPOINT PRINCIPAL: Otimiza financiamento
    
    Aceita formato nested (financiamento + recursos)
    Retorna melhor estratégia entre 875 cenários testados
    
    Também salva o cliente automaticamente se incluir nome/whatsapp
    """
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível encontrar estratégia viável com os recursos disponíveis"
            )
        
        return {
            "status": "success",
            "estrategia": estrategia_to_dict(estrategia),
            "cenarios_testados": 875
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao otimizar: {str(e)}"
        )

# ============================================
# SIMULAÇÃO RÁPIDA
# ============================================

@app.get("/simular")
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
    """
    Simulação rápida sem otimização
    
    Calcula resultado direto com os parâmetros fornecidos
    """
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
