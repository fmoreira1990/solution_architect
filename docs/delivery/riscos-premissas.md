# Riscos, premissas, débitos aceitos e fora de escopo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** o que pode dar errado, o que estamos assumindo sem saber, o que aceitamos carregar e o que decidimos **não** fazer. É o documento onde a proposta declara seus limites.
**Requisitos cobertos:** `P2-05`
**Fontes:** todas as ADRs, `docs/technical-context/constraints.md`, `docs/delivery/plano-30-60-90.md`
**Data:** 2026-09-23

---

## 1. Premissas — o que assumimos sem confirmação

Se qualquer uma for falsa, algo muda. A coluna da direita diz **o quê**.

| # | Premissa | Origem | Se for falsa |
|---|---|---|---|
| PR-01 | 60k pedidos/dia hoje → 600k no alvo | declarada | Redimensiona particionamento, cache e custo. Abaixo de ~20k/dia, parte da arquitetura vira overengineering |
| PR-02 | 8 itens em média, 15 no p95 | declarada | Muda o peso do N+1 e o orçamento de latência por hop |
| PR-03 | Segundo país na América Latina | declarada | Define região, regime de dados e moeda. **Bloqueia a `ADR-0006`** |
| PR-04 | Cloud AWS | decidida | Muda serviços, não a arquitetura lógica |
| PR-05 | Entrega ao parceiro por webhook assinado + polling | declarada | Muda o contrato de notificação |
| PR-06 | 60% do volume em 8h comerciais, pico de 3× | **inventada** | **Varejo tem Black Friday.** Se o pico real for 10× ou 20×, o dimensionamento inteiro muda |
| PR-07 | **Estoque e Pagamento existem como serviços integráveis** | **inventada** | A `ADR-0007` pressupõe integrações que não existem. **A onda 30 não cabe em 30 dias** |
| PR-08 | Já existe um carrinho na plataforma atual | **inventada** | "Carrinho e Oferta" deixa de ser evolução e vira contexto novo. Esforço da onda 30 sobe |
| PR-09 | ~40 ms por chamada ao Catálogo | estimativa | Todo o orçamento de latência de `constraints.md` §7.2 se desloca |
| PR-10 | TTL de 24h cobre o retry dos parceiros | declarada | Retry legítimo além disso cria pedido novo |

**PR-07 é a mais perigosa.** O enunciado nunca menciona Estoque nem Pagamento; a arquitetura os trata como existentes. É a premissa que, sozinha, invalida o prazo de `CTX-11`.

---

## 2. Riscos

Probabilidade × impacto, com resposta. Ordenados por exposição.

| # | Risco | Prob. | Impacto | Resposta |
|---|---|---|---|---|
| R1 | **Estoque/Pagamento não existirem** (PR-07) | Média | Crítico | Validar **antes** de comprometer o prazo. É a primeira pergunta ao Client Face |
| R2 | **Pré-requisitos P1–P3 escorregarem** — baseline, observabilidade, inventário de consumidores | Alta | Alto | Tratá-los como caminho crítico, não tarefa paralela. Sem baseline o G30 é indecidível |
| R3 | **Consumidores atuais serem externos** | Média | Alto | Muda `CTX-10` de negociável para contratual; 6 meses vira piso, não teto. Client Face precisa entrar |
| R4 | **Deduplicação nos consumidores depender de terceiros** (tarefa A9) | Alta | Médio | Declarar no contrato AsyncAPI; prever janela de adequação; medir quem já deduplica |
| R5 | **Normalização canônica do payload gerar 409 falso** (A3) | Média | Alto | Especificar na OpenAPI, não só no código. Monitorar taxa de 409 por divergência |
| R6 | **Pico real muito acima de 3×** (PR-06) | Média | Alto | Teste de carga na onda 90 com cenário de campanha, não só de média |
| R7 | **Rejeição pós-aceite alta demais** | Média | Alto | Reserva no carrinho deixa de ser otimização e vira obrigatória. Gatilho na `ADR-0007` |
| R8 | **A fachada v1 sobreviver por inércia** | Alta | Médio | Gatilho de revisão explícito: "último consumidor migrou → remover" |
| R9 | **Relay parado sem alerta configurado** | Baixa | Crítico | Falha silenciosa; o alerta de idade do outbox é a única defesa. Validar como configuração, não intenção |
| R10 | **Sem janela de indisponibilidade encarecer a fase 1** | Certa | Médio | Não é risco a mitigar, é custo a **declarar**. Deve aparecer na proposta comercial |

---

## 3. Débitos aceitos

Coisas que sabemos estar erradas ou incompletas e escolhemos carregar.

| # | Débito | Por que aceitamos | Quando cobrar |
|---|---|---|---|
| D1 | **Fachada v1 reintroduz o `CTX-17`** para consumidores antigos | Sem ela, é escolher entre evoluir e cumprir `CTX-12` | Morre com a v1, ao fim da janela |
| D2 | **Outbox por polling, não CDC** | CDC é superior em latência, mas adiciona componente operacional e não cabe em 30 dias | Quando a latência de publicação virar problema medido |
| D3 | **Broker stub na fatia executável** | A garantia provada é transacional, não de transporte | Não se aplica — é escopo de prova, não de produção |
| D4 | **Snapshot desnormalizado** — ~1,1 TB/ano | Auditoria exige; é o custo do registro | Exige particionamento e arquivamento na onda 90 |
| D5 | **Sem ordenação global de eventos** | Nenhum requisito pede | Se algum consumidor exigir |
| D6 | **Sem testes de injeção de falha (chaos)** | Não cabe nas 3 ondas | Antes de escalar para 10× real |
| D7 | **Valores de timeout derivados, não medidos** | Baseline não existe | Recalibrar na onda 30 (tarefa P1) |
| D8 | **Oversell como modo de operação** | Consequência direta da `ADR-0007` | Mitigado por reserva e autorizar-sem-capturar; não eliminado |
| D9 | **Backfill de snapshot impossível** | O dado nunca existiu | **Nunca se resolve.** Pedidos antigos seguem sem prova de preço |

---

## 4. Fora de escopo

Exclusões explícitas. Nenhuma é omissão.

| # | Fora | Motivo |
|---|---|---|
| F1 | **O aplicativo móvel em si** | A plataforma entrega BFF e API; construir iOS/Android é de outro time |
| F2 | **Reescrita do Catálogo** | Ele é desacoplado, não reescrito. Atacar o N+1 não exige abrir uma frente de modernização |
| F3 | **Operação logística e fiscal do 2º país** | Residência de dados e multi-moeda entram; integração fiscal local, transportadoras e meios de pagamento locais são projetos próprios |
| F4 | **Migração de pedidos históricos** | Backfill de snapshot é **impossível**, não caro — o dado do preço praticado nunca foi gravado |
| F5 | **Precificação das ondas 60 e 90** | §2.5.3 limita o compromisso orçado à fase 1 |
| F6 | **Escolha de ferramenta de observabilidade** | Decisão de infraestrutura; não muda as métricas |
| F7 | **Multi-tenancy para outras bandeiras do grupo** | Não foi pedido; adicioná-lo agora seria superdimensionar |

---

## 5. Decisões que precisam de validação

O que o resumo executivo leva para o cliente. Nenhuma pode ser resolvida por nós.

| # | Decisão | Quem decide | Bloqueia |
|---|---|---|---|
| V1 | Estoque e Pagamento existem? (PR-07) | Client Face / arquitetura da conta | Prazo da onda 30 |
| V2 | Consumidores atuais são internos ou externos? | Client Face | `ADR-0004`, janela de deprecação |
| V3 | Qual é o segundo país? (PR-03) | Negócio | `ADR-0006`, onda 90 |
| V4 | Limite aceitável de rejeição pós-aceite | Negócio | Gatilho da `ADR-0007` |
| V5 | Limite de defasagem tolerável em preço sob falha | Negócio | Regra de fallback da `ADR-0003` |
| V6 | Política de desfecho para pedido preso em validação | Negócio / operação | Reconciliação |
| V7 | Teto de custo de infraestrutura (`CTX-15`) | Negócio | Uma das 5 dimensões do §2.1 fica sem verificação |
| V8 | **Quem é dono do endereço de entrega** — Pedidos ou Logística? | Arquitetura da conta | `ADR-0006`: se ficar em Pedidos, a pseudonimização deixa de bastar |

---

## O que este documento admite

A proposta tem **três premissas inventadas** (PR-06, PR-07, PR-08), **nove débitos aceitos** e **oito decisões que dependem do cliente**. Isso não é fragilidade da análise — é o estado real de qualquer proposta feita sobre um enunciado, e declará-lo é o que permite ao cliente decidir com informação.

O maior risco isolado é **PR-07**: se Estoque e Pagamento não existirem, o prazo de 30 dias não fecha, e isso precisa ser verificado antes de qualquer compromisso comercial.
