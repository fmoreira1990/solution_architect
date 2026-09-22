# Mapa de Domínios — Pedidos e Catálogo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** bounded contexts, ownership de dados e relacionamentos entre contextos. A topologia de execução está em `docs/technical-context/architecture.md`.
**Requisitos cobertos:** `P1-09`, `P1-10`
**Fontes:** `docs/prd/pedidos-catalogo.md`, `docs/technical-context/constraints.md`, `docs/decisions/ADR-0003`, `ADR-0004`, `ADR-0007`
**Data:** 2026-09-22

---

## 1. Contextos

### Core — onde está a vantagem competitiva

**Pedidos** · *núcleo do problema*
Aceita, valida e acompanha o ciclo de vida do pedido. Dono da máquina de estados, do snapshot dos termos, da chave de idempotência e do outbox.
**Ownership:** `pedido`, `pedido_item`, `snapshot de termos`, `idempotency_key`, `outbox`, `transicao_estado`.
**Não é dono de:** preço vigente, saldo de estoque, transação de pagamento.

**Carrinho e Oferta** · *contexto novo, emergiu da `ADR-0007`*
Monta o carrinho, **cota** o preço e emite a **oferta assinada** com validade. Opcionalmente reserva estoque para canais próprios.
**Ownership:** `carrinho`, `oferta`, `reserva`.
Existe porque o preço precisa ser estabelecido **antes** da criação e carregado por ela — é o que remove a leitura de catálogo do caminho crítico.

### Supporting — necessários, não diferenciais

**Catálogo** — produto, preço vigente, unidade de medida, peso, dimensões, mídia.
**Ownership:** `produto`, `preco_vigente`, `atributo`. Upstream de Carrinho.

**Estoque** — saldo, reserva e baixa. Recurso **contendido**: não é congelável (`ADR-0007`).
**Ownership:** `saldo`, `reserva`, `movimento`.

**Pagamento** — autorização, captura e estorno. Autoriza no aceite, captura na confirmação.
**Ownership:** `transacao`, `autorizacao`.

**Notificação e Parceiros** — entrega assíncrona de mudança de status, com assinatura, retry e DLQ.
**Ownership:** `assinatura_webhook`, `tentativa_entrega`, `dlq`.

**Identidade e Acesso** — autenticação de cliente e de parceiro, escopos, quotas por parceiro.
**Ownership:** `credencial_parceiro`, `escopo`, `quota`.

### Fora do escopo

**Fiscal, logística e meios de pagamento locais do segundo país** — escopo OUT nº 3 do PRD. Aparecem no mapa apenas como consumidores de evento, para que a fronteira fique explícita.

---

## 2. Context map

```
                    ┌──────────────┐
                    │   Catálogo   │  (upstream)
                    └──────┬───────┘
                           │ Customer/Supplier + ACL
                           ▼
   cliente ──────►  ┌──────────────┐
                    │  Carrinho e  │──── reserva ───► Estoque
                    │    Oferta    │
                    └──────┬───────┘
                           │ OFERTA ASSINADA
                           │ (Published Language)
                           ▼
 parceiro ───────►  ┌──────────────┐
  (sem oferta)      │   PEDIDOS    │  ◄── núcleo
                    └──────┬───────┘
                           │ eventos de domínio (Open Host Service)
              ┌────────────┼────────────┬──────────────┐
              ▼            ▼            ▼              ▼
          Estoque     Pagamento    Notificação      Fiscal
                                   e Parceiros    (fora do escopo)
```

| De → Para | Padrão | Por quê |
|---|---|---|
| Carrinho → Catálogo | **Customer/Supplier + ACL** | Catálogo tem modelo rico e ciclo próprio; a ACL traduz produto em oferta enxuta e protege Carrinho de mudanças upstream |
| Carrinho → Pedidos | **Published Language** — a oferta assinada | A oferta é contrato explícito e versionado entre os dois, não acoplamento de modelo. É o que permite Pedidos aceitar sem consultar ninguém |
| Carrinho → Estoque | **Customer/Supplier**, síncrono | Reserva exige resposta imediata; fica **fora** do caminho crítico de criação, no momento do carrinho |
| Pedidos → Estoque, Pagamento | **Customer/Supplier**, assíncrono por evento | `ADR-0007`: validação posterior. Nenhuma chamada de saída no aceite |
| Pedidos → Notificação, Fiscal | **Open Host Service** | Pedidos publica eventos de domínio versionados; consumidores se inscrevem sem que Pedidos os conheça |
| Parceiro → Pedidos | **Open Host Service + Published Language** | OpenAPI e AsyncAPI versionadas (`CTX-08`). Fronteira de confiança: conteúdo do parceiro é **não confiável** |

**Assimetria deliberada entre canais.** Canal próprio traz oferta e reserva; parceiro não tem carrinho e, portanto, não tem nenhum dos dois. A consequência — taxa de rejeição pós-aceite estruturalmente maior no canal de parceiro — é comportamento esperado do modelo, e está registrada na `ADR-0007`.

---

## 3. Ownership de dados — quem pode escrever

| Dado | Dono | Quem lê | Regra |
|---|---|---|---|
| `preco_vigente` | Catálogo | Carrinho | Ninguém além do Catálogo escreve |
| `oferta` (preço cotado + validade + assinatura) | Carrinho | Pedidos | Imutável após emissão; expira por tempo |
| `snapshot` no item do pedido | Pedidos | todos | **Imutável para sempre.** Cópia dos termos, não referência |
| `saldo` e `reserva` | Estoque | Carrinho, Pedidos | Recurso contendido; nunca congelado |
| `estado do pedido` | Pedidos | todos | Só Pedidos transiciona; transição inválida é recusada pelo domínio |
| `outbox` | Pedidos | relay | Escrito na **mesma transação** do pedido |

**A regra que sustenta o desenho:** o pedido é **autocontido** no que diz respeito a termos acordados. Nenhuma leitura de pedido depende de outro contexto — verificado pelo teste com o Catálogo desligado (`ADR-0003`, Enforcement).

---

## 4. Integração síncrona × assíncrona (`P1-10`)

| Integração | Modo | Consistência | Justificativa |
|---|---|---|---|
| Carrinho → Catálogo | **síncrona** | forte no instante da cotação | O cliente precisa ver preço agora. Está fora do caminho crítico de criação, então não afeta `CTX-04` nem `CTX-17` |
| Carrinho → Estoque (reserva) | **síncrona** | forte | Reserva exige confirmação imediata; recurso contendido não tolera consistência eventual |
| Canal → Pedidos (aceite) | **síncrona, porém local** | forte, sem dependência externa | É o caminho crítico. Zero chamada de saída (`ADR-0007`) |
| Pedidos → Estoque, Pagamento (validação) | **assíncrona** | eventual | Trocar acoplamento por tempo: o pedido existe antes de ser confirmado |
| Pedidos → Notificação e demais consumidores | **assíncrona** | eventual, at-least-once | `CTX-08`. Consumidor deduplica por `event_id` |
| Notificação → Parceiro (webhook) | **assíncrona** | at-least-once, com retry e DLQ | Parceiro é externo e indisponível com frequência; entrega precisa sobreviver a isso |

**Critério aplicado:** síncrono apenas quando alguém **espera a resposta para decidir agora**. Todo o resto é assíncrono — porque cada dependência síncrona no caminho crítico multiplica a indisponibilidade (`CTX-17`).

---

## 5. Riscos abertos

1. **Carrinho e Oferta é contexto novo.** Não estava no enunciado e nasceu do desenho. Se a plataforma atual já tiver um carrinho com modelo próprio, a oferta assinada é acréscimo a ele, não contexto novo — e o esforço da onda 30 muda.
2. **A fronteira entre Carrinho e Pedidos pode ser artificial.** Se na prática forem o mesmo time e o mesmo deploy, a separação é lógica e não física. Isso é aceitável, mas precisa ser dito — separar contexto não obriga a separar serviço.
3. **Estoque e Pagamento são tratados como existentes.** O enunciado não os menciona. Se não existirem como serviços, a `ADR-0007` pressupõe integrações que precisam ser construídas — e a onda 30 não cabe em 30 dias.

## Pendências registradas

- O glossário da linguagem ubíqua está em `docs/business-context/glossario.md`.
- A decisão de residência de dados (`ADR-0006`) definirá se Pedidos é regional, global ou híbrido. Até lá, o mapa é agnóstico de região.
- Não há inventário dos consumidores atuais dos eventos de Pedidos — mesma pendência levantada na `ADR-0004`.
