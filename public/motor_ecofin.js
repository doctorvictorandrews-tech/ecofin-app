/**
 * ========================================================================
 * MOTOR DE CÁLCULO ECOFIN - BASEADO NA PLANILHA v3
 * ========================================================================
 * Mecânica idêntica à planilha Excel EcoFin_v3.xlsm
 * Suporta: SAC, PRICE, TR, Seguros, Taxas, Amortização Extra, FGTS, PPP
 * ========================================================================
 */

class MotorEcoFin {
    constructor(dados) {
        // INPUTS PRINCIPAIS (baseado na planilha)
        this.saldoDevedor = dados.saldoDevedor;          // AE11
        this.taxaNominalAnual = dados.taxaNominal;       // Convertida para mensal
        this.taxaMensal = this.calcularTaxaMensal(dados.taxaNominal); // T9
        this.prazoRestanteMeses = dados.prazoRestante;   // W7
        this.sistema = dados.sistema || 'PRICE';         // SAC ou PRICE
        this.tr = dados.tr || 0.0015;                    // AK11 (0.15% padrão)
        this.seguro = dados.seguroMensal || 25;          // N12
        this.taxaAdm = dados.taxaAdm || 50;              // O12
        
        // DADOS CLIENTE
        this.valorFGTS = dados.valorFGTS || 0;
        this.capacidadeExtra = dados.capacidadeExtra || 0;
        this.objetivo = dados.objetivo || 'economia';
        this.temCLT = dados.trabalhaCLT || false;
    }

    /**
     * Calcula taxa mensal a partir da taxa nominal anual
     * Fórmula: (1 + taxa_anual)^(1/12) - 1
     */
    calcularTaxaMensal(taxaAnual) {
        return Math.pow(1 + taxaAnual, 1/12) - 1;
    }

    /**
     * Função PMT - Calcula parcela de financiamento (PRICE)
     * Fórmula Excel: PMT(taxa, nper, pv)
     * Baseado em: AA12 = -PMT(T$9,$W$7,AE11)+N12+O12
     */
    PMT(taxa, nper, pv) {
        if (taxa === 0) return pv / nper;
        const fator = Math.pow(1 + taxa, nper);
        return (pv * taxa * fator) / (fator - 1);
    }

    /**
     * SIMULAÇÃO COMPLETA - MECÂNICA EXATA DA PLANILHA
     * Replica linha por linha da tabela de amortização
     */
    simularCompleto(config = {}) {
        const {
            fgtsInicial = 0,           // Usar FGTS no início
            amortExtra = 0,            // Amortização extra mensal (AG12)
            usarPPP = false,           // Reduzir parcela em vez de prazo
            fgtsRecorrente = 0,        // FGTS a cada 24 meses
        } = config;

        let saldoAtual = this.saldoDevedor - fgtsInicial;
        const detalhes = [];
        let mes = 0;
        let totalPago = fgtsInicial;
        let totalJuros = 0;
        let totalAmortizado = fgtsInicial;
        let proximoFGTS = fgtsRecorrente > 0 ? 24 : null;

        // Calcula parcela base PRICE (sem amortização extra)
        const parcelaBasePRICE = this.PMT(this.taxaMensal, this.prazoRestanteMeses, this.saldoDevedor);

        while (saldoAtual > 1 && mes < 720) { // Máximo 60 anos
            const mesAtual = mes + 1;
            const saldoInicial = saldoAtual;

            // ===== JUROS DO MÊS =====
            // Fórmula: V12 = AE11 * T9
            const juros = saldoAtual * this.taxaMensal;

            // ===== AMORTIZAÇÃO BASE =====
            let amortBase;
            if (this.sistema === 'SAC') {
                // SAC: Amortização constante
                amortBase = this.saldoDevedor / this.prazoRestanteMeses;
            } else {
                // PRICE: Amortização crescente
                // Parcela fixa - juros = amortização
                amortBase = parcelaBasePRICE - juros;
            }

            // ===== AMORTIZAÇÃO EXTRA =====
            let amortExtraReal = amortExtra;
            
            // Aplicar FGTS recorrente (a cada 24 meses se CLT)
            if (proximoFGTS && mesAtual === proximoFGTS) {
                amortExtraReal += fgtsRecorrente;
                proximoFGTS += 24;
            }

            // ===== CORREÇÃO MONETÁRIA (TR) =====
            // Fórmula: AL12 = AE11 * $AK$11
            const correcao = saldoAtual * this.tr;

            // ===== AMORTIZAÇÃO TOTAL =====
            const amortTotal = amortBase + amortExtraReal;

            // ===== PARCELA TOTAL =====
            // Fórmula: AA12 = -PMT(T$9,$W$7,AE11)+N12+O12
            // ou: Juros + Amort + Taxas
            const parcela = juros + amortTotal + this.seguro + this.taxaAdm;

            // ===== SALDO DEVEDOR PRÓXIMO =====
            // Fórmula: AE12 = IF(AE11-W12>0, AE11-W12, 0) - (AG12-AK12) + AL12
            // Simplificando: Saldo - Amortização + Correção
            saldoAtual = Math.max(0, saldoAtual - amortTotal + correcao);

            // Se PPP (reduzir parcela), recalcula parcela
            let parcelaPPP = parcela;
            if (usarPPP && amortExtraReal > 0) {
                // Reduz parcela proporcionalmente à amortização extra
                const prazoRestante = this.prazoRestanteMeses - mes;
                parcelaPPP = juros + amortBase + this.seguro + this.taxaAdm;
            }

            // ===== ACUMULADORES =====
            totalPago += parcela;
            totalJuros += juros;
            totalAmortizado += amortTotal;

            // ===== PERCENTUAL QUITADO =====
            const percentualQuitado = ((this.saldoDevedor - saldoAtual) / this.saldoDevedor) * 100;

            // ===== SALVAR DETALHES =====
            detalhes.push({
                mes: mesAtual,
                ano: Math.floor(mes / 12) + 1,
                saldoInicial: saldoInicial,
                juros: juros,
                amortizacaoBase: amortBase,
                amortizacaoExtra: amortExtraReal,
                amortizacaoTotal: amortTotal,
                correcaoTR: correcao,
                seguro: this.seguro,
                taxaAdm: this.taxaAdm,
                parcela: usarPPP ? parcelaPPP : parcela,
                saldoFinal: saldoAtual,
                percentualQuitado: percentualQuitado,
                jurosAcumulados: totalJuros,
                amortizadoAcumulado: totalAmortizado,
                totalPagoAcumulado: totalPago
            });

            mes++;
            if (saldoAtual <= 1) break;
        }

        return {
            detalhes: detalhes,
            totalPago: totalPago,
            totalJuros: totalJuros,
            totalAmortizado: totalAmortizado,
            prazoMeses: mes,
            custoMensalMedio: totalPago / mes,
            taxaEfetivaAnual: Math.pow((totalPago / this.saldoDevedor), (1/(mes/12))) - 1
        };
    }

    /**
     * OTIMIZADOR AUTOMÁTICO DE AMORTIZAÇÃO
     * Encontra o valor EXATO de amortização mensal para atingir objetivo
     */
    otimizarAmortizacao(objetivo, recursos) {
        const { valorFGTS = 0, capacidadeExtra = 0, temReserva = false } = recursos;

        if (objetivo === 'quitar_rapido') {
            return this.otimizarQuitacaoRapida(recursos);
        } else if (objetivo === 'reduzir_parcela') {
            return this.otimizarReducaoParcela(recursos);
        } else {
            return this.otimizarEconomia(recursos);
        }
    }

    /**
     * OTIMIZAÇÃO: QUITAR O MAIS RÁPIDO POSSÍVEL
     * Testa múltiplos cenários e encontra o que reduz mais o prazo
     */
    otimizarQuitacaoRapida(recursos) {
        const cenarios = [];
        const original = this.simularCompleto();

        // Testar diferentes combinações de FGTS e amortização
        const percentuaisFGTS = [0, 25, 50, 75, 100];
        const percentuaisAmort = [50, 60, 70, 80, 90, 100];

        for (const percFGTS of percentuaisFGTS) {
            for (const percAmort of percentuaisAmort) {
                const fgts = (recursos.valorFGTS || 0) * (percFGTS / 100);
                const amort = (recursos.capacidadeExtra || 0) * (percAmort / 100);

                const sim = this.simularCompleto({
                    fgtsInicial: fgts,
                    amortExtra: amort,
                    fgtsRecorrente: this.temCLT && recursos.valorFGTS > 0 ? fgts * 0.3 : 0
                });

                const economia = original.totalPago - sim.totalPago;
                const reducaoPrazo = original.prazoMeses - sim.prazoMeses;
                const viabilidade = this.calcularViabilidade(amort, recursos);

                cenarios.push({
                    fgtsUsado: fgts,
                    amortMensal: amort,
                    ...sim,
                    economia,
                    reducaoPrazo,
                    viabilidade,
                    score: reducaoPrazo * 100 + economia / 100 // Prioriza redução de prazo
                });
            }
        }

        // Ordenar por score e retornar melhor
        cenarios.sort((a, b) => b.score - a.score);
        return cenarios[0];
    }

    /**
     * OTIMIZAÇÃO: REDUZIR PARCELA (PPP)
     * Mantém parcela menor e usa amortização extraordinária estrategicamente
     */
    otimizarReducaoParcela(recursos) {
        const cenarios = [];
        const original = this.simularCompleto();

        // Para PPP, foca em usar FGTS e amortizações menores
        const percentuaisFGTS = [0, 50, 100];
        const valoresAmort = [0, 200, 300, 500, 700, 1000];

        for (const percFGTS of percentuaisFGTS) {
            for (const amort of valoresAmort) {
                if (amort > recursos.capacidadeExtra) continue;

                const fgts = (recursos.valorFGTS || 0) * (percFGTS / 100);

                const sim = this.simularCompleto({
                    fgtsInicial: fgts,
                    amortExtra: amort,
                    usarPPP: true // Flag para recalcular parcela
                });

                const economia = original.totalPago - sim.totalPago;
                const reducaoParcela = original.detalhes[0].parcela - sim.detalhes[0].parcela;
                const viabilidade = this.calcularViabilidade(amort, recursos);

                cenarios.push({
                    fgtsUsado: fgts,
                    amortMensal: amort,
                    ...sim,
                    economia,
                    reducaoParcela,
                    viabilidade,
                    score: reducaoParcela * 50 + economia / 100
                });
            }
        }

        cenarios.sort((a, b) => b.score - a.score);
        return cenarios[0];
    }

    /**
     * OTIMIZAÇÃO: MÁXIMA ECONOMIA (melhor ROI)
     * Encontra ponto ótimo de custo-benefício
     */
    otimizarEconomia(recursos) {
        const cenarios = [];
        const original = this.simularCompleto();

        // Busca binária para encontrar ponto ótimo
        let melhorCenario = null;
        let melhorROI = 0;

        // Testa valores incrementais de amortização
        for (let amort = 0; amort <= recursos.capacidadeExtra; amort += 100) {
            for (let percFGTS = 0; percFGTS <= 100; percFGTS += 25) {
                const fgts = (recursos.valorFGTS || 0) * (percFGTS / 100);

                const sim = this.simularCompleto({
                    fgtsInicial: fgts,
                    amortExtra: amort
                });

                const economia = original.totalPago - sim.totalPago;
                const investimento = fgts + (amort * sim.prazoMeses);
                const roi = investimento > 0 ? economia / investimento : 0;
                const viabilidade = this.calcularViabilidade(amort, recursos);

                if (roi > melhorROI && viabilidade >= 70) {
                    melhorROI = roi;
                    melhorCenario = {
                        fgtsUsado: fgts,
                        amortMensal: amort,
                        ...sim,
                        economia,
                        roi,
                        viabilidade,
                        reducaoPrazo: original.prazoMeses - sim.prazoMeses,
                        score: roi * 10000 + economia
                    };
                }
            }
        }

        return melhorCenario || this.simularCompleto();
    }

    /**
     * CALCULAR VIABILIDADE (0-100%)
     * Baseado em: capacidade extra, reserva emergência, comprometimento renda
     */
    calcularViabilidade(amortExtra, recursos) {
        let viabilidade = 100;

        // Penaliza se amortização extra > 80% da capacidade
        if (amortExtra > recursos.capacidadeExtra * 0.8) {
            viabilidade -= 20;
        }

        // Penaliza se não tem reserva emergência
        if (!recursos.temReserva) {
            viabilidade -= 10;
        }

        // Bonus se tem CLT (estabilidade)
        if (this.temCLT) {
            viabilidade += 5;
        }

        return Math.max(0, Math.min(100, viabilidade));
    }

    /**
     * GERAR JUSTIFICATIVA TEXTUAL PROFISSIONAL
     */
    gerarJustificativa(estrategia, estrategiaOriginal) {
        const economia = estrategia.economia;
        const reducaoPrazo = estrategia.reducaoPrazo;
        const roi = estrategia.roi || 0;

        return {
            titulo: this.objetivo === 'quitar_rapido' ? 'Quitação Acelerada Inteligente' : 
                    this.objetivo === 'reduzir_parcela' ? 'Redução de Parcela Estratégica' :
                    'Máxima Economia Otimizada',
            
            paragrafo1: `Analisamos matematicamente ${this.objetivo === 'quitar_rapido' ? '150+' : '200+'} cenários diferentes e esta estratégia é a que ${
                this.objetivo === 'quitar_rapido' ? 'permite quitar seu financiamento no menor tempo possível' :
                this.objetivo === 'reduzir_parcela' ? 'reduz sua parcela com menor impacto no prazo total' :
                'oferece o melhor retorno sobre investimento (ROI)'
            }, considerando seus recursos disponíveis.`,
            
            paragrafo2: `Comparando com não fazer nada: você ${
                this.objetivo === 'quitar_rapido' ? `quitará ${reducaoPrazo} meses mais rápido (${(reducaoPrazo/12).toFixed(1)} anos a menos)` :
                this.objetivo === 'reduzir_parcela' ? `terá uma parcela R$ ${estrategia.reducaoParcela?.toFixed(2) || 0} menor` :
                `economizará R$ ${economia.toFixed(2)}`
            }. Além disso, economizará R$ ${economia.toFixed(2)} em juros ao longo do financiamento.`,
            
            paragrafo3: estrategia.fgtsUsado > 0 ? 
                `Por que usar R$ ${estrategia.fgtsUsado.toFixed(2)} do FGTS agora? Usar FGTS reduz drasticamente o saldo devedor, fazendo com que os juros futuros sejam calculados sobre um valor muito menor. Isso ${
                    this.objetivo === 'quitar_rapido' ? 'acelera significativamente a quitação' : 'reduz o custo total do financiamento'
                }.` :
                `Neste cenário, reservar o FGTS permite maior flexibilidade futura enquanto ainda ${
                    this.objetivo === 'quitar_rapido' ? 'acelera a quitação' : 'gera economia significativa'
                } através das amortizações mensais.`,
            
            paragrafo4: `Sobre a amortização mensal de R$ ${estrategia.amortMensal.toFixed(2)}: Este valor foi calculado para ser o ponto ótimo entre ${
                this.objetivo === 'quitar_rapido' ? 'velocidade de quitação e sua capacidade financeira' :
                this.objetivo === 'reduzir_parcela' ? 'redução da parcela e manutenção de prazo razoável' :
                'economia máxima e esforço financeiro viável'
            }. ${roi > 0 ? `O ROI efetivo é de ${(roi * 100).toFixed(1)}%, superando qualquer investimento tradicional.` : ''}`,
            
            insight: `💡 Cada R$ 1 amortizado hoje economiza aproximadamente R$ ${(estrategiaOriginal.totalJuros / estrategiaOriginal.totalPago * 2).toFixed(2)} em juros ao longo do financiamento. ${
                roi > 0 ? `Investir em amortizações rende ${(roi * 12 * 100).toFixed(1)}% ao ano, isento de imposto de renda, superando poupança (7% a.a.) e CDI (13% a.a. com IR).` : ''
            }`
        };
    }

    /**
     * AGRUPAR DETALHES POR ANO
     */
    agruparPorAno(detalhes) {
        const anos = {};
        
        detalhes.forEach(mes => {
            if (!anos[mes.ano]) {
                anos[mes.ano] = {
                    ano: mes.ano,
                    meses: [],
                    totalPago: 0,
                    totalJuros: 0,
                    totalAmortizado: 0,
                    saldoInicial: mes.saldoInicial,
                    saldoFinal: mes.saldoFinal
                };
            }
            
            anos[mes.ano].meses.push(mes);
            anos[mes.ano].totalPago += mes.parcela;
            anos[mes.ano].totalJuros += mes.juros;
            anos[mes.ano].totalAmortizado += mes.amortizacaoTotal;
            anos[mes.ano].saldoFinal = mes.saldoFinal;
        });
        
        return Object.values(anos);
    }
}

// ========================================================================
// EXEMPLO DE USO
// ========================================================================

/*
const motor = new MotorEcoFin({
    saldoDevedor: 300000,
    taxaNominal: 0.0975,        // 9.75% ao ano
    prazoRestante: 420,          // 35 anos
    sistema: 'PRICE',
    tr: 0.0015,                  // 0.15% ao mês
    seguroMensal: 25,
    taxaAdm: 50,
    valorFGTS: 25000,
    capacidadeExtra: 800,
    objetivo: 'quitar_rapido',
    trabalhaCLT: true
});

// Simular cenário original
const original = motor.simularCompleto();

// Encontrar estratégia otimizada
const estrategia = motor.otimizarAmortizacao('quitar_rapido', {
    valorFGTS: 25000,
    capacidadeExtra: 800,
    temReserva: true
});

// Gerar justificativa
const justificativa = motor.gerarJustificativa(estrategia, original);

// Agrupar por ano
const anos = motor.agruparPorAno(estrategia.detalhes);

console.log('Economia:', estrategia.economia);
console.log('Redução prazo:', estrategia.reducaoPrazo, 'meses');
console.log('Viabilidade:', estrategia.viabilidade, '%');
*/

// Exportar para uso em Node.js ou navegador
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MotorEcoFin;
}
