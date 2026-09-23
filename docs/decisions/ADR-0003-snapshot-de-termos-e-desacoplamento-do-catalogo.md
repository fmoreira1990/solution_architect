# ADR-0003 — Snapshot dos termos negociados e desacoplamento do Catálogo

**Status:** Aceita — 2026-09-22 · **seção (b) superseded por `ADR-0007` em 2026-09-22**
**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** o **registro** dos termos acordados no pedido. A seção (b), sobre o caminho de leitura na criação, foi superseded pela `ADR-0007` e está mantida para preservar o raciocínio.
**Requisitos cobertos:** `CTX-03`, `CTX-04`, `CTX-05`, `CTX-06`, `CTX-17`, `P1-11`
**Fontes:** `docs/technical-context/constraints.md` (§7.2, §8), `docs/business-context/jornada.md`, `docs/prd/pedidos-catalogo.md`
**Data:** 2026-09-22 *(seção (b) superseded em 2026-09-22)*
**Nota de numeração:** a numeração segue o mapa de temas publicado em `ROTEIRO-EXECUCAO.md` §F2, não a ordem de criação. Esta é a primeira ADR escrita.

---

## Contexto

Pedidos consulta o Catálogo de forma síncrona, uma vez por item (`CTX-05`), e não registra preço nem descrição no momento da compra (`CTX-06`). Três restrições se combinam sobre esse desenho.

**1. O SLA não fecha na aritmética.** Com dependência síncrona no caminho crítico, a disponibilidade percebida é o produto das duas:

```
Pedidos 99,9% × Catálogo 99,9% = 99,8%
99,8% de 43.200 min/mês        → 86,4 min indisponível
Error budget de CTX-03         → 43,2 min

Estouro de 2×, no cenário em que tudo o mais funciona.
```

Isso independe da qualidade do código. Nenhuma implementação de uma chamada síncrona faz 99,9% × 99,9% valer 99,9%.

**2. O orçamento de latência já está estourado.** Com 9 chamadas a ~40 ms, um pedido de 8 itens consome 360 ms dos 500 ms de `CTX-04`, sobrando 140 ms para autenticação, idempotência, domínio, persistência e resposta. No p95 de 15 itens (`PR-02`), as 16 chamadas consomem 640 ms e violam o SLA sozinhas.

**3. A dor da auditoria é irreversível.** Sem snapshot, não há como provar qual preço o cliente viu quando o Catálogo muda depois. O dado não está perdido — **nunca existiu**. É a única dor do ANTES que nenhuma correção futura desfaz, e a razão de o backfill estar no escopo OUT do PRD.

Ao 10× (`CTX-02`), o N+1 multiplica duas vezes — por item e por pedido concorrente — e o Catálogo passa a receber ~338 req/s contra 37,5 de Pedidos. Ele satura antes e derruba a criação junto.

---

## Decisão

Duas sub-decisões acopladas, porque nenhuma isolada resolve `CTX-17`.

### (a) O registro — snapshot imutável dos termos negociados

O item do pedido passa a carregar os termos acordados no momento da compra, tornando o pedido **autocontido**:

```
pedido_item
  pedido_id, sku, quantidade
  descricao          ← congelado
  preco_unitario     ← congelado
  moeda              ← congelado
  promocao_id        ← congelado
  catalogo_versao    ← qual versão foi lida
  lido_em            ← quando foi lido
```

**Fronteira do que congela** — decisão de domínio, não de implementação:

> **Critério, e não lista:** congela tudo que serviu de base a um **compromisso assumido com o cliente**. O resto é operacional e pode ser relido sem alterar o que foi acordado.

| Congela | Por que é compromisso | Não congela | Por que é operacional |
|---|---|---|---|
| Preço unitário, moeda | base do valor cobrado | Status de entrega | estado que evolui por natureza |
| Descrição e atributos exibidos | o cliente comprou o que viu | Correspondência com o Catálogo | é verificação do mundo no instante, não acordo (ver ADR-0007) |
| Promoção aplicada | condição da compra | Dados cadastrais do cliente | ciclo próprio e sujeito a LGPD |
| **Unidade de medida** | "quantidade 2" não significa nada sem "kg" ou "un" | Localização no armazém, curva ABC | nunca foi prometido a ninguém |
| **Peso e dimensões** | base do **frete cotado** ao cliente | Fornecedor atual | interno, invisível ao cliente |
| Versão do catálogo lida | evidência de auditoria | Imagens e mídia | apresentação, não termo |

**Unidade de medida e peso foram adicionados** após a revisão de 2026-09-22. A tabela original tratou apenas os casos óbvios (preço e descrição) e deixaria de fora dois atributos que são base de compromisso: a unidade define o que foi comprado, e o peso define o frete que foi cobrado. Ambos são baratos de armazenar e caros de errar.

**Regra para o que sobrou fora do snapshot:** se o atributo não é base de compromisso, o cache que o serve **não pode falhar a requisição** em caso de miss — degrada exibindo vazio ou busca depois. Cache que pode falhar no caminho de leitura de pedido é dependência disfarçada, e o teste com o Catálogo desligado (seção Enforcement) a detecta.

### (b) O caminho de leitura na criação — ⚠️ SUPERSEDED por `ADR-0007`

> **Esta seção não vale mais.** Mantida na íntegra porque o raciocínio que a derrubou tem valor: ver "Por que foi superseded", abaixo.

~~**Onda 30:** resolução **em lote** (9 → 2 chamadas) + cache com TTL e **fallback explícito para entrada expirada** quando o Catálogo não responde.~~
~~**Onda 60/90:** avaliar **read model** do catálogo dentro de Pedidos, alimentado por evento, se o cache não sustentar o p95 sob 10×.~~
~~**Regra de negócio do fallback:** sob indisponibilidade do Catálogo, o pedido é criado com a última entrada conhecida, marcado com `fallback=true`.~~

#### Por que foi superseded

Dois argumentos independentes derrubaram a solução de cache, e a convergência entre eles é o que justifica a mudança de posição:

1. **Pelo lado da fidelidade da cotação.** A divergência real não é entre cache e Catálogo — é entre o preço que o cliente viu em T0 e o que Pedidos leria em T1, intervalo que pode ser de dias. Pior: **invalidação mais rápida piora a fidelidade**, porque destrói o preço cotado mais cedo. Frescor e estabilidade de cotação são requisitos opostos e não saem do mesmo mecanismo.

2. **Pelo lado da disponibilidade.** Cache com fallback reduz a janela de indisponibilidade, mas não zera a dependência: no miss, a chamada síncrona volta, e o `CTX-17` com ela.

A saída — preço estabelecido em uma **cotação prévia** e não relido na criação — elimina a leitura em vez de otimizá-la. Isso expôs que a dependência restante era a **conferência dos termos contra o Catálogo**, que não pode ser congelada por ser verificação e não acordo, e levou à aceitação assíncrona da `ADR-0007`.

**Nota de processo:** a alternativa "read model por evento" havia sido rejeitada abaixo *por prazo, não por mérito*. Ela foi alcançada de novo por um caminho independente — o da correção de negócio —, o que confirma que a rejeição por prazo merecia reexame. O desfecho foi melhor que o read model: nenhuma leitura, em vez de uma leitura local.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **Snapshot + lote + cache com fallback** | ✅ **Escolhida** | Única que resolve `CTX-03`, `CTX-04`, `CTX-05` e `CTX-06` simultaneamente, e cabe nos 30 dias de `CTX-11` |
| Apenas resolução em lote | ❌ Rejeitada | Corrige o N+1 (9→2) e o orçamento de latência, mas **mantém a dependência síncrona** — `CTX-17` continua valendo e `CTX-03` continua inatingível. Não resolve auditoria |
| Apenas cache com TTL, sem snapshot | ❌ Rejeitada | Reduz carga e latência média, mas não move o p95 que o SLA cobra: com 90% de acerto por SKU, só **43%** dos pedidos de 8 itens ficam totalmente em cache (0,9⁸), e **21%** nos pedidos de 15 itens. O p95 é governado pelos misses. E cache é otimização, não registro: não serve para auditoria |
| Exigir 99,99% do Catálogo | ❌ Rejeitada | Transfere o custo para outro time sem eliminar a dependência, e depende de um compromisso que Pedidos não controla |
| Read model replicado por evento já na onda 30 | ❌ Rejeitada — **por prazo, não por mérito** | É a solução mais forte e resolve `CTX-17` definitivamente. Mas exige contrato de evento do Catálogo, sincronização inicial e política de reconciliação — não cabe em 30 dias sem janela (`CTX-11`). Reavaliada na onda 60 |
| Event sourcing do pedido | ❌ Rejeitada | Resolveria auditoria com muito mais poder, mas reescreve o modelo de persistência inteiro para atender uma restrição que o snapshot atende. Overengineering sob a regra Q11 |

---

## Justificativa

O argumento decisivo não é que desacoplar seja boa prática. É que **com a dependência síncrona o SLA é matematicamente inatingível**: 99,9% × 99,9% = 99,8%, o dobro do error budget. Esse cálculo transforma uma preferência de design em restrição dura.

A escolha se sustenta por alavancagem: uma decisão fecha quatro restrições que o enunciado apresenta separadamente. Nenhuma alternativa avaliada fecha mais de duas.

A separação entre (a) e (b) é deliberada. Confundir snapshot com cache é o erro mais provável aqui, e eles resolvem problemas diferentes em tempos diferentes: **cache é otimização** — se sumir, você busca de novo e obtém o mesmo resultado; **snapshot é registro** — se sumir, a informação se perde, porque a fonte já mudou.

---

## Trade-offs aceitos

- **Desnormalização deliberada.** Descrição e preço passam a existir em dois lugares. São ~4,8M linhas de item/dia no alvo, cada uma carregando texto que antes era referência — ~3 GB/dia, ~1,1 TB/ano. Exige política de particionamento e arquivamento.
- **Correção de cadastro não propaga.** Descrição cadastrada errada não se corrige nos pedidos já emitidos pela via normal. **Na maioria dos casos isso é o comportamento certo**, mas exige processo explícito de exceção para os casos em que não é — sem esse processo, a decisão vira armadilha operacional.
- ~~O fallback aceita vender a preço defasado.~~ **Trade-off extinto com a seção (b).** A `ADR-0007` substituiu o fallback pela cotação assinada: o preço não é relido na criação, então não há defasagem a tolerar. A pergunta sobre o limite tolerável sobreviveu à resposta por um tempo, e foi removida na auditoria de 2026-09-23.
- **O cache não fecha `CTX-17` sozinho.** A onda 30 melhora a disponibilidade sem garanti-la nos 99,9%. O compromisso pleno depende do read model da onda 60 — e isso precisa estar explícito na proposta, não implícito.
- **A fronteira do que congela pode estar errada.** Foi decidida por raciocínio de domínio, sem validação com a operação. Se "promoção aplicada" precisar ser recalculada retroativamente por decisão comercial, a tabela muda.

---

## Gatilho de revisão

**Quando o p95 de criação passar de 400 ms sob carga real, ou quando o hit rate do cache cair abaixo de 90% por SKU.**

Qualquer um dos dois indica que a onda 30 não sustenta o alvo e que o read model da onda 60 deixa de ser avaliação e vira necessidade. O gatilho é medido, não percebido — e por isso os dois números entram como SLI em `/metricas`.

**Segundo gatilho:** se o Catálogo passar a expor evento de mudança de preço com contrato estável. Isso reduz o custo do read model o bastante para reabrir a comparação antes da onda 60.

**Terceiro gatilho:** se o negócio exigir recálculo retroativo de promoção em pedidos emitidos. Isso contradiz a premissa de imutabilidade do snapshot e força repensar a fronteira da seção (a).

---

## Enforcement

**Fitness function executável** — a mais direta é também a mais forte:

> **Teste de consulta com o Catálogo desligado.** O pipeline sobe Pedidos sem o Catálogo e verifica que `GET /orders/{id}` responde 200 com preço e descrição completos. Se o teste falhar, alguma leitura de pedido voltou a depender do Catálogo — exatamente a regressão que esta ADR existe para impedir.

Complementares, no CI:

1. **Schema check:** `pedido_item.preco_unitario`, `descricao`, `moeda` e `catalogo_versao` são `NOT NULL`. Migração que os torne opcionais falha o build.
2. **Regra de dependência:** nenhum módulo do caminho de **leitura** de pedido pode importar o cliente do Catálogo. Só o resolvedor de criação pode.

```bash
# .claude/hooks/check-desacoplamento-catalogo.sh
# ADR-0003: leitura de pedido não pode depender do Catálogo
if grep -rnE 'CatalogoClient|catalogo_client' --include='*' \
     ./src/pedidos/leitura ./src/pedidos/consulta 2>/dev/null; then
  echo "ADR-0003: cliente do Catálogo referenciado no caminho de leitura de pedido." >&2
  echo "O pedido deve ser autocontido. Use o snapshot gravado no item." >&2
  exit 2
fi
```

**Limitação conhecida, registrada de propósito:** o grep cobre o caminho feliz de nomeação. Uma chamada indireta — via camada genérica de integração ou injeção de dependência dinâmica — passa despercebida. O teste com o Catálogo desligado é a rede que pega esses casos, e é por isso que ele é o enforcement primário e o grep é secundário.

---

## Pendências registradas

- A validade da cotação é de 30 minutos (`oferta.emitir`) e precisa de confirmação do negócio.
- A fronteira "congela / não congela" não foi validada com a operação nem com o financeiro. É a premissa mais frágil desta ADR.
- O valor de ~40 ms por chamada ao Catálogo, usado no cálculo do orçamento de latência, é estimativa de ordem de grandeza, a medir no baseline `P1`.
