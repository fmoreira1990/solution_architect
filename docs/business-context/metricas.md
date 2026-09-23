# Métricas e cenários de qualidade

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** SLIs, SLOs e os cenários de qualidade em formato estímulo → resposta → medida, com critério de aceite por gate.
**Requisitos cobertos:** `P2-02`, `P1-08`
**Fontes:** `docs/prd/pedidos-catalogo.md` (§6), `docs/technical-context/constraints.md`, `docs/technical-context/atributos-qualidade.md`
**Data:** 2026-09-23

---

## As três camadas

### Camada 1 — Adoção: alguém usa o caminho novo?

| Métrica | Fórmula | Meta G30 | Meta G90 |
|---|---|---|---|
| Tráfego no caminho novo | `pedidos via flag ativa ÷ total` | 100% ao fim do rollout | — |
| Parceiros integrados | contagem de parceiros com ≥1 pedido em 7 dias | — | ≥ 1 em G60 |
| Adoção de `Idempotency-Key` | `requisições com header ÷ total` | — | 100% em v2 |

### Camada 2 — Engajamento: usa direito?

| Métrica | Fórmula | Meta | Por quê |
|---|---|---|---|
| Chaves de idempotência **estáveis** | `1 − (chaves usadas 1× em retry ÷ total de retries)` | > 95% | Cliente que gera chave nova a cada retry anula a proteção. É a falha mais provável em integração de terceiro |
| Consumidores que deduplicam | `consumidores sem reprocessamento ÷ total` | 100% | At-least-once só é seguro com dedup. É **obrigação de contrato** |
| Ofertas aproveitadas | `pedidos criados ÷ ofertas emitidas` | acompanhar | Queda indica validade curta demais |

### Camada 3 — Valor: a dor do PRD diminuiu?

Esta camada **é** a métrica-alvo do PRD.

| Métrica | Baseline | Meta | Kill criteria |
|---|---|---|---|
| **Pedidos duplicados por retry / mês** | `???` | **zero** com a mesma chave | se persistir após o outbox, o problema não era transacional |
| **Eventos perdidos / mês** | `???` | **zero** | — |
| **Disputas de preço sem resposta / mês** | `???` | zero para pedidos novos | — |
| **p95 de aceitação** | `???` | ≤ 500 ms com 10× o volume | se não cair após eliminar o N+1, o gargalo foi mal diagnosticado |
| **Consumidores quebrados** | 0 | **0** em 6 meses | se preservar contratos exigir congelar a evolução, a premissa do §2.1 cai |
| **Custo por pedido** | `???` | não crescer com o volume | se crescer proporcionalmente, escalou o gasto, não o desenho |

> **Os `???` são deliberados** (regra Q7). Não há dado de produção no enunciado. Levantá-los é a tarefa **P1 da onda 30** e **pré-requisito do gate G30** — sem régua, o gate é indecidível.

---

## SLIs e SLOs operacionais

| SLI | Definição | SLO | Error budget |
|---|---|---|---|
| Disponibilidade do aceite | `201 ÷ (201 + 5xx)` em janela de 1 min | 99,9% mensal | 43 min/mês |
| Latência de aceitação | p95 de `POST /v2/orders` | ≤ 500 ms | — |
| Latência de confirmação | p95 de `RECEBIDO` → desfecho | **≤ 30 s** | — |
| **Idade do evento mais antigo não publicado** | `now − min(criado_em)` onde `publicado_em IS NULL` | alerta em **5 min** | — |
| Taxa de rejeição pós-aceite | `REJEITADO ÷ (CONFIRMADO + REJEITADO)` | **≤ 2%** próprio · **≤ 8%** parceiro | — |
| Pedidos presos em validação | contagem além do timeout | zero após reconciliação diária | — |

**Segmentação obrigatória por versão de contrato.** A fachada v1 reintroduz o acoplamento que a `ADR-0007` eliminou; se a disponibilidade for reportada na média, o custo da fachada some dentro do número global. Reportar v1 e v2 separadamente.

**Segmentação obrigatória por canal** na taxa de rejeição. O parceiro **não cota**: submete os termos do sistema dele, conferidos depois — sua rejeição é estruturalmente maior. Misturar canais esconde tanto o comportamento normal quanto a anomalia real.

---

## Cenários de qualidade

Formato: **estímulo → ambiente → resposta → medida**.

### Disponibilidade

**D1.** O Catálogo fica indisponível por 10 minutos em horário de pico.
→ A criação de pedido continua funcionando (o aceite não o consulta); a vitrine degrada para itens em cache; consultas de pedido respondem normalmente.
→ **Aceite:** zero queda na taxa de `201`. Verificado por `test_consulta_de_pedido_funciona_com_o_catalogo_fora_do_ar`.

**D2.** O broker fica indisponível por 30 minutos.
→ O aceite continua respondendo `201`; o outbox acumula; nada se perde. A confirmação atrasa.
→ **Aceite:** zero evento perdido; alerta de idade do outbox dispara em até **5 min**.

**D3.** Uma AZ do banco cai.
→ Failover multi-AZ.
→ **Aceite:** RTO **15 min**, RPO **zero**. *(infraestrutura, fora da fatia)*

### Performance

**P1.** Pico de 37,5 pedidos/s (3× a média do alvo de 600k/dia).
→ Aceite local absorve; validação enfileira.
→ **Aceite:** p95 de aceitação ≤ 500 ms; p95 de confirmação dentro do alvo.

**P2.** Pedido com 40 itens (bem acima do p95 de 15).
→ Cotação em lote resolve em 2 chamadas, não 41.
→ **Aceite:** p95 ≤ 500 ms independentemente do número de itens.

### Segurança

**S1.** Um parceiro envia oferta com preço adulterado.
→ HMAC não confere; `422`; nenhuma transação é aberta.
→ **Aceite:** zero pedido criado. Verificado por `test_oferta_adulterada_e_recusada`.

**S2.** Um parceiro excede a quota contratada em 10×.
→ `429` na borda; demais parceiros não são afetados (bulkhead).
→ **Aceite:** zero impacto em outros parceiros. *(onda 60)*

### Auditabilidade

**A1.** O preço de um SKU muda 2 horas após um pedido; o cliente contesta.
→ O pedido apresenta o preço praticado, a versão do catálogo lida e o horário da leitura.
→ **Aceite:** resposta sem consultar o Catálogo. Verificado por `test_mudanca_de_preco_no_catalogo_nao_altera_o_pedido`.

**A2.** Auditoria pede a origem do valor cobrado em pedidos de um período.
→ Snapshot completo em 100% dos pedidos novos.
→ **Aceite:** zero pedido sem snapshot — garantido por `NOT NULL` no schema, não por código.

### Recuperação

**R1.** O relay cai entre publicar e marcar.
→ Na retomada, republica; consumidor deduplica por `event_id`.
→ **Aceite:** zero evento perdido, zero efeito duplicado. ⭐ `test_queda_entre_publicar_e_marcar_nao_perde_evento`.

**R2.** 20 requisições concorrentes com a mesma chave.
→ A `PRIMARY KEY` serializa; uma cria, as demais fazem replay.
→ **Aceite:** exatamente 1 pedido. ⭐ `test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido`.

**R3.** Pedidos ficam presos em `EM_VALIDACAO` por indisponibilidade prolongada do Catálogo.
→ Reconciliação diária os identifica e aplica a política de desfecho.
→ **Aceite:** zero pedido preso além de 24 h. Política de desfecho: **cancelamento automático com notificação ao cliente**.

### Evolução

**E1.** A v2 entra em produção com semântica assíncrona.
→ O consumidor v1 de referência continua recebendo pedido confirmado.
→ **Aceite:** zero consumidor quebrado. ⭐ `test_consumidor_v1_continua_passando_com_a_v2_no_ar`.

**E2.** Alguém adiciona um campo na resposta sem atualizar o contrato.
→ A fitness function de drift falha o build.
→ **Aceite:** build vermelho. Comprovado por teste de mutação em 2026-09-22.

⭐ = critério crítico do §2.4.2.

---

## Cobertura: 9 dos 14 cenários têm teste executável hoje

| Verificado por teste automatizado | Depende de infra, carga ou decisão pendente |
|---|---|
| D1, S1, A1, A2, R1, R2, E1, E2, P2 *(parcial)* | D3 (multi-AZ), P1 (carga 10×), S2 (quotas, onda 60), R3 (reconciliação, onda 30), D2 (alerta, onda 30) |

---

## Pendências registradas

- Os `???` restantes são **exclusivamente baselines de produção** da camada 3. Todos os alvos, limiares e políticas estão definidos e aguardam validação com o negócio — não definição.
- Levantar os baselines é a tarefa `P1` da onda 30 e **pré-requisito do gate G30**.
- Os quatro primeiros são tarefa **P1 da onda 30**; o último é decisão de negócio.
- Nenhum painel foi especificado. A escolha de ferramenta é de infraestrutura e não muda as métricas.
