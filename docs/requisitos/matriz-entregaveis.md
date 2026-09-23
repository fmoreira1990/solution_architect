# Matriz de Entregáveis — Desafio COE Sênior / Arquitetura de Soluções

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** inventário rastreável de tudo que o desafio exige. Não contém decisões — apenas o que precisa existir e como saber que está pronto.
**Fontes:** `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf`, `contexto/context.md`
**Data:** 2026-09-22

---

Cada requisito recebe um ID estável, citado no campo **Requisitos cobertos** dos demais artefatos (ver `docs/CONVENCOES.md` §2).

Status: `[ ]` não iniciado · `[~]` em andamento · `[x]` concluído e evidenciado.

---

## 1. Contexto e restrições (CTX)

Drivers arquiteturais. Não são entregáveis, mas **toda camada da solução precisa de um `CTX` que a justifique** — regra Q11 de `docs/CONVENCOES.md`.

Destino final: `docs/technical-context/constraints.md` (via `/constraints`).

| ID | Restrição / driver | Dimensão | Consequência arquitetural |
|---|---|---|---|
| CTX-01 | Hoje só canal web nacional; em 90 dias: app móvel + parceiros marketplace + 2º país | Escopo | BFF/API pública, multi-canal, multi-região |
| CTX-02 | Volume projetado 10× o atual | Performance | Eliminar N+1, cache, particionamento, autoscaling |
| CTX-03 | Disponibilidade mensal 99,9% (≈43 min/mês de error budget) | Disponibilidade | Degradação controlada, isolamento de falhas, multi-AZ |
| CTX-04 | Latência p95 ≤ 500 ms na **criação** de pedido | Performance | Caminho crítico sem chamada síncrona evitável |
| CTX-05 | Pedidos consulta Catálogo de forma síncrona 1×/item → N+1 | Débito atual | Resolução em lote, cache, snapshot no pedido |
| CTX-06 | Preço e descrição não são snapshot → auditoria comprometida | Débito atual | Snapshot imutável de preço no item do pedido |
| CTX-07 | Retries sem idempotency key; eventos publicados sem garantia transacional | Débito atual | `Idempotency-Key` + Transactional Outbox |
| CTX-08 | Parceiros exigem API pública versionada + notificações assíncronas de status | Integração | OpenAPI versionada, AsyncAPI, webhooks |
| CTX-09 | LGPD + residência de dados do 2º país | Regulação | Segregação regional de PII, minimização, criptografia |
| CTX-10 | Contratos atuais compatíveis por ≥ 6 meses | Compatibilidade | Versionamento aditivo, expand/contract, contract tests |
| CTX-11 | 1ª melhoria segura em produção em 30 dias, **sem janela de indisponibilidade** | Prazo | Strangler Fig, feature flags, rollout progressivo |
| CTX-12 | Consumidores atuais não podem ser interrompidos | Compatibilidade | Convivência de versões |

---

## 2. Parte 1 — Arquitetura-alvo e decisões (P1) · obrigatório

### 2.1 Visões arquiteturais (§2.3.1) — comando `/c4`, `/arquitetura`

| ID | Requisito | Destino | Critério de aceite |
|---|---|---|---|
| P1-01 | C4 Contexto — estado atual | `docs/technical-context/c4/contexto-as-is.md` | Atores, sistemas externos e fluxos atuais |
| P1-02 | C4 Contêineres — estado atual | `.../containers-as-is.md` | Contêineres, protocolos e datastores |
| P1-03 | C4 Contexto — arquitetura-alvo | `.../contexto-to-be.md` | Inclui app móvel, marketplace e 2º país (CTX-01) |
| P1-04 | C4 Contêineres — arquitetura-alvo | `.../containers-to-be.md` | Mostra o delta em relação ao as-is |
| P1-05 | Sequência: criação de pedido | `.../seq-criacao-pedido.md` | Idempotency-Key, snapshot de preço, outbox, caminho de erro |
| P1-06 | Sequência: atualização/notificação de status | `.../seq-status-notificacao.md` | Publicação, webhook, retry/DLQ, deduplicação |
| P1-07 | Componentes, dependências externas, fronteiras de confiança e pontos de falha | `docs/technical-context/architecture.md` | Trust boundaries no diagrama + tabela de SPOF |
| P1-08 | Atributo de qualidade ↔ mecanismo arquitetural | `docs/technical-context/atributos-qualidade.md` | Tabela: atributo → mecanismo → métrica → onde é verificado |

### 2.2 Domínios, dados e integração (§2.3.2) — comando `/arquitetura`, `/adr`

| ID | Requisito | Destino | Critério de aceite |
|---|---|---|---|
| P1-09 | Bounded contexts, responsabilidades, ownership, linguagem de domínio | `docs/business-context/mapa-dominios.md` + `glossario.md` | Context map com tipo de relacionamento (ACL, Conformist, Partnership) |
| P1-10 | Síncrono × assíncrono, justificando consistência, latência e acoplamento | `docs/business-context/mapa-dominios.md` §4 | Tabela por integração com trade-off explícito |
| P1-11 | Snapshot de preço | ADR + modelo de dados | Item carrega preço/descrição imutáveis + versão do catálogo |
| P1-12 | Idempotência | ADR + `slice/` | Chave, escopo, TTL, resposta em replay e em conflito |
| P1-13 | Publicação confiável de eventos | ADR + `slice/` | Outbox transacional com relay, at-least-once |
| P1-14 | Deduplicação | `docs/technical-context/architecture.md` §Consistência + `contracts/asyncapi/` | Obrigação declarada no contrato, não em documentação à parte |
| P1-15 | Reconciliação | `docs/technical-context/architecture.md` §Consistência | Job/relatório de divergência pedido ↔ eventos |
| P1-16 | API pública: authn, authz, quotas, versionamento | `docs/governance/politica-contratos.md` | OAuth2/mTLS, escopos, rate limit por parceiro |
| P1-17 | **Mínimo 4 ADRs** com contexto, alternativas, decisão e consequências | `docs/decisions/ADR-NNN-*.md` | Cada uma com ≥2 alternativas rejeitadas, trade-off, gatilho de revisão e enforcement |

---

## 3. Parte 2 — Evolução segura e prova arquitetural (P2) · obrigatório

### 3.1 Migração e atributos de qualidade (§2.4.1) — comando `/feature-breakdown`, `/metricas`, `/threat-model`

| ID | Requisito | Destino | Critério de aceite |
|---|---|---|---|
| P2-01 | Plano 30/60/90 com convivência, observabilidade, rollback e descomissionamento | `docs/delivery/plano-30-60-90.md` | Cada onda: objetivo, entregas, gate de saída, plano de rollback |
| P2-02 | Cenários de disponibilidade, performance, segurança, auditabilidade e recuperação | `docs/business-context/metricas.md` | Estímulo → resposta → medida; ≥1 cenário por categoria |
| P2-03 | Threat model: identidade, APIs públicas, dados, eventos, dependências | `docs/security-context/threat-model.md` | STRIDE por fronteira + mitigação + risco residual |
| P2-04 | Anti-cascata: timeout, retry com backoff, circuit breaker, bulkhead, degradação | `docs/technical-context/resiliencia.md` | Valores concretos por dependência, não genéricos |
| P2-05 | Riscos, premissas, débitos aceitos e **fora de escopo** | `docs/delivery/riscos-premissas.md` | Fora de escopo explícito; riscos com probabilidade/impacto/resposta |

### 3.2 Contratos e fatia executável (§2.4.2) — comando `/contratos`

| ID | Requisito | Destino | Critério de aceite |
|---|---|---|---|
| P2-06 | OpenAPI versionada para criação/consulta de pedidos | `contracts/openapi/orders-v1.yaml` + `orders-v2.yaml` | Passa no linter; documenta `Idempotency-Key` e catálogo de erros |
| P2-07 | AsyncAPI ou schema para mudança de status | `contracts/asyncapi/order-status.yaml` | Evento versionado, chave de partição, semântica de entrega |
| P2-08 | Prova mínima de uma decisão crítica | `slice/` | Roda isolada, sem dependência de nuvem |
| P2-09 | Testes positivos e negativos + execução automatizada no pipeline | `slice/tests/`, `.github/workflows/` | CI verde, saída anexada como evidência |
| P2-10 | Dados sintéticos + **um único comando documentado** | `slice/seed/`, `slice/prova.py` | Do zero ao resultado em um comando |
| P2-11 | **Critério crítico:** mesma chave não duplica pedido **e** contrato novo não quebra consumidor atual | testes nomeados | Dois testes explícitos, citados no README |

---

## 4. Parte Diferenciais (D) · opcional no PDF, **obrigatório na vaga**

> A descrição da vaga lista "IA aplicada à Arquitetura" e "precificação e construção de propostas" como **requisitos obrigatórios**. Tratados aqui como escopo obrigatório.

| ID | Requisito | Destino | Comando | Critério de aceite |
|---|---|---|---|---|
| D-01 | Capacidade de IA: isolamento, minimização, guardrails, observabilidade, avaliação | `docs/ai-context/arquitetura-ia.md` | `/ia capacidade` | Fronteira de dados, redação de PII, eval set com limiar |
| D-02 | Uso de IA **na elaboração**: prompts, validações, decisões rejeitadas | `docs/ai-context/uso-de-ia.md` + `prompts/` | `/ia log` | Método documentado; ≥3 sugestões rejeitadas com motivo |
| D-03 | Fitness functions no CI (OpenAPI/AsyncAPI, ADRs, regras arquiteturais) | `docs/governance/fitness-functions.md`, `.github/workflows/ci.yml` | `/contratos` | Pipeline falha ao quebrar contrato ou ADR malformado |
| D-04 | Política de evolução de contratos + processo leve de exceção técnica | `docs/governance/politica-contratos.md`, `excecao-tecnica.md` | `/contratos` | Lista fechada do que é breaking; waiver com prazo de validade |
| D-05 | Estimativa: esforço, time, custos, premissas e riscos da fase 1 | `docs/delivery/estimativa-fase1.md` | `/estimativa` | Esforço por perfil, custo de run, faixa de confiança |

---

## 5. Entrega (E) — §4 do desafio

| ID | Item | Destino | Critério de aceite |
|---|---|---|---|
| E-01 | Repositório GitHub com README, premissas, instruções e **índice dos artefatos** | `README.md` | Índice com link para cada ID desta matriz |
| E-02 | Diagramas C4 e sequência em formato versionável | `docs/technical-context/c4/` | Nenhuma imagem sem fonte versionada |
| E-03 | Mapa de domínios + ≥4 ADRs + threat model + plano 30/60/90 | ver P1-09, P1-17, P2-03, P2-01 | — |
| E-04 | OpenAPI + AsyncAPI + fatia executável e testes | `contracts/`, `slice/` | — |
| E-05 | Documento da ferramenta de IA: qual, por quê, prompts, validações, dados | ver D-02 | — |
| E-06 | Resumo executivo ≤ 2 páginas: recomendação, investimento, riscos, decisões a validar | `docs/delivery/resumo-executivo.md` | Cabe em 2 páginas, linguagem de negócio |
| E-07 | *(desejável)* Vídeo ou slides: atual, alvo, migração, demo, trade-offs | `docs/delivery/apresentacao/` | 8–12 slides ou 5–8 min |

---

## 6. Critérios de avaliação (AV) — §3 do desafio

Checklist de revisão final. Cada critério precisa ser defensável apontando artefato concreto.

| ID | Critério | Onde se prova |
|---|---|---|
| AV-01 | Arquitetura de solução: coerência contexto↔requisitos↔componentes↔integrações | P1-01..P1-08 |
| AV-02 | Modelagem de domínio e dados: bounded contexts, ownership, consistência | P1-09, P1-10, P1-14, P1-15 |
| AV-03 | Decisões e trade-offs: ADRs objetivos, alternativas reais, consequências | P1-17 |
| AV-04 | Estratégia de evolução: incremental, compatibilidade, observabilidade, rollback | P2-01, P2-04, P2-05 |
| AV-05 | Segurança e privacidade: threat model, identidade, autorização, LGPD | P2-03, P1-16, CTX-09 |
| AV-06 | Qualidade da prova: contratos versionados, teste executável, evidência | P2-06..P2-11 |
| AV-07 | Uso eficaz de IA: prompts e decisões documentados, validação, dados sensíveis | D-01, D-02 |
| AV-08 | **Atuação sênior:** pragmatismo, comunicação clara, **sem superdimensionar** | transversal — regra Q11 de `docs/CONVENCOES.md` |

---

## 7. Premissas a fechar (Frente F0)

A lista canônica de premissas é `docs/delivery/riscos-premissas.md` §1 — esta tabela apenas resume o estado, e usa a numeração de lá para não haver duas.

| # | Premissa | Valor proposto | Status |
|---|---|---|---|
| PR-01 | Volumetria atual | 60k/dia → 600k no alvo | ✅ decidida |
| PR-02 | Tamanho do pedido | 8 itens em média, 15 no p95 | ✅ decidida |
| PR-03 | Segundo país | Estados Unidos | ✅ decidida |
| PR-04 | Cloud de referência | AWS | ✅ decidido |
| PR-05 | Modelo de entrega ao parceiro | Webhook assinado + fallback por polling | a confirmar |
| CTX-13 | Tamanho e senioridade do time | `???` | **derivado** do esforço por tarefa em `/estimativa`, não declarado antes dele |
| — | Stack da fatia executável | Python 3.12 + FastAPI + PostgreSQL 18 | ✅ decidida no gate G2 (`ADR-0005`) |

---

## Pendências registradas

- `docs/technical-context/constraints.md` ainda não existe; os `CTX-*` vivem provisoriamente nesta matriz e devem migrar para lá na Frente F0, via `/constraints`.
- PR-01 a PR-03 são premissas inventadas por falta de dado no desafio. Devem aparecer como premissa declarada no README, nunca como fato.
