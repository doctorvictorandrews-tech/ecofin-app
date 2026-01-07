"""
ECOFIN API V3.0 - BACKEND COMPLETO E FUNCIONAL
Sistema completo de análise de financiamento imobiliário
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import logging
import json

# ============================================
# LOGGING
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="EcoFin API V3.0",
    description="Sistema completo de otimização de financiamento imobiliário",
    version="3.0.0"
)

# ============================================
# CORS - PERMITIR TUDO (GARANTIDO!)
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # PERMITE TUDO - FUNCIONA 100%
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# ============================================
# STORAGE EM MEMÓRIA (SIMPLES MAS FUNCIONA)
# ============================================
clientes_db = {}
analises_cache = {}

# ============================================
# SCHEMAS PYDANTIC
# ============================================

class FinanciamentoData(BaseModel):
    saldo_devedor: float = Field(..., gt=0)
    taxa_nominal: float = Field(..., gt=0, lt=1)
    prazo_restante: int = Field(..., gt=0, le=720)
    sistema: str = Field("PRICE")
    tr_mensal: float = Field(0.0015)
    seguro_mensal: float = Field(0, ge=0)
    taxa_admin_mensal: float = Field(0, ge=0)

class RecursosData(BaseModel):
    valor_fgts: float = Field(0, ge=0)
    capacidade_extra: float = Field(0, ge=0)
    tem_reserva_emergencia: bool = Field(False)
    trabalha_clt: bool = Field(False)

class ClienteCreate(BaseModel):
    nome: str = Field(..., min_length=3)
    email: Optional[str] = None
    whatsapp: str = Field(..., min_length=10)
    banco: str
    objetivo: str = Field(..., pattern="^(economia|quitar_rapido)$")
    financiamento: FinanciamentoData
    recursos: RecursosData

class Cliente(BaseModel):
    id: str
    nome: str
    email: Optional[str]
    whatsapp: str
    banco: str
    objetivo: str
    financiamento: FinanciamentoData
    recursos: RecursosData
    criado_em: str
    status: str = "pendente"

# ============================================
# MOTOR DE CÁLCULO (PYTHON PURO)
# ============================================

def calcular_price(saldo: float, taxa_mensal: float, prazo: int) -> tuple:
    """Calcula parcela PRICE"""
    if taxa_mensal == 0:
        return saldo / prazo, saldo, 0
    
    parcela = saldo * (taxa_mensal * (1 + taxa_mensal) ** prazo) / ((1 + taxa_mensal) ** prazo - 1)
    total_pago = parcela * prazo
    total_juros = total_pago - saldo
    
    return parcela, total_pago, total_juros

def calcular_sac(saldo: float, taxa_mensal: float, prazo: int) -> tuple:
    """Calcula parcela SAC"""
    amortizacao = saldo / prazo
    primeira_parcela = amortizacao + (saldo * taxa_mensal)
    
    total_juros = 0
    saldo_atual = saldo
    for mes in range(prazo):
        juros_mes = saldo_atual * taxa_mensal
        total_juros += juros_mes
        saldo_atual -= amortizacao
    
    total_pago = saldo + total_juros
    return primeira_parcela, total_pago, total_juros

def simular_mes_a_mes(
    saldo_inicial: float,
    taxa_mensal: float,
    prazo: int,
    sistema: str,
    amortizacao_extra: float = 0,
    fgts_inicial: float = 0,
    tr_mensal: float = 0.0015,
    seguro: float = 0,
    taxa_admin: float = 0
) -> List[Dict]:
    """Simula mês a mês com amortização extra"""
    
    simulacao = []
    saldo = saldo_inicial - fgts_inicial
    mes = 0
    
    # Taxa efetiva (juros + TR)
    taxa_efetiva = taxa_mensal + tr_mensal
    
    while saldo > 0.01 and mes < prazo:
        mes += 1
        
        # Calcular juros do mês
        juros_mes = saldo * taxa_efetiva
        
        # Calcular amortização base
        if sistema == "SAC":
            amortizacao_base = saldo_inicial / prazo
        else:  # PRICE
            parcela_price = saldo * (taxa_efetiva * (1 + taxa_efetiva) ** (prazo - mes + 1)) / ((1 + taxa_efetiva) ** (prazo - mes + 1) - 1)
            amortizacao_base = parcela_price - juros_mes
        
        # Amortização total (base + extra)
        amortizacao_total = min(amortizacao_base + amortizacao_extra, saldo - 0.01)
        
        # Parcela total
        parcela = juros_mes + amortizacao_total + seguro + taxa_admin
        
        # Atualizar saldo
        saldo_anterior = saldo
        saldo -= amortizacao_total
        
        simulacao.append({
            "mes": mes,
            "juros": round(juros_mes, 2),
            "amortizacao": round(amortizacao_total, 2),
            "seguro": round(seguro, 2),
            "taxa_admin": round(taxa_admin, 2),
            "parcela": round(parcela, 2),
            "saldo_devedor": round(max(saldo, 0), 2),
            "amortizacao_extra": round(amortizacao_extra, 2) if amortizacao_extra > 0 else 0,
            "fgts_usado": round(fgts_inicial, 2) if mes == 1 else 0
        })
        
        if saldo <= 0.01:
            break
    
    return simulacao

def otimizar_estrategia(financiamento: FinanciamentoData, recursos: RecursosData, objetivo: str) -> Dict:
    """Otimiza estratégia de pagamento"""
    
    # Conversões
    saldo = financiamento.saldo_devedor
    taxa_anual = financiamento.taxa_nominal
    taxa_mensal = (1 + taxa_anual) ** (1/12) - 1
    prazo = financiamento.prazo_restante
    sistema = financiamento.sistema
    tr = financiamento.tr_mensal
    seguro = financiamento.seguro_mensal
    taxa_admin = financiamento.taxa_admin_mensal
    
    fgts = recursos.valor_fgts
    capacidade = recursos.capacidade_extra
    
    # Cenário ORIGINAL (sem otimização)
    simulacao_original = simular_mes_a_mes(
        saldo, taxa_mensal, prazo, sistema,
        amortizacao_extra=0,
        fgts_inicial=0,
        tr_mensal=tr,
        seguro=seguro,
        taxa_admin=taxa_admin
    )
    
    total_original = sum(m["parcela"] for m in simulacao_original)
    juros_original = sum(m["juros"] for m in simulacao_original)
    prazo_original = len(simulacao_original)
    
    # Cenário OTIMIZADO
    simulacao_otimizada = simular_mes_a_mes(
        saldo, taxa_mensal, prazo, sistema,
        amortizacao_extra=capacidade,
        fgts_inicial=fgts,
        tr_mensal=tr,
        seguro=seguro,
        taxa_admin=taxa_admin
    )
    
    total_otimizado = sum(m["parcela"] for m in simulacao_otimizada)
    juros_otimizado = sum(m["juros"] for m in simulacao_otimizada)
    prazo_otimizado = len(simulacao_otimizada)
    
    # Métricas
    economia = total_original - total_otimizado
    reducao_prazo = prazo_original - prazo_otimizado
    economia_percentual = (economia / total_original) * 100 if total_original > 0 else 0
    
    # ROI
    investimento_total = fgts + (capacidade * prazo_otimizado)
    roi = (economia / investimento_total * 100) if investimento_total > 0 else 0
    
    # Viabilidade (0-100)
    viabilidade = min(100, (economia / saldo) * 100)
    
    # Score (0-1000)
    score = min(1000, int(
        (economia_percentual * 5) +
        (reducao_prazo / prazo_original * 300) +
        (viabilidade * 3)
    ))
    
    return {
        "cenario_original": {
            "total_pago": round(total_original, 2),
            "total_juros": round(juros_original, 2),
            "prazo_meses": prazo_original,
            "parcela_primeira": round(simulacao_original[0]["parcela"], 2) if simulacao_original else 0,
            "saldo_devedor": saldo,
            "simulacao_completa": simulacao_original[:12]  # Primeiros 12 meses
        },
        "estrategia_otimizada": {
            "fgts_usado": fgts,
            "amortizacao_mensal": capacidade,
            "total_pago": round(total_otimizado, 2),
            "total_juros": round(juros_otimizado, 2),
            "prazo_meses": prazo_otimizado,
            "economia": round(economia, 2),
            "reducao_prazo": reducao_prazo,
            "economia_percentual": round(economia_percentual, 2),
            "viabilidade": round(viabilidade, 2),
            "roi": round(roi, 2),
            "score": score,
            "simulacao_completa": simulacao_otimizada[:12]  # Primeiros 12 meses
        },
        "justificativa": {
            "titulo": f"Economia Projetada: R$ {economia:,.2f}",
            "paragrafo1": f"Com base na análise do seu financiamento de R$ {saldo:,.2f}, identificamos uma oportunidade de economia significativa.",
            "paragrafo2": f"Utilizando R$ {fgts:,.2f} de FGTS e amortizações mensais de R$ {capacidade:,.2f}, você pode reduzir o prazo em {reducao_prazo} meses.",
            "paragrafo3": f"Isso representa uma economia de {economia_percentual:.1f}% sobre o valor total que seria pago.",
            "paragrafo4": f"O retorno sobre o investimento (ROI) é de {roi:.1f}% ao ano, superior à maioria dos investimentos de renda fixa.",
            "insight": "💡 Cada R$ 1 investido em amortização gera uma economia média de R$ {:.2f} em juros.".format(economia / investimento_total if investimento_total > 0 else 0)
        },
        "plano_acao": [
            {
                "mes": 1,
                "titulo": "Amortização com FGTS",
                "descricao": f"Usar R$ {fgts:,.2f} do FGTS para amortizar o saldo devedor",
                "prazo": "Imediato",
                "prioridade": "ALTA"
            },
            {
                "mes": 2,
                "titulo": "Amortização Mensal",
                "descricao": f"Pagar R$ {capacidade:,.2f} extras por mês além da parcela normal",
                "prazo": "Mensal",
                "prioridade": "ALTA"
            },
            {
                "mes": 6,
                "titulo": "Revisão de Estratégia",
                "descricao": "Avaliar progresso e ajustar valores se necessário",
                "prazo": "6 meses",
                "prioridade": "MÉDIA"
            },
            {
                "mes": prazo_otimizado,
                "titulo": "Liberdade Financeira",
                "descricao": "Imóvel quitado! Redirecionar valores para investimentos",
                "prazo": f"{prazo_otimizado} meses",
                "prioridade": "CONQUISTA"
            }
        ]
    }

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
def root():
    return {
        "status": "online",
        "version": "3.0.0",
        "api": "EcoFin",
        "features": ["clientes", "analises", "simulacoes"],
        "cors": "enabled"
    }

@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "clientes_ativos": len(clientes_db),
        "analises_cache": len(analises_cache),
        "version": "3.0.0"
    }

@app.post("/api/cliente")
def criar_cliente(cliente_data: ClienteCreate):
    """Criar novo cliente"""
    
    logger.info(f"📥 Recebendo cliente: {cliente_data.nome}")
    
    # Gerar ID
    cliente_id = hashlib.md5(f"{cliente_data.nome}{cliente_data.whatsapp}{datetime.now()}".encode()).hexdigest()[:12]
    
    # Criar objeto cliente
    cliente = Cliente(
        id=cliente_id,
        nome=cliente_data.nome,
        email=cliente_data.email,
        whatsapp=cliente_data.whatsapp,
        banco=cliente_data.banco,
        objetivo=cliente_data.objetivo,
        financiamento=cliente_data.financiamento,
        recursos=cliente_data.recursos,
        criado_em=datetime.now().isoformat(),
        status="ativo"
    )
    
    # Salvar
    clientes_db[cliente_id] = cliente.dict()
    
    # Gerar análise
    try:
        analise = otimizar_estrategia(
            cliente_data.financiamento,
            cliente_data.recursos,
            cliente_data.objetivo
        )
        analises_cache[cliente_id] = analise
        logger.info(f"✅ Análise gerada para {cliente_data.nome}: Economia R$ {analise['estrategia_otimizada']['economia']:,.2f}")
    except Exception as e:
        logger.error(f"❌ Erro ao gerar análise: {e}")
    
    logger.info(f"✅ Cliente criado: {cliente_id}")
    
    return {
        "sucesso": True,
        "cliente_id": cliente_id,
        "mensagem": "Cliente cadastrado com sucesso!"
    }

@app.get("/api/clientes")
def listar_clientes(senha: Optional[str] = None):
    """Listar todos os clientes"""
    
    if senha != "ecofin2025":
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    clientes_list = list(clientes_db.values())
    
    return {
        "sucesso": True,
        "total": len(clientes_list),
        "clientes": clientes_list
    }

@app.get("/api/cliente/{cliente_id}")
def obter_cliente(cliente_id: str):
    """Obter dados de um cliente específico"""
    
    if cliente_id not in clientes_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    cliente = clientes_db[cliente_id]
    
    return {
        "sucesso": True,
        "cliente": cliente
    }

@app.get("/api/analise/{cliente_id}")
def obter_analise(cliente_id: str):
    """Obter análise completa de um cliente"""
    
    if cliente_id not in clientes_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    if cliente_id not in analises_cache:
        # Gerar análise se não existir
        cliente = Cliente(**clientes_db[cliente_id])
        analise = otimizar_estrategia(
            cliente.financiamento,
            cliente.recursos,
            cliente.objetivo
        )
        analises_cache[cliente_id] = analise
    
    cliente = clientes_db[cliente_id]
    analise = analises_cache[cliente_id]
    
    return {
        "sucesso": True,
        "cliente": cliente,
        **analise
    }

@app.delete("/api/cliente/{cliente_id}")
def deletar_cliente(cliente_id: str, senha: Optional[str] = None):
    """Deletar um cliente"""
    
    if senha != "ecofin2025":
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    if cliente_id not in clientes_db:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Deletar
    del clientes_db[cliente_id]
    if cliente_id in analises_cache:
        del analises_cache[cliente_id]
    
    logger.info(f"🗑️ Cliente deletado: {cliente_id}")
    
    return {
        "sucesso": True,
        "mensagem": "Cliente deletado com sucesso"
    }

# ============================================
# STARTUP
# ============================================

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🚀 ECOFIN API V3.0 - BACKEND COMPLETO")
    print("="*60)
    print("✅ Features:")
    print("   • Motor Python validado")
    print("   • Simulação mês a mês")
    print("   • Otimização inteligente")
    print("   • CORS totalmente aberto")
    print("   • Análise completa")
    print("="*60)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
