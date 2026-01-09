"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              SUPER OTIMIZADOR ECOFIN - EXPLORAÇÃO EXAUSTIVA                  ║
║                                                                              ║
║  EXPLORA TODAS AS POSSIBILIDADES:                                           ║
║  - FGTS: 0%, 25%, 50%, 75%, 100%                                          ║
║  - Amortização mensal: R$ 0 até capacidade máxima (passo R$ 50)           ║
║  - Duração: Analisa ponto ótimo para parar                                ║
║  - Múltiplos objetivos: Economia, ROI, Prazo, Equilíbrio                  ║
║                                                                              ║
║  RESULTADO: A SOLUÇÃO MATEMATICAMENTE PERFEITA                              ║
║                                                                              ║
║  Versão: 6.0.0 (Super Otimizador - 2025-01-08)                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, field
import math
from motor_ecofin import MotorEcoFin, ConfiguracaoFinanciamento, Recursos

@dataclass
class EstrategiaCompleta:
    """Estratégia completa com TODAS as métricas"""
    # Parâmetros da estratégia
    fgts_usado: Decimal
    fgts_percentual: Decimal
    amortizacao_mensal: Decimal
    amortizacao_percentual: Decimal
    duracao_amortizacao: int
    
    # Resultados financeiros
    total_pago: Decimal
    economia_total: Decimal
    reducao_prazo: int
    investimento_total: Decimal
    roi: Decimal
    
    # Viabilidade
    viabilidade: str
    compromisso_mensal_pct: Decimal
    explicacao_viabilidade: str
    
    # Scores
    score_geral: Decimal
    score_equilibrio: Decimal

class SuperOtimizador:
    """
    SUPER OTIMIZADOR - EXPLORAÇÃO EXAUSTIVA
    
    Testa TODAS as combinações possíveis para encontrar a SOLUÇÃO PERFEITA
    """
    
    def __init__(
        self,
        config: ConfiguracaoFinanciamento,
        recursos: Recursos,
        passo_amortizacao: int = 100  # Testar a cada R$ 100
    ):
        self.config = config
        self.recursos = recursos
        self.motor = MotorEcoFin(config)
        self.passo_amortizacao = passo_amortizacao
        
        print("📊 Calculando cenário original...")
        self.original = self.motor.simular_sem_estrategia()
        print(f"   Total original: R$ {self.original['total_pago']:,.2f}")
        
        self._cache = {}
        self.total_cenarios_testados = 0
    
    def _simular_com_cache(self, fgts: Decimal, amort: Decimal, duracao: int) -> Dict:
        """Simula com cache"""
        key = (float(fgts), float(amort), duracao)
        
        if key not in self._cache:
            self._cache[key] = self.motor.simular_com_estrategia(fgts, amort, duracao)
        
        return self._cache[key]
    
    def calcular_viabilidade(self, amort: Decimal) -> Tuple[str, str, Decimal]:
        """Calcula viabilidade"""
        if self.recursos.capacidade_extra_mensal == 0:
            return 'BAIXA', 'Sem capacidade mensal', Decimal('0')
        
        pct = (amort / self.recursos.capacidade_extra_mensal) * Decimal('100')
        
        if pct <= 30:
            return 'ALTA', f'Usa {pct:.0f}% da capacidade. Confortável!', pct
        elif pct <= 70:
            return 'MÉDIA', f'Usa {pct:.0f}% da capacidade. Requer disciplina.', pct
        else:
            return 'BAIXA', f'Usa {pct:.0f}% da capacidade. Pode apertar.', pct
    
    def analisar_melhor_duracao(self, fgts: Decimal, amort: Decimal) -> int:
        """
        Encontra a MELHOR DURAÇÃO para amortizar
        
        Testa: 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 180, 240, 999
        Retorna a duração com MELHOR ROI
        """
        sim_completa = self._simular_com_cache(fgts, amort, 999)
        prazo_max = sim_completa['prazo_meses']
        
        # Durações a testar (a cada 12 meses até 10 anos, depois 15, 20, completo)
        duracoes = [12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 180, 240]
        duracoes = [d for d in duracoes if d <= prazo_max]
        if prazo_max not in duracoes:
            duracoes.append(prazo_max)
        
        melhor_roi = Decimal('0')
        melhor_duracao = prazo_max
        
        for duracao in duracoes:
            sim = self._simular_com_cache(fgts, amort, duracao)
            economia = Decimal(str(self.original['total_pago'])) - Decimal(str(sim['total_pago']))
            meses_inv = sim.get('meses_amortizados', sim['prazo_meses'])
            investimento = fgts + (amort * Decimal(str(meses_inv)))
            
            roi = economia / investimento if investimento > 0 else Decimal('0')
            
            if roi > melhor_roi:
                melhor_roi = roi
                melhor_duracao = duracao
        
        return melhor_duracao
    
    def explorar_todas_possibilidades(self) -> List[EstrategiaCompleta]:
        """
        EXPLORAÇÃO EXAUSTIVA
        
        Testa TODAS as combinações:
        - FGTS: 0%, 25%, 50%, 75%, 100%
        - Amortização: R$ 0 até capacidade (passo R$ 100)
        - Duração: Melhor ROI para cada combinação
        """
        print("\n🔍 EXPLORANDO TODAS AS POSSIBILIDADES...")
        print("=" * 80)
        
        estrategias = []
        
        # FGTS
        fgts_pcts = [0, 25, 50, 75, 100] if self.recursos.valor_fgts > 0 else [0]
        
        # Amortização
        amort_valores = []
        if self.recursos.capacidade_extra_mensal > 0:
            v = Decimal('0')
            while v <= self.recursos.capacidade_extra_mensal:
                amort_valores.append(v)
                v += Decimal(str(self.passo_amortizacao))
            if self.recursos.capacidade_extra_mensal not in amort_valores:
                amort_valores.append(self.recursos.capacidade_extra_mensal)
        else:
            amort_valores = [Decimal('0')]
        
        total = len(fgts_pcts) * len(amort_valores)
        print(f"🎯 Total de combinações: {total}")
        
        atual = 0
        
        for fgts_pct in fgts_pcts:
            fgts_usar = (self.recursos.valor_fgts * Decimal(str(fgts_pct))) / Decimal('100')
            
            for amort in amort_valores:
                atual += 1
                
                if fgts_usar == 0 and amort == 0:
                    continue
                
                if atual % max(1, total // 10) == 0:
                    print(f"   Progresso: {(atual/total)*100:.0f}%")
                
                # Encontrar melhor duração
                melhor_dur = self.analisar_melhor_duracao(fgts_usar, amort)
                
                # Simular com melhor duração
                sim = self._simular_com_cache(fgts_usar, amort, melhor_dur)
                
                # Calcular métricas
                economia = Decimal(str(self.original['total_pago'])) - Decimal(str(sim['total_pago']))
                reducao = self.original['prazo_meses'] - sim['prazo_meses']
                meses_inv = sim.get('meses_amortizados', sim['prazo_meses'])
                investimento = fgts_usar + (amort * Decimal(str(meses_inv)))
                roi = economia / investimento if investimento > 0 else Decimal('0')
                
                viab, expl, pct = self.calcular_viabilidade(amort)
                
                # Scores
                score_eco = min(Decimal('100'), (economia / Decimal(str(self.original['total_pago']))) * Decimal('100'))
                score_roi_val = min(Decimal('100'), roi * Decimal('20'))
                score_viab = {'ALTA': Decimal('100'), 'MÉDIA': Decimal('60'), 'BAIXA': Decimal('20')}.get(viab, Decimal('50'))
                score_equil = (score_eco * Decimal('0.4') + score_roi_val * Decimal('0.3') + score_viab * Decimal('0.3'))
                score_geral = (score_eco + score_roi_val + score_equil) / Decimal('3')
                
                amort_pct = (amort / self.recursos.capacidade_extra_mensal * Decimal('100')) if self.recursos.capacidade_extra_mensal > 0 else Decimal('0')
                
                est = EstrategiaCompleta(
                    fgts_usado=fgts_usar,
                    fgts_percentual=Decimal(str(fgts_pct)),
                    amortizacao_mensal=amort,
                    amortizacao_percentual=amort_pct,
                    duracao_amortizacao=melhor_dur,
                    total_pago=Decimal(str(sim['total_pago'])),
                    economia_total=economia,
                    reducao_prazo=reducao,
                    investimento_total=investimento,
                    roi=roi,
                    viabilidade=viab,
                    compromisso_mensal_pct=pct,
                    explicacao_viabilidade=expl,
                    score_geral=score_geral,
                    score_equilibrio=score_equil
                )
                
                estrategias.append(est)
                self.total_cenarios_testados += 1
        
        print(f"\n✅ {self.total_cenarios_testados} cenários testados!")
        
        return estrategias
    
    def encontrar_top3_diversas(self, estrategias: List[EstrategiaCompleta]) -> List[EstrategiaCompleta]:
        """Encontra TOP 3 REALMENTE DIFERENTES"""
        ordenadas = sorted(estrategias, key=lambda x: -x.score_geral)
        
        diversas = [ordenadas[0]]
        
        for est in ordenadas[1:]:
            eh_dif = True
            
            for outra in diversas:
                diff_fgts = abs(est.fgts_percentual - outra.fgts_percentual)
                diff_amort = abs(est.amortizacao_percentual - outra.amortizacao_percentual)
                
                if diff_fgts < 20 and diff_amort < 20:
                    eh_dif = False
                    break
            
            if eh_dif:
                diversas.append(est)
                if len(diversas) >= 3:
                    break
        
        return diversas
    
    def otimizar(self) -> Dict:
        """OTIMIZAÇÃO COMPLETA"""
        todas = self.explorar_todas_possibilidades()
        
        if not todas:
            return {'status': 'sem_recursos'}
        
        # Ordenar por diferentes objetivos
        por_economia = sorted(todas, key=lambda x: -x.economia_total)[:10]
        por_roi = sorted(todas, key=lambda x: -x.roi)[:10]
        por_equilibrio = sorted(todas, key=lambda x: -x.score_equilibrio)[:10]
        
        top3 = self.encontrar_top3_diversas(todas)
        
        return {
            'status': 'success',
            'melhor_geral': por_equilibrio[0],
            'melhor_economia': por_economia[0],
            'melhor_roi': por_roi[0],
            'top3_diversas': top3,
            'top10_economia': por_economia,
            'top10_roi': por_roi,
            'top10_equilibrio': por_equilibrio,
            'estatisticas': {
                'total_testados': self.total_cenarios_testados,
                'economia_maxima': float(por_economia[0].economia_total)
            }
        }
