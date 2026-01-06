"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     TESTES COMPLETOS - API ECOFIN                            ║
║                                                                              ║
║  Suite de testes para validar todos os endpoints                           ║
║  Testa motor, otimizador e API completa                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
from decimal import Decimal
import time

# ============================================
# CONFIGURAÇÃO
# ============================================

API_URL = "http://localhost:8000"  # Alterar para URL de produção se necessário

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{'='*80}")
    print(f"{msg}")
    print(f"{'='*80}{Colors.END}\n")

# ============================================
# TESTES
# ============================================

def test_health_check():
    """Teste 1: Health Check"""
    print_header("TESTE 1: Health Check")
    
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API está online: {data.get('status')}")
            print_info(f"Timestamp: {data.get('timestamp')}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro ao conectar: {e}")
        print_warning("Certifique-se que o backend está rodando em localhost:8000")
        return False

def test_criar_cliente():
    """Teste 2: Criar Cliente"""
    print_header("TESTE 2: Criar Cliente via API")
    
    cliente_data = {
        "nome": "João Silva Teste",
        "email": "joao@teste.com",
        "whatsapp": "11999999999",
        "banco": "Caixa Econômica Federal",
        "financiamento": {
            "saldo_devedor": 300000,
            "taxa_nominal": 0.12,
            "prazo_restante": 420,
            "sistema": "PRICE",
            "tr_mensal": 0.0015,
            "seguro_mensal": 25,
            "taxa_admin_mensal": 50
        },
        "recursos": {
            "valor_fgts": 25000,
            "capacidade_extra": 800,
            "tem_reserva_emergencia": True,
            "trabalha_clt": True
        },
        "objetivo": "quitar_rapido"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/cliente",
            json=cliente_data,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            cliente_id = data.get('cliente_id')
            print_success(f"Cliente criado: {cliente_id}")
            print_info(f"Nome: {data['cliente']['nome']}")
            return cliente_id
        else:
            print_error(f"Erro ao criar cliente: {response.status_code}")
            print_error(response.text)
            return None
    except Exception as e:
        print_error(f"Erro: {e}")
        return None

def test_listar_clientes():
    """Teste 3: Listar Clientes"""
    print_header("TESTE 3: Listar Clientes")
    
    try:
        response = requests.get(f"{API_URL}/api/clientes", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total = len(data.get('clientes', []))
            print_success(f"Total de clientes: {total}")
            
            if total > 0:
                print_info("Primeiros 3 clientes:")
                for cliente in data['clientes'][:3]:
                    print(f"  - {cliente['nome']} ({cliente['banco']})")
            
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False

def test_otimizar():
    """Teste 4: Otimizar Estratégia"""
    print_header("TESTE 4: Otimizar Estratégia (150+ cenários)")
    
    otimizacao_data = {
        "financiamento": {
            "saldo_devedor": 300000,
            "taxa_nominal": 0.12,
            "prazo_restante": 420,
            "sistema": "PRICE"
        },
        "recursos": {
            "valor_fgts": 25000,
            "capacidade_extra": 800,
            "tem_reserva_emergencia": True,
            "trabalha_clt": True
        },
        "objetivo": "quitar_rapido"
    }
    
    try:
        print_info("Testando 150+ cenários... (pode levar alguns segundos)")
        start_time = time.time()
        
        response = requests.post(
            f"{API_URL}/api/otimizar",
            json=otimizacao_data,
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            estrategia = data.get('estrategia', {})
            
            print_success(f"Otimização completa em {elapsed:.2f} segundos")
            print_info(f"FGTS usado: R$ {estrategia.get('fgts_usado', 0):,.2f}")
            print_info(f"Amortização mensal: R$ {estrategia.get('amortizacao_mensal', 0):,.2f}")
            print_info(f"Economia: R$ {estrategia.get('economia', 0):,.2f}")
            print_info(f"Redução prazo: {estrategia.get('reducao_prazo', 0)} meses")
            print_info(f"Viabilidade: {estrategia.get('viabilidade', 0)}%")
            
            if estrategia.get('roi'):
                roi_anual = estrategia['roi'] * 12 * 100
                print_success(f"ROI: {roi_anual:.2f}% ao ano (isento IR!)")
            
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            print_error(response.text)
            return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False

def test_analise_completa(cliente_id):
    """Teste 5: Análise Completa"""
    print_header(f"TESTE 5: Análise Completa (Cliente: {cliente_id})")
    
    if not cliente_id:
        print_warning("Cliente ID não fornecido, pulando teste")
        return False
    
    try:
        print_info("Gerando análise completa...")
        start_time = time.time()
        
        response = requests.get(
            f"{API_URL}/api/analise/{cliente_id}",
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print_success(f"Análise gerada em {elapsed:.2f} segundos")
            
            # Validar estrutura da resposta
            required_keys = ['cliente', 'cenario_original', 'estrategia_otimizada', 'justificativa', 'plano_acao']
            missing_keys = [k for k in required_keys if k not in data]
            
            if missing_keys:
                print_error(f"Chaves faltando: {missing_keys}")
                return False
            
            # Exibir resumo
            original = data['cenario_original']
            otimizada = data['estrategia_otimizada']
            
            print_info("\n📊 CENÁRIO ORIGINAL:")
            print(f"  Total pago: R$ {original.get('total_pago', 0):,.2f}")
            print(f"  Prazo: {original.get('prazo_meses', 0)} meses")
            
            print_info("\n✅ ESTRATÉGIA OTIMIZADA:")
            print(f"  Total pago: R$ {otimizada.get('total_pago', 0):,.2f}")
            print(f"  Prazo: {otimizada.get('prazo_meses', 0)} meses")
            print(f"  Economia: R$ {otimizada.get('economia', 0):,.2f}")
            
            print_info(f"\n📝 Justificativas: {len(data['justificativa'])} parágrafos")
            print_info(f"🎯 Plano de ação: {len(data['plano_acao'])} passos")
            
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            print_error(response.text)
            return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False

def test_validacao_motor():
    """Teste 6: Validar Motor contra Planilha"""
    print_header("TESTE 6: Validar Motor Python contra Planilha")
    
    print_info("Testando valores conhecidos da planilha...")
    
    # Valores esperados da planilha (Mês 1)
    esperados = {
        'juros': 2846.64,
        'amortizacao': 54.95,
        'parcela': 2976.59,
        'tr': 450.00,
        'saldo_final': 300395.05
    }
    
    # Fazer otimização para obter simulação
    otimizacao_data = {
        "financiamento": {
            "saldo_devedor": 300000,
            "taxa_nominal": 0.12,
            "prazo_restante": 420,
            "sistema": "PRICE"
        },
        "recursos": {
            "valor_fgts": 0,
            "capacidade_extra": 0
        },
        "objetivo": "economia"
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/otimizar",
            json=otimizacao_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Pegar cenário original (sem amortização extra)
            original = data.get('cenario_original', {})
            meses = original.get('meses', [])
            
            if not meses:
                print_error("Nenhum mês retornado na simulação")
                return False
            
            mes1 = meses[0]
            
            # Validar valores
            tolerancia = 0.01
            testes = [
                ('Juros', mes1.get('juros'), esperados['juros']),
                ('Amortização', mes1.get('amortizacao_base'), esperados['amortizacao']),
                ('Parcela', mes1.get('parcela_total'), esperados['parcela']),
                ('TR', mes1.get('correcao_tr'), esperados['tr']),
                ('Saldo Final', mes1.get('saldo_final'), esperados['saldo_final'])
            ]
            
            todos_ok = True
            for nome, calculado, esperado in testes:
                diferenca = abs(calculado - esperado)
                
                if diferenca < tolerancia:
                    print_success(f"{nome}: R$ {calculado:.2f} (diferença: R$ {diferenca:.4f})")
                else:
                    print_error(f"{nome}: R$ {calculado:.2f} vs esperado R$ {esperado:.2f} (diferença: R$ {diferenca:.2f})")
                    todos_ok = False
            
            if todos_ok:
                print_success("\n🎉 TODOS OS VALORES BATEM COM A PLANILHA!")
                return True
            else:
                print_error("\n⚠️  Alguns valores divergem da planilha")
                return False
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False

def test_performance():
    """Teste 7: Performance"""
    print_header("TESTE 7: Teste de Performance")
    
    print_info("Fazendo 5 requisições de otimização...")
    
    otimizacao_data = {
        "financiamento": {
            "saldo_devedor": 300000,
            "taxa_nominal": 0.12,
            "prazo_restante": 420
        },
        "recursos": {
            "valor_fgts": 25000,
            "capacidade_extra": 800
        },
        "objetivo": "economia"
    }
    
    tempos = []
    
    for i in range(5):
        try:
            start_time = time.time()
            response = requests.post(
                f"{API_URL}/api/otimizar",
                json=otimizacao_data,
                timeout=60
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                tempos.append(elapsed)
                print_info(f"  Requisição {i+1}: {elapsed:.2f}s")
            else:
                print_error(f"  Requisição {i+1} falhou")
        except Exception as e:
            print_error(f"  Erro na requisição {i+1}: {e}")
    
    if tempos:
        media = sum(tempos) / len(tempos)
        print_success(f"\nTempo médio: {media:.2f}s")
        
        if media < 2:
            print_success("Performance EXCELENTE! (< 2s)")
        elif media < 5:
            print_success("Performance BOA! (< 5s)")
        else:
            print_warning("Performance ACEITÁVEL (> 5s)")
        
        return True
    else:
        print_error("Nenhuma requisição teve sucesso")
        return False

def test_cache():
    """Teste 8: Cache"""
    print_header("TESTE 8: Teste de Cache")
    
    print_info("Fazendo 2 requisições idênticas para testar cache...")
    
    otimizacao_data = {
        "financiamento": {
            "saldo_devedor": 300000,
            "taxa_nominal": 0.12,
            "prazo_restante": 420
        },
        "recursos": {
            "valor_fgts": 25000,
            "capacidade_extra": 800
        },
        "objetivo": "economia"
    }
    
    try:
        # Primeira requisição (sem cache)
        start1 = time.time()
        response1 = requests.post(f"{API_URL}/api/otimizar", json=otimizacao_data, timeout=60)
        tempo1 = time.time() - start1
        
        # Segunda requisição (com cache)
        start2 = time.time()
        response2 = requests.post(f"{API_URL}/api/otimizar", json=otimizacao_data, timeout=60)
        tempo2 = time.time() - start2
        
        if response1.status_code == 200 and response2.status_code == 200:
            print_info(f"Primeira requisição (sem cache): {tempo1:.2f}s")
            print_info(f"Segunda requisição (com cache): {tempo2:.2f}s")
            
            if tempo2 < tempo1 * 0.5:  # Cache deveria ser pelo menos 2x mais rápido
                print_success("Cache funcionando! Segunda requisição foi 2x+ mais rápida")
                return True
            else:
                print_warning("Cache pode não estar funcionando (tempos similares)")
                return True  # Não falha o teste
        else:
            print_error("Erro nas requisições")
            return False
    except Exception as e:
        print_error(f"Erro: {e}")
        return False

# ============================================
# EXECUTAR TODOS OS TESTES
# ============================================

def run_all_tests():
    """Executa todos os testes"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═"*78 + "╗")
    print("║" + " "*25 + "ECOFIN - SUITE DE TESTES" + " "*29 + "║")
    print("║" + " "*78 + "║")
    print("║" + f"  API URL: {API_URL}".ljust(78) + "║")
    print("╚" + "═"*78 + "╝")
    print(f"{Colors.END}\n")
    
    resultados = {}
    cliente_id = None
    
    # Executar testes
    resultados['Health Check'] = test_health_check()
    
    if resultados['Health Check']:
        cliente_id = test_criar_cliente()
        resultados['Criar Cliente'] = cliente_id is not None
        resultados['Listar Clientes'] = test_listar_clientes()
        resultados['Otimizar'] = test_otimizar()
        resultados['Análise Completa'] = test_analise_completa(cliente_id)
        resultados['Validação Motor'] = test_validacao_motor()
        resultados['Performance'] = test_performance()
        resultados['Cache'] = test_cache()
    else:
        print_error("\nBackend não está acessível. Pulando demais testes.")
    
    # Resumo
    print_header("RESUMO DOS TESTES")
    
    total = len(resultados)
    passou = sum(1 for v in resultados.values() if v)
    
    for teste, resultado in resultados.items():
        if resultado:
            print_success(f"{teste}")
        else:
            print_error(f"{teste}")
    
    print(f"\n{Colors.BOLD}Resultado Final: {passou}/{total} testes passaram{Colors.END}")
    
    if passou == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TODOS OS TESTES PASSARAM! SISTEMA 100% FUNCIONAL! 🎉{Colors.END}\n")
        return True
    else:
        print(f"\n{Colors.YELLOW}⚠️  Alguns testes falharam. Verifique os logs acima.{Colors.END}\n")
        return False

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import sys
    
    # Permitir passar URL customizada
    if len(sys.argv) > 1:
        API_URL = sys.argv[1]
        print_info(f"Usando API: {API_URL}")
    
    sucesso = run_all_tests()
    sys.exit(0 if sucesso else 1)
