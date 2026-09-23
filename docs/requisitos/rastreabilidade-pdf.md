# Rastreabilidade — cada tópico do enunciado e o que o responde

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** percorre o enunciado **seção por seção, bullet por bullet**, e aponta o artefato que responde cada um. Diferente da `matriz-entregaveis.md`, que organiza por IDs internos, aqui a ordem é a do próprio documento do desafio.
**Requisitos cobertos:** todos
**Fontes:** `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf`
**Data:** 2026-09-24

---

**Legenda:** ✅ entregue e verificável · 🟡 entregue parcialmente · ❌ não entregue

---

## §1 · Contextualização

Esta seção descreve o **perfil da vaga**, não entregáveis. Registrada aqui porque alguns itens deveriam se refletir no trabalho.

| Item do PDF | Onde se reflete | |
|---|---|---|
| *"microsserviços, event-driven, DDD, integração e APIs"* | `mapa-dominios.md` (bounded contexts, context map), `ADR-0002` e `ADR-0007` (event-driven), `contracts/` | ✅ |
| *"Cloud (AWS/Azure/GCP)"* | `PR-04` fixa AWS; serviços nomeados com tier e alternativa em `servicos-aws.md` | ✅ |
| *"governança de arquitetura, reference architectures e ADRs"* | 7 ADRs, `politica-contratos.md`, `excecao-tecnica.md`, `fitness-functions.md` | ✅ |
| *"modernização de legados"* | `plano-30-60-90.md` — Strangler Fig, convivência, descomissionamento | ✅ |
| *"precificação e construção de propostas"* | `decomposicao-onda-30.md` + `estimativa-fase1.md` | ✅ |
| *"IA aplicada à arquitetura"* | `arquitetura-ia.md` + `uso-de-ia.md` + `prompts/` | ✅ |
| *"Inglês ou espanhol avançado"* | não se aplica a artefato | — |
| *"Conhecimento avançado na plataforma SAI App 3.0"* | **não endereçado** — plataforma proprietária, sem informação pública no enunciado | ❌ |

> **Sobre o SAI App 3.0:** o PDF o cita como diferencial e o enunciado não fornece nenhuma informação sobre a plataforma. Não há como endereçá-lo sem inventar. Registrado como lacuna conhecida, não como omissão.

---

## §2.1 · Objetivo geral

> *"Definir a evolução arquitetural da plataforma de Pedidos e Catálogo, equilibrando escala, disponibilidade, segurança, custo e prazo. A proposta deve ser incremental, preservar os contratos atuais durante a transição e conter uma fatia executável que valide uma decisão crítica."*

| Exigência | Resposta | |
|---|---|---|
| **equilibrando** escala, disponibilidade, segurança, custo e prazo | Hipótese **composta** de 5 pernas no `prd/pedidos-catalogo.md` §2 — rejeitei estreitar a uma aposta única justamente por causa desta frase | ✅ |
| proposta **incremental** | `plano-30-60-90.md` — 3 ondas, cada uma com valor próprio e gate | ✅ |
| **preservar contratos** durante a transição | `ADR-0004` — fachada síncrona v1, compatibilidade semântica | ✅ |
| **fatia executável** que valide uma decisão crítica | `slice/` — valida três: idempotência, outbox e compatibilidade | ✅ |

---

## §2.2 · Cenário de evolução

| Exigência | Resposta | |
|---|---|---|
| app móvel em 90 dias | `CTX-01`; BFF multi-canal em `architecture.md`; onda 90 | ✅ |
| parceiros de marketplace | `CTX-08`; API pública + webhook; onda 60 | ✅ |
| operação em segundo país | `PR-03` = **Estados Unidos**; `ADR-0006` | ✅ |
| volume 10× maior | `CTX-02`; dimensionamento em `constraints.md` §7 | ✅ |
| consumidores atuais **não podem ser interrompidos** | `CTX-12`; `ADR-0004`; `test_consumidor_v1_continua_passando_com_a_v2_no_ar` | ✅ |

---

## §2.2.1 · Contexto e restrições

### Os três números do cabeçalho

| | Resposta | |
|---|---|---|
| **10×** de crescimento | `CTX-02` → `constraints.md` §7.1: 12,5 pedidos/s médio, 37,5 no pico | ✅ |
| **99,9%** de disponibilidade | `CTX-03` → **`CTX-17`**, a derivação que mostrou a meta inatingível com dependência síncrona | ✅ |
| **≤ 500 ms** p95 na criação | `CTX-04` → orçamento por hop em `constraints.md` §7.2 | ✅ |

### Os sete bullets

| # | Bullet do PDF | Resposta | |
|---|---|---|---|
| 1 | *"Pedidos consulta o Catálogo de forma síncrona uma vez por item; pedidos grandes geram padrão N+1"* | `CTX-05`; cotação em lote (`ADR-0003`, `ADR-0007`); `POST /v2/quotes` | ✅ |
| 2 | *"Preço e descrição não são registrados como snapshot, dificultando auditoria"* | `CTX-06`; `ADR-0003`; `test_mudanca_de_preco_no_catalogo_nao_altera_o_pedido` | ✅ |
| 3 | *"Retries não possuem idempotency key e eventos de pedido são publicados sem garantia transacional"* | `CTX-07`; `ADR-0001` + `ADR-0002`; **ambos com teste** | ✅ |
| 4 | *"Parceiros solicitam API pública versionada e notificações assíncronas de mudança de status"* | `CTX-08`; `contracts/openapi/` + `contracts/asyncapi/`; gateway de notificação | 🟡 |
| 5 | *"Dados pessoais devem atender LGPD e requisitos de residência de dados do novo país"* | `CTX-09a–d`; `lgpd-residencia-dados.md`; `ADR-0006` | ✅ |
| 6 | *"Os contratos atuais devem permanecer compatíveis por pelo menos seis meses"* | `CTX-10`; `politica-contratos.md` §4 | ✅ |
| 7 | *"A primeira melhoria segura deve entrar em produção em 30 dias, sem janela de indisponibilidade"* | `CTX-11`; onda 30; **feature flag implementada e testada** — rollout por percentual, rollback sem deploy | ✅ |

> **Bullet 4 é parcial:** os contratos existem e são versionados, mas o **gateway de notificação a parceiros não tem implementação nem teste** — é entrega da onda 60.
>
> **Bullet 7:** a flag roteia por percentual, o rollback é por desligamento sem deploy, e o **caminho legado foi implementado** para que a convivência seja demonstrável — sem ele não haveria o que comparar nem para onde reverter.

---

## §2.3.1 · Visões arquiteturais

| Bullet do PDF | Resposta | |
|---|---|---|
| *"diagramas C4 de contexto e contêineres para o estado atual e a arquitetura-alvo"* | 4 diagramas em `c4/`, validados pelo parser oficial do Mermaid | ✅ |
| *"ao menos dois diagramas de sequência: criação de pedido e atualização/notificação de status"* | `seq-criacao-pedido.md` (2 blocos) e `seq-status-notificacao.md` (4 blocos) | ✅ |
| *"componentes, dependências externas, fronteiras de confiança e pontos de falha"* | `architecture.md` §Fronteiras — 5 fronteiras, tabela de SPOF com modo de degradação | ✅ |
| *"Relacionar cada atributo de qualidade aos mecanismos arquiteturais que o suportam"* | `atributos-qualidade.md` — atributo → mecanismo → métrica → **onde é verificado**, mais a tabela de conflitos entre atributos | ✅ |

---

## §2.3.2 · Domínios, dados e integração

| Bullet do PDF | Resposta | |
|---|---|---|
| *"bounded contexts, responsabilidades, ownership de dados e linguagem de domínio"* | `mapa-dominios.md` + `glossario.md` | ✅ |
| *"Decidir onde usar integração síncrona ou assíncrona e justificar consistência, latência e acoplamento"* | `mapa-dominios.md` §4 — tabela por integração com o critério declarado | ✅ |
| *"Tratar snapshot de preço, idempotência, publicação confiável, deduplicação e reconciliação"* | 5 de 5: `ADR-0003`, `ADR-0001`, `ADR-0002`, dedup no AsyncAPI, reconciliação em `architecture.md` | ✅ |
| *"Definir estratégia para APIs públicas, autenticação, autorização, quotas e versionamento"* | `estrategia-api-publica.md` — os 4 itens consolidados, com estado de implementação por item | ✅ |
| *"Registrar no mínimo quatro ADRs com contexto, alternativas, decisão e consequências"* | **7 ADRs**, formato verificado por fitness function | ✅ |

> `estrategia-api-publica.md` consolida autenticação, autorização, quotas e versionamento num só lugar, e declara item a item o que está implementado e o que é desenho da onda 60. Quatro de nove itens têm verificação executável.

---

## §2.4.1 · Migração e atributos de qualidade

| Bullet do PDF | Resposta | |
|---|---|---|
| *"plano incremental de 30/60/90 dias, incluindo convivência, observabilidade, rollback e descomissionamento"* | `plano-30-60-90.md` — os 4 itens tratados, com descomissionamento em 5 passos | ✅ |
| *"cenários de disponibilidade, performance, segurança, auditabilidade e recuperação com métricas e critérios de aceite"* | `metricas.md` — 14 cenários estímulo→resposta→medida, nas 5 categorias exigidas | ✅ |
| *"threat model simples cobrindo identidade, APIs públicas, dados, eventos e dependências"* | `threat-model.md` — 6 fronteiras, 26 ameaças; as 5 dimensões cobertas | ✅ |
| *"como evitar efeito cascata usando timeout, retry com backoff, circuit breaker, bulkhead e degradação controlada"* | `resiliencia.md` — os 5 padrões **com valor concreto por dependência** | ✅ |
| *"riscos, premissas, débitos aceitos e itens explicitamente fora do escopo"* | `riscos-premissas.md` — os 4 itens, em seções próprias | ✅ |

---

## §2.4.2 · Contratos e fatia executável

| Bullet do PDF | Resposta | |
|---|---|---|
| *"Versionar uma especificação OpenAPI para criação/consulta de pedidos e uma AsyncAPI ou schema para mudança de status"* | `orders-v1.yaml`, `orders-v2.yaml`, `order-status.yaml` | ✅ |
| *"Implementar uma prova mínima de uma decisão crítica: idempotência, outbox, contract test ou compatibilidade de versão"* | **as quatro**, não uma | ✅ |
| *"Incluir testes positivos e negativos reproduzíveis e execução automatizada no pipeline"* | 127 testes, positivos e negativos; **CI verde em 5 execuções** | ✅ |
| *"Disponibilizar dados sintéticos e um único comando documentado"* | `slice/seed/` + `python prova.py`; caminho de erro testado em máquina limpa | ✅ |

### Critério crítico

> *"chamadas repetidas com a mesma chave não podem criar pedidos duplicados, e a evolução de contrato não pode quebrar um consumidor atual demonstrado no teste"*

| Metade | Teste | |
|---|---|---|
| mesma chave não duplica | `test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido` — 20 threads, 1 pedido, 1× `201` + 19× `200` | ✅ |
| contrato não quebra consumidor **demonstrado no teste** | `test_consumidor_v1_continua_passando_com_a_v2_no_ar` — consumidor de referência que emite nota no `201` | ✅ |

> O pipeline roda três jobs a cada push — prova com serviço `postgres:18`, validação de diagramas e varredura de confidencialidade. A prova roda em Linux sem nenhum ajuste, o que também valida que ela não depende do ambiente Windows onde foi escrita.

---

## §2.5.1 · Arquitetura e serviços de IA

| Bullet do PDF | Resposta | |
|---|---|---|
| *"capacidade de IA para suporte operacional ou consulta de pedidos, descrevendo isolamento, minimização de dados, guardrails, observabilidade e avaliação"* | `arquitetura-ia.md` — os 5 itens em seções próprias, mais a alternativa não-IA avaliada primeiro | ✅ |
| *"Documentar o uso de IA na elaboração do desafio, incluindo prompts, validações e decisões rejeitadas"* | `uso-de-ia.md` (método, validação e decisões rejeitadas) + `prompts/` (7 prompts literais) | ✅ |

---

## §2.5.2 · Segurança e governança

| Bullet do PDF | Resposta | |
|---|---|---|
| *"Automatizar validações de OpenAPI/AsyncAPI, ADRs e regras arquiteturais como fitness functions no CI"* | 18 fitness functions em 3 categorias, **rodando no CI**; 3 validadas por teste de mutação | ✅ |
| *"Definir política de evolução de contratos e processo leve de exceção técnica"* | `politica-contratos.md` + `excecao-tecnica.md` — este com validade obrigatória que **quebra o build** | ✅ |

> As fitness functions rodam a cada push, junto com a prova.

---

## §2.5.3 · Estimativa técnica

> *"Estimar esforço, composição de time, custos principais, premissas e riscos para executar a primeira fase em 30 dias."*

| Exigência | Resposta | |
|---|---|---|
| **esforço** | 63 d.p. com IA, derivados de 79 d.p. em 47 tarefas | ✅ |
| **composição de time** | 5 pessoas, 1 SRE, **derivada** do esforço | ✅ |
| **custos principais** | pessoas: tabela pronta, com encargos CLT e tributos · infra: `servicos-aws.md`, **US$ 1.812–3.034/mês** para Pedidos **e** Catálogo, na mesma infraestrutura · licenças de IA: US$ 100–350/mês | ✅ |
| **premissas** | 8 premissas com efeito declarado se falsas | ✅ |
| **riscos** | 6 riscos com impacto e resposta, mais faixa de confiança | ✅ |

> `servicos-aws.md` nomeia cada serviço com tier, alternativa confrontada e custo derivado do dimensionamento — e orça o Catálogo junto com Pedidos, porque os dois dividem a mesma infraestrutura.

---

## §3 · Critérios de avaliação

Revisão completa, com as lacunas nomeadas, em **[`checklist-avaliacao.md`](checklist-avaliacao.md)**.

---

## §4 · Entrega do desafio

| Bullet do PDF | Resposta | |
|---|---|---|
| *"Repositório no GitHub com README, premissas, instruções de execução e índice dos artefatos"* | `README.md` — os 4 itens, mais roteiro de leitura por tempo disponível | ✅ |
| *"Diagramas C4 e de sequência em formato versionável, como Mermaid, PlantUML ou Structurizr DSL"* | 17 diagramas validados pelo parser oficial no CI | ✅ |
| *"Mapa de domínios, no mínimo quatro ADRs, threat model e plano incremental de 30/60/90 dias"* | os 4, com 7 ADRs | ✅ |
| *"Especificações OpenAPI e AsyncAPI/schema, acompanhadas da fatia executável e seus testes"* | os 3 contratos + `slice/` com 128 testes | ✅ |
| *"Documento explicativo da ferramenta de IA utilizada, motivo da escolha, prompts relevantes, validações e cuidados com dados"* | `uso-de-ia.md` — os 5 itens em seções próprias | ✅ |
| *"Resumo executivo de até duas páginas com recomendação, investimento, riscos e decisões que precisam de validação"* | `resumo-executivo.md` — os 4 itens | ✅ |
| *(desejável)* *"breve apresentação em vídeo ou slides"* | `apresentacao/slides.md` — 10 slides | ✅ |

---

## Consolidado

| Seção | ✅ | 🟡 | ❌ |
|---|---|---|---|
| §1 Contextualização | 5 | 1 | 1 |
| §2.1 Objetivo geral | 4 | — | — |
| §2.2 Cenário | 5 | — | — |
| §2.2.1 Restrições | 9 | 1 | — |
| §2.3.1 Visões | 4 | — | — |
| §2.3.2 Domínios | 4 | 1 | — |
| §2.4.1 Migração | 5 | — | — |
| §2.4.2 Fatia | 4 | — | — |
| §2.5.1 IA | 2 | — | — |
| §2.5.2 Governança | 2 | — | — |
| §2.5.3 Estimativa | 4 | 1 | — |
| §4 Entrega | 7 | — | — |
| **Total** | **57** | **2** | **1** |

---

## O que falta — lista acionável

| # | Lacuna | Seção | Esforço |
|---|---|---|---|
| **1** | **Gateway de notificação a parceiros sem código** | §2.2.1 b4 | onda 60 — fora da fatia |
| **2** | **SAI App 3.0 não endereçado** | §1 | sem informação disponível |

**Nenhum dos dois é endereçável nesta entrega.** O 1 é escopo declarado de onda futura — implementá-lo agora seria construir a onda 60 numa prova que o enunciado pediu para cobrir **uma** decisão crítica. O 2 não tem como ser resolvido sem informação que o enunciado não fornece.
