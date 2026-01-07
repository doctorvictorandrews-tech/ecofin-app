# 📋 CHANGELOG - EcoFin

Todas as mudanças notáveis do projeto serão documentadas aqui.

---

## [3.0.0] - 2025-01-07 - VERSÃO DEFINITIVA ✅

### 🎉 Adicionado
- **Formulário Cliente Completo**
  - OCR automático com Tesseract.js
  - Guias passo a passo para 5 bancos
  - Opção upload ou manual
  - Validação de dados extraídos
  - 5 etapas guiadas
  - Identidade visual EcoFin

- **Painel Administrativo Completo**
  - Tabela mês a mês (até 600 meses)
  - 11 colunas de dados detalhados
  - Expansão por ano (colapsar/expandir)
  - Exportação Excel (XLSX)
  - Modo impressão otimizado
  - Senha de acesso (ecofin2025)

- **Motor de Cálculo Validado**
  - Baseado 100% na planilha EcoFin v3
  - Precisão Decimal (sem erros ponto flutuante)
  - Cálculo PRICE e SAC
  - Correção TR aplicada
  - Amortizações extraordinárias
  - Comparação com cenário original

- **API REST Completa**
  - POST /api/cliente (cadastrar)
  - GET /api/clientes (listar)
  - GET /api/cliente/{id} (buscar)
  - GET /health (health check)
  - CORS configurado
  - Fallback localStorage

### 🔧 Melhorado
- Performance do OCR (20-30s)
- Precisão da extração (80-95%)
- UX das etapas do formulário
- Layout responsivo
- Feedback visual de progresso

### 🛠️ Corrigido
- Cálculo de juros mensais
- Aplicação correta da TR
- Fórmulas PMT e NPER
- Saldo devedor final
- Percentual quitado

### 📦 Deploy
- Vercel (frontend)
- Railway (backend)
- Cloudflare (DNS ready)

---

## [2.0.0] - 2025-01-06

### Adicionado
- Sistema V2 com 1 estratégia otimizada
- Justificativas matemáticas
- Plano de ação detalhado
- Cronograma ano a ano
- Sistema de compartilhamento

### Removido
- Múltiplas estratégias (foco em UMA melhor)

---

## [1.0.0] - 2025-01-05

### Adicionado
- Sistema V1 inicial
- Questionário 30+ campos
- Painel com 6 estratégias
- Motor cálculo básico SAC/PRICE
- Backend Railway
- Frontend Vercel

---

## 🔮 Próximas Versões

### [3.1.0] - Planejado
- [ ] Integração Open Finance
- [ ] Comparador de taxas em tempo real
- [ ] Dashboard de acompanhamento
- [ ] Notificações WhatsApp

### [4.0.0] - Futuro
- [ ] App mobile (React Native)
- [ ] Simulador de portabilidade
- [ ] Calculadora investimentos
- [ ] Sistema de agendamento

---

## 📝 Convenções

- **[MAJOR.MINOR.PATCH]** - Semantic Versioning
- **Data:** AAAA-MM-DD
- **Categorias:**
  - 🎉 Adicionado: Novas funcionalidades
  - 🔧 Melhorado: Melhorias em funcionalidades existentes
  - 🛠️ Corrigido: Bugs corrigidos
  - 🗑️ Removido: Funcionalidades removidas
  - 📦 Deploy: Mudanças de infraestrutura
  - ⚠️ Deprecated: Funcionalidades obsoletas

---

**Mantido por:** Victor - EcoFin  
**Última atualização:** 07/01/2025
