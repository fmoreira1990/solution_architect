# Taxas de mercado por senioridade

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** referência de mercado para converter esforço em custo. **Não é a estrutura de custo da empresa** — é um modelo transparente, camada por camada, para que o comercial substitua cada uma pelos números reais.
**Requisitos cobertos:** `D-05`
**Fontes:** Glassdoor Brasil (junho de 2026), Cálculo Jurídico (encargos CLT 2026), `docs/delivery/estimativa-fase1.md`
**Data:** 2026-09-24

---

## Por que o modelo é apresentado em camadas

Um número fechado de taxa/hora esconde as premissas que o produziram e envelhece mal. Aqui cada camada é explícita, e **trocar uma não invalida as outras**:

```
salário de mercado
   × 1,8   encargos e provisões CLT          → custo para a empresa
   ÷ 21    dias úteis por mês                → custo por dia-pessoa
   × 1,5   overhead + margem + ociosidade    → taxa de faturamento
```

Se a empresa opera em Simples Nacional, a primeira camada cai. Se a margem-alvo é outra, muda só a terceira. **O esforço em dias-pessoa não muda em nenhum caso** — é isso que torna a estimativa reutilizável.

---

## Camada 1 — Salário de mercado

Glassdoor Brasil, junho de 2026. Média nacional; São Paulo fica acima.

| Perfil | Média | Faixa (p25–p75) |
|---|---|---|
| **Arquiteto de Soluções Sênior** | **R$ 19.097** | R$ 9.833 – 18.854 *(cargo geral: média R$ 14.667)* |
| **Desenvolvedor Sênior** | **R$ 12.800** | R$ 10.667 – 16.083 |
| **Desenvolvedor Pleno** | **R$ 7.500** | R$ 5.560 – 8.242 *(varia por stack e praça; SP no topo)* |
| **SRE / DevOps** | **R$ 10.438** | R$ 8.191 – 16.250 *(p90: R$ 20.750)* |

> **Duas observações sobre a dispersão.** A faixa do arquiteto é larga porque o título cobre desde arquiteto de aplicação até arquiteto de soluções corporativas — a estimativa usa a média do **sênior**, que é o perfil que a onda 30 exige. E a do SRE tem cauda longa: o p90 (R$ 20.750) supera a média do dev sênior, refletindo escassez do perfil.

## Camada 2 — Encargos CLT

Regime de Lucro Presumido, que é o caso de consultoria de porte:

| Componente | % sobre o salário |
|---|---|
| INSS patronal (20% + RAT + terceiros) | ~28,8% |
| FGTS | 8% |
| 13º salário (provisão) | 8,33% |
| Férias + 1/3 (provisão) | 11,1% |
| FGTS e INSS sobre provisões | ~7,3% |
| **Fator total** | **≈ 1,8×** |

Empresa em **Simples Nacional** não recolhe INSS patronal em separado, e o fator cai para ~1,4×.

## Camada 3 — Overhead e margem

O fator de **1,5×** sobre o custo carregado cobre gestão e coordenação, estrutura (ferramentas, ambiente, espaço), comercial e pré-venda, treinamento e certificação, banco de horas e ociosidade entre alocações, e a margem operacional.

> Este é o número **menos ancorado** deste documento — varia por contrato, por porte e por modelo de alocação. Consultoria de valor hora de mercado para TI costuma ficar entre R$ 70 e R$ 200 para perfis gerais, e acima disso para especialistas; o modelo abaixo produz valores coerentes com essa faixa nos perfis mais sêniores.

---

## Taxas resultantes

| Perfil | Salário | Custo CLT | Custo/dia | **Taxa/dia** | **Taxa/hora** |
|---|---|---|---|---|---|
| Arquiteto de Soluções Sr | R$ 19.097 | R$ 34.375 | R$ 1.637 | **R$ 2.455** | **R$ 307** |
| Desenvolvedor Sênior | R$ 12.800 | R$ 23.040 | R$ 1.097 | **R$ 1.646** | **R$ 206** |
| Desenvolvedor Pleno | R$ 7.500 | R$ 13.500 | R$ 643 | **R$ 964** | **R$ 121** |
| SRE / DevOps | R$ 10.438 | R$ 18.788 | R$ 895 | **R$ 1.342** | **R$ 168** |

*Dia-pessoa de 8 horas, 21 dias úteis por mês.*

---

## Custo da fase 1

Aplicando às 79 dias-pessoa da [decomposição](decomposicao-onda-30.md):

| Perfil | d.p. | Taxa/dia | Subtotal |
|---|---|---|---|
| Arquiteto de Soluções Sr | 9,5 | R$ 2.455 | R$ 23.323 |
| Desenvolvedor Sênior | 33 | R$ 1.646 | R$ 54.318 |
| Desenvolvedor Pleno | 16 | R$ 964 | R$ 15.424 |
| SRE / DevOps | 20,5 | R$ 1.342 | R$ 27.511 |
| **Total — 79 d.p.** | | | **R$ 120.576** |
| Contingência 15% (12 d.p.) | | | R$ 18.316 |
| **Total com contingência** | | | **R$ 138.892** |

**Taxa média ponderada: R$ 1.526 por dia-pessoa.**

### Infraestrutura, no mesmo período

| | |
|---|---|
| AWS em regime | US$ 835–1.489/mês → **R$ 4.509–8.041/mês** |
| Fase 1 (1 mês) | **R$ 4.509–8.041** |

*Câmbio de R$ 5,40/US$ como premissa declarada.*

### Total da fase 1

| | |
|---|---|
| Pessoas, com contingência | R$ 138.892 |
| Infraestrutura | R$ 4.509–8.041 |
| **Total** | **≈ R$ 143.400 – 146.900** |

---

## Cenário com desenvolvimento assistido por IA

Aplicando a redistribuição de esforço de [`impacto-ia-no-desenvolvimento.md`](impacto-ia-no-desenvolvimento.md):

| Perfil | d.p. | Subtotal |
|---|---|---|
| Arquiteto de Soluções Sr | 9,5 | R$ 23.323 |
| Desenvolvedor Sênior | 26 | R$ 42.796 |
| Desenvolvedor Pleno | 9 | R$ 8.676 |
| SRE / DevOps | 18,5 | R$ 24.827 |
| **Total — 63 d.p.** | | **R$ 99.622** |
| Licenças de IA | | R$ 490–1.730/mês |
| **Total de pessoas + licenças** | | **≈ R$ 100.100 – 101.400** |

### O achado: a economia em custo é **menor** que a economia em esforço

| | Sem IA | Com IA | Variação |
|---|---|---|---|
| Esforço | 79 d.p. | 63 d.p. | **−20,3%** |
| Custo de pessoas | R$ 120.576 | R$ 99.622 | **−17,4%** |

**A diferença de quase 3 pontos não é arredondamento.** A IA reduz proporcionalmente mais o trabalho de **pleno** (−44%), que é o perfil mais barato, e não reduz nada do **arquiteto**, que é o mais caro.

> Quanto mais o time se concentra em perfis sêniores, **menor o retorno financeiro de ferramenta de produtividade** — ainda que o ganho de prazo permaneça. Isso contraria a intuição de que o ganho de esforço se converte linearmente em economia.

A taxa média ponderada sobe de R$ 1.526 para **R$ 1.581** por dia-pessoa: o time fica menor e mais caro por cabeça.

---

## Premissas

| # | Premissa | Se falsa |
|---|---|---|
| T1 | Regime tributário de Lucro Presumido | Simples Nacional reduz o fator de 1,8 para ~1,4 — **−22% no custo total** |
| T2 | Fator comercial de 1,5× sobre custo carregado | É a camada menos ancorada; varia por contrato e porte |
| T3 | Salários na média nacional | São Paulo fica acima; contratação remota em outras praças, abaixo |
| T4 | 21 dias úteis, 8 horas | — |
| T5 | Alocação CLT, não PJ | PJ muda completamente a camada 2 |
| T6 | Câmbio de R$ 5,40/US$ | Afeta só a infraestrutura |

---

## O que este documento **não** é

**Não é a estrutura de custo da empresa.** É referência pública de mercado, útil para ordem de grandeza e para dar forma à proposta — não para fechar preço.

**Não substitui a decisão comercial.** Preço envolve relacionamento com a conta, volume, prazo contratual e posicionamento competitivo — nenhum deles é decisão de arquitetura.

**O que o arquiteto entrega é o esforço por perfil.** As 79 dias-pessoa da decomposição são o número que sustenta discussão técnica. As taxas acima só o traduzem para a linguagem de quem decide.

## Riscos

1. **T2 é o maior risco do documento.** Errar o fator comercial em 0,2 move o total em ~R$ 16 mil.
2. **Dados de salário têm dispersão alta** — as faixas p25–p75 chegam a variar 2×. Usar a média esconde isso.
3. **O mercado de SRE está aquecido** e a cauda longa sugere que contratar na média pode ser difícil.

## Pendências registradas

- Substituir as camadas 2 e 3 pelos números reais da empresa antes de virar proposta.
- Confirmar o regime tributário aplicável (`T1`), que sozinho move o total em 22%.
