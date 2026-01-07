# 🔑 EcoFin - Sistema Completo de Análise de Financiamento Imobiliário

**Menos juros. Mais patrimônio. Simples assim.**

---

## 📊 Sobre o Projeto

Sistema profissional para análise e otimização de financiamentos imobiliários, com:
- ✅ Cálculos baseados 100% na planilha EcoFin v3 validada
- ✅ Motor financeiro preciso (Decimal, sem erros de ponto flutuante)
- ✅ OCR automático de documentos bancários
- ✅ Painel administrativo completo
- ✅ Formulário cliente inteligente
- ✅ Exportação Excel
- ✅ API REST pronta para produção

---

## 🚀 Funcionalidades

### **Para Clientes:**
1. **Formulário Inteligente**
   - Upload automático de documentos (foto/PDF)
   - OCR com Tesseract.js (português)
   - Guias passo a passo para 5 bancos
   - Opção manual alternativa
   - 5 etapas guiadas

2. **Bancos Suportados:**
   - Caixa Econômica Federal
   - Itaú
   - Bradesco
   - Santander
   - Banco do Brasil

3. **Extração Automática:**
   - Saldo Devedor
   - Taxa de Juros
   - Prazo Restante
   - Valor da Parcela

### **Para Consultores:**
1. **Painel Administrativo**
   - Senha de acesso (ecofin2025)
   - Lista de todos os clientes
   - Tabela completa mês a mês (até 600 meses)
   - 11 colunas de dados
   - Expansível por ano
   - Exportação Excel (XLSX)
   - Modo impressão otimizado

2. **Dados Exibidos:**
   - Mês (sequencial)
   - Saldo Inicial
   - Juros do Mês
   - Amortização Base
   - Amortização Extra
   - Parcela Total
   - Saldo Final
   - % Quitado
   - Juros Acumulados
   - Amortização Acumulada
   - Economia vs Original

---

## 🛠️ Tecnologias

### **Frontend:**
- React 18 (CDN)
- Tesseract.js 4 (OCR)
- XLSX.js 0.18.5 (Export)
- CSS puro (sem frameworks)

### **Backend:**
- Python 3.12+
- FastAPI
- Decimal (precisão financeira)
- Openpyxl (Excel)

### **Deploy:**
- Frontend: Vercel
- Backend: Railway
- DNS: Cloudflare

---

## 📁 Estrutura do Projeto

```
ecofin-app/
├── public/
│   ├── index.html          # Formulário cliente
│   ├── painel.html         # Painel administrativo
│   ├── logo-branco.png
│   └── logo-preto.png
├── api/
│   ├── main.py             # API FastAPI
│   ├── motor_ecofin.py     # Motor de cálculo
│   └── otimizador.py       # Otimizador de estratégias
├── docs/
│   └── RESUMO_ANALISE.md   # Análise da planilha
├── package.json
├── requirements.txt
├── vercel.json
└── README.md
```

---

## 🔧 Instalação Local

### **1. Clone o repositório:**
```bash
git clone https://github.com/SEU-USUARIO/ecofin-app.git
cd ecofin-app
```

### **2. Backend (Python):**
```bash
cd api
pip install -r requirements.txt
python main.py
```
Acesse: `http://localhost:8000`

### **3. Frontend (HTML estático):**
```bash
cd public
python -m http.server 3000
```
Acesse: `http://localhost:3000`

---

## 🌐 Deploy

### **Vercel (Frontend):**
1. Conecte seu repositório no Vercel
2. Configure:
   - **Build Command:** `# deixar vazio`
   - **Output Directory:** `public`
   - **Install Command:** `# deixar vazio`
3. Deploy automático em cada commit

### **Railway (Backend):**
1. Conecte seu repositório no Railway
2. Configure:
   - **Root Directory:** `/`
   - **Start Command:** `cd api && uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Adicione variáveis de ambiente se necessário

---

## 🔑 Configurações Importantes

### **Senha do Painel:**
- Local padrão: `ecofin2025`
- Para alterar: edite `public/painel.html` linha 45

### **URL da API:**
- Produção: `https://ecofin-app-production.up.railway.app`
- Local: `http://localhost:8000`
- Edite em `public/index.html` e `public/painel.html`

### **Domínio Personalizado:**
- Configure no Cloudflare DNS
- Aponte CNAME para Vercel
- Aguarde propagação (até 48h)

---

## 📊 Motor de Cálculo

### **Fórmulas Implementadas:**

**1. Taxa Mensal:**
```python
taxa_mensal = ((1 + taxa_anual) ** (1/12)) - 1
```

**2. Juros:**
```python
juros = saldo_devedor × taxa_mensal
```

**3. Parcela (PRICE):**
```python
parcela_base = PMT(taxa, prazo, saldo)
parcela_total = parcela_base + taxa_admin + seguro
```

**4. Amortização:**
```python
amortizacao = parcela - juros - taxa_admin - seguro
```

**5. Correção TR:**
```python
correcao_tr = saldo_devedor × tr_mensal
```

**6. Saldo Final:**
```python
saldo_final = saldo_inicial - amortizacao_base - amortizacao_extra + correcao_tr
```

---

## 🎯 Fluxo de Uso

### **Cliente:**
```
1. Acessa formulário (app.meuecofin.com.br)
2. Preenche dados pessoais
3. Escolhe: Upload OU Manual
4. Se Upload:
   - Seleciona banco
   - Vê guia passo a passo
   - Faz upload de foto/PDF
   - Aguarda OCR (20-30s)
   - Confirma dados extraídos
5. Se Manual:
   - Preenche campos principais
6. Revisa resumo
7. Envia
8. Recebe confirmação
```

### **Consultor:**
```
1. Acessa painel (/painel)
2. Digite senha: ecofin2025
3. Vê lista de clientes
4. Clica em cliente
5. Aba "Visão Geral": resumo
6. Aba "Tabela Completa": 
   - Expande anos
   - Analisa dados
7. Exporta Excel
8. Apresenta ao cliente
9. Fecha contrato! 💰
```

---

## 📝 API Endpoints

### **POST /api/cliente**
Cadastra novo cliente.

**Body:**
```json
{
  "nome": "João Silva",
  "whatsapp": "(11) 99999-9999",
  "email": "joao@email.com",
  "saldoDevedor": 250000,
  "taxaNominal": 0.0975,
  "prazoRestante": 360,
  "valorFGTS": 25000,
  "capacidadeExtra": 500
}
```

**Response:**
```json
{
  "sucesso": true,
  "id": "abc123",
  "mensagem": "Cliente cadastrado com sucesso"
}
```

### **GET /api/clientes**
Lista todos os clientes.

**Response:**
```json
{
  "clientes": [
    {
      "id": "abc123",
      "nome": "João Silva",
      "data": "2025-01-07T10:30:00Z",
      "status": "pendente"
    }
  ]
}
```

### **GET /api/cliente/{id}**
Busca cliente específico.

**Response:**
```json
{
  "id": "abc123",
  "nome": "João Silva",
  "dados_completos": { ... }
}
```

---

## 🧪 Testes

### **Testar Motor:**
```bash
cd api
python motor_ecofin.py
```

### **Testar API:**
```bash
cd api
python test_api.py
```

### **Testar OCR (manual):**
1. Abra `public/index.html` no navegador
2. Faça upload de foto de contrato
3. Verifique dados extraídos

---

## 🐛 Troubleshooting

### **OCR não funciona:**
- Verifique conexão com CDN Tesseract.js
- Foto deve ser nítida e bem iluminada
- Use opção manual como fallback

### **API não conecta:**
- Verifique URL em `public/index.html`
- Teste endpoint: `https://ecofin-app-production.up.railway.app/health`
- Veja logs no Railway

### **Excel não exporta:**
- Verifique CDN do XLSX.js
- Teste em navegador moderno (Chrome/Edge)

### **Painel pede senha sempre:**
- sessionStorage pode estar desabilitado
- Teste em aba anônima
- Limpe cache do navegador

---

## 📈 Roadmap

- [ ] Integração com bancos (Open Finance)
- [ ] App mobile (React Native)
- [ ] Comparador de taxas em tempo real
- [ ] Simulador de portabilidade
- [ ] Dashboard de acompanhamento
- [ ] Alertas de melhores momentos para amortizar
- [ ] Calculadora de investimentos alternativos

---

## 📞 Contato

**Victor - EcoFin**
- WhatsApp: [seu número]
- Email: contato@meuecofin.com.br
- Site: app.meuecofin.com.br

---

## 📄 Licença

Proprietary - Todos os direitos reservados © 2025 EcoFin

---

## 🎉 Agradecimentos

- Clientes que confiaram no sistema
- Comunidade Python/JavaScript
- Tesseract.js (OCR open source)

---

**Desenvolvido com ❤️ para democratizar o acesso a consultoria financeira de qualidade.**
