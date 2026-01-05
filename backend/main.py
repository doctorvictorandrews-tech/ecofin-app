"""
EcoFin Backend - API REST
Versão simplificada e pronta para Railway
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from datetime import datetime
import json

app = FastAPI(title="EcoFin API", version="2.0")

# CORS - Permite frontend acessar backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique seu domínio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# MODELS (Estrutura dos Dados)
# ==========================================

class ClienteData(BaseModel):
    """Dados do cliente vindos do formulário"""
    nome: str
    whatsapp: str
    email: Optional[str] = ""
    objetivo: str
    trabalhaCLT: bool
    temFGTS: bool
    valorFGTS: float = 0
    capacidadeExtra: float = 0
    banco: str
    sistema: str  # SAC ou PRICE
    saldoDevedor: float
    taxaAnual: float
    prazoRestante: int

class ClienteResponse(BaseModel):
    """Resposta com ID do cliente"""
    id: str
    mensagem: str
    sucesso: bool

# ==========================================
# BANCO DE DADOS SIMPLES (JSON)
# ==========================================

def carregar_clientes():
    """Carrega clientes do arquivo JSON"""
    try:
        if os.path.exists('clientes.json'):
            with open('clientes.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except:
        return []

def salvar_clientes(clientes):
    """Salva clientes no arquivo JSON"""
    try:
        with open('clientes.json', 'w', encoding='utf-8') as f:
            json.dump(clientes, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# ==========================================
# ENDPOINTS DA API
# ==========================================

@app.get("/")
def root():
    """Endpoint raiz - Informações da API"""
    return {
        "app": "EcoFin API",
        "versao": "2.0",
        "status": "online",
        "endpoints": {
            "documentacao": "/docs",
            "health": "/health",
            "enviar_cliente": "POST /api/cliente",
            "listar_clientes": "GET /api/clientes",
            "buscar_cliente": "GET /api/cliente/{id}",
            "taxa_referencial": "GET /api/taxa-referencial"
        }
    }

@app.get("/health")
def health_check():
    """Verifica se API está funcionando"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/cliente", response_model=ClienteResponse)
def criar_cliente(cliente: ClienteData):
    """
    Recebe dados do cliente do formulário
    
    O frontend envia os dados aqui quando o cliente clica "Enviar"
    """
    try:
        # Carregar clientes existentes
        clientes = carregar_clientes()
        
        # Criar novo cliente
        cliente_id = f"CLI{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        novo_cliente = {
            "id": cliente_id,
            "data_cadastro": datetime.now().isoformat(),
            "status": "pendente",
            **cliente.dict()
        }
        
        # Adicionar à lista
        clientes.append(novo_cliente)
        
        # Salvar
        if salvar_clientes(clientes):
            return ClienteResponse(
                id=cliente_id,
                mensagem=f"Cliente {cliente.nome} cadastrado com sucesso!",
                sucesso=True
            )
        else:
            raise HTTPException(status_code=500, detail="Erro ao salvar cliente")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clientes")
def listar_clientes():
    """
    Lista todos os clientes cadastrados
    
    Seu painel chama este endpoint para mostrar a lista
    """
    try:
        clientes = carregar_clientes()
        
        # Ordenar por data (mais recente primeiro)
        clientes.sort(key=lambda x: x.get('data_cadastro', ''), reverse=True)
        
        return {
            "sucesso": True,
            "total": len(clientes),
            "clientes": clientes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cliente/{cliente_id}")
def buscar_cliente(cliente_id: str):
    """
    Busca um cliente específico pelo ID
    """
    try:
        clientes = carregar_clientes()
        
        # Procurar cliente
        cliente = next((c for c in clientes if c['id'] == cliente_id), None)
        
        if cliente:
            return {
                "sucesso": True,
                "cliente": cliente
            }
        else:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/taxa-referencial")
def taxa_referencial():
    """
    Retorna Taxa Referencial do Banco Central
    
    Em produção, isso buscaria da API real do BC
    Por enquanto, retorna valor simulado
    """
    return {
        "sucesso": True,
        "taxa_atual": 0.0015,
        "taxa_atual_percent": 0.15,
        "data_atualizacao": datetime.now().isoformat(),
        "fonte": "Banco Central do Brasil (simulado)"
    }

@app.delete("/api/cliente/{cliente_id}")
def deletar_cliente(cliente_id: str):
    """
    Deleta um cliente
    """
    try:
        clientes = carregar_clientes()
        
        # Filtrar (remover o cliente)
        clientes_filtrados = [c for c in clientes if c['id'] != cliente_id]
        
        if len(clientes_filtrados) < len(clientes):
            salvar_clientes(clientes_filtrados)
            return {
                "sucesso": True,
                "mensagem": f"Cliente {cliente_id} deletado"
            }
        else:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# EXECUTAR SERVIDOR
# ==========================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
