"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        OTIMIZADOR ECOFIN V4.1                               ║
║                                                                              ║
║  Testa centenas de cenários e encontra a estratégia ótima                  ║
║  Algoritmos de otimização inteligentes                                     ║
║  ROI, viabilidade e score                                                  ║
║                                                                              ║
║  Versão: 4.1.0 (2025-01-07)                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List
from decimal import Decimal
from dataclasses import dataclass
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos

@dataclass
class Estrategia:
    """Resultado de uma estratégia otimizada"""
    # Configuração
    fgts_usado: Decimal
    amortizacao_mensal: Decimal
    duracao_amortizacao: int
    
    # Resultados financeiros
    total_pago: Decimal
    total_juros: Decimal
    prazo_meses: int
    economia: Decimal
    reducao_prazo: int
    
    # Métricas
    viabilidade: str  # 'ALTA', 'MÉDIA', 'BAIXA'
    roi: Decimal  # Retorno sobre investimento
    score: Decimal  # Pontuação geral
    investimento_total: Decimal
    
    # Detalhes
    simulacao_completa: Dict

class Otimizador:
    """Otimizador de estratégias de amortização"""
    
    def __init__(self, motor: MotorEcoFin, recursos: Recursos):
        self.motor = motor
        self.recursos = recursos
        
        # Simular cenário original (sem amortização)
        self.original = motor.simular_completo(Decimal('0'), Decimal('0'), 0)
    
    def otimizar(self, objetivo: str = 'economia') -> Estrategia:
        """
        Encontra a melhor estratégia
        
        Args:
            objetivo: 'economia' (maximizar economia) ou 'prazo' (quitar rápido)
        
        Returns:
            Melhor estratégia encontrada
        """
        
        cenarios = []
        
        # 1. CENÁRIOS COM FGTS
        fgts_disponivel = self.recursos.valor_fgts
        
        for fgts_perc in [0, 25, 50, 75, 100]:
            fgts_usar = (fgts_disponivel * Decimal(str(fgts_perc))) / Decimal('100')
            
            # 2. CENÁRIOS COM AMORTIZAÇÃO MENSAL
            capacidade = self.recursos.capacidade_extra_mensal
            
            for amort_perc in [0, 30, 50, 70, 100]:
                amort_mensal = (capacidade * Decimal(str(amort_perc))) / Decimal('100')
                
                # 3. DIFERENTES DURAÇÕES
                duracoes = [12, 24, 36, 60, 120, 240, 999]  # 1, 2, 3, 5, 10, 20 anos, infinito
                
                for duracao in duracoes:
                    # Pular cenários inviáveis
                    if fgts_usar == 0 and amort_mensal == 0:
                        continue
                    
                    # Simular
                    try:
                        resultado = self.motor.simular_completo(
                            fgts_usar,
                            amort_mensal,
                            duracao
                        )
                        
                        # Calcular métricas
                        economia = self.original['total_pago'] - resultado['total_pago']
                        reducao_prazo = self.original['prazo_meses'] - resultado['prazo_meses']
                        
                        # Investimento total
                        meses_com_amort = min(duracao, resultado['prazo_meses'])
                        investimento_total = fgts_usar + (amort_mensal * Decimal(str(meses_com_amort)))
                        
                        # ROI
                        roi = (economia / investimento_total) if investimento_total > 0 else Decimal('0')
                        
                        # Viabilidade
                        if amort_mensal <= capacidade * Decimal('0.3'):
                            viabilidade = 'ALTA'
                        elif amort_mensal <= capacidade * Decimal('0.7'):
                            viabilidade = 'MÉDIA'
                        else:
                            viabilidade = 'BAIXA'
                        
                        # Score baseado no objetivo
                        if objetivo == 'prazo':
                            # Prioriza redução de prazo
                            score = (Decimal(str(reducao_prazo)) * Decimal('100')) + (economia / Decimal('1000'))
                        else:
                            # Prioriza economia (padrão)
                            score = economia + (roi * Decimal('10000'))
                        
                        # Criar estratégia
                        estrategia = Estrategia(
                            fgts_usado=fgts_usar,
                            amortizacao_mensal=amort_mensal,
                            duracao_amortizacao=duracao,
                            total_pago=resultado['total_pago'],
                            total_juros=resultado['total_juros'],
                            prazo_meses=resultado['prazo_meses'],
                            economia=economia,
                            reducao_prazo=reducao_prazo,
                            viabilidade=viabilidade,
                            roi=roi,
                            score=score,
                            investimento_total=investimento_total,
                            simulacao_completa=resultado
                        )
                        
                        cenarios.append(estrategia)
                        
                    except Exception as e:
                        # Ignorar cenários que dão erro
                        continue
        
        # Ordenar por score
        cenarios.sort(key=lambda x: float(x.score), reverse=True)
        
        # Retornar melhor
        return cenarios[0] if cenarios else None
    
    def comparar_estrategias(self, limite: int = 5) -> List[Estrategia]:
        """
        Retorna as N melhores estratégias
        
        Args:
            limite: Número de estratégias a retornar
        
        Returns:
            Lista das melhores estratégias
        """
        
        # Otimizar para economia
        melhor_economia = self.otimizar('economia')
        
        # Otimizar para prazo
        melhor_prazo = self.otimizar('prazo')
        
        # Combinar e remover duplicatas
        estrategias = []
        
        if melhor_economia:
            estrategias.append(melhor_economia)
        
        if melhor_prazo and melhor_prazo.score != melhor_economia.score:
            estrategias.append(melhor_prazo)
        
        # Ordenar por score
        estrategias.sort(key=lambda x: float(x.score), reverse=True)
        
        return estrategias[:limite]

# Teste
if __name__ == "__main__":
    from motor_ecofin import ConfiguracaoFinanciamento, Recursos
    
    config = ConfiguracaoFinanciamento(
        saldo_devedor=Decimal('300000'),
        taxa_anual=Decimal('0.12'),
        prazo_meses=420,
        sistema='PRICE',
        tr_mensal=Decimal('0.0015'),
        seguro_mensal=Decimal('50'),
        taxa_admin_mensal=Decimal('25')
    )
    
    recursos = Recursos(
        valor_fgts=Decimal('30000'),
        capacidade_extra_mensal=Decimal('1000'),
        tem_reserva_emergencia=True,
        trabalha_clt=True
    )
    
    motor = MotorEcoFin(config)
    otimizador = Otimizador(motor, recursos)
    
    print("🔍 Otimizando estratégias...")
    melhor = otimizador.otimizar('economia')
    
    if melhor:
        print("\n✅ MELHOR ESTRATÉGIA ENCONTRADA:")
        print(f"  FGTS: R$ {float(melhor.fgts_usado):,.2f}")
        print(f"  Amortização Mensal: R$ {float(melhor.amortizacao_mensal):,.2f}")
        print(f"  Duração: {melhor.duracao_amortizacao} meses")
        print(f"  Economia: R$ {float(melhor.economia):,.2f}")
        print(f"  Redução Prazo: {melhor.reducao_prazo} meses")
        print(f"  ROI: {float(melhor.roi) * 100:.2f}%")
        print(f"  Viabilidade: {melhor.viabilidade}")
