# Resiliência — contenção de falha em cascata

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** timeout, retry, circuit breaker, bulkhead e degradação controlada, com **valor concreto por dependência**. Padrão sem número é intenção, não mecanismo.
**Requisitos cobertos:** `P2-04`, `CTX-03`, `CTX-17`
**Fontes:** `docs/technical-context/constraints.md` (§7.2, §8), `ADR-0007`, `docs/technical-context/architecture.md`
**Data:** 2026-09-23

---

## O mecanismo mais forte é não ter a chamada

Antes de qualquer padrão de resiliência, vale registrar a decisão que torna a maioria deles desnecessária no caminho crítico: **o aceite do pedido não faz nenhuma chamada de saída** (`ADR-0007`).

Não existe timeout para chamada que não acontece. Não existe circuit breaker para dependência que não está lá. Os padrões abaixo protegem as bordas — cotação, notificação, validação — e **não** o caminho que `CTX-04` cronometra.

Isso importa porque é aritmético: cada dependência síncrona no caminho crítico multiplica a indisponibilidade. Três serviços a 99,9% entregam 99,7%, o triplo do error budget de `CTX-03`.

---

## Orçamento de tempo, antes dos valores

Timeout que não cabe no orçamento de latência é ficção. A cotação (Pedidos → Catálogo) tem **80 ms** no orçamento de `CTX-04`; qualquer timeout acima disso significa que o cliente já desistiu antes de a resposta chegar.

| Chamada | Orçamento | Timeout | Retentativas | Orçamento total pior caso |
|---|---|---|---|---|
| Cotação → Catálogo (lote) | 80 ms | **150 ms** | 1 | 300 ms + jitter |
| Validação assíncrona → Catálogo | fora do caminho crítico | **2 s** | 3, com backoff | — |
| Relay → Broker | fora do caminho crítico | **2 s** | infinitas, com backoff | — |
| Gateway → Webhook do parceiro | fora do caminho crítico | **5 s** | 6, em ~30 min | — |
| Aplicação → Banco | 120 ms | **1 s** | 0 | 1 s |

**O timeout do banco é maior e sem retry de propósito.** Retry de transação que pode ter commitado é como se duplica pedido. A idempotência protege o cliente; dentro do serviço, a regra é falhar e deixar o cliente reenviar com a mesma chave.

---

## Retry com backoff e jitter

Aplicável **somente** a operações idempotentes. A tabela acima marca quais.

```
espera = min(base × 2^tentativa, teto) × (0,5 + random(0,5))
```

| Dependência | Base | Teto | Tentativas |
|---|---|---|---|
| Catálogo (leitura) | 50 ms | 400 ms | 1 |
| Broker (publicação) | 200 ms | 30 s | ilimitadas |
| Webhook do parceiro | 5 s | 15 min | 6 → DLQ |

**O jitter não é detalhe.** Sem ele, N clientes que falharam juntos retornam juntos — a retentativa vira a segunda onda do mesmo incidente. O fator aleatório de 0,5 a 1,0 espalha a volta.

**Retry ao Catálogo é limitado a 1.** Com 80 ms de orçamento, a segunda tentativa já estourou o tempo do cliente. Retry aqui só faria sentido se a falha fosse instantânea, e nesse caso a origem provavelmente está fora.

---

## Circuit breaker

| Dependência | Abre em | Meio-aberto | Comportamento aberto |
|---|---|---|---|
| Catálogo | 50% de erro em 20 requisições / 10 s | 1 sonda a cada 5 s | serve do cache, marca a cotação como defasada |
| Catálogo (validação) | 50% em 20 req / 10 s | 1 sonda / 5 s | validação não conclui; pedido **permanece** em `RECEBIDO` |
| Webhook por parceiro | 5 falhas seguidas | 1 sonda / 60 s | acumula em fila; DLQ após a janela |

**O breaker do webhook é por parceiro, não global.** Um parceiro fora do ar não pode abrir o circuito dos demais — é o que transforma o gateway em bulkhead de verdade.

---

## Bulkhead — isolamento de recursos

| Pool | Limite | Protege contra |
|---|---|---|
| Conexões de banco — aceite | 60% do pool | consulta pesada consumir o caminho crítico |
| Conexões de banco — consulta | 30% do pool | — |
| Conexões de banco — relay e jobs | 10% do pool | expurgo/reconciliação afogarem o aceite |
| Workers de webhook, por parceiro | 5 simultâneos | parceiro lento monopolizar a entrega |
| Requisições por parceiro (quota) | por contrato | parceiro abusivo degradar os demais |

O bulkhead mais importante é o **gateway de notificação**: ele mantém a instabilidade dos parceiros — a fronteira mais imprevisível do desenho — fora da plataforma.

---

## Degradação controlada

Ordem de sacrifício, do menos ao mais doloroso:

| Nível | Situação | O que se degrada | O que **continua** |
|---|---|---|---|
| 1 | Catálogo lento | cotação usa cache; preço pode estar defasado | compra funciona |
| 2 | Catálogo fora | vitrine limitada a itens em cache | **pedidos existentes consultáveis** |
| 3 | Catálogo fora na validação | pedidos ficam em `RECEBIDO`; reconciliação assume | **aceite funciona** |
| 4 | Broker fora | outbox acumula; confirmação atrasa | **aceite funciona** |
| 5 | Relay parado | confirmação atrasa; outbox acumula | **aceite funciona** |
| 6 | Banco de Pedidos fora | **aceite para** | nada — é o único SPOF |

**Dos seis cenários, apenas o último derrota a criação de pedido.** Essa é a propriedade que o desenho compra em troca da complexidade assíncrona, e é o que torna `CTX-03` alcançável.

**Regra do que nunca degrada:** consulta de pedido responde sempre, porque o pedido é autocontido. Garantido pelo teste que executa `GET /orders/{id}` com o Catálogo fora do ar.

---

## O modo de falha que nenhum padrão cobre

**Relay parado é falha silenciosa.** Nada quebra: o aceite responde `201`, a API está no ar, os dashboards de erro ficam verdes. Os pedidos apenas demoram cada vez mais a confirmar.

Nenhum circuit breaker detecta, porque não há chamada falhando. Nenhum timeout dispara, porque nada está lento. A única coisa que detecta é o SLI:

> **idade do evento mais antigo não publicado** — alerta acima de **5 minutos**, que é 10× o p95 de confirmação alvo (30 s)

Implementado em `relay.idade_do_mais_antigo_pendente()` e coberto por `test_sli_de_relay_parado_detecta_pendencia`.

---

## O que **não** usamos

| Ausente | Por quê | Traria de volta se |
|---|---|---|
| Retry no caminho de escrita do pedido | duplicaria pedido; a idempotência é a resposta certa | nunca — é erro de padrão |
| Service mesh para resiliência | 8 serviços não pagam o custo operacional | passar de ~20 serviços |
| Fallback com resposta sintética de preço | inventar preço é pior que recusar a venda | nunca |
| Retry no webhook sem DLQ | fila infinita esconde parceiro quebrado | nunca |

---

## Riscos abertos

1. **Todos os valores desta página são pontos de partida, não medições.** Foram derivados do orçamento de latência de `constraints.md` §7.2, que por sua vez usa uma estimativa de ~40 ms por chamada ao Catálogo — ordem de grandeza, não medição. Precisam ser recalibrados com dado real antes da onda 60.
2. **O limiar do SLI de relay parado (5 min) é derivado, não medido.** Precisa ser recalibrado contra o comportamento real do polling na onda 30 — se o intervalo efetivo for maior que o previsto, 5 min gera ruído.
3. **Circuit breaker por parceiro exige estado por parceiro.** Com muitos parceiros, isso vira cardinalidade de métrica e memória no gateway. Não é problema hoje; é gatilho de revisão.

## Pendências registradas

- Calibrar todos os timeouts contra medição real na onda 30 (tarefa P1 do plano).
- Definir o limiar de alerta do SLI de outbox junto com o alvo de p95 de confirmação.
- Testes de injeção de falha (chaos leve) não estão no escopo das 3 ondas e ficam registrados como débito aceito em `riscos-premissas.md`.
