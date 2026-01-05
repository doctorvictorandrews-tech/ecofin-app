# EcoFin Backend API

Backend Python para o sistema EcoFin.

## Arquivos

- `ecofin_backend_railway.py` - API principal
- `requirements.txt` - Dependências Python
- `Procfile` - Comando para Railway
- `railway.json` - Configuração Railway

## Como funciona

### Endpoints disponíveis:

**GET /**
- Informações da API

**GET /health**
- Verifica se está funcionando

**POST /api/cliente**
- Recebe dados do formulário do cliente
- Salva no banco de dados

**GET /api/clientes**
- Lista todos os clientes cadastrados
- Usado pelo painel administrativo

**GET /api/cliente/{id}**
- Busca um cliente específico

**GET /api/taxa-referencial**
- Retorna Taxa Referencial do Banco Central

**DELETE /api/cliente/{id}**
- Deleta um cliente

## Deploy no Railway

1. Crie conta em railway.app
2. New Project → Deploy from GitHub repo
3. Selecione o repositório
4. Railway detecta Python automaticamente
5. Adicione variável: PORT=8000
6. Deploy!

## Testar localmente

```bash
pip install -r requirements.txt
python ecofin_backend_railway.py
```

Acesse: http://localhost:8000/docs

## URL em produção

Após deploy, você terá algo como:
https://ecofin-backend-production.up.railway.app

Use essa URL para conectar o frontend!
