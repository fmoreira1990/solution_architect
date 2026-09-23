# ADR-0004 — Versionamento de contratos e compatibilidade semântica

**Status:** Aceita — 2026-09-22
**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** a política de compatibilidade e versionamento dos contratos públicos. Não decide o conteúdo dos contratos, e sim as regras sob as quais eles podem mudar.
**Requisitos cobertos:** `CTX-08`, `CTX-10`, `CTX-12`, `P1-16`, `P2-06`, `P2-11`, `D-04`
**Fontes:** `docs/technical-context/constraints.md` (§6), `docs/decisions/ADR-0007-...md`, `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf` (§2.2.1)
**Data:** 2026-09-22

---

## Contexto

Duas restrições duras: os contratos atuais devem permanecer compatíveis por **≥ 6 meses** (`CTX-10`) e os consumidores atuais **não podem ser interrompidos** durante a evolução (`CTX-12`). Ao mesmo tempo, `CTX-08` exige API pública versionada para parceiros.

A ADR-0007 introduziu um problema que o versionamento tradicional não cobre. O `201` de `POST /orders` deixa de significar "venda confirmada" e passa a significar "pedido recebido, em validação". **O JSON pode ser idêntico:** mesmo status code, mesmos campos, `status` como string.

Consequência: o contract test de `P2-11` **passa**, e ainda assim todo consumidor que hoje trata `201` como venda feita passa a agir sobre pedido que pode ser rejeitado — emite nota fiscal, baixa comissão, dispara separação.

É quebra de contrato que nenhuma validação de schema detecta. Tratar compatibilidade como propriedade estrutural deixa `CTX-10` e `CTX-12` desprotegidos exatamente no ponto mais perigoso da evolução.

---

## Decisão

### 1. Versão no caminho da URL

`/v1/orders`, `/v2/orders`. Escolhido por ser visível em log, roteável na borda sem inspecionar header, trivial de testar e de documentar para parceiro externo.

### 2. Compatibilidade é estrutural **e** semântica

Lista fechada do que constitui **breaking change** neste projeto:

**Estrutural** — detectável por diff de schema:
- remover campo, endpoint ou valor de enum;
- tornar opcional um campo que era obrigatório na **resposta**;
- tornar obrigatório um campo que era opcional na **requisição**;
- estreitar tipo ou formato;
- alterar status code de sucesso.

**Semântica** — **não** detectável por diff de schema:
- alterar o **significado** de um status code (o caso da ADR-0007);
- alterar o momento do ciclo de vida em que a resposta é emitida;
- alterar a garantia de entrega de um evento (exactly-once → at-least-once);
- alterar a unidade, a moeda ou o fuso de um campo sem renomeá-lo;
- alterar a ordem ou a cardinalidade esperada de eventos.

Toda mudança semântica exige **nova versão**, ainda que o schema não mude — e a justificativa entra na ADR correspondente.

### 3. Fachada síncrona para v1

Durante os 6 meses de `CTX-10`, `/v1/orders` preserva a semântica atual: bloqueia até a confirmação, com timeout, e só então responde. É uma **fachada síncrona sobre núcleo assíncrono**.

`/v2/orders` expõe a aceitação assíncrona e exige que o consumidor trate os estados.

Ao fim da janela, v1 é descomissionada e a fachada morre com ela. **É débito com data de vencimento, não débito permanente.**

### 4. Expand-and-contract como regra de evolução

Adicionar o novo, migrar consumidores, remover o antigo — nesta ordem, nunca sobreposta. Nenhuma remoção antes de evidência de que ninguém consome.

### 5. Deprecação anunciada no protocolo

Respostas de versão em deprecação carregam `Deprecation` e `Sunset` (RFC 8594). O parceiro descobre pelo contrato, não por e-mail.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **Versão na URL + compatibilidade semântica + fachada v1** | ✅ **Escolhida** | Única que protege `CTX-12` contra a quebra semântica da ADR-0007 |
| Versão na URL, compatibilidade só estrutural | ❌ Rejeitada | É o desenho que **deixa passar** a quebra da ADR-0007. Contract test verde, consumidor quebrado em produção |
| Versionamento por media type (`application/vnd...v2+json`) | ❌ Rejeitada | Tecnicamente mais correto em REST, mas invisível em log, difícil de rotear na borda e hostil ao parceiro externo. Custo de suporte maior que o ganho de pureza |
| Versão em header customizado | ❌ Rejeitada | Mesmos problemas do media type, sem a justificativa de padrão |
| Só evolução aditiva, sem versão | ❌ Rejeitada | Não comporta mudança semântica de forma alguma — e a ADR-0007 é exatamente isso |
| Quebrar e negociar janela com os consumidores | ❌ Rejeitada — **indisponível** | `CTX-12` proíbe interromper consumidores atuais. Não é alternativa preterida: o enunciado a exclui |

---

## Justificativa

A mudança mais perigosa deste projeto é invisível para as ferramentas que normalmente guardam compatibilidade. Um regime que valide só schema entrega falsa segurança — pior do que nenhuma, porque o pipeline verde autoriza o merge.

A fachada v1 é a peça que torna a ADR-0007 executável dentro de `CTX-10`. Sem ela, seria necessário escolher entre evoluir e cumprir a restrição de continuidade. Ela reintroduz acoplamento **apenas para os consumidores v1**, de forma temporária, documentada e com data de término — a forma honesta de carregar esse custo.

---

## Trade-offs aceitos

- **Duas semânticas no ar por 6 meses.** Dobra a superfície de teste do caminho de criação e obriga a manter dois conjuntos de cenários.
- **A fachada v1 carrega o problema que a ADR-0007 resolveu.** Consumidores v1 continuam expostos ao `CTX-17`, com latência e disponibilidade acopladas às validações. É consciente, é minoritário e é temporário — mas é real, e precisa aparecer no relatório de disponibilidade **segmentado por versão**, não diluído na média.
- **Compatibilidade semântica não é automatizável por completo.** Parte do enforcement é humana — checklist de revisão de contrato. Depende de disciplina, como toda governança leve.
- **Versão na URL prolifera caminhos.** Aceito: legibilidade e suporte a parceiro externo valem mais que pureza REST aqui.

---

## Gatilho de revisão

**Quando o último consumidor v1 migrar.** A fachada deixa de ter razão de existir e deve ser removida imediatamente — fachada sem consumidor é complexidade órfã que sobrevive por inércia.

**Se surgir um terceiro conjunto de semânticas** (por exemplo, um canal que exija confirmação síncrona por regulação). Duas versões convivendo é gerenciável; três indica que a estratégia de versionamento não está absorvendo a variação e o problema é de modelagem, não de versão.

**Se a janela de 6 meses precisar ser estendida.** Sinal de que a migração de consumidores não tem dono — problema de processo, não de contrato.

---

## Enforcement

**1. Detector de breaking change estrutural, bloqueante no CI.**
Diff da OpenAPI contra a versão publicada (`oasdiff` ou equivalente). Quebra estrutural sem bump de versão falha o build.

**2. Teste de semântica v1 — o mais importante desta ADR.**

> O consumidor v1 de referência é executado contra a implementação atual e **precisa receber um pedido já confirmado**. Se `/v1/orders` passar a responder `RECEBIDO`, o teste falha.

Isso cobre exatamente o buraco que o diff de schema não vê. É o teste que `P2-11` exige, estendido para semântica.

**3. Checklist de revisão de contrato** — humano, curto, obrigatório em todo PR que toque `contracts/`:

- [ ] O significado de algum status code mudou?
- [ ] O momento do ciclo de vida em que a resposta é emitida mudou?
- [ ] A garantia de entrega de algum evento mudou?
- [ ] Alguma unidade, moeda ou fuso mudou sem renomear o campo?
- [ ] A ordem ou a cardinalidade esperada de eventos mudou?

Qualquer "sim" exige nova versão e ADR.

**4. Verificação de sunset.** Versão marcada como deprecada sem header `Sunset` falha a validação de contrato.

---

## Pendências registradas

- **Quem são os consumidores atuais — internos, externos ou ambos — segue `???`.** É a pendência mais consequente: com consumidor interno, a deprecação é negociável; com externo, é contratual, e a janela de 6 meses pode ser piso, não teto. Levantado como bloqueio desde `docs/business-context/personas.md`.
- O timeout da fachada v1 não está definido. Precisa ser menor que o timeout dos consumidores atuais, que também é `???`.
- Não há inventário de quem consome o contrato hoje. Sem ele, "expand-and-contract" não tem como saber quando pode contrair — e o gatilho de revisão principal desta ADR fica sem sinal.
