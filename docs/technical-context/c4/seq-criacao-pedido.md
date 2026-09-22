# Sequência — Criação de pedido

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** o caminho crítico, com os desvios de erro. Cada passo tem correspondência em teste automatizado.
**Requisitos cobertos:** `P1-05`, `P1-12`, `P1-13`
**Fontes:** `ADR-0001`, `ADR-0002`, `ADR-0003`, `ADR-0007`, `slice/app/pedidos.py`
**Data:** 2026-09-22

---

## Caminho principal — canal próprio

```mermaid
sequenceDiagram
    autonumber
    actor C as Cliente
    participant B as BFF
    participant Ca as Carrinho e Oferta
    participant K as Cache/Catálogo
    participant E as Estoque
    participant P as Pedidos
    participant DB as Banco de Pedidos
    participant R as Relay
    participant Br as Broker
    participant V as Validadores

    rect rgb(238, 246, 255)
    note over C,E: ANTES do caminho crítico — aqui mora a chamada externa
    C->>B: monta carrinho
    B->>Ca: cotar itens
    Ca->>K: resolver em LOTE (2 chamadas, não 9)
    K-->>Ca: preço, descrição, unidade, peso
    Ca->>E: reservar (TTL)
    E-->>Ca: reservado
    Ca-->>B: OFERTA ASSINADA (HMAC + validade)
    end

    rect rgb(232, 245, 233)
    note over C,DB: CAMINHO CRÍTICO — p95 ≤ 500ms · ZERO chamada de saída
    C->>B: finalizar
    B->>P: POST /v2/orders<br/>Idempotency-Key + oferta
    P->>P: valida oferta (assinatura + validade) — LOCAL
    P->>DB: BEGIN
    P->>DB: 1. idempotency_key ← falha rápido na PK
    P->>DB: 2. pedido (status=RECEBIDO)
    P->>DB: 3. itens + SNAPSHOT dos termos
    P->>DB: 4. outbox ← MESMA transação
    P->>DB: COMMIT
    P-->>B: 201 RECEBIDO
    B-->>C: "pedido em análise"
    end

    rect rgb(255, 248, 225)
    note over R,V: DEPOIS — validação assíncrona
    R->>DB: SELECT ... FOR UPDATE SKIP LOCKED
    R->>Br: publica PedidoRecebido (①)
    R->>DB: marca publicado_em (②)
    Br->>V: entrega (at-least-once)
    V->>V: deduplica por event_id
    V->>P: confirmar / rejeitar
    P->>DB: transição + novo outbox
    end
```

---

## Leitura do diagrama

**As três faixas são a decisão arquitetural.** Tudo que exige resposta externa está na faixa azul (antes) ou amarela (depois). A faixa verde — o caminho crítico que `CTX-04` cronometra — não tem **nenhuma** chamada de saída.

**A ordem dentro da transação não é arbitrária.** A chave de idempotência entra **primeiro** para falhar rápido na `PRIMARY KEY`; se falhar, a transação inteira é revertida, inclusive o outbox — nunca sobra evento órfão.

**A ordem ① antes de ② é a garantia do outbox.** Publicar antes de marcar produz at-least-once: se o relay cair no meio, o evento sai de novo. A ordem inversa perderia o evento.

## Desvios de erro

```mermaid
sequenceDiagram
    autonumber
    participant B as BFF
    participant P as Pedidos
    participant DB as Banco

    alt Retry com a MESMA chave e mesmo payload
        B->>P: POST + Idempotency-Key (repetida)
        P->>DB: INSERT idempotency_key
        DB-->>P: ❌ violação de PRIMARY KEY
        P->>DB: SELECT pedido existente
        P-->>B: 200 + Idempotency-Replayed: true<br/>com o ESTADO CORRENTE
    else Mesma chave, payload DIFERENTE
        B->>P: POST + chave repetida, corpo outro
        DB-->>P: ❌ violação de PRIMARY KEY
        P->>P: payload_hash não confere
        P-->>B: 409 Conflict — nenhum pedido criado
    else Oferta expirada ou adulterada
        B->>P: POST com oferta inválida
        P->>P: HMAC não confere ou expira_em vencido
        P-->>B: 422 — não abre transação
    else 20 requisições CONCORRENTES, mesma chave
        B->>P: 20× em paralelo
        P->>DB: 20× BEGIN
        DB-->>P: 1 vence, 19 violam a PK
        P-->>B: 1× 201 + 19× 200 — UM pedido no banco
    end
```

**O replay devolve o estado corrente, não a resposta gravada.** Com aceite assíncrono, a resposta original foi `RECEBIDO` e o pedido pode já estar `CONFIRMADO`; devolver o texto gravado mentiria. Desvio consciente da convenção de mercado, registrado na `ADR-0001`.

## Correspondência com os testes

| Passo | Teste |
|---|---|
| Caminho principal | `test_criacao_simples_responde_201_e_recebido` |
| Retry mesma chave | `test_replay_com_mesma_chave_devolve_o_mesmo_pedido` |
| **20 concorrentes** | `test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido` ⭐ |
| Payload divergente | `test_mesma_chave_com_payload_diferente_responde_409` |
| Oferta expirada / adulterada | `test_oferta_expirada_e_recusada`, `test_oferta_adulterada_e_recusada` |
| Transação única | `test_pedido_e_evento_nascem_na_mesma_transacao` |
| Replay com estado corrente | `test_replay_devolve_estado_corrente_e_nao_o_gravado` |

⭐ = critério crítico do §2.4.2.

## Canal de parceiro

Idêntico a partir do `POST`, **sem a faixa azul**: o parceiro não tem carrinho, logo não tem oferta nem reserva. Preço e atributos vêm no payload dele e são validados de forma assíncrona junto com o estoque. Taxa de rejeição estruturalmente maior — esperado, não defeito.
