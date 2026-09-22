# ADR-0007 — Aceitação assíncrona do pedido com validação posterior

**Status:** Aceita — 2026-09-22
**Slug do PRD:** pedidos-catalogo
**Requisitos cobertos:** `CTX-03`, `CTX-04`, `CTX-08`, `CTX-17`, `P1-10`, `P1-13`, `P1-15`
**Supersede:** `ADR-0003` seção (b) — caminho de leitura na criação
**Fontes:** `docs/technical-context/constraints.md` (§8), `docs/decisions/ADR-0003-...md`, `docs/business-context/jornada.md`

---

## Contexto

A ADR-0003 removeu o Catálogo do caminho de criação por meio do snapshot, e a evolução do desenho levou o preço a ser estabelecido no carrinho — não relido na criação. Isso resolveu a dependência de **preço**.

Restou a **disponibilidade de estoque**, que não pode receber o mesmo tratamento. A assimetria é de natureza, não de implementação:

| | Natureza | Congelável? |
|---|---|---|
| **Preço** | termo **acordado** entre as partes | ✅ é compromisso, e compromisso se registra |
| **Estoque** | recurso **contendido** com outros compradores | ❌ não se acorda estoque; ele é do mundo real |

Com verificação síncrona de estoque no aceite, o `CTX-17` apenas troca de parceiro e a aritmética permanece idêntica:

```
Pedidos 99,9% × Estoque 99,9%   = 99,8%  →  86,4 min/mês
Com pagamento síncrono também:
Pedidos × Estoque × Pagamento   = 99,7%  → 129,6 min/mês
Error budget de CTX-03                    →  43,2 min/mês
```

Cada dependência síncrona no caminho crítico multiplica a indisponibilidade. Três serviços a 99,9% entregam 99,7% — **três vezes** o budget.

O padrão consolidado de mercado resolve isso invertendo a ordem: marketplaces aceitam o pedido primeiro e validam estoque, pagamento e fraude em seguida.

---

## Decisão

O pedido é **aceito** de forma local e **validado** de forma assíncrona.

### Máquina de estados

```
POST /orders  →  201  RECEBIDO            operação local: valida a oferta
                        ↓ outbox              do carrinho, persiste, publica
                    EM_VALIDACAO          estoque · pagamento · fraude
                        ↓
            CONFIRMADO  ou  REJEITADO     → evento → cliente e parceiro
```

O handler de criação **não faz nenhuma chamada de saída**. Ele valida a oferta (dado local, vindo do carrinho), grava pedido, itens, snapshot e outbox na mesma transação, e responde.

### Dois SLOs, não um

Redefinir "criação" como "aceitação" torna o p95 de 500 ms trivial. Isso é legítimo e está declarado — mas exige uma segunda métrica, sob pena de otimizarmos o indicador em vez da experiência:

| Métrica | Alvo | O que mede |
|---|---|---|
| p95 de **aceitação** | ≤ 500 ms (`CTX-04`) | o pedido foi recebido e persistido |
| p95 de **confirmação** | `???` — proposto ≤ 30 s | o cliente sabe se a venda existe |
| Taxa de rejeição pós-aceite | `???` — a estabelecer | quanto do aceite é promessa vazia |

Sem as duas últimas, "500 ms" é número de vitrine.

### Pagamento: autorizar no aceite, capturar na confirmação

Aceitar o que talvez não se possa entregar exige que o dinheiro não seja movimentado antes da confirmação. Autorização reserva o limite sem capturar; captura ocorre em `CONFIRMADO`. Em `REJEITADO`, a autorização é liberada.

### Reserva no carrinho — otimização, não pré-requisito

Para canais próprios (web e app), reservar estoque no carrinho com TTL reduz a taxa de rejeição pós-aceite. **Não é condição para esta decisão funcionar**, e por isso entra aqui como otimização e não como ADR separada.

O canal de parceiro não tem carrinho e, portanto, não tem reserva — sua taxa de rejeição é estruturalmente maior. Isso é comportamento esperado do modelo, não defeito.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **Aceitação assíncrona com validação posterior** | ✅ **Escolhida** | Única que zera dependência síncrona no caminho crítico. Resolve `CTX-17` em vez de deslocá-lo, e transforma `CTX-08` em mecanismo primário |
| Validação síncrona de estoque no aceite | ❌ Rejeitada | 99,9% × 99,9% = 99,8% → 86,4 min/mês contra budget de 43,2. `CTX-03` inatingível, mesma armadilha da ADR-0003 com outro parceiro |
| Reserva no carrinho + confirmação síncrona rápida | ❌ Rejeitada | Reduz a janela mas mantém chamada síncrona no aceite; e o canal de parceiro, sem carrinho, fica sem cobertura |
| Aceitação assíncrona **sem** reserva alguma | ❌ Rejeitada | Funciona, mas eleva a rejeição nos canais próprios quando a redução é barata. Pior experiência sem ganho arquitetural |
| Two-phase commit com Estoque e Pagamento | ❌ Rejeitada | Acopla o commit do pedido à disponibilidade de dois serviços externos; piora latência e disponibilidade simultaneamente, e não escala ao 10× |
| Saga com compensação síncrona no aceite | ❌ Rejeitada | Mesma dependência síncrona, com complexidade adicional de compensação — o pior dos dois mundos |

---

## Justificativa

Uma decisão fecha três restrições que o enunciado trata separadamente:

1. **`CTX-17`** — sem chamada externa no caminho crítico, não há multiplicação de indisponibilidade.
2. **`CTX-04`** — sem chamada externa, o orçamento de latência deixa de ser restrição.
3. **`CTX-08`** — a notificação assíncrona de status deixa de ser acessório para parceiros e passa a ser o **canal primário de resultado** para todos os canais.

O item 3 é o mais consequente para a proposta: ele promove o outbox (ADR-0002) de correção de dívida técnica a espinha dorsal da plataforma. Os dois bullets que o PDF apresenta separados — validação de pedido e notificação de status — são, neste desenho, o mesmo mecanismo.

---

## Trade-offs aceitos

- **Oversell é agora um modo de operação, não um incidente.** Aceita-se o que talvez não se entregue. No varejo físico, cancelar depois tem custo de experiência e implicação frente ao Código de Defesa do Consumidor. Mitigado por autorizar-sem-capturar e por reserva nos canais próprios, **não eliminado**.
- **A reconciliação deixa de ser opcional** (`P1-15`). Pedido preso em `EM_VALIDACAO` é dinheiro parado e cliente sem resposta. Exige timeout, varredura periódica e política de desfecho — trabalho novo que não existia no desenho síncrono.
- **O estado do pedido vira o modelo de domínio central.** Ganho de clareza em DDD, custo de complexidade: transições precisam ser explícitas, testadas e observáveis.
- **Quebra semântica sob schema compatível.** O `201` deixa de significar "venda feita" e passa a significar "pedido recebido". Nenhum contract test de schema detecta isso. Tratado na **ADR-0004**, com fachada síncrona para v1 — e é o risco mais subestimado desta decisão.
- **O cliente não sabe na hora.** Para canais próprios é o padrão de mercado ("pedido em análise"); ainda assim, é degradação de experiência frente à confirmação imediata.

---

## Gatilho de revisão

**Quando a taxa de rejeição pós-aceite ultrapassar `???`% nos canais próprios** — o valor precisa ser estabelecido com o negócio antes da onda 60. Acima dele, o aceite vira promessa não confiável e a reserva no carrinho deixa de ser otimização e passa a ser obrigatória.

**Quando o p95 de confirmação passar de 30 s.** Indica que a validação assíncrona virou fila, não pipeline, e o cliente perde a noção de desfecho.

**Se houver exigência regulatória ou contratual de confirmação imediata** em algum canal. Isso reabre a decisão para aquele canal especificamente, provavelmente com reserva síncrona.

---

## Enforcement

**Fitness function primária — teste com as dependências desligadas:**

> O pipeline sobe Pedidos **sem Estoque e sem Pagamento** e verifica que `POST /orders` responde `201 RECEBIDO` e que o evento correspondente está no outbox. Se falhar, alguma validação voltou ao caminho síncrono.

**Complementares, no CI:**

1. **Teste de ausência de chamada de saída.** O handler de criação é executado com o cliente HTTP instrumentado; qualquer chamada externa falha o teste. Cobre o caso que o grep não pega.
2. **Teste de reconciliação.** Um pedido forçado a permanecer em `EM_VALIDACAO` além do timeout **precisa** aparecer no relatório de reconciliação. Garante que `P1-15` não seja documentação sem implementação.
3. **Teste de máquina de estados.** Transição não prevista (ex.: `REJEITADO` → `CONFIRMADO`) deve ser recusada pelo domínio, não pelo banco.

```bash
# .claude/hooks/check-aceite-local.sh
# ADR-0007: o handler de criação não pode fazer chamada de saída
if grep -rnE 'http(Client)?\.(get|post|put)|fetch\(|HttpClient' \
     ./src/pedidos/criacao 2>/dev/null; then
  echo "ADR-0007: chamada de saída no caminho de aceite do pedido." >&2
  echo "O aceite é local. Validação de estoque/pagamento é assíncrona." >&2
  exit 2
fi
```

**Limitação conhecida:** o grep não alcança chamada indireta por camada genérica de integração. O teste com dependências desligadas e o teste de ausência de chamada de saída são as redes que pegam esses casos — por isso são primários, e o grep é secundário.

---

## Pendências registradas

- O alvo de p95 de confirmação (proposto 30 s) e o limite de taxa de rejeição são `???`. Ambos precisam de dono no negócio antes da onda 60; sem eles, o gatilho de revisão não tem número.
- A política de desfecho para pedido preso em `EM_VALIDACAO` não está definida: cancela automaticamente, escala para atendimento, ou tenta novamente? Decisão de negócio.
- O TTL da reserva no carrinho não está definido e é o dial que calibra subvenda por carrinho abandonado.
- A interação com a idempotência (ADR-0001) precisa ficar explícita: retry após o aceite deve devolver o mesmo pedido em seu estado **corrente**, não recriar nem reverter para `RECEBIDO`.
