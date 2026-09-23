# ADR-0001 — Idempotência na criação de pedido

**Status:** Aceita — 2026-09-22
**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** a garantia de não-duplicação na **criação** de pedido. Não cobre idempotência de cancelamento, alteração ou de outras operações.
**Requisitos cobertos:** `CTX-07`, `P1-12`, `P2-08`, `P2-11`
**Fontes:** `docs/technical-context/constraints.md`, `ADR-0002` (transação comum), `ADR-0004` (compatibilidade), `ADR-0007` (aceite local)
**Data:** 2026-09-22 *(revista em 2026-09-23 após o achado F1.5 do threat model)*

---

## Contexto

Retries não possuem chave de idempotência (`CTX-07`). Um timeout de rede, um retry automático de cliente ou um duplo clique produzem pedidos distintos para uma única intenção de compra. A consequência chega à operação, que reconcilia manualmente — e é a dor classificada como **irreversível** na jornada: o pedido duplicado corrompe dado, não degrada experiência.

Ao 10× (`CTX-02`), retries crescem com o volume **e** com a instabilidade. O problema escala por um multiplicador próprio.

O desafio eleva isso a **critério crítico** (§2.4.2): *"chamadas repetidas com a mesma chave não podem criar pedidos duplicados"*. É o item de maior peso em `AV-06`.

---

## Decisão

### Chave fornecida pelo cliente, no header

`Idempotency-Key` em `POST /orders`, gerada pelo cliente e **estável entre retries** da mesma intenção.

**Escopo da chave:** `(identidade do chamador, endpoint)` — não global. Dois parceiros distintos podem gerar o mesmo UUID sem colidir, e a unicidade não vira acoplamento entre consumidores.

> ⚠️ **Revisão de 2026-09-23 — `chamador` é o principal autenticado, nunca o canal.**
>
> O threat model (ameaça **F1.5**) mostrou que esta ADR tratava a chave apenas como problema de **integridade**, quando ela é também superfície de **autorização**.
>
> Se `chamador` identificar o canal (`web`) em vez do principal autenticado, todos os clientes do canal compartilham o mesmo espaço de chaves — e quem adivinhar a chave de outro receberia, no replay, **o pedido alheio completo**. Agravante: na implementação inicial da fatia, `X-Chamador` era um header **controlado pelo cliente**, ou seja, quem chamava escolhia o próprio namespace.
>
> **Correções incorporadas:**
> 1. `chamador` é derivado da identidade autenticada pela borda. A borda **sobrescreve** headers de identidade vindos de fora (generalizado em F3.2).
> 2. O replay verifica, além do `payload_hash`, que o pedido recuperado **pertence ao solicitante** — defesa em profundidade que sobrevive a mudanças futuras no hash canônico.
> 3. Verificado por `test_chave_de_outro_cliente_nao_devolve_pedido_alheio` e `test_defesa_em_profundidade_independe_do_hash`, este último com o hash neutralizado para isolar a camada nova.
>
> **Lição:** a ADR nasceu correta para o problema que se propôs a resolver, e incompleta para o problema que criou. Modelar o fluxo não revelou isso; modelar ameaças revelou.

### Store na mesma base, na mesma transação

A chave é gravada junto com o pedido, no mesmo commit descrito na `ADR-0002`:

```
idempotency_key
  chave, chamador
  payload_hash        ← impressão canônica da requisição
  pedido_id           ← a decisão tomada
  criado_em, expira_em
  UNIQUE (chamador, chave)
```

Guarda-se a **decisão** (qual pedido foi criado), não a resposta em bytes. A razão está no comportamento de replay, abaixo.

### Comportamento

| Situação | Resposta |
|---|---|
| Chave nova | processa, grava, `201 Created` |
| Chave repetida, **mesmo** `payload_hash` | `200 OK` + `Idempotency-Replayed: true`, com o **estado corrente** do pedido |
| Chave repetida, `payload_hash` **diferente** | `409 Conflict` — a chave já foi usada para outra intenção |
| Chave em processamento concorrente | `409 Conflict` + `Retry-After` |

**Replay devolve o estado corrente, não a resposta original.** Com a `ADR-0007`, a resposta original foi `RECEBIDO`; cinco minutos depois o pedido pode estar `CONFIRMADO` ou `REJEITADO`. Devolver o texto gravado mentiria sobre a realidade e faria o cliente agir sobre estado vencido.

Isso diverge da convenção de replay literal (Stripe e similares). É desvio consciente, e existe porque o aceite assíncrono torna o estado volátil — em API onde a resposta é final, replay literal é o correto.

### Concorrência resolvida pelo banco

N requisições simultâneas com a mesma chave disputam a `UNIQUE (chamador, chave)`. Uma vence; as demais recebem violação de unicidade e a tratam como replay. **Sem lock distribuído** — que adicionaria dependência externa no caminho crítico e contrariaria a `ADR-0007`.

### TTL de 24 horas

Cobre a janela de retry de clientes e parceiros. Após o TTL, a mesma chave cria pedido novo.

**Implementado** em `slice/app/pedidos.py` (`TTL_IDEMPOTENCIA_HORAS = 24`). É decisão tomada, não lacuna: 24h é muito além de qualquer retry automático razoável. O que falta é **confirmação** contra o comportamento real de retry dos parceiros, não definição.

### Obrigatória em v2, opcional em v1

Tornar um campo de requisição obrigatório é **breaking change** pela lista fechada da `ADR-0004`. Então:

- **v1** — header opcional. Sem chave, comportamento atual; com chave, idempotente. Não pioramos nem quebramos.
- **v2** — obrigatória.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **`Idempotency-Key` + store transacional** | ✅ **Escolhida** | Explícita, sob controle do cliente, resolve concorrência pelo banco e cabe na mesma transação da `ADR-0002` |
| Chave natural do pedido (cliente + itens + janela de tempo) | ❌ Rejeitada | O servidor infere a intenção em vez de recebê-la. Falha quando o cliente **quer** dois pedidos iguais, e a janela de tempo é sempre arbitrária |
| Deduplicação por hash do payload, sem chave | ❌ Rejeitada | Falso positivo caro: cliente que compra o mesmo item duas vezes em um minuto tem o segundo pedido silenciosamente engolido. Perder venda é pior que duplicá-la |
| Deduplicação apenas no broker, por `event_id` | ❌ Rejeitada | Trata o sintoma. O pedido **já foi gravado duas vezes** no banco; deduplicar o evento não desfaz a linha duplicada |
| Lock distribuído (Redis) na chave | ❌ Rejeitada | Introduz dependência externa síncrona no caminho crítico — exatamente o que a `ADR-0007` eliminou. A `UNIQUE` do banco resolve de graça |

---

## Justificativa

A decisão se apoia em dois pontos.

**A unicidade vem do banco, não da aplicação.** Concorrência resolvida por constraint é determinística e não adiciona componente; resolvida por lock aplicacional depende de mais uma peça viva no caminho crítico. Como a transação já existe para o pedido e o outbox, a chave entra nela sem custo adicional.

**A intenção é do cliente, não inferida pelo servidor.** Toda alternativa que adivinha duplicidade erra em um dos dois sentidos — engole pedido legítimo ou deixa passar duplicata. A chave explícita transfere a declaração de intenção a quem a possui.

---

## Trade-offs aceitos

- **O cliente precisa gerar a chave corretamente.** Chave nova a cada retry anula a proteção inteira. Isso **precisa** estar no contrato e na documentação do parceiro, não só na implementação — e é a falha mais provável em integração de terceiro.
- **O `payload_hash` precisa ser canônico.** Ordem de campos, espaços e precisão numérica alteram o hash e produzem `409` falso. É fonte clássica de bug e exige normalização documentada.
- **O TTL cria uma janela.** Retry legítimo após 24h cria pedido novo. Aceito, por ser muito além de qualquer retry automático razoável.
- **Replay devolve estado corrente, divergindo da convenção de mercado.** Ganha-se verdade, perde-se familiaridade. Precisa estar explícito na OpenAPI.
- **A tabela cresce com o volume.** 600k pedidos/dia com TTL de 24h — expurgo é obrigatório, mesma política do outbox.

---

## Gatilho de revisão

**Se a taxa de `409` por `payload_hash` divergente passar de 0,5%.** Indica uma de duas coisas, ambas acionáveis: clientes reutilizando chave para intenções diferentes, ou nossa normalização canônica está errada. O segundo caso é nosso defeito disfarçado de erro do cliente — e acima de 0,5% a segunda hipótese passa a ser a mais provável.

**Se surgir retry legítimo além do TTL de 24h.** O valor foi presumido; comportamento real de parceiro pode exigir mais.

**Se a idempotência precisar valer para outras operações** além da criação (cancelamento, alteração). A decisão atual cobre um endpoint; generalizar exige repensar o escopo da chave.

---

## Enforcement

**Fitness functions executáveis — as duas primeiras são o critério crítico de `P2-11`:**

0. **Isolamento entre clientes (F1.5).** Chave reutilizada por outro cliente devolve `409` e **não vaza** o pedido nem o identificador da vítima. Validado por teste de mutação: removendo a verificação de dono, o teste falha.

1. **Concorrência.** N requisições paralelas com a mesma chave produzem **exatamente um** pedido. Teste com N ≥ 20 e asserção de contagem no banco.
2. **Conflito.** Mesma chave com payload diferente devolve `409`, e **nenhum** segundo pedido é criado.
3. **Replay pós-transição.** Pedido aceito, transicionado para `CONFIRMADO`, e então revisitado com a mesma chave → resposta traz `CONFIRMADO`, não `RECEBIDO`.
4. **Schema check.** A `UNIQUE (chamador, chave)` existe. Migração que a remova falha o build — é ela que sustenta a garantia, não o código.

```bash
# .claude/hooks/check-unique-idempotencia.sh
# ADR-0001: a garantia depende da constraint, não da aplicação
if ! grep -rqiE 'UNIQUE.*\(.*chamador.*chave.*\)|idx_idempotency_unique' ./migrations; then
  echo "ADR-0001: constraint UNIQUE(chamador, chave) ausente nas migrações." >&2
  exit 2
fi
```

---

## Pendências registradas

- O TTL de 24h é premissa. Confrontar com a política real de retry dos parceiros antes da onda 60.
- A normalização canônica do payload não está especificada. Precisa entrar na OpenAPI (`P2-06`), não apenas no código.
- O limite de `409` por divergência (0,5%) foi definido em 2026-09-23 por raciocínio, não por medição: conflito legítimo de chave é evento raro, e um patamar acima disso aponta para defeito nosso.
- **Fronteira com `ADR-0002`:** a chave de idempotência e o registro do outbox são gravados na **mesma transação** do pedido. A ordem das operações dentro dela e o tratamento da violação de unicidade são contrato comum entre as duas ADRs e estão detalhados na `ADR-0002`.
