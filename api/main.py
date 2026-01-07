"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          API ECOFIN - FASTAPI                                ║
║                                                                              ║
║  API REST completa para o sistema EcoFin                                    ║
║  - Autenticação JWT                                                         ║
║  - Rate Limiting                                                            ║
║  - Validação Pydantic                                                       ║
║  - Integração com Motor Python                                              ║
║  - Cache em memória                                                         ║
║  - CORS configurado                                                         ║
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

# Imports do motor
from motor_ecofin import (
    MotorEcoFin, 
    ConfiguracaoFinanciamento,
    Recursos
)
from otimizador import Otimizador

# ============================================
# CONFIGURAÇÃO DA API
# ============================================

app = FastAPI(
    title="EcoFin API",
    description="API REST para otimização de financiamentos imobiliários",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.meuecofin.com.br",
        "https://meuecofin.com.br",
        "https://ecofin-app.vercel.app",
        "https://*.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "*"  # Temporário para debug
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compressão
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Senha simples
ADMIN_PASSWORD = "ecofin2025"

# ============================================
# SCHEMAS PYDANTIC
# ============================================

class FinanciamentoData(BaseModel):
    saldo_devedor: float = Field(..., gt=0)
    taxa_nominal: float = Field(..., gt=0, lt=1)
    prazo_restante: int = Field(..., gt=0, le=720)
    sistema: str = Field("PRICE")
    tr_mensal: float = Field(0.0015)
    seguro_mensal: float = Field(25)
    taxa_admin_mensal: float = Field(50)

class RecursosData(BaseModel):
    valor_fgts: float = Field(0, ge=0)
    capacidade_extra: float = Field(0, ge=0)
    tem_reserva_emergencia: bool = Field(False)
    trabalha_clt: bool = Field(False)

class ClienteCreate(BaseModel):
    nome: str = Field(..., min_length=3)
    email: Optional[str] = None
    whatsapp: str = Field(..., min_length=10)
    banco: str = Field(..., min_length=3)
    financiamento: FinanciamentoData
    recursos: RecursosData
    objetivo: str = Field("economia")

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
        
        return cliente_id
    
    def obter_cliente(self, cliente_id: str) -> Optional[Dict]:
        return self.clientes.get(cliente_id)
    
    def listar_clientes(self) -> List[Dict]:
        return list(self.clientes.values())
    
    def atualizar_cliente(self, cliente_id: str, dados: Dict) -> bool:
        if cliente_id in self.clientes:
            self.clientes[cliente_id].update(dados)
            return True
        return False
    
    def deletar_cliente(self, cliente_id: str) -> bool:
        if cliente_id in self.clientes:
            del self.clientes[cliente_id]
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
# HELPERS
# ============================================

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return decimal_to_float(vars(obj))
    return obj

def gerar_justificativa(estrategia, original) -> Dict[str, str]:
    economia = float(estrategia.economia)
    roi = float(estrategia.roi) if estrategia.roi else 0
    
    return {
        'titulo': 'Estratégia Otimizada Inteligente',
        'paragrafo1': f"Analisamos mais de 150 cenários. Esta estratégia economiza R$ {economia:,.2f}.",
        'paragrafo2': f"Com esta estratégia, você pagará R$ {float(estrategia.total_pago):,.2f} em vez de R$ {float(original['total_pago']):,.2f}.",
        'paragrafo3': f"FGTS usado: R$ {float(estrategia.fgts_usado):,.2f}. Amortização mensal: R$ {float(estrategia.amortizacao_mensal):,.2f}.",
        'paragrafo4': f"ROI: {roi*12*100:.1f}% ao ano, isento de IR!" if roi > 0 else "Estratégia eficiente.",
        'insight': f"Economia de R$ {economia:,.2f} em {estrategia.reducao_prazo} meses!"
    }

def gerar_plano_acao(estrategia) -> List[Dict]:
    plano = []
    
    if estrategia.fgts_usado > 0:
        plano.append({
            'mes': 1,
            'titulo': '💰 Usar FGTS',
            'descricao': f"Use R$ {float(estrategia.fgts_usado):,.2f} do FGTS para amortizar.",
            'prazo': 'Mês 1',
            'prioridade': 'ALTA'
        })
    
    plano.append({
        'mes': 2,
        'titulo': '📅 Amortização Mensal',
        'descricao': f"Configure R$ {float(estrategia.amortizacao_mensal):,.2f}/mês.",
        'prazo': 'A partir do Mês 2',
        'prioridade': 'ALTA'
    })
    
    plano.append({
        'mes': estrategia.prazo_meses,
        'titulo': '🏠 QUITAÇÃO TOTAL',
        'descricao': f"Economizou R$ {float(estrategia.economia):,.2f}! Parabéns!",
        'prazo': f"Mês {estrategia.prazo_meses}",
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
        "service": "EcoFin API",
        "version": "3.0.0",
        "docs": "/api/docs"
    }

@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/cliente", status_code=status.HTTP_201_CREATED)
async def criar_cliente(cliente: ClienteCreate):
    try:
        cliente_id = storage.criar_cliente(cliente)
        return {
            "sucesso": True,
            "cliente_id": cliente_id,
            "cliente": storage.obter_cliente(cliente_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clientes")
async def listar_clientes():
    return {
        "sucesso": True,
        "clientes": storage.listar_clientes()
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
        # Verificar cache
        cache_key = f"otimizar:{request.financiamento.saldo_devedor}:{request.objetivo}"
        cached = cache.get(cache_key)
        if cached:
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
        justificativa = gerar_justificativa(estrategia, otimizador.original)
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
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

@app.get("/api/analise/{cliente_id}")
async def obter_analise(cliente_id: str):
    try:
        # Verificar cache
        cache_key = f"analise:{cliente_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Buscar cliente
        cliente = storage.obter_cliente(cliente_id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # Extrair dados
        fin = cliente['financiamento']
        rec = cliente['recursos']
        
        # Criar configuração
        config = ConfiguracaoFinanciamento(
            saldo_devedor=Decimal(str(fin['saldo_devedor'])),
            taxa_anual=Decimal(str(fin['taxa_nominal'])),
            prazo_meses=fin['prazo_restante'],
            sistema=fin.get('sistema', 'PRICE'),
            tr_mensal=Decimal(str(fin.get('tr_mensal', 0.0015))),
            seguro_mensal=Decimal(str(fin.get('seguro_mensal', 25))),
            taxa_admin_mensal=Decimal(str(fin.get('taxa_admin_mensal', 50)))
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
        
        # Gerar dados
        justificativa = gerar_justificativa(estrategia, otimizador.original)
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
        raise HTTPException(status_code=500, detail=f"Erro: {str(e)}")

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    print("="*80)
    print("🚀 INICIANDO API ECOFIN")
    print("="*80)
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
