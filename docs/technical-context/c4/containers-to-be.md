# C4 Nível 2 — Contêineres · Arquitetura-alvo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** contêineres do alvo, com o delta em relação ao as-is marcado.
**Requisitos cobertos:** `P1-04`, `P1-07`
**Fontes:** `docs/technical-context/architecture.md`, ADRs 0001 a 0007
**Data:** 2026-09-22

---

```mermaid
flowchart TB
    cliente(["Cliente<br/>web e app"])
    parceiro(["Parceiro"])
    legado(["Consumidor v1"])

    subgraph borda["🛡️ Borda — fronteira de confiança"]
        gw["<b>API Gateway</b><br/><i>authn · escopos · quotas<br/>roteia /v1 e /v2</i>"]
    end

    subgraph app["🔒 Aplicação"]
        bff["<b>BFF multi-canal</b><br/><i>NOVO · um só, não dois</i>"]
        apub["<b>API Pública de Parceiros</b><br/><i>NOVO · contrato versionado</i>"]
        carrinho["<b>Carrinho e Oferta</b><br/><i>NOVO · cota preço, assina oferta,<br/>reserva estoque</i>"]
        pedidos["<b>Serviço de Pedidos</b><br/><i>aceite LOCAL · zero chamada de saída</i>"]
        relay["<b>Relay do Outbox</b><br/><i>processo interno, não serviço</i>"]
        catalogo["Catálogo"]
    end

    subgraph dados["🗄️ Dados"]
        dbped[("<b>Pedidos</b><br/>pedido · item+snapshot<br/>idempotency_key · outbox<br/><i>MESMA transação</i>")]
        cache[("Cache do Catálogo<br/><i>serve o Carrinho</i>")]
        dbcat[("Catálogo")]
    end

    broker{{"<b>Broker</b>"}}

    subgraph validadores["Validação assíncrona"]
        estoque["Estoque"]
        pagto["Pagamento"]
        fraude["Antifraude"]
    end

    notif["<b>Gateway de Notificação</b><br/><i>webhook assinado · retry · DLQ</i>"]

    cliente --> gw
    parceiro --> gw
    legado --> gw
    gw --> bff
    gw --> apub
    gw -->|"/v1 fachada síncrona"| pedidos

    bff --> carrinho
    carrinho -->|"cota em LOTE"| cache
    cache -.-> catalogo
    catalogo --> dbcat
    carrinho -->|"reserva com TTL"| estoque

    bff ==>|"POST /v2/orders<br/>Idempotency-Key + oferta"| pedidos
    apub ==>|"sem carrinho:<br/>sem oferta, sem reserva"| pedidos

    pedidos ===>|"1 transação:<br/>pedido+snapshot+chave+outbox"| dbped
    relay -->|"SELECT ... FOR UPDATE SKIP LOCKED"| dbped
    relay -->|"publica ANTES de marcar<br/>at-least-once"| broker

    broker --> estoque
    broker --> pagto
    broker --> fraude
    broker --> notif
    estoque -.->|"evento de desfecho"| broker
    pagto -.-> broker
    notif -->|"webhook assinado"| parceiro

    style pedidos stroke-width:4px
    style dbped stroke-width:3px
    linkStyle 11 stroke:#080,stroke-width:3px
    linkStyle 13 stroke:#080,stroke-width:4px
```

---

## Leitura do diagrama

**A seta verde grossa para o banco é a decisão inteira.** Pedido, itens com snapshot, chave de idempotência e registro no outbox entram em **uma transação**. É daí que saem as garantias de `ADR-0001`, `ADR-0002` e `ADR-0003` — e é por isso que o store é relacional: não é preferência, é requisito.

**Não há seta de Pedidos para fora.** Nenhuma. O aceite é local (`ADR-0007`); tudo que exige resposta externa foi deslocado para **antes** (Carrinho: cotação e reserva) ou para **depois** (validadores, por evento).

**A API Pública entra direto em Pedidos, sem passar pelo Carrinho.** Parceiro não tem carrinho, logo não tem oferta nem reserva — e por isso sua taxa de rejeição pós-aceite é estruturalmente maior. Assimetria deliberada, não lacuna.

**O relay é um processo dentro de Pedidos, não um serviço.** Ele lê a tabela `outbox`, que pertence a Pedidos; um serviço separado lendo esse banco quebraria o ownership do mapa de domínios.

**O cache serve o Carrinho, não Pedidos.** Depois da criação, o pedido é autocontido: nenhuma leitura de pedido toca o Catálogo — garantido pelo teste que executa a consulta com o Catálogo fora do ar.

## Pontos de falha e degradação

| Componente | Se falhar | Aceite continua? |
|---|---|---|
| **Banco de Pedidos** | aceite para | ❌ **único SPOF** — multi-AZ obrigatório |
| Broker | eventos não saem, outbox acumula | ✅ |
| Relay | publicação atrasa | ✅ falha **silenciosa** — depende do SLI |
| Catálogo / Cache | não dá para montar carrinho | ✅ pedidos existentes seguem |
| Estoque / Pagamento | validação não conclui | ✅ ficam em `EM_VALIDACAO`; reconciliação assume |
| Gateway de Notificação | webhook falha | ✅ retry, backoff, DLQ — bulkhead |

**Dos sete componentes, apenas um derruba a criação.** Essa é a propriedade que o desenho compra em troca da complexidade assíncrona.

## O que **não** está aqui

Service mesh, CQRS, event sourcing, sharding e BFF por canal foram deliberadamente omitidos — cada um com o gatilho numérico que o traria de volta em `architecture.md`. Ausência é decisão, não esquecimento (`AV-08`).
