# ADR-0002 — Publicação confiável de eventos via Transactional Outbox

**Status:** Aceita — 2026-09-22
**Slug do PRD:** pedidos-catalogo
**Requisitos cobertos:** `CTX-07`, `CTX-08`, `P1-13`, `P1-14`, `P1-15`, `P2-08`
**Fontes:** `docs/technical-context/architecture.md`, `ADR-0001` (transação comum), `ADR-0007` (o outbox vira espinha dorsal)

---

## Contexto

Eventos de pedido são publicados sem garantia transacional (`CTX-07`). O problema é de **escrita dupla**: gravar no banco e publicar no broker são operações em sistemas diferentes, e não existe ordem segura entre elas.

```
COMMIT do pedido → publish()     falha no publish:
                                 pedido existe, evento nunca saiu

publish() → COMMIT do pedido     falha no commit:
                                 evento existe, pedido não
```

Qualquer ordem produz divergência entre o estado e o que o resto da plataforma acredita.

A `ADR-0007` elevou drasticamente o peso disso. Com aceite local e validação assíncrona, **o evento deixou de ser notificação e passou a ser o mecanismo de continuidade do processo**: se `PedidoRecebido` não sair, o pedido nunca é validado, nunca confirma e nunca chega ao cliente. Evento perdido deixa de ser aviso perdido e vira venda parada.

---

## Decisão

### Outbox na mesma base, na mesma transação

O evento é gravado como linha, junto com o pedido — nunca publicado durante a transação:

```
BEGIN
  INSERT pedido
  INSERT pedido_item        (com snapshot — ADR-0003)
  INSERT idempotency_key    (ADR-0001)
  INSERT outbox             { event_id, tipo, versao, chave_particao, payload }
COMMIT                      ← atômico
```

O evento existe **se e somente se** o pedido existir. A divergência deixa de ser possível por construção, não por cuidado de implementação.

**Fronteira comum com `ADR-0001`:** as duas ADRs escrevem na mesma transação. Em violação da `UNIQUE` de idempotência, a transação inteira é revertida — inclusive o outbox — e o fluxo segue para replay. Nunca há evento órfão de pedido não criado.

### Relay por polling, dentro do serviço de Pedidos

```
repetir:
   eventos ← SELECT * FROM outbox
             WHERE publicado_em IS NULL
             ORDER BY id LIMIT 100
             FOR UPDATE SKIP LOCKED

   para cada evento:
       broker.publish(evento)                ① publica
       UPDATE outbox SET publicado_em = now() ② marca
```

**A ordem entre ① e ② é a decisão**, não detalhe:

| Ordem | Falha no meio | Garantia |
|---|---|---|
| publica → marca | republica na retomada → duplica | **at-least-once** ✅ |
| marca → publica | marcado e nunca publicado → perde | at-most-once ❌ |

Escolhemos duplicar em vez de perder.

`FOR UPDATE SKIP LOCKED` permite múltiplas instâncias de Pedidos sem publicar o mesmo evento repetidamente — sem eleição de líder e sem componente novo.

### Deduplicação é obrigação do consumidor, declarada no contrato

At-least-once transfere responsabilidade. Todo consumidor deduplica por `event_id` com janela, e **isso entra no AsyncAPI** (`P2-07`), não em documentação à parte. Consumidor que não deduplica está violando contrato, não sendo descuidado.

### Ordenação por agregado, não global

`chave_particao = pedido_id`. Eventos de um mesmo pedido chegam em ordem; entre pedidos distintos, não há garantia — e não há requisito que exija.

### Expurgo obrigatório

Eventos publicados há mais de `???` dias são removidos. A ~3M eventos/dia do dimensionamento, ausência de expurgo transforma o outbox no maior objeto da base em poucos meses.

### SLI: idade do evento mais antigo não publicado

É a única métrica que detecta relay parado. A falha é **silenciosa**: nada quebra, o aceite continua respondendo `201`, e os pedidos simplesmente demoram cada vez mais a confirmar. Sem esse alerta, descobre-se pelo cliente.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **Outbox + relay por polling** | ✅ **Escolhida** | Garantia transacional sem componente novo, cabe em 30 dias (`CTX-11`) e reusa a transação que `ADR-0001` e `ADR-0003` já exigem |
| CDC / leitura do log de transação (Debezium) | ❌ Rejeitada — **por prazo e operação, não por mérito** | Latência menor e sem carga de polling. Mas adiciona componente operacional e acopla ao log interno do banco. Reavaliar se a latência de publicação virar problema medido |
| Two-phase commit entre banco e broker | ❌ Rejeitada | Acopla o commit do pedido à disponibilidade do broker — piora latência e disponibilidade ao mesmo tempo, e reintroduz o `CTX-17` pela porta dos fundos |
| Publicar após o commit (como é hoje) | ❌ Rejeitada | É precisamente o defeito descrito em `CTX-07` |
| Publicar antes do commit | ❌ Rejeitada | Inverte o dano: evento de pedido que não existe, gerando validação e notificação de venda inexistente. Pior que o atual |
| Event sourcing — o log de eventos como fonte da verdade | ❌ Rejeitada | Resolveria com mais poder, mas reescreve a persistência inteira para atender uma restrição que o outbox atende. Overengineering pela regra Q11 |

---

## Justificativa

A escolha não é pelo outbox ser elegante, e sim por ser a única opção que **reusa uma transação que já precisa existir**. `ADR-0001` exige a chave de idempotência no mesmo commit; `ADR-0003` exige o snapshot no mesmo commit. Acrescentar uma linha de evento a essa transação tem custo marginal próximo de zero e elimina uma classe inteira de inconsistência.

O CDC é tecnicamente superior em latência e carga. Foi rejeitado por prazo e por peso operacional — e isso está registrado como tal, para que a reavaliação seja decisão futura e não redescoberta.

---

## Trade-offs aceitos

- **At-least-once empurra trabalho para todo consumidor.** Cada um precisa deduplicar. Mitigado por estar no contrato, mas continua sendo custo distribuído por quem integra.
- **Latência de publicação = intervalo de polling.** Proposta de 200 ms a 1 s. Some-se ao p95 de confirmação — e é por isso que o alvo de confirmação (`ADR-0007`) não pode ser apertado sem revisitar esta decisão.
- **Carga adicional no banco.** O polling consulta continuamente, inclusive quando não há nada. Com índice parcial em `publicado_em IS NULL` o custo é baixo, mas não é zero.
- **O outbox acopla seu crescimento ao do pedido.** Mesma base, mesmo destino de backup e restore. Expurgo deixa de ser higiene e vira requisito.
- **Sem ordenação global.** Consumidor que dependa de ordem entre pedidos diferentes não é suportado. Restrição declarada, não omissão.
- **Falha silenciosa do relay.** Nada quebra quando ele para. Depende inteiramente do SLI de idade do evento mais antigo — e um alerta mal configurado equivale a não ter a garantia.

---

## Gatilho de revisão

**Se a latência de publicação p95 ultrapassar `???` ms de forma sustentada.** É o sinal que promove o CDC de alternativa rejeitada a necessidade — e a rejeição foi explicitamente por prazo, então a reabertura é esperada, não excepcional.

**Se a tabela de outbox passar a dominar o volume da base** mesmo com expurgo ativo. Indica que retenção e política de arquivamento precisam sair da mesma base.

**Se algum consumidor exigir ordenação global ou exactly-once.** Ambos estão fora do que esta decisão entrega; exigi-los reabre a escolha do mecanismo de transporte, não apenas do relay.

---

## Enforcement

**Fitness function primária — é a prova executável de `P2-08`:**

> **Falha entre commit e publicação.** O teste cria um pedido, derruba o relay **após** o commit e **antes** do publish, reinicia e verifica que o evento foi publicado, e que existe **exatamente uma** linha no outbox para aquele pedido. É a única forma de demonstrar que a garantia é real, e não acidente de caminho feliz.

**Complementares, no CI:**

1. **Atomicidade.** Rollback forçado do pedido não deixa linha no outbox. Cobre a fronteira com `ADR-0001`.
2. **Concorrência do relay.** Duas instâncias simultâneas não publicam o mesmo `event_id` mais de uma vez em condições normais — valida o `SKIP LOCKED`.
3. **Contrato de deduplicação.** O AsyncAPI declara `event_id` e a exigência de deduplicação. Validação de contrato falha se o campo sumir.
4. **Alerta de SLI.** Existência do alerta sobre idade do evento mais antigo não publicado é verificada como configuração, não como intenção.

```bash
# .claude/hooks/check-outbox-mesma-base.sh
# ADR-0002: a garantia depende de outbox e pedido na MESMA transação
if grep -rqiE 'outbox.*(connection|datasource|dsn).*(secundari|outra|events_db)' ./src; then
  echo "ADR-0002: outbox aparentemente em base separada do pedido." >&2
  echo "A garantia transacional exige a mesma base e a mesma transação." >&2
  exit 2
fi
```

**Limitação conhecida:** o grep detecta apenas o caso explícito de conexão nomeada. Uma separação feita por configuração externa passa despercebida — o teste de atomicidade é a rede que pega isso, e por isso é primário.

---

## Pendências registradas

- O intervalo de polling (200 ms a 1 s) é proposta; precisa ser calibrado contra o alvo de p95 de confirmação da `ADR-0007`.
- A janela de retenção do expurgo é `???`.
- O limiar de alerta para idade do evento mais antigo é `???`.
- A janela de deduplicação exigida do consumidor não está definida e precisa entrar no AsyncAPI — sem ela, a obrigação é vaga demais para ser cobrada.
- Não há inventário de consumidores atuais dos eventos (mesma pendência de `ADR-0004`). Sem ele, não se sabe quantos já deduplicam.
