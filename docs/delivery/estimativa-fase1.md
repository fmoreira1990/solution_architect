# Estimativa da fase 1 — 30 dias

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** esforço, composição de time, custos, premissas e riscos para executar a **onda 30**. Apenas a fase 1 é estimada — §2.5.3 limita o compromisso orçado a ela.
**Requisitos cobertos:** `D-05`
**Fontes:** `docs/delivery/decomposicao-onda-30.md`, `docs/delivery/impacto-ia-no-desenvolvimento.md`, `docs/technical-context/constraints.md` (§7), `slice/`
**Data:** 2026-09-23

---

## Método, antes do número

A estimativa é **por decomposição**, não por analogia nem por palpite calibrado:

```
1. Decompor até tarefas de 0,5 a 3 dias-pessoa   → 47 tarefas
2. Atribuir perfil por tarefa                     → o perfil SAI daqui
3. Somar por bloco e por perfil                   → 79 dias-pessoa, sem IA
4. Aplicar o ganho de IA bloco a bloco            → 63 dias-pessoa
5. Derivar time e prazo por perfil                → ver §2 e §3
6. Declarar premissas e faixa de confiança        → ver §5 e §6
```

**A composição do time é consequência do esforço, não premissa dele.** Declarar "squad de 5" antes de saber o que precisa ser feito produz um time que cabe no orçamento e não na tarefa.

Há uma âncora de calibração incomum: a fatia executável em `slice/` **já implementa** o núcleo de idempotência, outbox, snapshot, cotação e contract test, com 128 testes. Não estamos estimando algo nunca construído — estamos estimando **a distância entre a prova e a produção**, e essa distância está decomposta item a item.

---

## 1. Esforço

| Bloco | Sem IA | Com IA | Observação |
|---|---|---|---|
| Pré-requisitos (baseline, observabilidade, inventário) | 16 | 14,5 | **bloqueiam o gate**, não são paralelos |
| A — Idempotência | 11 | 7 | núcleo provado; falta identidade e normalização |
| B — Snapshot e cotação | 9,5 | 5,5 | falta cofre de chave e rotação |
| C — Outbox e publicação | 16 | 12 | inclui adequação de consumidores |
| D — Convivência e rollout | 11,5 | 9 | é o que `CTX-11` custa |
| Transversal (review, segurança, runbook, rollout, cerimônias) | 15 | 15 | omitir isto é como nasce estimativa otimista |
| **Total** | **79** | **63** | |

**A proposta é o cenário com IA.** A decomposição é medida sem IA porque é a base verificável; o ganho é aplicado depois, bloco a bloco, com a justificativa de cada percentual em [`impacto-ia-no-desenvolvimento.md`](impacto-ia-no-desenvolvimento.md). O transversal não ganha nada, de propósito.

---

## 2. Composição do time — derivada, não declarada

### O que a decomposição revelou

| Perfil | Sem IA | Com IA |
|---|---|---|
| Arquiteto de Soluções | 9,5 | 9,5 |
| Dev Sênior | 33 | 26 |
| Dev Pleno | 16 | 9 |
| SRE / DevOps | 20,5 | 18,5 |
| **Total** | **79** | **63** |

**SRE consome 26% do esforço sem IA** — mais que o dobro do arquiteto. Isso não foi planejado: saiu da soma. A causa é `CTX-11`: rollout progressivo com comparação a cada degrau, alertas de falha silenciosa e reversibilidade sem deploy são trabalho de **operação**, não de desenvolvimento.

**E é o perfil que a IA menos reduz: −10%.** Os degraus do rollout levam o tempo que levam. O ganho cai quase todo no código dos devs — o pleno perde quase metade do esforço.

Uma proposta que dimensionasse esta fase com 4 devs e "apoio de infra" erraria por aí — e erraria justamente na parte que sustenta o critério mais duro do gate: zero janela de indisponibilidade.

### O time proposto: um SRE

Com 18,5 d.p., o SRE ainda pediria uma pessoa e meia. Fecha em **uma** com dois ajustes:

1. **A instrumentação que mora no código vai para quem escreve o código.** `P1.3` (p95 por faixa de itens) e `A3.3` (métrica de `409` por divergência) passam ao Dev Sênior, que já faz `P1.1`, `P1.2` e `A3.1`. `P1.4` (consolidação do baseline) e `A11.1` (SLI de idade do outbox) passam ao Dev Pleno, que já faz o expurgo do outbox. São ~3,5 d.p. de métrica emitida pela aplicação.
2. **Code review e cerimônias dividem-se por um SRE, não por um e meio.** ~1 d.p. volta para os devs.

O SRE continua dono do que só ele faz: tracing, painel comparativo, alertas de divergência e de relay parado, rollback exercitado e rollout em degraus.

**É a IA que torna isso possível.** Sem ela, os dois sêniores já estão no limite — 33 d.p. levam 20,6 dias úteis — e não há para onde mover trabalho.

| Perfil | d.p. | Alocação | Pessoas | Termina em |
|---|---|---|---|---|
| **Arquiteto de Soluções** | 9,5 | 50% | 1, meio período | 19 dias úteis |
| **Dev Sênior** | 28 | 80% | 2 | 17,5 dias úteis |
| **Dev Pleno** | 11,5 | 80% | 1 | 14,5 dias úteis |
| **SRE / DevOps** | **14** | 70% | **1** | **20 dias úteis** |
| **Total** | **63** | | **5 pessoas** · 4,5 em tempo integral | |

*"Termina em" = d.p. ÷ (pessoas × alocação). A alocação desconta reuniões, suporte e troca de contexto; a do SRE é menor porque ele absorve incidente.*

**O arquiteto é parcial, e é correto que seja.** 9,5 dias em 20 úteis é meio período. As decisões estruturais já estão tomadas (7 ADRs); o que resta é normalização de contrato, negociação e revisão. Arquiteto em tempo integral nesta fase seria custo sem contrapartida.

---

## 3. Prazo

```
SRE        14   d.p. ÷ (1 × 70%)  =  20    dias úteis   ← define o prazo
Arquiteto   9,5 d.p. ÷ (1 × 50%)  =  19
Sênior     28   d.p. ÷ (2 × 80%)  =  17,5
Pleno      11,5 d.p. ÷ (1 × 80%)  ≈  14,5
```

**20 dias úteis ≈ 4 semanas. Cabe nos 30 dias corridos de `CTX-11`, que têm 21 dias úteis — com 1 dia de folga.**

O prazo é o do SRE, e isso é aceitável: o trabalho dele é o que *tem* de terminar por último, porque o rollout da semana 4 só começa com o código pronto. A folga dos devs nas semanas 3 e 4 vai para acompanhamento de rollout e correção em produção (`T4`).

**A IA vira time menor, não data mais cedo.** Mantendo 1,5 SRE, o prazo cairia para ~17,5 dias úteis — e não compraria nada: o gate G30 depende do inventário e da adequação de consumidores, que não aceleram. Uma pessoa a menos é ganho real; três dias antes de um gate que espera terceiros, não.

| Semana | Foco | Marco |
|---|---|---|
| 1 | Pré-requisitos P1–P3 + migrações aditivas (A1.1, A4.1, A7.1) | baseline publicado |
| 2 | Núcleo: idempotência, snapshot, cotação, outbox | caminho novo passando em homologação · **recalibração** |
| 3 | Observabilidade, feature flag, reconciliação, adequação de consumidores | flag pronta, consumidores avisados |
| 4 | Rollout 1% → 100%, com comparação a cada degrau | **gate G30** |

**O caminho crítico não é o código.** É `P1` (baseline) → `P3` (inventário) → `A9.2/A9.3` (adequação de consumidores). Esses três dependem de medição e de terceiros; os demais dependem só do time, e time se contrata.

---

## 4. Custos

### 4.1 Pessoas

O custo de pessoa depende de taxa por senioridade, que é **decisão comercial, não técnica**. A tabela entrega o insumo pronto:

| Perfil | d.p. | Taxa/dia *(faturada)* | Subtotal |
|---|---|---|---|
| Arquiteto de Soluções Sr | 9,5 | R$ 3.051 | R$ 28.985 |
| Dev Sênior | 28 | R$ 2.045 | R$ 57.260 |
| Dev Pleno | 11,5 | R$ 1.198 | R$ 13.777 |
| SRE / DevOps | 14 | R$ 1.668 | R$ 23.352 |
| **Total** | **63** | média R$ 1.958 | **R$ 123.374** |
| Contingência 15% | 9,5 | | R$ 18.506 |
| **Com contingência** | **72,5** | | **R$ 141.880** |
| Licenças de IA | | | US$ 100–350/mês |

Sem IA, o mesmo escopo custaria **R$ 149.832** — R$ 172.306 com contingência — e exigiria 1,5 SRE. A derivação está em [`taxas-de-mercado.md`](taxas-de-mercado.md).

As taxas vêm de **referência pública de mercado**, derivadas em quatro camadas explícitas — salário, encargos CLT, overhead e margem, e **tributos sobre o faturamento**. **Não são a estrutura de custo da empresa**: o comercial substitui cada camada pelos números reais, e o esforço em dias-pessoa não muda.

São valores **faturados**, no regime de **Lucro Presumido**: 19,53% do total são PIS, COFINS, ISS, IRPJ (com adicional) e CSLL. Do preço, 53,6% é custo carregado de pessoal, 19,5% tributos e 26,8% overhead e margem — proporções que não dependem do mix de perfis, porque cada camada é um fator aplicado igualmente a todos.

Duas camadas movem muito o total: a **tributária** — ISS a 2% em vez de 5% derruba o total para R$ 118.939, e o Simples Nacional exige recálculo, não ajuste — e o **fator comercial** de 1,5×, em que errar 0,2 move ~R$ 16 mil.

### 4.2 Infraestrutura — custo de *run*

Serviços nomeados, com tier e alternativa confrontada, em **[`servicos-aws.md`](../technical-context/servicos-aws.md)**. Resumo:

| Componente | Serviço | US$/mês |
|---|---|---|
| Store transacional | RDS PostgreSQL Multi-AZ, `db.m6g.large` | 480–620 |
| Cache do Catálogo | ElastiCache, 2 nós `cache.t4g.medium` | 90–160 |
| Computação | ECS Fargate, 4 tarefas | 90–220 |
| Broker | SNS + SQS FIFO | 25–60 |
| Borda | CloudFront + WAF, API Gateway HTTP + Cognito, ALB interno, Route 53 | 77–175 |
| Observabilidade | CloudWatch + X-Ray | 120–350 |
| Rede e apoio | NAT, Secrets, KMS, S3, ECR | 80–149 |
| **Subtotal — Pedidos** | | **US$ 962–1.734** |
| Catálogo — computação | ECS Fargate, 4→12 tarefas | 150–400 |
| Catálogo — store | RDS Multi-AZ + réplica de leitura | 700–900 |
| **Total — plataforma** | | **US$ 1.812–3.034** |

**Custo por pedido: menos de meio centavo** — US$ 0,000101 a 0,000169. A maior parte é **fixa** — Multi-AZ, NAT, control planes —, não por transação, o que atende `CTX-16`.

> **Pedidos e Catálogo já rodam na mesma infraestrutura e continuam nela.** Por isso a conta é uma só, e a onda 30 não tem esforço de migração: o trabalho dentro do Catálogo começa na onda 60.

> **Duas escolhas respondem por ~US$ 700/mês de economia:** SQS FIFO no lugar de Kafka gerenciado (~US$ 500) e RDS Multi-AZ no lugar de Aurora (~US$ 200). Nos dois casos a opção mais cara entregava capacidade que o dimensionamento não pede — `AV-08` aplicado a custo.

**O salto de custo é a onda 90, não a 30:** multi-região duplica quase toda a infraestrutura fixa (**+70 a 90%**). Precisa estar claro antes de aprovar as três ondas olhando só o número da primeira.

**Custo incremental da fase 1 é pequeno.** A onda 30 não muda a topologia — adiciona tabelas, um relay e observabilidade sobre infraestrutura que já existe. O salto de custo vem na **onda 90**, com multi-região e escala 10×.

### 4.3 O custo que `CTX-11` impõe

| Se houvesse janela de manutenção | Com "zero janela" |
|---|---|
| migração direta | migração aditiva + convivência |
| deploy único | feature flag + rollout em 4 degraus |
| rollback por restore | rollback por flag, exercitado em produção |
| — | observabilidade comparativa entre caminhos |
| | **+11,5 d.p. ≈ 15% do total**, medido sem IA |

Isso não é desperdício — é o preço de uma restrição que o cliente impôs, e precisa estar **visível na proposta**. Um concorrente que não a respeitar parecerá 15% mais barato entregando outra coisa.

---

## 5. Premissas

| # | Premissa | Se falsa |
|---|---|---|
| E1 | Ambiente de desenvolvimento e CI existem | +5 a 8 d.p. |
| E2 | Broker gerenciado disponível | +3 a 5 d.p. |
| E3 | Consumidores internos cooperam dentro da onda | **gate G30 não fecha** — é prazo, não esforço |
| E4 | Não há integrações no caminho de criação além do Catálogo | +~4 d.p. **por integração**, e cada uma reintroduz o `CTX-17` |
| E5 | O time conhece a stack de produção (`CTX-14` é `???`) | rampa não estimada: +10 a 20% |
| E6 | Migrações aditivas rodam sem janela na base atual | +5 d.p. se exigir migração online |
| E7 | SRE dedicado, com alocação efetiva de 70% | a 60%, o prazo vai para 23 dias úteis — **estoura os 30 corridos** |
| E8 | Fator de produção de 3,5× sobre o núcleo provado | é a premissa mais consequente do documento |
| E9 | Ganho de IA de ~20% se confirma | o SRE estoura primeiro — ver o gatilho em §6 |

---

## 6. Faixa de confiança

| Cenário | d.p. | Prazo | Quando acontece |
|---|---|---|---|
| **Otimista** | 50 (−20%) | 16 dias úteis | Consumidores cooperam rápido; normalização canônica sem surpresa; ambiente pronto |
| **Provável** | **63** | **20 dias úteis** | Cenário das premissas E1–E9 |
| **Pessimista** | 88 (+40%) | 28 dias úteis | A3 dobra; consumidores externos lentos; rampa de stack; migração online necessária |

**O pessimista não cabe nos 30 dias corridos**, que têm 21 dias úteis. E não cabe com nenhum time: a +40%, o SRE vai a 28 dias úteis e os sêniores a 24,5. Reforçar resolve um gargalo e expõe o outro.

Por isso a **recalibração da semana 2** é marco, não formalidade: ela decide cedo, com dado real, entre reforçar o time e renegociar a data do gate — enquanto as duas opções ainda existem.

### Contingência

**Reserva de 15% (9,5 d.p., R$ 18.506), como linha separada.** Embutir contingência no esforço das tarefas esconde a incerteza e corrompe a base para a próxima estimativa. Declarada, ela pode ser negociada ou devolvida.

**Com um SRE no limite, a contingência tem destino previsto.** Se a recalibração mostrar o SRE acima do plano, entra **meio SRE nas semanas 3 e 4** — ~5 dias de trabalho, ≈ R$ 8.300, menos da metade da reserva. O meio SRE que o cenário sem IA pagaria sempre vira gatilho, pago só se preciso.

---

## 7. Riscos da estimativa

| # | Risco | Impacto | Resposta |
|---|---|---|---|
| R1 | **A9.2/A9.3 dependem de terceiros** | Alto — é prazo, não esforço | Começar o inventário (`P3`) no dia 1. Mais gente não acelera |
| R2 | **A3 (normalização canônica) dobrar** | Médio — +2 d.p. | Especificar na OpenAPI antes de implementar |
| R3 | **SRE único, sem folga** | Alto — define o prazo; férias ou doença param o rollout | Dedicação exclusiva confirmada **antes** de assumir a data; runbooks (`T3`) e sêniores no acompanhamento de rollout (`T4`) cobrem ausência curta; ausência longa aciona o gatilho de §6 |
| R4 | **Fator de produção 3,5× subestimado** | Alto — erro sistemático em tudo | Recalibrar ao fim da semana 2, com dado real |
| R5 | **`CTX-14` desconhecido** | Médio | Se o time não conhecer a stack, somar rampa explícita |
| R6 | **Integração no caminho de criação não mapeada** | Alto | `V1` é a primeira pergunta ao Client Face |
| R7 | **Ganho de IA abaixo do previsto** | Alto — o SRE estoura primeiro | Recalibrar na semana 2; gatilho de meio SRE, pago pela contingência |

---

## 8. O que **não** está nesta estimativa

- **Ondas 60 e 90** — §2.5.3 limita o compromisso à fase 1. Estimá-las agora daria falsa precisão sobre escopo que o gate G30 pode redefinir.
- **Licenças de software de runtime** — nenhuma identificada; a arquitetura usa serviços gerenciados AWS. As licenças de **ferramenta de desenvolvimento assistido por IA** estão em §4.1 e detalhadas em [`impacto-ia-no-desenvolvimento.md`](impacto-ia-no-desenvolvimento.md).
- **Custo das ondas 60 e 90** — dimensionado em ordem de grandeza em `servicos-aws.md`, não orçado.
- **Treinamento e rampa** — depende de `CTX-14`, que é `???`.
- **Contingência de escopo** — a reserva de 15% cobre variação de esforço, não escopo novo.

## Pendências registradas

- As taxas por senioridade são referência de mercado; o comercial substitui pelas da empresa antes de virar proposta.
- `CTX-14` (conhecimento do time) permanece `???` e afeta E5.
- O fator de produção de 3,5× e o ganho de IA devem ser recalibrados ao fim da semana 2 — e a recalibração vale mais que a estimativa inicial.
