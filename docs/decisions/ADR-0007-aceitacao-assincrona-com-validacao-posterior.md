# ADR-0007 — Aceitação assíncrona do pedido com validação posterior

**Status:** Aceita — 2026-09-22
**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** **em que momento do ciclo de vida** o pedido é validado contra o Catálogo. Não decide as regras de validação em si — decide que ela é posterior ao aceite.
**Requisitos cobertos:** `CTX-03`, `CTX-04`, `CTX-08`, `CTX-17`, `P1-10`, `P1-13`, `P1-15`
**Supersede:** `ADR-0003` seção (b) — caminho de leitura na criação
**Fontes:** `docs/technical-context/constraints.md` (§8), `ADR-0003`, `docs/business-context/jornada.md`
**Data:** 2026-09-22

---

## Contexto

A `ADR-0003` removeu o Catálogo do caminho de **leitura** por meio do snapshot: consultar um pedido não depende mais dele. Restou a dependência no caminho de **criação** — validar que os termos submetidos correspondem ao Catálogo.

Essa validação não pode ser resolvida por snapshot, e a assimetria é de natureza:

| | Natureza | Congelável? |
|---|---|---|
| **Termos acordados** (preço, descrição, unidade) | compromisso entre as partes | ✅ é acordo, e acordo se registra |
| **Correspondência com o Catálogo** | estado do mundo **no instante da validação** | ❌ não se acorda; é verificação |

O canal de parceiro torna isso concreto: o parceiro submete preço e descrição vindos do sistema **dele**. Alguém precisa conferir contra o Catálogo — e fazer isso de forma síncrona reintroduz o `CTX-17`:

```
Pedidos 99,9% × Catálogo 99,9%  =  99,8%  →  86,4 min/mês
Error budget de CTX-03                     →  43,2 min/mês
```

Cada dependência síncrona no caminho crítico multiplica a indisponibilidade. A aritmética é a mesma da `ADR-0003` §8 de `constraints.md`, com o Catálogo no papel que antes era da leitura de preço.

O padrão consolidado de mercado resolve invertendo a ordem: aceita-se o pedido primeiro e valida-se em seguida.

## Decisão

O pedido é **aceito** de forma local e **validado** de forma assíncrona.

### Máquina de estados

```
POST /orders  →  201  RECEBIDO            operação local: valida a cotação
                        ↓ outbox              assinada, persiste, publica
                    EM_VALIDACAO          confere os termos contra o Catálogo
                        ↓
            CONFIRMADO  ou  REJEITADO     → evento → cliente e parceiro
```

O handler de criação **não faz nenhuma chamada de saída**. Ele valida a cotação (assinatura e validade — verificação local), grava pedido, itens, snapshot e outbox na mesma transação, e responde.

### Dois SLOs, não um

Redefinir "criação" como "aceitação" torna o p95 de 500 ms trivial. Isso é legítimo e está declarado — mas exige uma segunda métrica, sob pena de otimizarmos o indicador em vez da experiência:

| Métrica | Alvo | O que mede |
|---|---|---|
| p95 de **aceitação** | ≤ 500 ms (`CTX-04`) | o pedido foi recebido e persistido |
| p95 de **confirmação** | **≤ 30 s** | o cliente sabe se a venda existe |
| Taxa de rejeição pós-aceite | **≤ 2%** canal próprio · **≤ 8%** parceiro | quanto do aceite é promessa vazia |

**De onde vêm os números.** Os 30 s não são arbitrários: o relay opera com polling de 200 ms a 1 s, e a validação é uma consulta ao Catálogo — 30 s dá duas ordens de grandeza de folga e ainda é rápido o bastante para o cliente não abandonar a tela. Os limites de rejeição refletem a assimetria do desenho: o canal próprio **cota antes**, então rejeição ali é anomalia; o parceiro **não cota**, então rejeição é o funcionamento normal do modelo.

Sem as duas últimas, "500 ms" é número de vitrine.

### Cotação assinada — otimização, não pré-requisito

Canais próprios obtêm uma **cotação** antes de submeter o pedido: `POST /v2/quotes` lê o Catálogo e devolve os termos assinados com validade. A criação valida a assinatura **localmente** e honra o preço cotado, mesmo que o Catálogo mude depois.

Isso reduz a rejeição pós-aceite a praticamente zero nesses canais — mas **não é condição para a decisão funcionar**, e por isso entra como otimização, não como ADR separada.

O canal de parceiro **não tem cotação**: ele submete preço e descrição do sistema dele. A conferência contra o Catálogo acontece na validação assíncrona, e sua taxa de rejeição é estruturalmente maior. Comportamento esperado do modelo, não defeito.

**A cotação é capacidade do próprio Pedidos**, não um contexto separado: ela existe para tirar a leitura do Catálogo do caminho crítico, e quem a emite é quem precisa do resultado.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **Aceitação assíncrona com validação posterior** | ✅ **Escolhida** | Única que zera dependência síncrona no caminho crítico. Resolve `CTX-17` em vez de deslocá-lo, e transforma `CTX-08` em mecanismo primário |
| Conferência síncrona contra o Catálogo no aceite | ❌ Rejeitada | 99,9% × 99,9% = 99,8% → 86,4 min/mês contra budget de 43,2. `CTX-03` inatingível — a mesma aritmética que a `ADR-0003` já havia enfrentado no caminho de leitura |
| Cotação prévia + conferência síncrona rápida no aceite | ❌ Rejeitada | Reduz a janela mas mantém chamada síncrona; e o canal de parceiro, que não cota, fica sem cobertura |
| Aceitação assíncrona **sem** cotação alguma | ❌ Rejeitada | Funciona, mas eleva a rejeição nos canais próprios quando a redução é barata. Pior experiência sem ganho arquitetural |
| Two-phase commit entre Pedidos e Catálogo | ❌ Rejeitada | Acopla o commit do pedido à disponibilidade do Catálogo; piora latência e disponibilidade ao mesmo tempo, e não escala ao 10× |
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

- **Rejeição pós-aceite vira modo de operação, não incidente.** Aceita-se um pedido que pode ser recusado depois. No varejo, recusar após aceitar tem custo de experiência e implicação frente ao Código de Defesa do Consumidor. Mitigado pela cotação assinada nos canais próprios, **não eliminado** — e no canal de parceiro não há mitigação possível.
- **A reconciliação deixa de ser opcional** (`P1-15`). Pedido preso em `EM_VALIDACAO` é dinheiro parado e cliente sem resposta. Exige timeout de **24 h**, varredura diária e cancelamento automático com notificação — trabalho novo que não existia no desenho síncrono.
- **O estado do pedido vira o modelo de domínio central.** Ganho de clareza em DDD, custo de complexidade: transições precisam ser explícitas, testadas e observáveis.
- **Quebra semântica sob schema compatível.** O `201` deixa de significar "venda feita" e passa a significar "pedido recebido". Nenhum contract test de schema detecta isso. Tratado na **ADR-0004**, com fachada síncrona para v1 — e é o risco mais subestimado desta decisão.
- **O cliente não sabe na hora.** Para canais próprios é o padrão de mercado ("pedido em análise"); ainda assim, é degradação de experiência frente à confirmação imediata.

---

## Gatilho de revisão

**Quando a taxa de rejeição pós-aceite ultrapassar 2% nos canais próprios.** Acima disso o aceite vira promessa não confiável, e a cotação assinada deixa de ser otimização e passa a ser obrigatória — inclusive para o canal de parceiro, que hoje não cota.

**Quando o p95 de confirmação passar de 30 s.** Indica que a validação assíncrona virou fila, não pipeline, e o cliente perde a noção de desfecho. É também o gatilho de reavaliação do CDC na `ADR-0002`.

**Se houver exigência regulatória ou contratual de confirmação imediata** em algum canal. Isso reabre a decisão para aquele canal especificamente, provavelmente com conferência síncrona e o custo de disponibilidade que ela traz.

---

## Enforcement

**Fitness function primária — teste com as dependências desligadas:**

> O pipeline sobe Pedidos **com o Catálogo fora do ar** e verifica que `POST /orders` responde `201 RECEBIDO` e que o evento correspondente está no outbox. Se falhar, alguma validação voltou ao caminho síncrono.

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
  echo "O aceite e local. A conferencia contra o Catalogo e assincrona." >&2
  exit 2
fi
```

**Limitação conhecida:** o grep não alcança chamada indireta por camada genérica de integração. O teste com dependências desligadas e o teste de ausência de chamada de saída são as redes que pegam esses casos — por isso são primários, e o grep é secundário.

---

## Pendências registradas

- Os alvos de p95 de confirmação (30 s) e de taxa de rejeição (2% / 8%) **precisam de validação com o negócio** antes da onda 60. São números defensáveis, não medidos.
- **Política de desfecho para pedido preso:** após **24 h** em validação, o pedido é cancelado automaticamente e o cliente notificado. O prazo é largo de propósito — três ordens de grandeza acima do p95 de confirmação (30 s), então só alcança pedido genuinamente travado, nunca pedido lento. Aguarda validação da operação.
- A validade da cotação está implementada em 30 minutos (`oferta.emitir`, `validade_segundos=1800`). Precisa de confirmação do negócio: validade curta aumenta recotação, validade longa aumenta o risco de honrar preço defasado.
- A interação com a idempotência (ADR-0001) precisa ficar explícita: retry após o aceite deve devolver o mesmo pedido em seu estado **corrente**, não recriar nem reverter para `RECEBIDO`.
