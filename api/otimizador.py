"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      OTIMIZADOR ECOFIN - PYTHON                             ║
║                                                                              ║
║  Testa centenas de cenários e encontra a estratégia ótima                  ║
║  Algoritmos de otimização inteligentes                                     ║
║  Cálculo de viabilidade e ROI                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
from dataclasses import dataclass, field
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos
import concurrent.futures
from functools import lru_cache

@dataclass
class Estrategia:
    """Resultado de uma estratégia otimizada"""
    # Configuração
    fgts_usado: Decimal
    amortizacao_mensal: Decimal
    usa_fgts_recorrente: bool
    percentual_fgts_recorrente: Decimal
    
    # Resultados financeiros
    total_pago: Decimal
    total_juros: Decimal
    prazo_meses: int
    economia: Decimal  # vs cenário original
    reducao_prazo: int  # vs cenário original
    
    # Métricas de qualidade
    viabilidade: Decimal  # 0-100
    score: Decimal  # Score de qualidade
    
    # Opcionais
    reducao_parcela: Optional[Decimal] = None
    roi: Optional[Decimal] = None  # Retorno sobre investimento
    simulacao_completa: Optional[Dict] = None
    
    def __str__(self):
        return f"""
Estratégia EcoFin:
  FGTS inicial: R$ {float(self.fgts_usado):,.2f}
  Amortização mensal: R$ {float(self.amortizacao_mensal):,.2f}
  Total pago: R$ {float(self.total_pago):,.2f}
  Economia: R$ {float(self.economia):,.2f}
  Prazo: {self.prazo_meses} meses
  Redução: {self.reducao_prazo} meses
  Viabilidade: {float(self.viabilidade)}%
  ROI: {float(self.roi)*100:.2f}% {'(isento IR!)' if self.roi else ''}
  Score: {float(self.score):.2f}
"""

class Otimizador:
    """
    Otimizador de estratégias EcoFin
    Testa centenas de cenários e encontra o melhor
    """
    
    def __init__(self, motor: MotorEcoFin, recursos: Recursos):
        self.motor = motor
        self.recursos = recursos
        
        # Simular cenário original (sem fazer nada)
        self.original = motor.simular_completo()
    
    def calcular_viabilidade(
        self,
        amortizacao_mensal: Decimal,
        fgts_usado: Decimal
    ) -> Decimal:
        """
        Calcula viabilidade da estratégia (0-100)
        
        Baseado em:
        - Percentual da capacidade extra usada
        - Uso de reservas
        - Situação empregatícia
        """
        viabilidade = Decimal('100')
        
        # Penalidade por usar muito da capacidade
        if self.recursos.capacidade_extra_mensal > 0:
            percentual_usado = amortizacao_mensal / self.recursos.capacidade_extra_mensal
            if percentual_usado > Decimal('0.8'):
                viabilidade -= Decimal('20')  # Usando mais de 80%
            elif percentual_usado > Decimal('0.6'):
                viabilidade -= Decimal('10')  # Usando mais de 60%
        
        # Penalidade por não ter reserva
        if not self.recursos.tem_reserva_emergencia:
            viabilidade -= Decimal('15')
        
        # Bonus por ser CLT (FGTS reposto)
        if self.recursos.trabalha_clt:
            viabilidade += Decimal('5')
        
        # Penalidade por usar muito do FGTS
        if self.recursos.valor_fgts > 0:
            percentual_fgts = fgts_usado / self.recursos.valor_fgts
            if percentual_fgts > Decimal('0.9'):
                viabilidade -= Decimal('10')  # Usando mais de 90%
        
        # Garantir entre 0-100
        return max(Decimal('0'), min(Decimal('100'), viabilidade))
    
    def calcular_roi(
        self,
        economia: Decimal,
        investimento_total: Decimal
    ) -> Decimal:
        """Calcula ROI (Return on Investment)"""
        if investimento_total == 0:
            return Decimal('0')
        
        return economia / investimento_total
    
    def otimizar_quitacao_rapida(
        self,
        max_cenarios: int = 150
    ) -> Estrategia:
        """
        Otimiza para QUITAR O MAIS RÁPIDO POSSÍVEL
        
        Testa:
        - 5 percentuais de FGTS (0%, 25%, 50%, 75%, 100%)
        - 6 percentuais de amortização (50%, 60%, 70%, 80%, 90%, 100%)
        - FGTS recorrente (se CLT)
        
        Total: 5 × 6 = 30 cenários base
        """
        cenarios: List[Estrategia] = []
        
        percentuais_fgts = [Decimal('0'), Decimal('0.25'), Decimal('0.5'), Decimal('0.75'), Decimal('1')]
        percentuais_amort = [Decimal('0.5'), Decimal('0.6'), Decimal('0.7'), Decimal('0.8'), Decimal('0.9'), Decimal('1')]
        
        for perc_fgts in percentuais_fgts:
            fgts_usado = self.recursos.valor_fgts * perc_fgts
            
            for perc_amort in percentuais_amort:
                amort_mensal = self.recursos.capacidade_extra_mensal * perc_amort
                
                # Simular
                resultado = self.motor.simular_completo(
                    fgts_inicial=fgts_usado,
                    amortizacao_extra_mensal=amort_mensal,
                    usar_fgts_recorrente=self.recursos.trabalha_clt and fgts_usado > 0,
                    percentual_fgts_recorrente=Decimal('0.3')
                )
                
                # Calcular métricas
                economia = self.original['total_pago'] - resultado['total_pago']
                reducao_prazo = self.original['prazo_meses'] - resultado['prazo_meses']
                
                viabilidade = self.calcular_viabilidade(amort_mensal, fgts_usado)
                
                # Score: Prioriza redução de prazo, mas considera economia
                score = Decimal(str(reducao_prazo)) * Decimal('100') + economia / Decimal('100')
                
                # Calcular ROI
                investimento_total = fgts_usado + (amort_mensal * Decimal(str(resultado['prazo_meses'])))
                roi = self.calcular_roi(economia, investimento_total)
                
                estrategia = Estrategia(
                    fgts_usado=fgts_usado,
                    amortizacao_mensal=amort_mensal,
                    usa_fgts_recorrente=self.recursos.trabalha_clt and fgts_usado > 0,
                    percentual_fgts_recorrente=Decimal('0.3'),
                    total_pago=resultado['total_pago'],
                    total_juros=resultado['total_juros'],
                    prazo_meses=resultado['prazo_meses'],
                    economia=economia,
                    reducao_prazo=reducao_prazo,
                    viabilidade=viabilidade,
                    roi=roi,
                    score=score,
                    simulacao_completa=resultado
                )
                
                cenarios.append(estrategia)
        
        # Ordenar por score (maior = melhor)
        cenarios.sort(key=lambda x: x.score, reverse=True)
        
        return cenarios[0]
    
    def otimizar_economia(
        self,
        incremento: Decimal = Decimal('100')
    ) -> Estrategia:
        """
        Otimiza para MÁXIMA ECONOMIA com melhor ROI
        
        Busca o ponto ótimo onde:
        - ROI é máximo
        - Viabilidade >= 70%
        - Economia é significativa
        """
        cenarios: List[Estrategia] = []
        
        # Testar amortizações de 0 até capacidade máxima (incrementos de R$ 100)
        amort_atual = Decimal('0')
        while amort_atual <= self.recursos.capacidade_extra_mensal:
            
            # Testar diferentes percentuais de FGTS
            for perc_fgts in [Decimal('0'), Decimal('0.25'), Decimal('0.5'), Decimal('0.75'), Decimal('1')]:
                fgts_usado = self.recursos.valor_fgts * perc_fgts
                
                # Simular
                resultado = self.motor.simular_completo(
                    fgts_inicial=fgts_usado,
                    amortizacao_extra_mensal=amort_atual
                )
                
                # Calcular métricas
                economia = self.original['total_pago'] - resultado['total_pago']
                reducao_prazo = self.original['prazo_meses'] - resultado['prazo_meses']
                
                viabilidade = self.calcular_viabilidade(amort_atual, fgts_usado)
                
                # Calcular ROI
                investimento_total = fgts_usado + (amort_atual * Decimal(str(resultado['prazo_meses'])))
                roi = self.calcular_roi(economia, investimento_total) if investimento_total > 0 else Decimal('0')
                
                # Score: Prioriza ROI e economia
                score = roi * Decimal('10000') + economia
                
                # Só considerar se viabilidade >= 70%
                if viabilidade >= Decimal('70'):
                    estrategia = Estrategia(
                        fgts_usado=fgts_usado,
                        amortizacao_mensal=amort_atual,
                        usa_fgts_recorrente=False,
                        percentual_fgts_recorrente=Decimal('0'),
                        total_pago=resultado['total_pago'],
                        total_juros=resultado['total_juros'],
                        prazo_meses=resultado['prazo_meses'],
                        economia=economia,
                        reducao_prazo=reducao_prazo,
                        viabilidade=viabilidade,
                        roi=roi,
                        score=score,
                        simulacao_completa=resultado
                    )
                    
                    cenarios.append(estrategia)
            
            amort_atual += incremento
        
        # Se não encontrou nenhum cenário viável, usar o original
        if not cenarios:
            return Estrategia(
                fgts_usado=Decimal('0'),
                amortizacao_mensal=Decimal('0'),
                usa_fgts_recorrente=False,
                percentual_fgts_recorrente=Decimal('0'),
                total_pago=self.original['total_pago'],
                total_juros=self.original['total_juros'],
                prazo_meses=self.original['prazo_meses'],
                economia=Decimal('0'),
                reducao_prazo=0,
                viabilidade=Decimal('100'),
                roi=Decimal('0'),
                score=Decimal('0'),
                simulacao_completa=self.original
            )
        
        # Ordenar por score
        cenarios.sort(key=lambda x: x.score, reverse=True)
        
        return cenarios[0]
    
    def otimizar_reducao_parcela(self) -> Estrategia:
        """
        Otimiza para REDUZIR A PARCELA MENSAL
        Usa PPP (usar FGTS/amortização para diminuir parcela)
        
        Testa:
        - 3 percentuais de FGTS (0%, 50%, 100%)
        - 6 valores de amortização mensal (0, 200, 300, 500, 700, 1000)
        """
        cenarios: List[Estrategia] = []
        
        percentuais_fgts = [Decimal('0'), Decimal('0.5'), Decimal('1')]
        valores_amort = [Decimal('0'), Decimal('200'), Decimal('300'), Decimal('500'), Decimal('700'), Decimal('1000')]
        
        parcela_original = self.original['meses'][0].parcela_total
        
        for perc_fgts in percentuais_fgts:
            fgts_usado = self.recursos.valor_fgts * perc_fgts
            
            for amort_mensal in valores_amort:
                # Pular se ultrapassar capacidade
                if amort_mensal > self.recursos.capacidade_extra_mensal:
                    continue
                
                # Simular
                resultado = self.motor.simular_completo(
                    fgts_inicial=fgts_usado,
                    amortizacao_extra_mensal=amort_mensal
                )
                
                # Calcular métricas
                economia = self.original['total_pago'] - resultado['total_pago']
                reducao_prazo = self.original['prazo_meses'] - resultado['prazo_meses']
                parcela_nova = resultado['meses'][0].parcela_total
                reducao_parcela = parcela_original - parcela_nova
                
                viabilidade = self.calcular_viabilidade(amort_mensal, fgts_usado)
                
                # Score: Prioriza redução de parcela
                score = reducao_parcela * Decimal('50') + economia / Decimal('100')
                
                estrategia = Estrategia(
                    fgts_usado=fgts_usado,
                    amortizacao_mensal=amort_mensal,
                    usa_fgts_recorrente=False,
                    percentual_fgts_recorrente=Decimal('0'),
                    total_pago=resultado['total_pago'],
                    total_juros=resultado['total_juros'],
                    prazo_meses=resultado['prazo_meses'],
                    economia=economia,
                    reducao_prazo=reducao_prazo,
                    reducao_parcela=reducao_parcela,
                    viabilidade=viabilidade,
                    roi=Decimal('0'),
                    score=score,
                    simulacao_completa=resultado
                )
                
                cenarios.append(estrategia)
        
        # Ordenar por score
        cenarios.sort(key=lambda x: x.score, reverse=True)
        
        return cenarios[0]
    
    def otimizar(self, objetivo: str = 'economia') -> Estrategia:
        """
        Otimiza baseado no objetivo
        
        Args:
            objetivo: 'quitar_rapido', 'economia', ou 'reduzir_parcela'
        
        Returns:
            Melhor estratégia encontrada
        """
        if objetivo == 'quitar_rapido':
            return self.otimizar_quitacao_rapida()
        elif objetivo == 'economia':
            return self.otimizar_economia()
        elif objetivo == 'reduzir_parcela':
            return self.otimizar_reducao_parcela()
        else:
            raise ValueError(f"Objetivo inválido: {objetivo}")


# ============================================
# EXEMPLO DE USO
# ============================================

if __name__ == "__main__":
    print("="*80)
    print("TESTE DO OTIMIZADOR ECOFIN")
    print("="*80)
    
    # Configuração
    from motor_ecofin import ConfiguracaoFinanciamento, Recursos
    
    config = ConfiguracaoFinanciamento(
        saldo_devedor=Decimal('300000'),
        taxa_anual=Decimal('0.12'),
        prazo_meses=420,
        sistema='PRICE'
    )
    
    recursos = Recursos(
        valor_fgts=Decimal('25000'),
        capacidade_extra_mensal=Decimal('800'),
        tem_reserva_emergencia=True,
        trabalha_clt=True
    )
    
    motor = MotorEcoFin(config)
    otimizador = Otimizador(motor, recursos)
    
    # Testar os 3 objetivos
    objetivos = ['quitar_rapido', 'economia', 'reduzir_parcela']
    
    for obj in objetivos:
        print(f"\n{'='*80}")
        print(f"OBJETIVO: {obj.upper().replace('_', ' ')}")
        print('='*80)
        
        estrategia = otimizador.otimizar(obj)
        print(estrategia)
        
        print(f"\n📊 Comparação com cenário original:")
        print(f"  Original: R$ {float(otimizador.original['total_pago']):,.2f} em {otimizador.original['prazo_meses']} meses")
        print(f"  Otimizado: R$ {float(estrategia.total_pago):,.2f} em {estrategia.prazo_meses} meses")
        print(f"  💰 Economia: R$ {float(estrategia.economia):,.2f} ({float(estrategia.economia/otimizador.original['total_pago']*100):.1f}%)")
        print(f"  ⏱️  Redução prazo: {estrategia.reducao_prazo} meses ({estrategia.reducao_prazo/12:.1f} anos)")
        
        if estrategia.roi and estrategia.roi > 0:
            print(f"  📈 ROI: {float(estrategia.roi)*100:.2f}% = {float(estrategia.roi)*12*100:.1f}% ao ano (isento IR!)")
    
    print("\n" + "="*80)
    print("✅ OTIMIZAÇÕES CONCLUÍDAS!")
    print("="*80)
