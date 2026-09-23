# Arquitetura

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** arquitetura-alvo da plataforma de Pedidos e Catálogo para o cenário de 90 dias. Diagramas C4 versionáveis em `docs/technical-context/c4/`.
**Requisitos cobertos:** `P1-07`, `P1-10`, `P1-14`, `P1-15`
**Fontes:** `docs/prd/pedidos-catalogo.md`, `docs/business-context/mapa-dominios.md`, `docs/technical-context/constraints.md`, `ADR-0003`, `ADR-0004`, `ADR-0007`
**Data:** 2026-09-23 *(escopo recortado a Pedidos e Catálogo)*

---

## Visão geral

**Estilo: serviços por bounded context, com criação de pedido local e validação orientada a eventos.**

A arquitetura não é orientada a eventos por preferência de estilo. Ela é assim porque a aritmética de disponibilidade não fecha de outro jeito: cada dependência síncrona no caminho crítico multiplica a indisponibilidade, e três serviços a 99,9% entregam 99,7% — três vezes o error budget de `CTX-03`.

A decisão estruturante é deslocar tudo o que exige resposta externa para **antes** (a cotação, que lê o Catálogo) ou para **depois** (a conferência dos termos contra o Catálogo, por evento). Sobra, no caminho crítico, uma operação puramente local: validar a assinatura da cotação, persistir e gravar o outbox na mesma transação.

Disso decorre a propriedade central do desenho: **o pedido é autocontido**. Nenhuma leitura de pedido depende de outro contexto, porque os termos acordados foram copiados, não referenciados.

---

## Componentes

**Borda / API Gateway**
Autenticação, autorização por escopo, quotas por parceiro e roteamento por versão (`/v1`, `/v2`). É a primeira fronteira de confiança e o ponto onde `P1-16` é implementado.

**BFF multi-canal** — web e app móvel
Agrega para os canais próprios. **Um só, não dois:** nenhuma restrição hoje justifica separar. Gatilho para dividir está na seção final.

**API Pública de Parceiros** — separada do BFF
Fronteira de confiança distinta: o parceiro é externo, o conteúdo que ele envia é **não confiável**, e o contrato dele é versionado e público (`CTX-08`). **Não cota**: submete os termos do sistema dele, conferidos depois.

**Cotação** — capacidade de Pedidos, não serviço separado
`POST /v2/quotes` lê o Catálogo **em lote** e devolve os termos assinados com validade. É a única leitura síncrona do Catálogo, e está **fora** do caminho crítico de criação.

**Serviço de Pedidos** — núcleo
Aceite local, máquina de estados, snapshot imutável dos termos, idempotência e outbox. **Não faz nenhuma chamada de saída no aceite** (`ADR-0007`).

**Relay do Outbox**
Lê o outbox e publica no broker, marcando o que já saiu. Garante at-least-once. Processo do próprio serviço de Pedidos — não há necessidade identificada para deploy separado.

**Broker de eventos**
Justificado por duas restrições, não por estilo: validação assíncrona (`ADR-0007`) e notificação assíncrona de status (`CTX-08`).

**Validador assíncrono**
Consome `PedidoRecebido` e confere os termos do pedido contra o Catálogo. Pedido **cotado** tem o preço honrado; pedido **sem cotação** (parceiro) é conferido contra o preço vigente.

**Gateway de Notificação a Parceiros**
Webhook assinado, retry com backoff e DLQ. Isola a indisponibilidade do parceiro do restante da plataforma — bulkhead natural.

**Store transacional de Pedidos** — relacional
Pedido, itens, snapshot, chave de idempotência e outbox **na mesma base**, porque precisam da mesma transação. Esta é a razão de ser relacional, não preferência.

**Cache / read model do Catálogo**
Serve **a cotação**, não a leitura de pedido. Também serve atributos operacionais fora do snapshot (mídia, atributos de vitrine) — e ali o miss **não pode falhar a requisição** (`ADR-0003`).

---

## Fluxo principal

### Criação de pedido — canal próprio

1. **Entrada.** Cliente navega; BFF chama `POST /v2/quotes`.
2. **Cotação.** Pedidos lê o Catálogo **em lote** e devolve os termos assinados: sku, preço, moeda, unidade, peso, promoção, validade.
3. **Submissão.** Cliente finaliza. BFF chama `POST /v2/orders` com `Idempotency-Key` e a oferta.
4. **Processamento — local.** Pedidos verifica a chave de idempotência, valida a oferta (assinatura e validade), e grava **em uma única transação**: pedido, itens, snapshot dos termos, chave de idempotência e registro no outbox.
5. **Saída.** Responde `201 RECEBIDO`. Nenhuma chamada externa ocorreu.
6. **Publicação.** O relay publica `PedidoRecebido`.
7. **Validação assíncrona.** O validador confere os termos contra o Catálogo e decide o desfecho.
8. **Desfecho.** Pedidos transiciona para `CONFIRMADO` ou `REJEITADO`, grava outbox; o relay publica; Notificação entrega ao cliente e ao parceiro.

### Criação de pedido — canal de parceiro

Idêntico a partir do passo 3, **sem** os passos 1 e 2: o parceiro não cota. Preço e atributos vêm no payload dele e são conferidos contra o Catálogo de forma assíncrona. Taxa de rejeição estruturalmente maior — esperado, não defeito.

### Consulta de pedido

Lê exclusivamente do store de Pedidos. **Nenhuma chamada ao Catálogo**, garantido por teste automatizado.

---

## Integrações

| Sistema | Modo | Fronteira |
|---|---|---|
| Catálogo | síncrono na cotação; assíncrono na validação | interna |
| Parceiros de marketplace | API pública versionada + webhook assinado | **externa, não confiável** |
| Fiscal, logística do 2º país | consumidores de evento | externa, fora do escopo |

---

## Fronteiras de confiança e pontos de falha (`P1-07`)

### Fronteiras

1. **Internet → borda (cliente final)** — autenticação de cliente, rate limit.
2. **Internet → API Pública (parceiro)** — a mais sensível: identidade de parceiro, quotas, e **conteúdo não confiável** que pode alcançar validação, log e, futuramente, prompt de IA.
3. **Borda → serviços internos.**
4. **Serviços → dados** — PII sob `CTX-09a`.
5. **Região Brasil ↔ Região EUA** — segregação de PII por domicílio do titular, conforme `ADR-0006`.

### Pontos de falha e modo de degradação

| Componente | Se falhar | Degradação |
|---|---|---|
| **Store de Pedidos** | aceite para | **SPOF real.** Multi-AZ é obrigatório, não opcional |
| Broker | eventos não saem | ✅ **Aceite continua.** Outbox acumula; nada se perde. Pedidos demoram mais a confirmar |
| Relay do outbox | publicação atrasa | ✅ Aceite continua; outbox acumula |
| Catálogo | não dá para cotar nem validar | ✅ **Aceite continua**; pedidos existentes seguem consultáveis; novos ficam em `RECEBIDO` e a reconciliação assume |
| Parceiro externo | webhook falha | ✅ Isolado no gateway: retry, backoff, DLQ. Não contamina a plataforma |

**A propriedade que o desenho compra:** de seis componentes, apenas um derruba a criação de pedido. Isso é consequência direta de não haver chamada de saída no aceite — e é o que torna `CTX-03` alcançável.

---

## Consistência: deduplicação e reconciliação (`P1-14`, `P1-15`)

**Deduplicação.** Entrega é at-least-once. Todo consumidor deduplica por `event_id` com janela; consumidor que não deduplica está errado, e isso entra no contrato AsyncAPI, não em documentação à parte.

**Reconciliação.** Deixa de ser opcional com a `ADR-0007`:

1. Pedidos em `EM_VALIDACAO` além do timeout → relatório diário e política de desfecho.
2. Divergência entre pedidos commitados e eventos publicados → varredura do outbox.
3. Cotações emitidas e nunca usadas, além da validade → expurgo.

---

## Decisões e trade-offs

- **Decisão:** nenhuma chamada de saída no aceite do pedido.
  - Motivo: `CTX-17` — cada dependência síncrona multiplica a indisponibilidade.
  - Trade-off: o cliente não sabe na hora se a venda existe; rejeição pós-aceite vira modo de operação, não incidente.

- **Decisão:** cotação assinada emitida pelo próprio Pedidos.
  - Motivo: estabelece o preço antes da criação e o carrega, em vez de relê-lo.
  - Trade-off: oferta expira; expiração obriga recotação e exposição do novo preço ao cliente.

- **Decisão:** outbox na mesma base do pedido.
  - Motivo: a garantia transacional exige uma transação só.
  - Trade-off: prende o store a um banco relacional e acopla o crescimento do outbox ao do pedido — exige política de expurgo.

- **Decisão:** API de parceiros separada do BFF.
  - Motivo: fronteira de confiança diferente e contrato público versionado.
  - Trade-off: mais um componente para operar e observar.

- **Decisão:** cotação como capacidade de Pedidos, não serviço separado.
  - Motivo: nenhuma restrição justifica um contêiner a mais (regra Q11); quem emite a cotação é quem precisa do resultado.
  - Trade-off: Pedidos passa a ter duas responsabilidades de leitura — cotar e consultar — com perfis de dependência diferentes.

- **Decisão:** um BFF para web e app.
  - Motivo: nenhuma restrição atual justifica dois (regra Q11).
  - Trade-off: necessidades divergentes de canal ficam em condicional dentro do BFF até o gatilho de divisão.

---

## O que **não** está nesta arquitetura

Registrado de propósito — `AV-08` avalia não superdimensionar. Cada linha traz o gatilho que a traria de volta.

| Ausente | Por que não | Traria de volta se… |
|---|---|---|
| Service mesh | 8 serviços não justificam o custo operacional | passar de ~20 serviços ou exigir mTLS uniforme por compliance |
| CQRS em Pedidos | leitura e escrita têm o mesmo modelo e o mesmo volume | leitura superar escrita em uma ordem de grandeza |
| Event sourcing | o snapshot já resolve auditoria (`CTX-06`) | exigência de reconstruir estado em qualquer ponto do tempo |
| Sharding do banco | 37,5 pedidos/s no pico e 1,1 TB/ano não justificam | passar de ~500 pedidos/s ou ~10 TB |
| Banco distribuído global | residência de dados favorece silo regional | transação cross-região virar requisito |
| BFF por canal | um atende ambos hoje | divergência de payload tornar o condicional ilegível |
| Read model do Catálogo em Pedidos | o snapshot tornou a leitura desnecessária | atributos fora do snapshot virarem caminho crítico |
| Estoque, Pagamento e Carrinho | **o enunciado não os nomeia** — incluí-los era inventar escopo | o Client Face confirmar que existem no caminho de criação |

---

## Gatilhos de revisão

- **Taxa de rejeição pós-aceite acima do limite** — o aceite vira promessa não confiável; a cotação deixa de ser otimização e passa a obrigatória, inclusive no canal de parceiro (`ADR-0007`).
- **p95 de confirmação acima de 30 s** — a validação assíncrona virou fila, não pipeline.
- **Terceiro conjunto de semânticas de contrato** — duas versões convivendo é gerenciável; três indica problema de modelagem (`ADR-0004`).
- **A plataforma real tiver integrações no caminho de criação** que o enunciado não nomeia — cada uma reintroduz o `CTX-17` e muda o dimensionamento da onda 30.
- **Residência de dados decidida** (`ADR-0006`) — define se Pedidos é regional, global ou híbrido, e pode mudar o store.
- **Volume real divergir de `PR-01`** — todo o dimensionamento da seção 7 de `constraints.md` deriva dele.
- **A cotação já existir na plataforma atual** — deixa de ser capacidade nova e vira evolução, reduzindo o esforço da onda 30.

---

## Riscos abertos

1. **O escopo foi recortado ao que o enunciado nomeia.** Pedidos e Catálogo, mais as capacidades que §2.2.1 exige. Se a plataforma real tiver outras integrações no caminho de criação, elas precisam ser tratadas com o mesmo critério do `CTX-17`.
2. **A fachada síncrona v1 (`ADR-0004`) reintroduz o `CTX-17` para os consumidores antigos.** Minoritário e temporário, mas precisa aparecer no relatório de disponibilidade **segmentado por versão**, não diluído na média.
3. **A cotação pode já existir na plataforma atual** em outra forma. Se existir, é evolução de algo, não capacidade nova — e o esforço da onda 30 muda.
4. **A residência de dados está indefinida** e pode invalidar a escolha de store único.

## Pendências registradas

- Diagramas C4 e de sequência (`P1-01` a `P1-06`) — próximo comando, `/c4`.
- Tabela de atributo de qualidade → mecanismo → métrica (`P1-08`) — em `/metricas`.
- Resiliência com valores concretos de timeout, retry, circuit breaker e bulkhead (`P2-04`) — `docs/technical-context/resiliencia.md`.
- ADR-0001 (idempotência) e ADR-0002 (outbox) detalham o passo 4 do fluxo principal e ainda não foram escritas.
