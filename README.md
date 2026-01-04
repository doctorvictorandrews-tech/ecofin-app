# EcoFin App

Sistema automatizado de otimização de financiamentos imobiliários.

## Estrutura

- `/` - Landing page do app
- `/cliente` - Questionário para clientes (público)
- `/painel` - Dashboard administrativo (protegido)

## Como fazer upload no GitHub

1. Crie um repositório chamado `ecofin-app`
2. Faça upload de TODOS os arquivos desta pasta
3. Conecte com Vercel
4. Configure o domínio `app.meuecofin.com.br`

## Arquivos nesta pasta

```
ECOFIN_APP_COMPLETO/
├── public/
│   ├── index.html      → Landing page
│   ├── cliente.html    → Questionário (cliente preenche)
│   └── painel.html     → Dashboard (você acessa)
├── vercel.json         → Configuração Vercel
└── README.md           → Este arquivo
```

## Depois do deploy

URLs disponíveis:
- `app.meuecofin.com.br` → Landing
- `app.meuecofin.com.br/cliente` → Questionário
- `app.meuecofin.com.br/painel` → Seu painel

## Próximos passos

1. ✅ Upload no GitHub
2. ✅ Deploy na Vercel
3. ✅ Configurar DNS (CNAME: app → cname.vercel-dns.com)
4. ✅ Aguardar propagação (1-4h)
5. ✅ Testar tudo!
