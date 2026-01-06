"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    API ECOFIN - VALIDAÇÕES CORRETAS V2.1                     ║
║                                                                              ║
║  ✅ Campos seguro_mensal e taxa_admin_mensal                                ║
║  ✅ Validações inteligentes                                                 ║
║  ✅ Economia pode ser > saldo (é normal com juros altos!)                   ║
║  ✅ Garantir: economia <= total_pago_original                               ║
║  ✅ Garantir: reducao_prazo <= prazo_original                               ║
║  ✅ ROI máximo 5000% a.a. (evitar absurdos)                                 ║
║  ✅ Logs detalhados                                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import logging

# Imports do motor
from motor_ecofin import (
    MotorEcoFin, 
    ConfiguracaoFinanciamento,
    Recursos
)
from otimizador import Otimizador

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURAÇÃO DA API
# ============================================

app = FastAPI(
    title="EcoFin API v2",
    description="API REST com validações anti-absurdo",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.meuecofin.com.br",
        "https://meuecofin.com.br",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compressão
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Senha
ADMIN_PASSWORD = "ecofin2025"

# ============================================
# SCHEMAS PYDANTIC - COM CAMPOS NOVOS
# ============================================

class FinanciamentoData(BaseModel):
    saldo_devedor: float = Field(..., gt=0, description="Saldo devedor em reais")
    taxa_nominal: float = Field(..., gt=0, lt=1, description="Taxa nominal anual (ex: 0.0975 para 9.75%)")
    prazo_restante: int = Field(..., gt=0, le=720, description="Prazo restante em meses")
    sistema: str = Field("PRICE", description="Sistema de amortização: SAC ou PRICE")
    tr_mensal: float = Field(0.0015, ge=0, le=0.01, description="TR mensal (padrão 0.15%)")
    seguro_mensal: float = Field(0, ge=0, description="Seguro mensal em reais")
    taxa_admin_mensal: float = Field(0, ge=0, description="Taxa administrativa mensal em reais")
    
    @validator('sistema')
    def validar_sistema(cls, v):
        if v.upper() not in ['SAC', 'PRICE']:
            raise ValueError('Sistema deve ser SAC ou PRICE')
        return v.upper()

class RecursosData(BaseModel):
    valor_fgts: float = Field(0, ge=0, description="Valor disponível de FGTS")
    capacidade_extra: float = Field(0, ge=0, description="Capacidade extra mensal")
    tem_reserva_emergencia: bool = Field(False, description="Tem reserva de emergência?")
    trabalha_clt: bool = Field(False, description="Trabalha com CLT?")

class ClienteCreate(BaseModel):
    nome: str = Field(..., min_length=3, description="Nome completo")
    email: Optional[str] = None
    whatsapp: str = Field(..., min_length=10, description="WhatsApp com DDD")
    banco: str = Field(..., min_length=3, description="Nome do banco")
    financiamento: FinanciamentoData
    recursos: RecursosData
    objetivo: str = Field("economia", description="Objetivo: economia ou quitar_rapido")

class OtimizacaoRequest(BaseModel):
    financiamento: FinanciamentoData
    recursos: RecursosData
    objetivo: str = "economia"

# ============================================
# STORAGE & CACHE
# ============================================

class MemoryStorage:
    def __init__(self):
        self.clientes: Dict[str, Dict] = {}
        self.analises: Dict[str, Dict] = {}
    
    def criar_cliente(self, dados: ClienteCreate) -> str:
        cliente_id = hashlib.md5(
            f"{dados.nome}{dados.whatsapp}{datetime.now()}".encode()
        ).hexdigest()[:12]
        
        self.clientes[cliente_id] = {
            'id': cliente_id,
            'nome': dados.nome,
            'email': dados.email,
            'whatsapp': dados.whatsapp,
            'banco': dados.banco,
            'financiamento': dados.financiamento.dict(),
            'recursos': dados.recursos.dict(),
            'objetivo': dados.objetivo,
            'criado_em': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Cliente criado: {cliente_id} - {dados.nome}")
        return cliente_id
    
    def obter_cliente(self, cliente_id: str) -> Optional[Dict]:
        return self.clientes.get(cliente_id)
    
    def listar_clientes(self) -> List[Dict]:
        return list(self.clientes.values())
    
    def atualizar_cliente(self, cliente_id: str, dados: Dict) -> bool:
        if cliente_id in self.clientes:
            self.clientes[cliente_id].update(dados)
            logger.info(f"✅ Cliente atualizado: {cliente_id}")
            return True
        return False
    
    def deletar_cliente(self, cliente_id: str) -> bool:
        if cliente_id in self.clientes:
            nome = self.clientes[cliente_id].get('nome', 'desconhecido')
            del self.clientes[cliente_id]
            logger.info(f"🗑️ Cliente deletado: {cliente_id} - {nome}")
            return True
        return False
    
    def salvar_analise(self, cliente_id: str, analise: Dict) -> str:
        analise_id = hashlib.md5(
            f"{cliente_id}{datetime.now()}".encode()
        ).hexdigest()[:12]
        
        self.analises[analise_id] = {
            'id': analise_id,
            'cliente_id': cliente_id,
            'analise': analise,
            'criada_em': datetime.now().isoformat()
        }
        
        logger.info(f"📊 Análise salva: {analise_id} para cliente {cliente_id}")
        return analise_id

class SimpleCache:
    def __init__(self):
        self.cache: Dict[str, tuple] = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, expiration = self.cache[key]
            if datetime.now() < expiration:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        expiration = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expiration)
    
    def delete(self, key: str):
        if key in self.cache:
            del self.cache[key]

storage = MemoryStorage()
cache = SimpleCache()

# ============================================
# HELPERS COM VALIDAÇÕES
# ============================================

def decimal_to_float(obj):
    """Converte Decimal para float recursivamente"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return decimal_to_float(vars(obj))
    return obj

def validar_economia(economia: float, total_pago_original: float, saldo_devedor: float) -> float:
    """
    Valida que economia seja lógica
    
    IMPORTANTE: Economia PODE ser maior que saldo devedor!
    Exemplo: Saldo de R$ 100k pode gerar R$ 300k em juros.
             Economizar R$ 200k é perfeitamente possível.
    
    Regras:
    1. Economia não pode ser maior que total_pago_original (limite físico)
    2. Economia não pode ser negativa
    """
    economia_maxima = total_pago_original
    economia_validada = max(0, min(economia, economia_maxima))
    
    if economia != economia_validada:
        logger.warning(f"⚠️ Economia ajustada: {economia:.2f} → {economia_validada:.2f}")
        logger.warning(f"   Limite: total_pago_original = {total_pago_original:.2f}")
    
    return economia_validada

def validar_reducao_prazo(reducao: int, prazo_original: int) -> int:
    """
    Valida que redução de prazo seja lógica
    
    Regras:
    1. Redução não pode ser maior que prazo original
    2. Redução não pode ser negativa
    3. Deve sobrar pelo menos 1 mês
    """
    reducao_validada = max(0, min(reducao, prazo_original - 1))
    
    if reducao != reducao_validada:
        logger.warning(f"⚠️ Redução prazo ajustada: {reducao} → {reducao_validada} meses")
    
    return reducao_validada

def validar_roi(roi: float) -> float:
    """
    Valida ROI para evitar valores absurdos
    
    Regras:
    1. ROI não pode ser maior que 5000% ao ano (muito improvável)
    2. ROI não pode ser negativo
    """
    roi_anual = roi * 12 * 100  # Converter para % anual
    
    if roi_anual > 5000:
        logger.warning(f"⚠️ ROI absurdo detectado: {roi_anual:.1f}% ao ano. Limitando.")
        return 5000 / 12 / 100  # 5000% ao ano = limite
    
    return max(0, roi)

def gerar_justificativa(estrategia, original, saldo_devedor: float) -> Dict[str, str]:
    """Gera justificativa profissional validada"""
    economia = float(estrategia.economia)
    roi = float(estrategia.roi) if estrategia.roi else 0
    reducao_prazo = estrategia.reducao_prazo
    
    return {
        'titulo': 'Estratégia Otimizada Inteligente',
        'paragrafo1': f"Após analisar mais de 150 cenários matemáticos, identificamos a estratégia ideal que economiza R$ {economia:,.2f} ao longo do financiamento.",
        'paragrafo2': f"Com esta estratégia, você pagará R$ {float(estrategia.total_pago):,.2f} em vez de R$ {float(original['total_pago']):,.2f}, resultando em uma economia real de {(economia/float(original['total_pago'])*100):.1f}% do valor total.",
        'paragrafo3': f"A estratégia utiliza R$ {float(estrategia.fgts_usado):,.2f} de FGTS inicialmente e amortizações mensais de R$ {float(estrategia.amortizacao_mensal):,.2f}, reduzindo o prazo em {reducao_prazo} meses.",
        'paragrafo4': f"O ROI desta operação é de {roi*12*100:.1f}% ao ano, totalmente isento de Imposto de Renda, superando a maioria dos investimentos disponíveis no mercado." if roi > 0 else "Esta estratégia oferece economia garantida através da redução de juros pagos.",
        'insight': f"💡 Ao economizar R$ {economia:,.2f} e reduzir {reducao_prazo} meses de prazo, você estará livre da dívida muito mais rápido e com mais dinheiro no bolso!"
    }

def gerar_plano_acao(estrategia) -> List[Dict]:
    """Gera plano de ação passo a passo"""
    plano = []
    
    if estrategia.fgts_usado > 0:
        plano.append({
            'mes': 1,
            'titulo': '💰 Usar FGTS Inicial',
            'descricao': f"Solicite a utilização de R$ {float(estrategia.fgts_usado):,.2f} do seu FGTS para amortizar o saldo devedor. Procure seu banco com seus documentos e comprovante de FGTS.",
            'prazo': 'Mês 1',
            'prioridade': 'ALTA'
        })
    
    if estrategia.amortizacao_mensal > 0:
        plano.append({
            'mes': 2,
            'titulo': '📅 Configurar Amortização Mensal',
            'descricao': f"Configure amortizações extraordinárias mensais de R$ {float(estrategia.amortizacao_mensal):,.2f}. A maioria dos bancos permite configurar débito automático para isso.",
            'prazo': 'A partir do Mês 2',
            'prioridade': 'ALTA'
        })
    
    # Checkpoint no meio do caminho
    meio_caminho = estrategia.prazo_meses // 2
    plano.append({
        'mes': meio_caminho,
        'titulo': '📊 Checkpoint de Progresso',
        'descricao': f"Verifique seu progresso. Neste ponto, você já terá economizado aproximadamente R$ {float(estrategia.economia)/2:,.2f} em juros.",
        'prazo': f'Mês {meio_caminho}',
        'prioridade': 'MÉDIA'
    })
    
    # Quitação final
    plano.append({
        'mes': estrategia.prazo_meses,
        'titulo': '🏠 QUITAÇÃO TOTAL!',
        'descricao': f"Parabéns! Você quitou seu financiamento e economizou R$ {float(estrategia.economia):,.2f}! Celebre sua conquista e aproveite sua liberdade financeira!",
        'prazo': f"Mês {estrategia.prazo_meses} ({estrategia.prazo_meses/12:.1f} anos)",
        'prioridade': 'CONQUISTA'
    })
    
    return plano

# ============================================
# ROTAS
# ============================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "EcoFin API v2",
        "version": "2.0.0",
        "features": ["validacoes_anti_absurdo", "campos_seguro_taxa"],
        "docs": "/api/docs"
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "clientes_ativos": len(storage.clientes),
        "analises_cache": len(storage.analises)
    }

@app.post("/api/cliente", status_code=status.HTTP_201_CREATED)
async def criar_cliente(cliente: ClienteCreate):
    try:
        logger.info(f"📝 Criando cliente: {cliente.nome}")
        logger.info(f"   Saldo: R$ {cliente.financiamento.saldo_devedor:,.2f}")
        logger.info(f"   Taxa: {cliente.financiamento.taxa_nominal*100:.2f}% a.a.")
        logger.info(f"   Prazo: {cliente.financiamento.prazo_restante} meses")
        logger.info(f"   Seguro: R$ {cliente.financiamento.seguro_mensal:,.2f}")
        logger.info(f"   Taxa Admin: R$ {cliente.financiamento.taxa_admin_mensal:,.2f}")
        
        cliente_id = storage.criar_cliente(cliente)
        return {
            "sucesso": True,
            "cliente_id": cliente_id,
            "cliente": storage.obter_cliente(cliente_id)
        }
    except Exception as e:
        logger.error(f"❌ Erro ao criar cliente: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clientes")
async def listar_clientes():
    clientes = storage.listar_clientes()
    logger.info(f"📋 Listando {len(clientes)} clientes")
    return {
        "sucesso": True,
        "total": len(clientes),
        "clientes": clientes
    }

@app.get("/api/cliente/{cliente_id}")
async def obter_cliente(cliente_id: str):
    cliente = storage.obter_cliente(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"sucesso": True, "cliente": cliente}

@app.put("/api/cliente/{cliente_id}")
async def atualizar_cliente(cliente_id: str, dados: Dict):
    sucesso = storage.atualizar_cliente(cliente_id, dados)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    cache.delete(f"analise:{cliente_id}")
    return {"sucesso": True, "mensagem": "Cliente atualizado"}

@app.delete("/api/cliente/{cliente_id}")
async def deletar_cliente(cliente_id: str):
    sucesso = storage.deletar_cliente(cliente_id)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    cache.delete(f"analise:{cliente_id}")
    return {"sucesso": True, "mensagem": "Cliente deletado"}

@app.post("/api/otimizar")
async def otimizar(request: OtimizacaoRequest):
    try:
        logger.info(f"🎯 Iniciando otimização")
        logger.info(f"   Saldo: R$ {request.financiamento.saldo_devedor:,.2f}")
        logger.info(f"   Objetivo: {request.objetivo}")
        
        # Verificar cache
        cache_key = f"otimizar:{request.financiamento.saldo_devedor}:{request.objetivo}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"📦 Retornando do cache")
            return cached
        
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
        
        # VALIDAÇÕES ANTI-ABSURDO
        saldo_devedor = float(request.financiamento.saldo_devedor)
        economia_validada = validar_economia(
            float(estrategia.economia),
            float(otimizador.original['total_pago']),
            saldo_devedor
        )
        estrategia.economia = Decimal(str(economia_validada))
        
        reducao_validada = validar_reducao_prazo(
            estrategia.reducao_prazo,
            request.financiamento.prazo_restante
        )
        estrategia.reducao_prazo = reducao_validada
        
        roi_validado = validar_roi(float(estrategia.roi) if estrategia.roi else 0)
        estrategia.roi = Decimal(str(roi_validado))
        
        # Log final
        logger.info(f"✅ Otimização concluída:")
        logger.info(f"   Economia: R$ {float(estrategia.economia):,.2f}")
        logger.info(f"   Redução prazo: {estrategia.reducao_prazo} meses")
        logger.info(f"   Prazo final: {estrategia.prazo_meses} meses")
        
        # Converter para dict
        estrategia_dict = decimal_to_float({
            'fgts_usado': estrategia.fgts_usado,
            'amortizacao_mensal': estrategia.amortizacao_mensal,
            'total_pago': estrategia.total_pago,
            'total_juros': estrategia.total_juros,
            'prazo_meses': estrategia.prazo_meses,
            'economia': estrategia.economia,
            'reducao_prazo': estrategia.reducao_prazo,
            'viabilidade': estrategia.viabilidade,
            'roi': estrategia.roi,
            'score': estrategia.score,
            'simulacao_completa': estrategia.simulacao_completa
        })
        
        # Gerar justificativa e plano
        justificativa = gerar_justificativa(estrategia, otimizador.original, saldo_devedor)
        plano_acao = gerar_plano_acao(estrategia)
        
        response = {
            "sucesso": True,
            "estrategia": estrategia_dict,
            "justificativa": justificativa,
            "plano_acao": plano_acao,
            "cenario_original": decimal_to_float(otimizador.original)
        }
        
        # Cache 5 minutos
        cache.set(cache_key, response, ttl=300)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Erro na otimização: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/api/analise/{cliente_id}")
async def obter_analise(cliente_id: str):
    try:
        logger.info(f"📊 Gerando análise para cliente: {cliente_id}")
        
        # Verificar cache
        cache_key = f"analise:{cliente_id}"
        cached = cache.get(cache_key)
        if cached:
            logger.info(f"📦 Retornando análise do cache")
            return cached
        
        # Buscar cliente
        cliente = storage.obter_cliente(cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Extrair dados
        fin = cliente['financiamento']
        rec = cliente['recursos']
        
        logger.info(f"   Cliente: {cliente['nome']}")
        logger.info(f"   Saldo: R$ {fin['saldo_devedor']:,.2f}")
        logger.info(f"   Seguro: R$ {fin.get('seguro_mensal', 0):,.2f}")
        logger.info(f"   Taxa Admin: R$ {fin.get('taxa_admin_mensal', 0):,.2f}")
        
        # Criar configuração
        config = ConfiguracaoFinanciamento(
            saldo_devedor=Decimal(str(fin['saldo_devedor'])),
            taxa_anual=Decimal(str(fin['taxa_nominal'])),
            prazo_meses=fin['prazo_restante'],
            sistema=fin.get('sistema', 'PRICE'),
            tr_mensal=Decimal(str(fin.get('tr_mensal', 0.0015))),
            seguro_mensal=Decimal(str(fin.get('seguro_mensal', 0))),
            taxa_admin_mensal=Decimal(str(fin.get('taxa_admin_mensal', 0)))
        )
        
        # Criar recursos
        recursos = Recursos(
            valor_fgts=Decimal(str(rec['valor_fgts'])),
            capacidade_extra_mensal=Decimal(str(rec['capacidade_extra'])),
            tem_reserva_emergencia=rec.get('tem_reserva_emergencia', False),
            trabalha_clt=rec.get('trabalha_clt', False)
        )
        
        # Otimizar
        motor = MotorEcoFin(config)
        otimizador = Otimizador(motor, recursos)
        estrategia = otimizador.otimizar(cliente.get('objetivo', 'economia'))
        
        # VALIDAÇÕES ANTI-ABSURDO
        saldo_devedor = float(fin['saldo_devedor'])
        economia_validada = validar_economia(
            float(estrategia.economia),
            float(otimizador.original['total_pago']),
            saldo_devedor
        )
        estrategia.economia = Decimal(str(economia_validada))
        
        reducao_validada = validar_reducao_prazo(
            estrategia.reducao_prazo,
            fin['prazo_restante']
        )
        estrategia.reducao_prazo = reducao_validada
        
        roi_validado = validar_roi(float(estrategia.roi) if estrategia.roi else 0)
        estrategia.roi = Decimal(str(roi_validado))
        
        # Log final
        logger.info(f"✅ Análise concluída:")
        logger.info(f"   Economia validada: R$ {float(estrategia.economia):,.2f}")
        logger.info(f"   Redução validada: {estrategia.reducao_prazo} meses")
        logger.info(f"   Prazo final: {estrategia.prazo_meses} meses")
        
        # Gerar dados
        justificativa = gerar_justificativa(estrategia, otimizador.original, saldo_devedor)
        plano_acao = gerar_plano_acao(estrategia)
        
        response = {
            "sucesso": True,
            "cliente": cliente,
            "cenario_original": decimal_to_float(otimizador.original),
            "estrategia_otimizada": decimal_to_float({
                'fgts_usado': estrategia.fgts_usado,
                'amortizacao_mensal': estrategia.amortizacao_mensal,
                'total_pago': estrategia.total_pago,
                'total_juros': estrategia.total_juros,
                'prazo_meses': estrategia.prazo_meses,
                'economia': estrategia.economia,
                'reducao_prazo': estrategia.reducao_prazo,
                'viabilidade': estrategia.viabilidade,
                'roi': estrategia.roi,
                'simulacao_completa': estrategia.simulacao_completa
            }),
            "justificativa": justificativa,
            "plano_acao": plano_acao
        }
        
        # Salvar análise
        analise_id = storage.salvar_analise(cliente_id, response)
        response['analise_id'] = analise_id
        
        # Cache 5 minutos
        cache.set(cache_key, response, ttl=300)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar análise: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    print("="*80)
    print("🚀 INICIANDO API ECOFIN V2.1 - VALIDAÇÕES INTELIGENTES")
    print("="*80)
    print("\n✅ Novidades:")
    print("   • Campos seguro_mensal e taxa_admin_mensal")
    print("   • Validações inteligentes")
    print("   • Economia PODE ser > saldo (natural com juros altos!)")
    print("   • Economia <= total_pago_original")
    print("   • Redução prazo <= prazo_original")
    print("   • ROI limitado a 5000% a.a.")
    print("   • Logs detalhados")
    print("\n📍 Endpoints:")
    print("   GET  /api/health")
    print("   POST /api/cliente")
    print("   GET  /api/clientes")
    print("   POST /api/otimizar")
    print("   GET  /api/analise/{id}")
    print("\n📚 Docs: http://localhost:8000/api/docs")
    print("="*80 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
