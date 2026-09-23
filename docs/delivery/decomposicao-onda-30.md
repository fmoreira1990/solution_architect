# Decomposição da onda 30 — unidades estimáveis

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** a onda 30 quebrada até o nível em que cada item admite estimativa de esforço e perfil. É o **insumo** de `estimativa-fase1.md` — o esforço sai daqui, e a composição do time sai do esforço, não o contrário.
**Requisitos cobertos:** `D-05`, `P2-01`
**Fontes:** `docs/delivery/plano-30-60-90.md`, ADRs 0001 a 0007, `slice/`
**Data:** 2026-09-23

---

## Por que este documento existe

O plano 30/60/90 nomeia 17 entregas. Cada uma é uma linha. Estimar em cima de linhas produz número com aparência de método e nenhuma base.

Aqui cada entrega vira tarefas de 0,5 a 3 dias-pessoa, com perfil e dependência. Unidade maior que 3 dias é sinal de que ainda não foi entendida.

---

## O que a fatia executável já responde

A prova em `slice/` implementa o **núcleo** de `A1`–`A8`: idempotência com `PRIMARY KEY`, outbox transacional, relay com `SKIP LOCKED`, snapshot imutável, cotação assinada e contract test. Ela roda, com 128 testes.

Isso é uma âncora de calibração incomum: não estamos estimando algo nunca construído. Estamos estimando **a distância entre a prova e a produção**.

| O que a prova tem | O que falta para produção |
|---|---|
| Lógica correta, testada | Migração de schema em base com dados, sem downtime |
| Um caminho | Convivência com o caminho legado, sob feature flag |
| Postgres local | Multi-AZ, pool, tuning, backup |
| Broker stub | Broker real, ACL, particionamento, DLQ |
| Testes de unidade e integração | Observabilidade, alertas, runbook |
| Nenhum consumidor real | Inventário, comunicação, janela de adequação |
| Sem revisão | Code review, revisão de segurança, aceite |

**Fator de produção aplicado: 3,5×** sobre o esforço de núcleo. Não é regra de bolso — é a soma das sete linhas acima, e cada tarefa abaixo mostra onde ele incide.

---

## Pré-requisitos — bloqueiam o gate, não são paralelos

| # | Tarefa | d.p. | Perfil | Depende |
|---|---|---|---|---|
| P1.1 | Instrumentar contagem de duplicatas por retry na base atual | 2 | Dev Sênior | — |
| P1.2 | Medir divergência entre pedidos commitados e eventos publicados | 2 | Dev Sênior | — |
| P1.3 | Medir p95 de criação por faixa de itens | 1,5 | SRE | — |
| P1.4 | Consolidar baseline e publicar painel | 1 | SRE | P1.1–P1.3 |
| P2.1 | Tracing distribuído no caminho de criação | 3 | SRE | — |
| P2.2 | Painel comparativo caminho novo × antigo | 2 | SRE | P2.1 |
| P2.3 | Alertas de divergência de resultado | 1,5 | SRE | P2.2 |
| P3.1 | Inventariar consumidores por log de acesso | 2 | Dev Pleno | — |
| P3.2 | Classificar interno × externo e mapear responsáveis | 1 | Arquiteto | P3.1 |
| | **Subtotal pré-requisitos** | **16** | | |

> **P1 e P3 são o caminho crítico real.** Sem baseline, o gate G30 é indecidível; sem inventário, `CTX-10` não é verificável. Tratá-los como paralelos é o erro mais comum deste tipo de plano.

---

## Bloco A — Idempotência (`ADR-0001`)

| # | Tarefa | d.p. | Perfil | Notas |
|---|---|---|---|---|
| A1.1 | Migração: tabela `idempotency_key` com PK `(chamador, chave)` | 1 | Dev Sênior | aditiva, sem downtime |
| A1.2 | Job de expurgo por TTL de 24 h | 1 | Dev Pleno | — |
| A2.1 | Aceitar `Idempotency-Key`; gravar na mesma transação | 2 | Dev Sênior | núcleo provado na fatia |
| A2.2 | Replay com estado corrente; `409` em conflito | 1,5 | Dev Sênior | desvio consciente da convenção |
| A2.3 | **Derivar `chamador` da identidade autenticada, não de header** | 2 | Dev Sênior | ameaça **F1.5** do threat model |
| A3.1 | Normalização canônica do payload | 2 | Dev Sênior | **maior risco do bloco** |
| A3.2 | Documentar a normalização na OpenAPI | 0,5 | Arquiteto | contrato, não só código |
| A3.3 | Métrica de `409` por divergência, alerta em 0,5% | 1 | SRE | detecta hash errado |
| | **Subtotal** | **11** | | |

**A3 é o risco alto do bloco.** Ordem de campos, espaços e precisão numérica alteram o hash e produzem `409` falso — o cliente vê erro sem ter errado. É defeito nosso disfarçado de erro dele.

---

## Bloco B — Snapshot e cotação (`ADR-0003`, `ADR-0007`)

| # | Tarefa | d.p. | Perfil | Notas |
|---|---|---|---|---|
| A4.1 | Migração: colunas de snapshot `NOT NULL` em `pedido_item` | 1,5 | Dev Sênior | aditiva; default temporário para linhas antigas |
| A4.2 | Backfill impossível: marcar pedidos legados como sem snapshot | 1 | Dev Pleno | o dado nunca existiu |
| A5.1 | `POST /v2/quotes`: leitura em lote do Catálogo | 2 | Dev Sênior | elimina o N+1 na cotação |
| A5.2 | Assinatura HMAC com chave em cofre gerenciado | 2 | Dev Sênior | a fatia usa chave fixa — **não vai para produção** |
| A5.3 | Rotação de chave sem invalidar cotações vigentes | 1,5 | Dev Sênior | ameaça **F1.3** |
| A6.1 | Gravar snapshot na criação | 1 | Dev Pleno | núcleo provado na fatia |
| A6.2 | Teste de consulta com o Catálogo fora do ar, no CI | 0,5 | Dev Pleno | enforcement da `ADR-0003` |
| | **Subtotal** | **9,5** | | |

**A5.2 e A5.3 não existem na prova.** A fatia usa chave HMAC fixa e sintética. Em produção, ela é o ativo mais concentrado do desenho: quem a obtém falsifica preço em qualquer pedido.

---

## Bloco C — Outbox e publicação (`ADR-0002`)

| # | Tarefa | d.p. | Perfil | Notas |
|---|---|---|---|---|
| A7.1 | Migração: tabela `outbox` com índice parcial | 1 | Dev Sênior | — |
| A8.1 | Relay com `FOR UPDATE SKIP LOCKED` | 2 | Dev Sênior | núcleo provado na fatia |
| A8.2 | Publicação em broker real, com particionamento por `pedido_id` | 2,5 | Dev Sênior | a fatia usa stub |
| A8.3 | Tratamento de falha de publicação e backoff | 1,5 | Dev Sênior | — |
| A9.1 | Declarar a obrigação de deduplicar no AsyncAPI | 0,5 | Arquiteto | já feito no desafio |
| A9.2 | **Adequar consumidores internos** | 3 | Dev Pleno | quantos são é `???` (P3.1) |
| A9.3 | **Negociar janela com consumidores externos** | 2 | Arquiteto | depende de terceiros |
| A10.1 | Expurgo do outbox em 90 dias | 1 | Dev Pleno | — |
| A11.1 | SLI de idade do evento mais antigo não publicado | 1 | SRE | provado na fatia |
| A11.2 | Alerta em 5 min + runbook de relay parado | 1,5 | SRE | **falha silenciosa** |
| | **Subtotal** | **16** | | |

**A9.2 e A9.3 dependem de terceiros e são o risco mais alto da onda.** O esforço de 5 dias-pessoa presume que os consumidores cooperam no prazo. Se forem externos e lentos, isso não escala com mais gente.

---

## Bloco D — Convivência, rollout e reconciliação

| # | Tarefa | d.p. | Perfil | Notas |
|---|---|---|---|---|
| A12.1 | Feature flag por percentual de tráfego | 2 | Dev Sênior | mecanismo provado na fatia; falta serviço de configuração |
| A12.2 | Rollback sem deploy, exercitado em produção | 1,5 | SRE | critério do gate G30 |
| A12.3 | Rollout 1% → 10% → 50% → 100% com comparação a cada degrau | 2 | SRE | `CTX-11` |
| A13.1 | Job de reconciliação: presos, outbox parado, cotações órfãs | 2,5 | Dev Pleno | — |
| A13.2 | Cancelamento automático em 24 h com notificação | 1,5 | Dev Pleno | decisão de negócio implementada |
| A14.1 | Contract test v1 no CI | 1 | Dev Sênior | provado na fatia |
| A14.2 | Detector de breaking change estrutural | 1 | Dev Sênior | precisa de linha de base |
| | **Subtotal** | **11,5** | | |

**A12 é o que `CTX-11` custa.** Sem a exigência de "zero janela de indisponibilidade", esses 5,5 dias-pessoa não existiriam — seria uma migração com janela de manutenção. É o preço da restrição, e precisa estar visível na proposta comercial.

---

## Transversal — não é entrega, é o que torna entrega confiável

| # | Tarefa | d.p. | Perfil |
|---|---|---|---|
| T1 | Code review e ajustes | 5 | todos |
| T2 | Revisão de segurança sobre as ameaças F1.2, F1.3, F1.5 | 2 | Arquiteto |
| T3 | Runbooks e documentação operacional | 2 | SRE |
| T4 | Acompanhamento de rollout e correção em produção | 3 | Dev Sênior |
| T5 | Cerimônias, alinhamento e aceite | 3 | todos |
| | **Subtotal** | **15** | |

Omitir o transversal é como estimativas otimistas nascem. São 15 dias-pessoa — **19% do total** — e nenhum deles é opcional.

---

## Consolidado

| Bloco | d.p. | % |
|---|---|---|
| Pré-requisitos (P1–P3) | 16 | 20% |
| A — Idempotência | 11 | 14% |
| B — Snapshot e cotação | 9,5 | 12% |
| C — Outbox e publicação | 16 | 20% |
| D — Convivência e rollout | 11,5 | 15% |
| Transversal | 15 | 19% |
| **Total** | **79 dias-pessoa** | 100% |

### Distribuição por perfil

| Perfil | d.p. | O que exige este perfil |
|---|---|---|
| **Arquiteto** | 9,5 | Normalização de contrato, negociação com consumidores, revisão de segurança |
| **Dev Sênior** | 33 | Transação única, relay, rotação de chave, feature flag — tudo que erra caro |
| **Dev Pleno** | 16 | Expurgo, backfill, reconciliação, adequação de consumidores |
| **SRE** | 20,5 | Observabilidade, alertas, rollout, runbooks |
| **Total** | **79** | |

Esta é a distribuição **sem IA**, base verificável da estimativa. No time proposto — com IA e um SRE —, `P1.3` e `A3.3` passam ao Dev Sênior e `P1.4` e `A11.1` ao Dev Pleno; a derivação está em [`estimativa-fase1.md`](estimativa-fase1.md) §2.

O perfil **saiu da decomposição**, não foi declarado antes. A proporção de SRE (26%) surpreende e é consequência direta de `CTX-11`: rollout progressivo com comparação a cada degrau é trabalho de operação, não de desenvolvimento.

---

## O que esta decomposição assume

| # | Premissa | Efeito se falsa |
|---|---|---|
| E1 | Ambiente de desenvolvimento e CI já existem | +5 a 8 d.p. |
| E2 | Broker gerenciado disponível, sem provisionamento novo | +3 a 5 d.p. |
| E3 | Consumidores internos cooperam dentro da onda | A9.2 escorrega; gate G30 não fecha |
| E4 | Não há integrações no caminho de criação além do Catálogo | cada uma adiciona ~4 d.p. e reintroduz o `CTX-17` |
| E5 | O time conhece a stack de produção | rampa não estimada (`CTX-14` é `???`) |
| E6 | Migrações aditivas rodam sem janela na base atual | pode exigir estratégia de migração online, +5 d.p. |

## Riscos da decomposição

1. **A3 (normalização canônica) pode consumir o dobro.** É o tipo de tarefa que parece simples e revela casos de borda em produção.
2. **A9.2/A9.3 não escalam com mais gente.** Depender de terceiros é prazo, não esforço.
3. **O fator de produção 3,5× é derivado, não medido.** Foi construído somando as sete linhas da tabela "prova × produção", mas é a premissa mais consequente deste documento.
4. **Nenhuma tarefa de performance.** A onda 30 não ataca o N+1 nem testa carga — isso é onda 60 e 90. Se o volume crescer antes, o plano muda.

## Pendências registradas

- `E5` depende de `CTX-14`, que é `???`. Rampa não está estimada.
- O esforço total (79 d.p., sem IA) alimenta `estimativa-fase1.md`, onde recebe o ganho de IA e vira prazo e composição de time.
