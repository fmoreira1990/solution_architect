# Constraints — Plataforma de Pedidos e Catálogo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** as restrições que limitam a solução, com número ou critério verificável. Inclui o dimensionamento derivado delas. Nenhuma camada da arquitetura pode existir sem um `CTX` desta lista que a justifique (regra Q11).
**Fontes:** `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf` (§2.2, §2.2.1), `docs/prd/pedidos-catalogo.md`, `docs/business-context/jornada.md`
**Data:** 2026-09-22

---

## 1. Performance e escala

| ID | Restrição | Número verificável | Origem | Consequência arquitetural |
|---|---|---|---|---|
| CTX-02 | Crescimento de tráfego | **10×** o volume atual em 90 dias | §2.2.1 | Autoscaling, eliminação do N+1, cache |
| CTX-04 | Latência de criação de pedido | **p95 ≤ 500 ms** | §2.2.1 | Orçamento por hop (§5); sem dependência síncrona evitável |
| CTX-05 | Acoplamento síncrono com o Catálogo | **9 chamadas** por pedido de 8 itens (1 + N) | §2.2.1 | Resolução em lote e/ou snapshot |
| PR-01 | Volumetria (premissa declarada) | **60k pedidos/dia hoje → 600k/dia no alvo** | premissa | Base de todo o dimensionamento |
| PR-02 | Tamanho do pedido (premissa declarada) | **8 itens em média, 15 no p95** | premissa | Define o peso do N+1 |

## 2. Disponibilidade e resiliência

| ID | Restrição | Número verificável | Origem | Consequência arquitetural |
|---|---|---|---|---|
| CTX-03 | Disponibilidade mensal | **99,9%** → error budget de **43 min/mês** | §2.2.1 | Multi-AZ, degradação controlada |
| CTX-12 | Consumidores atuais não podem ser interrompidos | **zero** interrupção durante a evolução | §2.2 | Convivência de versões |
| CTX-11 | Primeira melhoria em produção | **30 dias, com zero janela de indisponibilidade** | §2.2.1 | Feature flag, rollout progressivo, rollback sem deploy |

## 3. Equipe

| ID | Restrição | Número verificável | Origem | Consequência arquitetural |
|---|---|---|---|---|
| CTX-13 | Tamanho e senioridade do time | **`???`** | não informado | **Derivado, não declarado:** o esforço por tarefa em `/estimativa` determina o perfil, e não o contrário |
| CTX-14 | Conhecimento do time na stack-alvo — **.NET 10** (`ADR-0008`) | **`???`** | não informado | Afeta a rampa na estimativa (`E5`). A stack foi escolhida por mérito técnico; o conhecimento do time continua não declarado |

O desafio não informa nenhuma das duas. São a premissa mais consequente ainda em aberto: `D-05` exige composição de time e esforço por senioridade, e nenhum dos dois é derivável de §2.2.1. Serão declarados como premissa em `/estimativa`, com o efeito de cada uma explicitado caso seja falsa.

## 4. Orçamento

| ID | Restrição | Número verificável | Origem | Consequência arquitetural |
|---|---|---|---|---|
| CTX-15 | Custo de infraestrutura | **`???`** — sem teto informado | não informado | Impede validar a perna (e) da hipótese do PRD |
| CTX-16 | Custo por pedido não cresce proporcionalmente ao volume | critério relativo, sem baseline | `docs/prd` §2(e) | Favorece cache e lote sobre escala horizontal bruta |

Sem teto de custo declarado, a decisão arquitetural fica sem uma das cinco dimensões do §2.1. Registrado como risco aberto nº 2.

## 5. Regulação

| ID | Restrição | Critério verificável | Origem | Consequência arquitetural |
|---|---|---|---|---|
| CTX-09a | LGPD — dados pessoais de clientes | minimização, base legal, retenção definida | §2.2.1 | Classificação de PII, criptografia, expurgo |
| CTX-09b | Regime de dados do segundo país | **EUA: sem exigência de residência.** Mosaico estadual (CCPA/CPRA e congêneres) + opt-out de venda/compartilhamento | §2.2.1 + `PR-03` | Segregação por **domicílio do titular**, não por território |
| CTX-09c | Transferência internacional BR → EUA | LGPD art. 33: exige instrumento jurídico (cláusulas-padrão da ANPD ou equivalente) | derivado de `PR-03` | Minimizar dado brasileiro que atravessa |
| CTX-09d | Direito de opt-out de venda/compartilhamento | Preferência do titular precisa **propagar** a todos os consumidores de dado | CCPA/CPRA | Serviço de preferências; sinal honrado em toda a cadeia |
| CTX-06 | Auditabilidade de preço | provar **qual preço o cliente viu** no momento da compra | §2.2.1 | Snapshot imutável no item do pedido |
| PR-03 | Qual é o segundo país | **Estados Unidos** | ✅ decidido | Destrava a `ADR-0006`; muda o regime de residência para mosaico estadual |

## 6. Prazo e compatibilidade

| ID | Restrição | Número verificável | Origem | Consequência arquitetural |
|---|---|---|---|---|
| CTX-10 | Compatibilidade dos contratos atuais | **≥ 6 meses** | §2.2.1 | Versionamento aditivo, expand-and-contract |
| CTX-01 | Novos canais e geografia | app móvel + marketplace + 2º país em **90 dias** | §2.2 | API pública, BFF multi-canal, multi-região |
| CTX-07 | Integridade da criação e da publicação | **zero** pedido duplicado com a mesma chave; **zero** evento perdido | §2.2.1 | `Idempotency-Key` + outbox transacional |
| CTX-08 | Demanda dos parceiros | API pública versionada + notificação assíncrona de status | §2.2.1 | OpenAPI + AsyncAPI, webhook assinado |

---

## 7. Dimensionamento derivado (F0.5)

Premissas de distribuição: **60% do volume em 8 horas comerciais**, **pico de 3×** sobre a média comercial.

### 7.1 Taxa de requisição

| Medida | Hoje (60k/dia) | Alvo (600k/dia) |
|---|---|---|
| Média comercial | 1,25 pedidos/s | **12,5 pedidos/s** |
| Pico (3×) | 3,75 pedidos/s | **37,5 pedidos/s** |
| Carga no Catálogo **com N+1** (8 itens) | ~34 req/s | **~338 req/s** |
| Carga no Catálogo **com N+1** (p95, 15 itens) | ~60 req/s | **~600 req/s** |
| Carga no Catálogo **com lote** (2 chamadas) | ~7,5 req/s | **~75 req/s** — redução de **78%** |

O N+1 multiplica **duas vezes**: por item e por pedido concorrente. O Catálogo recebe ~27× mais requisições do que Pedidos — ele satura antes, e derruba a criação junto se for dependência síncrona.

### 7.2 Orçamento de latência do caminho crítico (`CTX-04`: 500 ms)

| Etapa de `POST /orders` | Orçamento | % |
|---|---|---|
| Autenticação e autorização na borda | 20 ms | 4% |
| Verificação de idempotência (lookup da chave) | 30 ms | 6% |
| Resolução do catálogo **em lote** | 80 ms | 16% |
| Validação de domínio, preço e promoção | 100 ms | 20% |
| Persistência transacional (pedido + itens + snapshot + outbox) | 120 ms | 24% |
| Serialização, resposta e overhead de rede interno | 50 ms | 10% |
| **Reserva** | **100 ms** | **20%** |
| **Total** | **500 ms** | 100% |

A publicação do evento pelo relay do outbox é **assíncrona** e fica fora deste orçamento — é justamente o que o outbox compra: confiabilidade sem custo de latência no caminho crítico.

**Com o N+1 atual, o orçamento é impossível:** 9 chamadas a 40 ms consomem 360 ms dos 500, sobrando 140 ms para todo o resto. No p95 de 15 itens, 16 chamadas consomem 640 ms — **estouram o SLA sozinhas**, antes de qualquer outra etapa.

### 7.3 Volume de dados

| Medida | Alvo |
|---|---|
| Linhas de item de pedido | 600k × 8 = **4,8M/dia** ≈ 1,75 bilhão/ano |
| Volume aproximado | ~5 KB/pedido → **~3 GB/dia** ≈ 1,1 TB/ano |
| Eventos no outbox (criação + ~4 mudanças de status) | **~3M/dia** ≈ 35/s médio, ~105/s no pico |

Justifica política de particionamento e de retenção/arquivamento — não justifica, por si só, banco distribuído.

---

## 8. Restrição derivada crítica — indisponibilidade composta

> **`CTX-17` — Dependência síncrona no caminho crítico torna `CTX-03` matematicamente inatingível.**

Se Pedidos depende sincronamente do Catálogo para criar um pedido, a disponibilidade percebida é o **produto** das duas:

```
Pedidos 99,9%  ×  Catálogo 99,9%  =  99,8%
99,8% de 43.200 min/mês  →  86,4 min de indisponibilidade
Error budget de CTX-03    →  43,2 min

Estouro: 2× o budget — e isso no cenário em que
tudo o mais funciona perfeitamente.
```

Três saídas, e a escolha entre elas é decisão de arquitetura, não de implementação:

1. **Exigir 99,99% do Catálogo** — transfere o custo para outro time e não elimina a dependência.
2. **Remover a dependência do caminho crítico** — snapshot de preço, que é o que a onda 30 já faz por outro motivo (auditabilidade, `CTX-06`).
3. **Degradar de forma controlada** — cache com TTL e fallback quando o Catálogo não responde, aceitando preço levemente defasado sob falha.

A opção 2 resolve `CTX-03`, `CTX-04`, `CTX-05` e `CTX-06` de uma vez. Este é o argumento quantitativo que sustenta a ADR-0003, e é mais forte do que "desacoplar é boa prática": **com a dependência síncrona, o SLA não fecha na aritmética**, independentemente de quão bem o código for escrito.

### 8.1 A mesma conta, aplicada ao caminho novo — SLA não é SLO

O argumento acima multiplica disponibilidades. Aplicado com honestidade, ele vale também para os serviços gerenciados que a chamada atravessa no desenho novo (`servicos-aws.md`):

| Componente no caminho da criação | SLA publicado pela AWS |
|---|---|
| Route 53 | 100% |
| CloudFront + WAF | 99,9% |
| API Gateway | 99,95% |
| ALB | 99,99% |
| ECS Fargate, em duas AZs | 99,99% |
| RDS PostgreSQL Multi-AZ | 99,95% |
| **Produto** | **≈ 99,78%** — cerca de 95 min/mês, contra 43,2 de orçamento |

Pela mesma aritmética do `CTX-17`, o caminho novo também não fecharia 99,9%. Três pontos respondem a isso — e os três precisam estar escritos, porque é a objeção mais natural a esta proposta:

1. **SLA é piso contratual, não previsão.** É o nível abaixo do qual a AWS devolve crédito; a disponibilidade observada desses serviços costuma ficar bem acima dele. Multiplicar SLAs dá o pior caso de contrato, não o comportamento esperado. Quanto a borda entrega de fato, na conta e na região escolhidas, é `???` até ser medido.
2. **A borda está em qualquer desenho — inclusive no atual.** O caminho de hoje é borda × Pedidos × Catálogo; o novo é borda × Pedidos. Com os mesmos pisos de SLA, o atual fica em ≈ 99,68% e o novo em ≈ 99,78%. Seja qual for a borda, a arquitetura **retira um fator da multiplicação** — é esse o ganho, e ele não depende do número da AWS.
3. **O SLO precisa dizer onde é medido.** O SLO de 99,9% do aceite (`metricas.md`) é medido **na borda**, no API Gateway: é o que o cliente vive. Por isso o orçamento de 43,2 min é consumido por **qualquer** componente, inclusive os gerenciados. O SLA da AWS só compensa em crédito; não devolve minuto de disponibilidade ao cliente.

**Consequências:**

- **Premissa nova, declarada:** a meta de 99,9% pressupõe que a borda gerenciada entregue bem acima do seu SLA (`PR-11` em `riscos-premissas.md`).
- **Medição separada desde a onda 30:** o mesmo SLI é medido na borda **e** no serviço. A diferença entre os dois é quanto do orçamento a borda consome — e deixa de ser suposição.
- **Gatilho:** se a borda consumir mais da metade do orçamento (21,6 min/mês), o elo mais fraco da série sai. O CloudFront tem o menor SLA da cadeia e está ali só por causa do WAF; trocar o API Gateway HTTP por REST API, que aceita WAF nativo, tira o CloudFront do caminho — ao custo de ~3,5× no gateway, que hoje foi rejeitado por custo.

---

## Riscos abertos

1. **`CTX-13` e `CTX-14` (equipe) em aberto bloqueiam `D-05`.** A estimativa é requisito obrigatório da vaga, não apenas do PDF. Precisam ser declarados como premissa em `/estimativa`, com efeito explícito caso falsos.
2. **`CTX-15` (orçamento) sem teto retira uma das cinco dimensões do §2.1.** Sem custo-limite, "equilibrar custo" vira afirmação não verificável.
3. **A meta de 99,9% depende de a borda gerenciada entregar acima do seu SLA** (§8.1). Pelos pisos publicados, a série de serviços da AWS fica em ≈ 99,78%. Medido desde a onda 30, com gatilho declarado.
4. **As premissas de distribuição (60% em 8h, pico 3×) são inventadas.** Se o varejo tiver pico concentrado de campanha — Black Friday, lançamento — o fator de pico pode ser 10× ou 20×, não 3×. Isso muda o dimensionamento inteiro da seção 7.

## Pendências registradas

- O valor de 40 ms por chamada ao Catálogo (usado em §7.2) é estimativa de ordem de grandeza, não medição — a medir no baseline `P1`.
