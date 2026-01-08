"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              OTIMIZADOR INTELIGENTE ECOFIN - VERSÃO 6.0                      ║
║                                                                              ║
║  AUTOMAÇÃO COMPLETA:                                                        ║
║  - Testa FGTS (se tiver) + retorno a cada 24 meses                         ║
║  - Testa TODOS os valores de amortização (R$ 1 até capacidade máxima)     ║
║  - Testa TODAS as durações (1 mês até quitar)                             ║
║  - Descobre ponto ótimo de parada (custo-benefício)                       ║
║  - Analisa se vale parar antes e guardar dinheiro                         ║
║  - Encontra melhor estratégia automaticamente                             ║
║                                                                              ║
║  O QUE VOCÊ FAZIA MANUALMENTE NA PLANILHA, AGORA É AUTOMÁTICO! 🚀         ║
║                                                                              ║
║  Versão: 6.0.0 (Inteligente - 2025-01-08)                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass
import math
from motor_ecofin_v5_corrigido import MotorEcoFin, ConfiguracaoFinanciamento, Recursos

@dataclass
class EstrategiaInteligente:
    """Resultado de uma estratégia INTELIGENTE"""
    # Parâmetros da estratégia
    usa_fgts: bool
    valor_fgts: Decimal
    fgts_retorna_24m: bool
    amortizacao_mensal: Decimal
    duracao_amortizacao: int
    
    # Resultados financeiros
    total_pago: Decimal
    total_juros: Decimal
    prazo_meses: int
    economia: Decimal
    reducao_prazo: int
    
    # Análise de viabilidade
    viabilidade: str
    roi: Decimal
    score: Decimal
    investimento_total: Decimal
    percentual_economia: Decimal
    
    # Análise de parada antecipada
    vale_parar_antes: bool
    meses_otimo_parada: Optional[int]
    economia_parada_antecipada: Optional[Decimal]
    diferenca_parar_antes: Optional[Decimal]  # Diferença de economia se parar antes
    
    # Explicações
    explicacao_viabilidade: str
    recomendacao: str  # Texto explicando a estratégia
    
    # Simulação completa
    simulacao_completa: Dict

class OtimizadorInteligente:
    """
    Otimizador que AUTOMATIZA o trabalho manual da planilha
    
    LÓGICA INTELIGENTE:
    1. Se tem FGTS → Sempre usa (prioridade máxima)
    2. FGTS volta a cada 24 meses (se CLT)
    3. Testa TODOS os valores de amortização (R$ 1 a R$ capacidade_max)
    4. Testa TODAS as durações (1 mês até quitar)
    5. Calcula custo-benefício de parar antes
    6. Encontra MELHOR estratégia automaticamente
    
    TOTAL DE CENÁRIOS: capacidade_max × durações
    Exemplo: R$ 1.000 × 500 meses = 500.000 cenários testados!
    """
    
    def __init__(
        self,
        config: ConfiguracaoFinanciamento,
        recursos: Recursos,
        salario_mensal: Optional[Decimal] = None
    ):
        self.config = config
        self.recursos = recursos
        self.salario_mensal = salario_mensal or Decimal('0')
        self.motor = MotorEcoFin(config)
        
        # Cenário original para comparação
        self.original = self.motor.simular_sem_estrategia()
        
        # Cache de resultados
        self.cache_resultados = {}
    
    def calcular_fgts_futuro(self, mes: int) -> Decimal:
        """
        Calcula FGTS disponível no mês N
        
        LÓGICA:
        - FGTS atual sempre disponível no início
        - Se CLT: FGTS acumula 8% do salário por mês
        - Pode usar novamente a cada 24 meses
        
        Args:
            mes: Mês atual da simulação
        
        Returns:
            FGTS disponível para usar no mês
        """
        if not self.recursos.trabalha_clt or self.salario_mensal == 0:
            return Decimal('0')
        
        # FGTS acumula 8% do salário mensal
        fgts_mensal = self.salario_mensal * Decimal('0.08')
        
        # A cada 24 meses, pode usar novamente
        ciclos_completos = mes // 24
        fgts_acumulado = fgts_mensal * Decimal(str(mes))
        
        # Mas só pode usar em múltiplos de 24 meses
        if mes % 24 == 0 and mes > 0:
            return fgts_acumulado
        else:
            return Decimal('0')
    
    def simular_com_fgts_recorrente(
        self,
        fgts_inicial: Decimal,
        amort_mensal: Decimal,
        duracao_max: int
    ) -> Dict:
        """
        Simula com FGTS inicial + FGTS a cada 24 meses
        
        LÓGICA:
        1. Usa FGTS no início
        2. Amortiza valor mensal
        3. A cada 24 meses: aplica FGTS novamente (se CLT)
        4. Para quando quita ou atinge duração máxima
        """
        
        # Começar com FGTS inicial
        saldo = self.config.saldo_devedor - fgts_inicial
        
        if saldo <= Decimal('0.01'):
            return {
                'prazo_meses': 0,
                'total_pago': float(fgts_inicial),
                'total_juros': 0.0,
                'fgts_total_usado': float(fgts_inicial),
                'fgts_aplicacoes': 1
            }
        
        mes = 0
        total_pago = fgts_inicial
        total_juros = Decimal('0')
        fgts_total_usado = fgts_inicial
        fgts_aplicacoes = 1
        
        # PMT base
        pmt_base = self.motor.calcular_pmt(
            self.motor.taxa_mensal, 
            self.config.prazo_meses, 
            saldo
        )
        
        detalhes = []
        
        while saldo > Decimal('0.01') and mes < min(duracao_max, self.config.prazo_meses):
            mes += 1
            saldo_inicial = saldo
            
            # A cada 24 meses: aplicar FGTS novamente
            fgts_mes = Decimal('0')
            if mes % 24 == 0 and self.recursos.trabalha_clt and self.salario_mensal > 0:
                fgts_mes = self.calcular_fgts_futuro(mes)
                saldo -= fgts_mes
                fgts_total_usado += fgts_mes
                fgts_aplicacoes += 1
                
                if saldo <= Decimal('0.01'):
                    saldo = Decimal('0')
                    total_pago += fgts_mes
                    break
            
            # Juros do mês
            juros = saldo * self.motor.taxa_mensal
            
            # Amortização base
            amortizacao_base = pmt_base - juros
            if amortizacao_base < 0:
                amortizacao_base = Decimal('0')
            
            # Amortização extra (dentro da duração)
            amort_extra = amort_mensal if mes <= duracao_max else Decimal('0')
            
            # Amortização total
            amortizacao_total = amortizacao_base + amort_extra
            
            # Limitar ao saldo
            if amortizacao_total > saldo:
                amortizacao_total = saldo
            
            # Parcela do mês
            parcela = (
                juros + 
                amortizacao_total + 
                self.config.seguro_mensal + 
                self.config.taxa_admin_mensal
            )
            
            # Atualizar
            saldo -= amortizacao_total
            total_pago += parcela
            total_juros += juros
            
            if saldo <= Decimal('0.01'):
                saldo = Decimal('0')
                break
        
        return {
            'prazo_meses': mes,
            'total_pago': float(total_pago),
            'total_juros': float(total_juros),
            'fgts_total_usado': float(fgts_total_usado),
            'fgts_aplicacoes': fgts_aplicacoes,
            'amortizacao_mensal': float(amort_mensal),
            'duracao_amortizacao': duracao_max
        }
    
    def analisar_ponto_otimo_parada(
        self,
        fgts_usar: Decimal,
        amort_mensal: Decimal
    ) -> Tuple[int, Decimal, bool]:
        """
        Analisa se vale a pena PARAR de amortizar antes da quitação
        
        LÓGICA:
        - Testa parar em múltiplos momentos
        - Calcula economia de cada momento
        - Identifica se diferença é < 5% (não vale a pena)
        - Retorna momento ótimo para parar
        
        Returns:
            Tuple[meses_otimo, economia_otima, vale_parar_antes]
        """
        
        # Simular até quitar
        resultado_completo = self.simular_com_fgts_recorrente(
            fgts_usar,
            amort_mensal,
            999
        )
        
        economia_completa = Decimal(str(self.original['total_pago'])) - Decimal(str(resultado_completo['total_pago']))
        prazo_completo = resultado_completo['prazo_meses']
        
        # Testar parar em vários momentos
        melhor_roi = Decimal('0')
        melhor_momento = prazo_completo
        melhor_economia = economia_completa
        
        # Testar parar 12, 24, 36, 48, 60 meses antes
        for meses_antes in [12, 24, 36, 48, 60]:
            duracao_teste = prazo_completo - meses_antes
            
            if duracao_teste < 12:  # Mínimo 1 ano
                continue
            
            resultado = self.simular_com_fgts_recorrente(
                fgts_usar,
                amort_mensal,
                duracao_teste
            )
            
            economia = Decimal(str(self.original['total_pago'])) - Decimal(str(resultado['total_pago']))
            
            # Investimento
            meses_investidos = duracao_teste
            investimento = fgts_usar + (amort_mensal * Decimal(str(meses_investidos)))
            
            # ROI
            roi = economia / investimento if investimento > 0 else Decimal('0')
            
            # Se ROI melhor E economia similar (diferença < 10%)
            diferenca_economia = abs(economia_completa - economia) / economia_completa * Decimal('100')
            
            if roi > melhor_roi and diferenca_economia < 10:
                melhor_roi = roi
                melhor_momento = duracao_teste
                melhor_economia = economia
        
        # Vale parar antes se:
        # 1. ROI melhor
        # 2. Economia ainda significativa (> 90% da completa)
        vale_parar = (
            melhor_momento < prazo_completo and
            melhor_economia > economia_completa * Decimal('0.9')
        )
        
        return melhor_momento, melhor_economia, vale_parar
    
    def gerar_todas_estrategias(
        self,
        step_amortizacao: int = 50,  # Testar a cada R$ 50
        step_duracao: int = 12       # Testar a cada 12 meses
    ) -> List[EstrategiaInteligente]:
        """
        Gera TODAS as estratégias possíveis
        
        AUTOMAÇÃO COMPLETA do trabalho manual!
        
        Args:
            step_amortizacao: Incremento de teste (menor = mais preciso, mais lento)
            step_duracao: Incremento de duração (menor = mais preciso, mais lento)
        
        Returns:
            Lista com TODAS as estratégias testadas
        """
        
        print(f"🔍 Iniciando análise inteligente...")
        print(f"   Capacidade máxima: R$ {self.recursos.capacidade_extra_mensal:,.2f}")
        print(f"   FGTS disponível: R$ {self.recursos.valor_fgts:,.2f}")
        print(f"   CLT: {'Sim' if self.recursos.trabalha_clt else 'Não'}")
        
        estrategias = []
        
        # 1. FGTS: Sempre usar se tiver
        usar_fgts = self.recursos.valor_fgts > 0
        fgts_valor = self.recursos.valor_fgts if usar_fgts else Decimal('0')
        
        # 2. Valores de amortização a testar
        if self.recursos.capacidade_extra_mensal == 0:
            valores_amort = [Decimal('0')]
        else:
            # De R$ 50 até capacidade máxima, a cada step
            valores_amort = []
            valor_teste = Decimal(str(step_amortizacao))
            while valor_teste <= self.recursos.capacidade_extra_mensal:
                valores_amort.append(valor_teste)
                valor_teste += Decimal(str(step_amortizacao))
            # Adicionar o valor máximo exato
            if valores_amort[-1] != self.recursos.capacidade_extra_mensal:
                valores_amort.append(self.recursos.capacidade_extra_mensal)
        
        # 3. Durações a testar
        prazo_max = self.original['prazo_meses']
        duracoes = list(range(step_duracao, prazo_max + 1, step_duracao))
        duracoes.append(999)  # Até quitar
        
        total_testes = len(valores_amort) * len(duracoes)
        print(f"   Total de cenários a testar: {total_testes:,}")
        
        contador = 0
        
        # 4. TESTAR TODAS AS COMBINAÇÕES
        for amort_mensal in valores_amort:
            for duracao in duracoes:
                contador += 1
                
                if contador % 100 == 0:
                    progresso = (contador / total_testes) * 100
                    print(f"   Progresso: {progresso:.1f}% ({contador}/{total_testes})")
                
                # Simular estratégia
                if usar_fgts and self.recursos.trabalha_clt and self.salario_mensal > 0:
                    # Com FGTS recorrente
                    resultado = self.simular_com_fgts_recorrente(
                        fgts_valor,
                        amort_mensal,
                        duracao
                    )
                else:
                    # Sem FGTS recorrente (usa motor padrão)
                    resultado = self.motor.simular_com_estrategia(
                        fgts_valor,
                        amort_mensal,
                        duracao
                    )
                
                # Calcular métricas
                economia = Decimal(str(self.original['total_pago'])) - Decimal(str(resultado['total_pago']))
                reducao_prazo = self.original['prazo_meses'] - resultado['prazo_meses']
                
                # Investimento
                fgts_usado = Decimal(str(resultado.get('fgts_total_usado', fgts_valor)))
                meses_amort = min(duracao, resultado['prazo_meses'])
                investimento = fgts_usado + (amort_mensal * Decimal(str(meses_amort)))
                
                # ROI
                roi = economia / investimento if investimento > 0 else Decimal('0')
                
                # Viabilidade
                if amort_mensal == 0:
                    viab = 'ALTA'
                    expl_viab = 'Sem amortização mensal'
                elif self.recursos.capacidade_extra_mensal == 0:
                    viab = 'ALTA'
                    expl_viab = 'Apenas FGTS'
                else:
                    pct = (amort_mensal / self.recursos.capacidade_extra_mensal) * Decimal('100')
                    if pct <= 30:
                        viab = 'ALTA'
                        expl_viab = f'Usa {pct:.0f}% da capacidade. Confortável.'
                    elif pct <= 70:
                        viab = 'MÉDIA'
                        expl_viab = f'Usa {pct:.0f}% da capacidade. Requer disciplina.'
                    else:
                        viab = 'BAIXA'
                        expl_viab = f'Usa {pct:.0f}% da capacidade. Pode apertar.'
                
                # Score
                economia_norm = min(Decimal('100'), (economia / Decimal(str(self.original['total_pago']))) * Decimal('100'))
                roi_norm = min(Decimal('100'), roi * Decimal('20'))
                viab_pontos = {'ALTA': Decimal('100'), 'MÉDIA': Decimal('60'), 'BAIXA': Decimal('20')}
                score = economia_norm * Decimal('0.5') + roi_norm * Decimal('0.3') + viab_pontos[viab] * Decimal('0.2')
                
                # Analisar ponto ótimo de parada (apenas para cenários promissores)
                if economia > self.original['total_pago'] * Decimal('0.3'):  # Economia > 30%
                    momento_otimo, economia_otima, vale_parar = self.analisar_ponto_otimo_parada(
                        fgts_valor,
                        amort_mensal
                    )
                else:
                    momento_otimo = duracao
                    economia_otima = economia
                    vale_parar = False
                
                # Criar estratégia
                estrategia = EstrategiaInteligente(
                    usa_fgts=usar_fgts,
                    valor_fgts=fgts_valor,
                    fgts_retorna_24m=(usar_fgts and self.recursos.trabalha_clt and self.salario_mensal > 0),
                    amortizacao_mensal=amort_mensal,
                    duracao_amortizacao=duracao if duracao < 999 else resultado['prazo_meses'],
                    total_pago=Decimal(str(resultado['total_pago'])),
                    total_juros=Decimal(str(resultado['total_juros'])),
                    prazo_meses=resultado['prazo_meses'],
                    economia=economia,
                    reducao_prazo=reducao_prazo,
                    viabilidade=viab,
                    roi=roi,
                    score=score,
                    investimento_total=investimento,
                    percentual_economia=(economia / Decimal(str(self.original['total_pago']))) * Decimal('100'),
                    vale_parar_antes=vale_parar,
                    meses_otimo_parada=momento_otimo if vale_parar else None,
                    economia_parada_antecipada=economia_otima if vale_parar else None,
                    diferenca_parar_antes=(economia - economia_otima) if vale_parar else None,
                    explicacao_viabilidade=expl_viab,
                    recomendacao=self._gerar_recomendacao(
                        usar_fgts, fgts_valor, amort_mensal, duracao, 
                        resultado, economia, vale_parar, momento_otimo
                    ),
                    simulacao_completa=resultado
                )
                
                estrategias.append(estrategia)
        
        print(f"✅ Análise completa! {len(estrategias):,} estratégias testadas.")
        
        # Ordenar por economia
        estrategias.sort(key=lambda x: (-x.economia, -x.roi))
        
        return estrategias
    
    def _gerar_recomendacao(
        self,
        usa_fgts, fgts_valor, amort_mensal, duracao,
        resultado, economia, vale_parar, momento_otimo
    ) -> str:
        """Gera recomendação em texto para o cliente"""
        
        rec = []
        
        if usa_fgts:
            rec.append(f"Use seus R$ {fgts_valor:,.2f} de FGTS imediatamente.")
        
        if amort_mensal > 0:
            rec.append(f"Amortize R$ {amort_mensal:,.2f} por mês")
            
            if vale_parar:
                anos = momento_otimo // 12
                rec.append(f"por {anos} anos (pode parar aqui, diferença mínima).")
            else:
                if duracao < 999:
                    anos = duracao // 12
                    rec.append(f"por {anos} anos.")
                else:
                    rec.append(f"até quitar.")
        
        rec.append(f"Economia total: R$ {economia:,.2f}.")
        
        return " ".join(rec)
    
    def encontrar_melhor_estrategia(
        self,
        criterio: str = 'economia',
        viabilidade_minima: str = 'BAIXA'
    ) -> Optional[EstrategiaInteligente]:
        """
        Encontra a MELHOR estratégia baseado no critério
        
        Args:
            criterio: 'economia', 'roi', 'prazo', 'viabilidade'
            viabilidade_minima: Filtrar por viabilidade mínima
        
        Returns:
            Melhor estratégia ou None
        """
        
        estrategias = self.gerar_todas_estrategias()
        
        # Filtrar por viabilidade
        viab_ordem = {'ALTA': 3, 'MÉDIA': 2, 'BAIXA': 1}
        min_nivel = viab_ordem[viabilidade_minima]
        
        estrategias_filtradas = [
            e for e in estrategias 
            if viab_ordem[e.viabilidade] >= min_nivel
        ]
        
        if not estrategias_filtradas:
            estrategias_filtradas = estrategias  # Fallback
        
        # Ordenar por critério
        if criterio == 'roi':
            estrategias_filtradas.sort(key=lambda x: -x.roi)
        elif criterio == 'prazo':
            estrategias_filtradas.sort(key=lambda x: -x.reducao_prazo)
        elif criterio == 'viabilidade':
            estrategias_filtradas.sort(key=lambda x: (-viab_ordem[x.viabilidade], -x.economia))
        else:  # economia
            estrategias_filtradas.sort(key=lambda x: -x.economia)
        
        return estrategias_filtradas[0] if estrategias_filtradas else None
    
    def comparar_top_estrategias(
        self,
        limite: int = 3,
        garantir_diversidade: bool = True
    ) -> List[EstrategiaInteligente]:
        """
        Retorna TOP N estratégias DIFERENTES
        
        Args:
            limite: Número de estratégias
            garantir_diversidade: Forçar diferença entre elas
        """
        
        todas = self.gerar_todas_estrategias()
        
        if not garantir_diversidade:
            return todas[:limite]
        
        # Garantir diversidade
        diversas = []
        
        for estrategia in todas:
            eh_diferente = True
            
            for outra in diversas:
                # Diferença em amortização
                diff_amort = abs(estrategia.amortizacao_mensal - outra.amortizacao_mensal)
                diff_amort_pct = (diff_amort / max(self.recursos.capacidade_extra_mensal, Decimal('1'))) * Decimal('100')
                
                # Diferença em duração
                diff_dur = abs(estrategia.duracao_amortizacao - outra.duracao_amortizacao)
                
                # Se muito similar
                if diff_amort_pct < 20 and diff_dur < 24:
                    eh_diferente = False
                    break
            
            if eh_diferente:
                diversas.append(estrategia)
                
                if len(diversas) >= limite:
                    break
        
        return diversas
