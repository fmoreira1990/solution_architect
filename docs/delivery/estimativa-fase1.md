# Estimativa da fase 1 — 30 dias

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** esforço, composição de time, custos, premissas e riscos para executar a **onda 30**. Apenas a fase 1 é estimada — §2.5.3 limita o compromisso orçado a ela.
**Requisitos cobertos:** `D-05`
**Fontes:** `docs/delivery/decomposicao-onda-30.md`, `docs/technical-context/constraints.md` (§7), `slice/`
**Data:** 2026-09-23

---

## Método, antes do número

A estimativa é **por decomposição**, não por analogia nem por palpite calibrado:

```
1. Decompor até tarefas de 0,5 a 3 dias-pessoa   → 47 tarefas
2. Atribuir perfil por tarefa                     → o perfil SAI daqui
3. Somar por bloco e por perfil                   → 79 dias-pessoa
4. Derivar prazo a partir de alocação realista    → ver §2
5. Declarar premissas e faixa de confiança        → ver §5 e §6
```

**A composição do time é consequência do esforço, não premissa dele.** Declarar "squad de 5" antes de saber o que precisa ser feito produz um time que cabe no orçamento e não na tarefa.

Há uma âncora de calibração incomum: a fatia executável em `slice/` **já implementa** o núcleo de idempotência, outbox, snapshot, cotação e contract test, com 127 testes. Não estamos estimando algo nunca construído — estamos estimando **a distância entre a prova e a produção**, e essa distância está decomposta item a item.

---

## 1. Esforço

| Bloco | d.p. | % | Observação |
|---|---|---|---|
| Pré-requisitos (baseline, observabilidade, inventário) | 16 | 20% | **bloqueiam o gate**, não são paralelos |
| A — Idempotência | 11 | 14% | núcleo provado; falta identidade e normalização |
| B — Snapshot e cotação | 9,5 | 12% | falta cofre de chave e rotação |
| C — Outbox e publicação | 16 | 20% | inclui adequação de consumidores |
| D — Convivência e rollout | 11,5 | 15% | é o que `CTX-11` custa |
| Transversal (review, segurança, runbook, rollout, cerimônias) | 15 | 19% | omitir isto é como nasce estimativa otimista |
| **Total** | **79** | 100% | |

---

## 2. Composição do time — derivada, não declarada

| Perfil | d.p. | Alocação | Pessoas | Por que este perfil |
|---|---|---|---|---|
| **Arquiteto de Soluções** | 9,5 | 30% | 1 | Normalização de contrato, negociação com consumidores externos, revisão de segurança. Não é papel de tempo integral nesta fase |
| **Dev Sênior** | 33 | 80% | 2 | Transação única, relay, rotação de chave HMAC, feature flag — tudo que **erra caro** e cujo erro só aparece em produção |
| **Dev Pleno** | 16 | 80% | 1 | Expurgo, backfill, reconciliação, adequação de consumidores internos |
| **SRE / DevOps** | 20,5 | 70% | 1,5 | Observabilidade, alertas, rollout progressivo, runbooks |
| **Total** | **79** | | **5,5** | |

### O que a decomposição revelou

**SRE consome 26% do esforço.** Mais que o dobro do arquiteto e quase igual a um dev sênior. Isso não foi planejado — saiu da soma. A causa é `CTX-11`: rollout progressivo com comparação a cada degrau, alertas de falha silenciosa e reversibilidade sem deploy são trabalho de **operação**, não de desenvolvimento.

Uma proposta que dimensionasse esta fase com 4 devs e "apoio de infra" erraria por aí — e erraria justamente na parte que sustenta o critério mais duro do gate: zero janela de indisponibilidade.

**O arquiteto é parcial, e é correto que seja.** 9,5 dias em 30 é meio período nominal. As decisões estruturais já estão tomadas (7 ADRs); o que resta é normalização de contrato, negociação e revisão. Arquiteto em tempo integral nesta fase seria custo sem contrapartida.

---

## 3. Prazo

```
79 d.p. ÷ 5,5 pessoas ≈ 14,4 dias-pessoa/pessoa
                      ÷ alocação média de 72%
                      ≈ 20 dias úteis ≈ 4 semanas
```

**Cabe nos 30 dias corridos de `CTX-11` — com folga estreita.**

| Semana | Foco | Marco |
|---|---|---|
| 1 | Pré-requisitos P1–P3 + migrações aditivas (A1.1, A4.1, A7.1) | baseline publicado |
| 2 | Núcleo: idempotência, snapshot, cotação, outbox | caminho novo passando em homologação |
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
| Dev Sênior | 33 | R$ 2.045 | R$ 67.485 |
| Dev Pleno | 16 | R$ 1.198 | R$ 19.168 |
| SRE / DevOps | 20,5 | R$ 1.668 | R$ 34.194 |
| **Total** | **79** | média R$ 1.897 | **R$ 149.832** |
| Contingência 15% | 12 | | R$ 22.475 |
| **Com contingência** | **91** | | **R$ 172.306** |

As taxas vêm de **referência pública de mercado**, derivadas em quatro camadas explícitas — salário, encargos CLT, overhead e margem, e **tributos sobre o faturamento** — em [`taxas-de-mercado.md`](taxas-de-mercado.md). **Não são a estrutura de custo da empresa**: o comercial substitui cada camada pelos números reais, e o esforço em dias-pessoa não muda.

São valores **faturados**, no regime de **Lucro Presumido**: 19,53% do total são PIS, COFINS, ISS, IRPJ (com adicional) e CSLL. Do preço acima, R$ 80.384 são custo carregado de pessoal, R$ 29.262 são tributos e R$ 40.186 são overhead e margem.

Duas camadas movem muito o total: a **tributária** — ISS a 2% em vez de 5% derruba o total para R$ 144.446, e o Simples Nacional exige recálculo, não ajuste — e o **fator comercial** de 1,5×, em que errar 0,2 move ~R$ 20 mil.

### 4.2 Infraestrutura — custo de *run*

Serviços nomeados, com tier e alternativa confrontada, em **[`servicos-aws.md`](../technical-context/servicos-aws.md)**. Resumo:

| Componente | Serviço | US$/mês |
|---|---|---|
| Store transacional | RDS PostgreSQL Multi-AZ, `db.m6g.large` | 480–620 |
| Cache do Catálogo | ElastiCache, 2 nós `cache.t4g.medium` | 90–160 |
| Computação | ECS Fargate, 4 tarefas | 90–220 |
| Broker | SNS + SQS FIFO | 25–60 |
| Borda | API Gateway HTTP + Cognito | 40–90 |
| Observabilidade | CloudWatch + X-Ray | 120–350 |
| Rede e apoio | NAT, Secrets, KMS, S3, ECR | 80–149 |
| **Subtotal — Pedidos** | | **US$ 925–1.649** |
| Catálogo — computação | ECS Fargate, 4→12 tarefas | 150–400 |
| Catálogo — store | RDS Multi-AZ + réplica de leitura | 700–900 |
| **Total — plataforma completa** | | **US$ 1.775–2.949** |

**Custo por pedido: menos de meio centavo** — US$ 0,000051 a 0,000092 no escopo Pedidos, US$ 0,000099 a 0,000164 na plataforma completa. A maior parte é **fixa** — Multi-AZ, NAT, control planes —, não por transação, o que atende `CTX-16`.

> **`V11` decide qual total vale.** O enunciado nomeia *"Pedidos e Catálogo"*, e a onda 60 mexe no Catálogo — por isso o número levado à proposta é o da plataforma completa. Se o cliente seguir hospedando o Catálogo, cai para US$ 925–1.649. **A hospedagem do Catálogo não está nas 79 dias-pessoa**: se entrar no escopo, muda custo e esforço.

> **Uma versão anterior deste documento projetava US$ 1.700–3.700/mês** com componentes genéricos — e chegou perto do escopo completo **pelo motivo errado**: era larga o bastante para acertar por acidente. O que sobrevive da análise é o mérito de duas escolhas, SQS no lugar de Kafka gerenciado (~US$ 500/mês) e RDS no lugar de Aurora (~US$ 200/mês), em que a opção mais cara entregava capacidade que o dimensionamento não pede.

**O salto de custo é a onda 90, não a 30:** multi-região duplica quase toda a infraestrutura fixa (**+70 a 90%**). Precisa estar claro antes de aprovar as três ondas olhando só o número da primeira.

**Custo incremental da fase 1 é pequeno.** A onda 30 não muda a topologia — adiciona tabelas, um relay e observabilidade sobre infraestrutura que já existe. O salto de custo vem na **onda 90**, com multi-região e escala 10×.

### 4.3 O custo que `CTX-11` impõe

| Se houvesse janela de manutenção | Com "zero janela" |
|---|---|
| migração direta | migração aditiva + convivência |
| deploy único | feature flag + rollout em 4 degraus |
| rollback por restore | rollback por flag, exercitado em produção |
| — | observabilidade comparativa entre caminhos |
| | **+11,5 d.p. ≈ 15% do total** |

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
| E7 | Alocação média efetiva de 72% | a 50%, o prazo vai para 29 dias úteis — **estoura os 30 corridos** |
| E8 | Fator de produção de 3,5× sobre o núcleo provado | é a premissa mais consequente do documento |

---

## 6. Faixa de confiança

| Cenário | d.p. | Prazo | Quando acontece |
|---|---|---|---|
| **Otimista** | 63 (−20%) | 16 dias úteis | Consumidores cooperam rápido; normalização canônica sem surpresa; ambiente pronto |
| **Provável** | **79** | **20 dias úteis** | Cenário das premissas E1–E8 |
| **Pessimista** | 111 (+40%) | 28 dias úteis | A3 dobra; consumidores externos lentos; rampa de stack; migração online necessária |

**O pessimista ainda cabe em 30 dias corridos — por pouco.** É o que torna o prazo viável e apertado ao mesmo tempo, e o que justifica tratar `P1` e `P3` como caminho crítico desde o primeiro dia.

### Contingência

**Reserva de 15% (12 d.p.), como linha separada.** Embutir contingência no esforço das tarefas esconde a incerteza e corrompe a base para a próxima estimativa. Declarada, ela pode ser negociada ou devolvida.

Total com contingência: **91 dias-pessoa**.

### Cenário alternativo: desenvolvimento assistido por IA

| | Conservador *(este documento)* | Com IA |
|---|---|---|
| Esforço | 79 d.p. | **63 d.p.** (−22%) |
| Time | 5,5 pessoas | **4,5 pessoas** |
| Prazo | 20 dias úteis | **16 dias úteis** (−20%) |
| Licenças | — | US$ 90–320/mês |
| **Preço de pessoas** | R$ 149.832 | **R$ 123.795** (−17,4%) |
| *com contingência de 15%* | *R$ 172.306* | *R$ 142.364* |

**O prazo cai menos que o esforço**, porque o caminho crítico — baseline, inventário de consumidores e adequação de terceiros — não acelera com IA.

E o **transversal permanece em 15 d.p., inegociável**: revisão de código assistido por IA não é mais rápida, é diferente. Análise completa, com a evidência deste próprio repositório, em [`impacto-ia-no-desenvolvimento.md`](impacto-ia-no-desenvolvimento.md).

---

## 7. Riscos da estimativa

| # | Risco | Impacto | Resposta |
|---|---|---|---|
| R1 | **A9.2/A9.3 dependem de terceiros** | Alto — é prazo, não esforço | Começar o inventário (`P3`) no dia 1. Mais gente não acelera |
| R2 | **A3 (normalização canônica) dobrar** | Médio — +2 d.p. | Especificar na OpenAPI antes de implementar |
| R3 | **Alocação real abaixo de 72%** | Alto — E7 estoura o prazo | Confirmar dedicação **antes** de assumir a data |
| R4 | **Fator de produção 3,5× subestimado** | Alto — erro sistemático em tudo | Recalibrar ao fim da semana 2, com dado real |
| R5 | **`CTX-14` desconhecido** | Médio | Se o time não conhecer a stack, somar rampa explícita |
| R6 | **Integração no caminho de criação não mapeada** | Alto | `V1` é a primeira pergunta ao Client Face |

---

## 8. O que **não** está nesta estimativa

- **Ondas 60 e 90** — §2.5.3 limita o compromisso à fase 1. Estimá-las agora daria falsa precisão sobre escopo que o gate G30 pode redefinir.
- **Custo de pessoa em moeda** — insumo pronto, preço é comercial.
- **Licenças de software** — nenhuma de runtime ou banco identificada; a arquitetura usa serviços gerenciados AWS. Licenças de **ferramenta de desenvolvimento assistido por IA** estão em [`impacto-ia-no-desenvolvimento.md`](impacto-ia-no-desenvolvimento.md), no cenário alternativo.
- **Custo das ondas 60 e 90** — dimensionado em ordem de grandeza em `servicos-aws.md`, não orçado.
- **Treinamento e rampa** — depende de `CTX-14`, que é `???`.
- **Contingência de escopo** — a reserva de 15% cobre variação de esforço, não escopo novo.

## Pendências registradas

- A taxa por senioridade precisa ser preenchida pelo comercial para fechar o custo total.
- `CTX-14` (conhecimento do time) permanece `???` e afeta E5.
- O fator de produção de 3,5× deve ser recalibrado ao fim da semana 2 — e a recalibração vale mais que a estimativa inicial.
