# ANÁLISE COMPLETA PLANILHA ECOFIN V3

## ESTRUTURA DESCOBERTA

### ABA: "Meu EcoFin" (673 linhas x 207 colunas)

**INPUTS PRINCIPAIS:**
- Célula AE11: Saldo Devedor Inicial (300.000)
- Célula T9: Taxa mensal
- Célula W7: Prazo original
- Célula N12: Taxa administrativa (25)
- Célula O12: Seguro (50)

**COLUNAS PRINCIPAIS (linha 12 em diante):**
- H: Data (mês)
- J: Meses restantes (=U10, depois =J12-1)
- L: Triênio (=ROUNDUP(U12/36,0))
- M: Ano
- N: Taxa administrativa
- O: Seguro
- U: Contador de meses (1, 2, 3...)
- V: **JUROS** (=AE11*T9, depois =IF(AE12>W12,AE12*$T$9,0))
- W: **AMORTIZAÇÃO** (=IF(AE11>W11,AA12-V12-N12-O12,AE11))
- AA: **PARCELA** (=-PMT(T$9,$W$7,AE11)+N12+O12)
- AB: PARCELA SAC
- AC: Economia/FGTS
- AE: **SALDO DEVEDOR** (=IF((W11+AG11)>AE11,0,IF(AE11-W12>0,AE11-W12,0)-IF(AE11-W12>0,AG12-AK12,0)))
- AG: **AMORTIZAÇÃO EXTRAORDINÁRIA**
- AH: Meses restantes

## FÓRMULAS CRÍTICAS IDENTIFICADAS

### 1. JUROS (Coluna V)
```excel
Linha 12: =AE11*T9
Linha 13+: =IF(AE12>W12, AE12*$T$9, 0)
```
**Lógica:** Saldo anterior × Taxa mensal

### 2. PARCELA (Coluna AA)
```excel
Linha 12: =-PMT(T$9, $W$7, AE11) + N12 + O12
Linha 13+: =IF(OR(AE12<W12, INT(AE12)=0), 0, -PMT($T$9, IF(AI12="V", AH12, NPER($T$9, -AA12+N13+O13, AE12)), AE12+AK12) + N13 + O13)
```
**Lógica:** PMT (taxa, prazo, saldo) + Taxa Adm + Seguro

### 3. AMORTIZAÇÃO (Coluna W)
```excel
=IF(AE11>W11, AA12-V12-N12-O12, AE11)
```
**Lógica:** Parcela - Juros - TaxaAdm - Seguro

### 4. SALDO DEVEDOR (Coluna AE)
```excel
=IF((W11+AG11)>AE11, 0, IF(AE11-W12>0, AE11-W12, 0) - IF(AE11-W12>0, AG12-AK12, 0))
```
**Lógica:** Saldo anterior - Amortização base - Amortização extra (com TR)

### 5. DATA (Coluna H)
```excel
Linha 12: 2025-06-01
Linha 13+: =H12+31
```
**Lógica:** Soma 31 dias (aproximação de 1 mês)

## DESCOBERTAS IMPORTANTES

1. **TR ESTÁ APLICADA:** Coluna AK parece ter correção TR
2. **SISTEMA É PRICE:** Usa PMT para calcular parcela
3. **TAXA ADM + SEGURO:** São somados à parcela
4. **AMORTIZAÇÃO EXTRAORDINÁRIA:** Coluna AG permite aportes extras
5. **ECONOMIA:** Coluna AC compara com cenário original

## CONCLUSÃO

O motor precisa:
✅ Calcular juros = saldo × taxa mensal
✅ Calcular parcela PMT + taxa + seguro
✅ Calcular amortização = parcela - juros - taxa - seguro
✅ Aplicar TR no saldo
✅ Permitir amortizações extras
✅ Comparar com cenário original (sem amortizações)
