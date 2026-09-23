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
| PR-03 | Segundo país: **Estados Unidos** | ✅ **decidida** | Define o regime aplicável: não há residência obrigatória, e sim mosaico estadual mais transferência internacional sob a LGPD |
| PR-04 | Cloud AWS | decidida | Muda serviços, não a arquitetura lógica |
| PR-05 | Entrega ao parceiro por webhook assinado + polling | declarada | Muda o contrato de notificação |
| PR-06 | 60% do volume em 8h comerciais, pico de 3× | **inventada** | **Varejo tem Black Friday.** Se o pico real for 10× ou 20×, o dimensionamento inteiro muda |
| PR-08 | A capacidade de **cotação** pode já existir na plataforma atual | declarada | Se existir, é evolução de algo e não capacidade nova — o esforço da onda 30 cai |
| PR-09 | ~40 ms por chamada ao Catálogo | estimativa | Todo o orçamento de latência de `constraints.md` §7.2 se desloca |
| PR-10 | TTL de 24h cobre o retry dos parceiros | declarada | Retry legítimo além disso cria pedido novo |
| PR-11 | A borda gerenciada — CloudFront, API Gateway, ALB — entrega bem acima do SLA publicado | declarada | Pelos pisos de SLA, a série fica em ≈ 99,78% e o SLO de 99,9% não fecha. Medido desde a onda 30; gatilho em `constraints.md` §8.1 |

**O desenho não supõe sistemas que o enunciado não nomeia.** Estoque, Pagamento e Carrinho ficam fora — supô-los exigiria inventar contrato e disponibilidade justamente no caminho crítico. A `ADR-0007` se ancora no Catálogo, que o enunciado nomeia, e o argumento do `CTX-17` não depende de nenhum outro sistema.

---

## 2. Riscos

Probabilidade × impacto, com resposta. Ordenados por exposição.

| # | Risco | Prob. | Impacto | Resposta |
|---|---|---|---|---|
| R1 | **A plataforma real ter integrações no caminho de criação** que o enunciado não nomeia | Média | Alto | Cada uma reintroduz o `CTX-17`. Mapear antes de comprometer o prazo — primeira pergunta ao Client Face |
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
| D8 | **Rejeição pós-aceite como modo de operação** | Consequência direta da `ADR-0007` | Mitigada pela cotação assinada nos canais próprios; **sem mitigação** no canal de parceiro |
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
| F8 | **Alteração de pedido aceito** | Por decisão: mudar é cancelar e criar outro. Preserva o snapshot e mantém um só caminho de escrita (`ADR-0001`) |

---

## 5. Decisões que precisam de validação

O que o resumo executivo leva para o cliente. Nenhuma pode ser resolvida por nós.

| # | Decisão | Quem decide | Bloqueia |
|---|---|---|---|
| V1 | Existem integrações no caminho de criação além do Catálogo? | Client Face / arquitetura da conta | Prazo da onda 30; cada uma reintroduz o `CTX-17` |
| V12 | **Baseline atual** — duplicatas por mês, eventos perdidos, p95, disponibilidade | Operação | **Gate G30**: sem régua, é indecidível. É a tarefa `P1` da onda 30 |
| V7 | Teto de custo de infraestrutura (`CTX-15`) | Negócio | Uma das 5 dimensões do §2.1 fica sem verificação |
| V8 | **Quem é dono do endereço de entrega** — Pedidos ou Logística? | Arquitetura da conta | `ADR-0006`: se ficar em Pedidos, a pseudonimização deixa de bastar |
| V9 | **Instrumento jurídico para transferência BR → EUA** (`CTX-09c`) | Jurídico / DPO | `ADR-0006`; nenhuma PII brasileira cruza sem ele |
| V10 | **Em quais estados dos EUA a operação estará sujeita** | Jurídico / negócio | Define quais leis estaduais se aplicam |
| V2 | Consumidores internos ou externos? | — | ✅ **mistos**. O que resta é o **inventário** (tarefa `P3`) |
| V3 | Qual é o segundo país? | — | ✅ **Estados Unidos** |
| V4 | Limite de rejeição pós-aceite | — | ✅ **2% nos canais próprios, 8% no de parceiro**; aguarda validação do negócio |
| V5 | Defasagem tolerável de preço sob falha | — | ✅ **não se aplica**: com a cotação assinada (`ADR-0007`), não há preço de fallback |
| V6 | Política de desfecho para pedido preso | — | ✅ **cancela em 24 h**; aguarda validação da operação |
| V11 | Hospedagem do Catálogo | — | ✅ **na mesma infraestrutura de Pedidos, hoje e depois da evolução** — conta de infraestrutura única e nenhum esforço de migração |

---

## O que este documento admite

A proposta tem **nove premissas declaradas** — uma delas, `PR-06`, sem âncora alguma —, **nove débitos aceitos** e **seis decisões que dependem do cliente**. Isso não é fragilidade da análise — é o estado real de qualquer proposta feita sobre um enunciado, e declará-lo é o que permite ao cliente decidir com informação.

O risco mais perigoso é `V1`: se a plataforma real tiver integrações no caminho de criação que o enunciado não nomeia, cada uma reintroduz o `CTX-17` e muda o prazo.
