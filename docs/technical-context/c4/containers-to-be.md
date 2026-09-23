# C4 Nível 2 — Contêineres · Arquitetura-alvo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** contêineres do alvo, com o delta em relação ao as-is marcado. Escopo recortado a Pedidos e Catálogo.
**Requisitos cobertos:** `P1-04`, `P1-07`
**Fontes:** `docs/technical-context/architecture.md`, ADRs 0001 a 0007
**Data:** 2026-09-23

---

```mermaid
flowchart TB
    cliente(["Cliente<br/>web e app"])
    parceiro(["Parceiro"])
    legado(["Consumidor v1"])

    subgraph borda["🛡️ Borda — fronteira de confiança"]
        gw["<b>WAF · API Gateway</b><br/><i>filtro · authn · escopos · quotas<br/>roteia /v1 e /v2</i>"]
    end

    subgraph app["🔒 Aplicação"]
        bff["<b>BFF multi-canal</b><br/><i>NOVO · um só, não dois</i>"]
        apub["<b>API Pública de Parceiros</b><br/><i>NOVO · contrato versionado</i>"]
        pedidos["<b>Serviço de Pedidos</b><br/><i>aceite LOCAL · zero chamada de saída</i><br/><b>+ cotação</b> <i>(POST /v2/quotes)</i>"]
        relay["<b>Relay do Outbox</b><br/><i>processo interno, não serviço</i>"]
        validador["<b>Validador assíncrono</b><br/><i>NOVO · confere termos vs. Catálogo</i>"]
        catalogo["Catálogo"]
    end

    subgraph dados["🗄️ Dados"]
        dbped[("<b>Pedidos</b><br/>pedido · item+snapshot<br/>idempotency_key · outbox<br/><i>MESMA transação</i>")]
        cache[("Cache do Catálogo<br/><i>serve a cotação</i>")]
        dbcat[("Catálogo")]
    end

    broker{{"<b>Broker</b>"}}
    notif["<b>Gateway de Notificação</b><br/><i>webhook assinado · retry · DLQ</i>"]

    cliente --> gw
    parceiro --> gw
    legado --> gw
    gw --> bff
    gw --> apub
    gw -->|"/v1 fachada síncrona"| pedidos

    bff -->|"1. POST /v2/quotes"| pedidos
    pedidos -->|"cota em LOTE<br/><i>fora do caminho crítico</i>"| cache
    cache -.-> catalogo
    catalogo --> dbcat

    bff ==>|"2. POST /v2/orders<br/>Idempotency-Key + cotação"| pedidos
    apub ==>|"sem cotação:<br/>conferido depois"| pedidos

    pedidos ===>|"1 transação:<br/>pedido+snapshot+chave+outbox"| dbped
    relay -->|"SELECT ... FOR UPDATE SKIP LOCKED"| dbped
    relay -->|"publica ANTES de marcar<br/>at-least-once"| broker

    broker --> validador
    broker --> notif
    validador -.->|"confere termos"| catalogo
    validador -->|"confirma ou rejeita"| pedidos
    notif -->|"webhook assinado"| parceiro

    style pedidos stroke-width:4px
    style dbped stroke-width:3px
    linkStyle 11 stroke:#080,stroke-width:3px
    linkStyle 13 stroke:#080,stroke-width:4px
```

---

## Leitura do diagrama

**A seta verde grossa para o banco é a decisão inteira.** Pedido, itens com snapshot, chave de idempotência e registro no outbox entram em **uma transação**. É daí que saem as garantias de `ADR-0001`, `ADR-0002` e `ADR-0003` — e é por isso que o store é relacional: não é preferência, é requisito.

**Não há seta de Pedidos para fora no caminho de aceite.** A leitura do Catálogo acontece no passo 1 (cotação) e na validação assíncrona. O passo 2 — o que `CTX-04` cronometra — é puramente local.

**A cotação é do próprio Pedidos, não de um serviço à parte.** Ela existe para tirar a leitura do Catálogo do caminho crítico, e quem a emite é quem precisa do resultado. Criar um contêiner separado para isso seria complexidade sem `CTX` que a justifique.

**A API Pública entra direto no aceite, sem cotar.** Parceiro submete os termos do sistema dele, conferidos depois pelo validador — e por isso sua taxa de rejeição pós-aceite é estruturalmente maior. Assimetria deliberada, não lacuna.

**O relay é um processo dentro de Pedidos, não um serviço.** Ele lê a tabela `outbox`, que pertence a Pedidos; um serviço separado lendo esse banco quebraria o ownership do mapa de domínios.

**O cache serve a cotação, não a leitura de pedido.** Depois da criação, o pedido é autocontido: nenhuma leitura de pedido toca o Catálogo — garantido pelo teste que executa a consulta com o Catálogo fora do ar.

## Pontos de falha e degradação

| Componente | Se falhar | Aceite continua? |
|---|---|---|
| **Banco de Pedidos** | aceite para | ❌ **único SPOF** — multi-AZ obrigatório |
| Broker | eventos não saem, outbox acumula | ✅ |
| Relay | publicação atrasa | ✅ falha **silenciosa** — depende do SLI |
| Catálogo / Cache | não dá para cotar nem validar | ✅ novos pedidos ficam em `RECEBIDO`; reconciliação assume |
| Validador | desfecho não chega | ✅ pedidos permanecem em `RECEBIDO` |
| Gateway de Notificação | webhook falha | ✅ retry, backoff, DLQ — bulkhead |

**Dos seis componentes, apenas um derruba a criação.** Essa é a propriedade que o desenho compra em troca da complexidade assíncrona.

## O que **não** está aqui

Service mesh, CQRS, event sourcing, sharding e BFF por canal foram deliberadamente omitidos — cada um com o gatilho numérico que o traria de volta em `architecture.md`.

Estoque, Pagamento e Carrinho também não estão, e por outro motivo: **o enunciado não os nomeia.** Ausência por escopo, não por dimensionamento (`AV-08`).
