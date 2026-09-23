# Taxas de mercado por senioridade

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** referência de mercado para converter esforço em preço. **Não é a estrutura de custo da empresa** — é um modelo transparente, camada por camada, para que o comercial substitua cada uma pelos números reais.
**Requisitos cobertos:** `D-05`
**Fontes:** Glassdoor Brasil (junho de 2026), Cálculo Jurídico (encargos CLT 2026), Contabilizei e Contabilidade.com (Lucro Presumido 2026), `docs/delivery/estimativa-fase1.md`
**Data:** 2026-09-24 *(revisado: camada tributária acrescentada)*

---

## O modelo, em camadas substituíveis

Um número fechado de taxa/hora esconde as premissas que o produziram. Aqui cada camada é explícita, e **trocar uma não invalida as outras**:

```
salário de mercado
   × 1,8              encargos e provisões CLT        → custo para a empresa
   ÷ 21               dias úteis por mês              → custo por dia-pessoa
   × 1,5              overhead + margem + ociosidade  → preço líquido
   ÷ (1 − 19,53%)     tributos sobre o faturamento    → PREÇO FATURADO
```

**O esforço em dias-pessoa não muda em nenhuma hipótese** — é isso que torna a estimativa reutilizável quando as premissas comerciais mudarem.

> ### Correção registrada
>
> Uma versão anterior deste documento **omitia a quarta camada**. O resultado era um preço de R$ 120.576 que parecia ter 33% de margem e, na prática, tinha **13,8%** — porque os tributos sobre faturamento saíam dela, e o overhead ainda teria de sair do que restasse.
>
> Não é ajuste de arredondamento: é a diferença entre uma proposta com margem e uma proposta que financia o cliente.

---

## Camada 1 — Salário de mercado

Glassdoor Brasil, junho de 2026. Média nacional; São Paulo fica acima.

| Perfil | Média | Faixa (p25–p75) |
|---|---|---|
| **Arquiteto de Soluções Sênior** | **R$ 19.097** | R$ 9.833 – 18.854 *(cargo geral: média R$ 14.667)* |
| **Desenvolvedor Sênior** | **R$ 12.800** | R$ 10.667 – 16.083 |
| **Desenvolvedor Pleno** | **R$ 7.500** | R$ 5.560 – 8.242 *(varia por stack e praça)* |
| **SRE / DevOps** | **R$ 10.438** | R$ 8.191 – 16.250 *(p90: R$ 20.750)* |

> A faixa do arquiteto é larga porque o título cobre desde arquiteto de aplicação até arquiteto corporativo — a estimativa usa a média do **sênior**, que é o perfil que a onda 30 exige. A do SRE tem cauda longa: o p90 supera a média do dev sênior, refletindo escassez.

## Camada 2 — Encargos e provisões CLT

| Componente | % sobre o salário |
|---|---|
| INSS patronal (20% + RAT + terceiros) | ~28,8% |
| FGTS | 8% |
| 13º salário (provisão) | 8,33% |
| Férias + 1/3 (provisão) | 11,1% |
| FGTS e INSS sobre provisões | ~7,3% |
| **Fator** | **≈ 1,8×** |

## Camada 3 — Overhead, margem e ociosidade

Fator de **1,5×** sobre o custo carregado. Cobre gestão e coordenação, estrutura, comercial e pré-venda, treinamento, banco de horas e ociosidade entre alocações, e a margem operacional.

> É a camada **menos ancorada** do documento — varia por contrato, porte e modelo de alocação.

## Camada 4 — Tributos sobre o faturamento

Regime de **Lucro Presumido**, atividade de prestação de serviços.

| Tributo | Base | Alíquota | % do faturamento |
|---|---|---|---|
| PIS | faturamento | 0,65% | **0,65%** |
| COFINS | faturamento | 3,00% | **3,00%** |
| ISS | faturamento | 2% a 5% *(município e serviço)* | **5,00%** ¹ |
| IRPJ | presunção de **32%** | 15% | **4,80%** |
| IRPJ — adicional | presunção de 32% | 10% sobre o excedente ² | **3,20%** |
| CSLL | presunção de **32%** | 9% | **2,88%** |
| | | **Total** | **19,53%** |

¹ **5% é o teto, e é a alíquota adotada** — decisão deliberada de orçar pelo pior caso. Serviços de TI são enquadrados entre 2% e 3% em vários municípios; com ISS a 2% a carga cai para **16,53%**, e o desvio joga a favor da proposta em vez de contra.

² O adicional incide sobre o lucro presumido que exceder R$ 60 mil no trimestre. Para uma consultoria já acima desse patamar, **a alíquota marginal de um projeto novo inclui o adicional integralmente** — que é a hipótese usada aqui.

### Por que o gross-up, e não a soma

Tributo sobre faturamento incide sobre o **preço final**, não sobre o custo. Somar 19,53% ao preço líquido subestima: o correto é dividir por `(1 − 0,1953)`, o que equivale a multiplicar por **1,2427**.

---

## Taxas resultantes

| Perfil | Salário | Custo CLT | Custo/dia | Preço líquido | **Preço faturado/dia** | **/hora** |
|---|---|---|---|---|---|---|
| Arquiteto de Soluções Sr | R$ 19.097 | R$ 34.375 | R$ 1.637 | R$ 2.455 | **R$ 3.051** | **R$ 381** |
| Desenvolvedor Sênior | R$ 12.800 | R$ 23.040 | R$ 1.097 | R$ 1.646 | **R$ 2.045** | **R$ 256** |
| SRE / DevOps | R$ 10.438 | R$ 18.788 | R$ 895 | R$ 1.342 | **R$ 1.668** | **R$ 209** |
| Desenvolvedor Pleno | R$ 7.500 | R$ 13.500 | R$ 643 | R$ 964 | **R$ 1.198** | **R$ 150** |

*Dia-pessoa de 8 horas, 21 dias úteis por mês.*

---

## Preço da fase 1

Aplicando às 79 dias-pessoa da [decomposição](decomposicao-onda-30.md):

| Perfil | d.p. | Preço/dia | Subtotal |
|---|---|---|---|
| Arquiteto de Soluções Sr | 9,5 | R$ 3.051 | R$ 28.985 |
| Desenvolvedor Sênior | 33 | R$ 2.045 | R$ 67.485 |
| SRE / DevOps | 20,5 | R$ 1.668 | R$ 34.194 |
| Desenvolvedor Pleno | 16 | R$ 1.198 | R$ 19.168 |
| **Total — 79 d.p.** | | | **R$ 149.832** |
| Contingência 15% (12 d.p.) | | | R$ 22.475 |
| **Total com contingência** | | | **R$ 172.306** |

**Preço médio ponderado: R$ 1.897 por dia-pessoa.**

### Onde vai cada real

| Camada | Valor | % do faturado |
|---|---|---|
| Salário bruto | R$ 44.658 | 29,8% |
| Encargos e provisões CLT | R$ 35.726 | 23,8% |
| *Subtotal: custo carregado* | *R$ 80.384* | *53,6%* |
| **Tributos sobre faturamento** | **R$ 29.262** | **19,5%** |
| Overhead + margem | R$ 40.186 | 26,8% |
| **Total faturado** | **R$ 149.832** | 100% |

**Encargos e tributos somados são 43,4% do preço** — mais que o salário bruto. É o dado que costuma surpreender em discussão comercial. Como cada camada é independente, dá para ver quanto cada premissa move o total:

| Variação | Efeito no total |
|---|---|
| ISS a 2% em vez de 5% | **R$ 144.446** *(−3,6%)* |
| Simples Nacional | encargos caem e o regime substitui os tributos da camada 4 — **exige recálculo, não ajuste** |
| Fator comercial a 1,3× em vez de 1,5× | ≈ **R$ 129.854** *(−13%)* |

> **O que NÃO está no preço:** infraestrutura AWS, licenças de ferramenta, deslocamento e custos de ambiente do cliente. Orçados em separado, de propósito — misturá-los na taxa/hora esconde o que é recorrente e o que é do projeto. Se forem repassados com faturamento próprio, também sofrem o gross-up da camada 4.

### Infraestrutura, no mesmo período

| | |
|---|---|
| AWS — escopo Pedidos | US$ 925–1.649/mês → R$ 4.995–8.905/mês |
| AWS — plataforma completa *(`V11`)* | US$ 1.775–2.949/mês → **R$ 9.585–15.925/mês** |

*Câmbio de R$ 5,40/US$, premissa declarada. Normalmente contratada direto pelo cliente ou repassada a custo — neste caso não sofre o gross-up.*

### Total da fase 1

| | |
|---|---|
| Serviços, com contingência | R$ 172.306 |
| Infraestrutura *(plataforma completa)* | R$ 9.585–15.925 |
| **Total** | **≈ R$ 181.900 – 188.200** |

---

## Cenário com desenvolvimento assistido por IA

| Perfil | d.p. | Subtotal |
|---|---|---|
| Arquiteto de Soluções Sr | 9,5 | R$ 28.985 |
| Desenvolvedor Sênior | 26 | R$ 53.170 |
| SRE / DevOps | 18,5 | R$ 30.858 |
| Desenvolvedor Pleno | 9 | R$ 10.782 |
| **Total — 63 d.p.** | | **R$ 123.795** |
| Licenças de IA | | R$ 490–1.730/mês |
| **Total** | | **≈ R$ 124.300 – 125.500** |

### A economia em preço é **menor** que a economia em esforço

| | Sem IA | Com IA | Variação |
|---|---|---|---|
| Esforço | 79 d.p. | 63 d.p. | **−20,3%** |
| Preço | R$ 149.832 | R$ 123.795 | **−17,4%** |

**A diferença de quase 3 pontos não é arredondamento.** A IA reduz proporcionalmente mais o trabalho de **pleno** (−44%), o perfil mais barato, e **não reduz nada** do arquiteto, o mais caro.

> Quanto mais o time se concentra em perfis sêniores, **menor o retorno financeiro de ferramenta de produtividade** — ainda que o ganho de prazo permaneça. O preço médio ponderado sobe de R$ 1.897 para **R$ 1.965** por dia-pessoa: time menor e mais caro por cabeça.

---

## Premissas

| # | Premissa | Se falsa |
|---|---|---|
| T1 | Regime de **Lucro Presumido** — ✅ **decidido** | Simples Nacional muda as camadas 2 **e** 4 ao mesmo tempo — exige recálculo, não ajuste de fator |
| T2 | ISS a **5%**, o teto — ✅ **decidido**, hipótese conservadora | Se o município enquadrar TI em 2–3%, o total cai até 3,6% — a favor da proposta, nunca contra |
| T3 | Adicional de IRPJ **aplicável** | Empresa abaixo de R$ 60 mil de lucro presumido trimestral não o recolhe — total cai para 16,33% |
| T4 | Fator comercial de **1,5×** | Camada menos ancorada; a 1,3× o total cai 13% |
| T5 | Salários na média nacional | São Paulo acima; contratação remota em outras praças, abaixo |
| T6 | 21 dias úteis, 8 horas, alocação CLT | PJ muda completamente a camada 2 |
| T7 | Câmbio de R$ 5,40/US$ | Afeta só a infraestrutura |

---

## O que este documento **não** é

**Não é a estrutura de custo nem a política de preço da empresa.** É referência pública de mercado, útil para ordem de grandeza e para dar forma à proposta.

**Não substitui a decisão comercial.** Preço envolve relacionamento com a conta, volume, prazo contratual e posicionamento competitivo — nenhum deles é decisão de arquitetura.

**O que o arquiteto entrega é o esforço por perfil.** As 79 dias-pessoa da decomposição sustentam discussão técnica; as camadas acima apenas as traduzem para a linguagem de quem decide.

## Riscos

1. **`T1` é o maior risco.** Trocar o regime tributário não é mexer num fator — muda duas camadas simultaneamente, com sinais opostos, e exige refazer a conta.
2. **`T4` é o menos ancorado.** Errar 0,2 no fator comercial move ~R$ 20 mil.
3. **Dados salariais têm dispersão alta** — faixas p25–p75 chegam a variar 2×. A média esconde isso.
4. **O mercado de SRE está aquecido**, e a cauda longa sugere que contratar na média pode não ser realista.

## Pendências registradas

- ~~Confirmar o regime tributário e a alíquota de ISS.~~ **Decidido:** Lucro Presumido e ISS a 5%, o teto. A escolha do teto é deliberada — se o município enquadrar TI em faixa menor, o desvio é a favor da proposta.
- Substituir as camadas 2, 3 e 4 pelos números reais da empresa antes de virar proposta.
