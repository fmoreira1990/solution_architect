# PRD — Evolução da Plataforma de Pedidos e Catálogo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** o problema, a aposta e os limites da evolução arquitetural. Não contém solução — a arquitetura nasce daqui, em `docs/technical-context/architecture.md`.
**Fontes:** `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf` (§2.1, §2.2, §2.5.3, §4), `docs/requisitos/matriz-entregaveis.md`
**Data:** 2026-09-22

---

## 1. Tese

**Problema.** A plataforma de Pedidos e Catálogo sustenta hoje um único canal, e carrega quatro débitos estruturais que já produzem dano em escala pequena:

1. Pedidos consulta o Catálogo de forma síncrona, uma vez por item — pedidos grandes geram padrão N+1 (`CTX-05`).
2. Preço e descrição não são registrados como snapshot, então uma mudança no Catálogo reescreve retroativamente o que o cliente viu, inviabilizando auditoria (`CTX-06`).
3. Retries não têm idempotency key, e eventos de pedido são publicados sem garantia transacional — o sistema pode duplicar pedido e pode perder evento (`CTX-07`).
4. Não existe API pública versionada nem notificação assíncrona de status para terceiros (`CTX-08`).

**Quem.** Rede de varejo omnichannel (moda, eletro e casa), vendendo hoje por canal web nacional próprio. Sofrem o problema, em ordem de intensidade: a operação de pedidos (que concilia duplicidade na mão), o cliente final (que vê preço divergente do que comprou) e o parceiro de marketplace (que hoje não tem como integrar).

**Por que agora.** Em 90 dias a plataforma precisa atender **app móvel**, **parceiros de marketplace** e **operação em um segundo país**, com volume projetado **10× maior** — e os consumidores atuais não podem ser interrompidos durante a evolução. Os quatro débitos acima são toleráveis no volume de hoje e deixam de ser ao 10×: o N+1 multiplica por item, a duplicidade multiplica por retry, e a ausência de contrato público bloqueia o canal de parceiros por completo.

---

## 2. Hipótese

O objetivo do desafio (§2.1) é equilíbrio entre escala, disponibilidade, segurança, custo e prazo — não a otimização de um eixo. A hipótese é, portanto, composta, e cada perna é verificável isoladamente:

> **Se** a plataforma evoluir de forma incremental — desacoplando Pedidos de Catálogo por snapshot e resolução em lote, tornando a criação idempotente com publicação transacional, e versionando contratos por *expand-and-contract* — **então**:
>
> **(a) Escala e latência** — suporta 10× o volume atual mantendo p95 ≤ 500 ms na criação de pedido.
> **(b) Disponibilidade** — sustenta 99,9% mensal, degradando de forma controlada em vez de cascatear.
> **(c) Continuidade** — nenhum consumidor atual quebra durante os 6 meses de compatibilidade obrigatória.
> **(d) Prazo e risco** — a primeira melhoria segura entra em produção em 30 dias, sem janela de indisponibilidade.
> **(e) Custo** — o ganho de escala não exige crescimento proporcional de infraestrutura.

Nenhuma perna sozinha é o PRD. Uma solução que entregue (a) sacrificando (c) falha o objetivo tanto quanto uma que preserve (c) sem atingir (a).

---

## 3. Escopo IN

1. **Desacoplamento Pedidos ↔ Catálogo** — snapshot imutável de preço e descrição no item do pedido, e resolução do catálogo em lote no lugar do N+1. `CTX-05`, `CTX-06`
2. **Integridade transacional da criação** — `Idempotency-Key` na criação de pedido e publicação confiável de eventos via outbox transacional, com deduplicação e reconciliação. `CTX-07`
3. **API pública versionada para parceiros** — autenticação, autorização por escopo, quotas por parceiro e política de versionamento. `CTX-08`
4. **Notificação assíncrona de mudança de status** — contrato de evento versionado e entrega ao parceiro com retry e DLQ. `CTX-08`
5. **Capacidade multi-canal e multi-região** — API/BFF que sustenta web, app móvel e marketplace; residência de dados pessoais no segundo país. `CTX-01`, `CTX-09`
6. **Convivência, observabilidade e reversibilidade** — versões coexistindo, instrumentação do caminho crítico, rollback por feature flag e descomissionamento planejado do caminho legado. `CTX-03`, `CTX-10`, `CTX-11`, `CTX-12`
7. **Fatia executável** — prova automatizada de uma decisão crítica, exigida pelo §2.1.

---

## 4. Escopo OUT

Exclusões explícitas. Cada uma tem motivo, e nenhuma é omissão por prazo apenas.

1. **O aplicativo móvel em si.** A plataforma entrega o BFF e a API que o app consome. Construir iOS/Android é de outro time, e prometê-lo aqui confundiria a fronteira da disciplina de Arquitetura.
2. **Reescrita do Catálogo.** O Catálogo é **desacoplado** — snapshot, resolução em lote e read model — não reescrito. Atacar o N+1 não exige abrir uma frente de modernização que não cabe em 90 dias.
3. **Operação logística e fiscal do segundo país.** Entram residência de dados, multi-região e multi-moeda. Ficam fora integração fiscal local, transportadoras e meios de pagamento locais — são projetos próprios, não arquiteturais.
4. **Migração de pedidos históricos.** O modelo novo vale para pedidos novos; o histórico continua legível pelo caminho atual durante a convivência. **Backfill retroativo de snapshot de preço é impossível, não apenas caro** — o dado do preço praticado no momento da compra não existe em lugar nenhum.
5. **Precificação das ondas 60 e 90.** Por §2.5.3, apenas a fase 1 (30 dias) é estimada em esforço, time e custo. As ondas seguintes são planejadas e têm critério de saída, mas não são compromisso orçado.

---

## 5. Critério de pronto

Por onda, com gate de saída que autoriza a seguinte (§4 exige plano 30/60/90; §2.5.3 limita o compromisso estimado à fase 1).

### G30 — primeira melhoria segura em produção
- `Idempotency-Key`, outbox transacional e snapshot de preço em produção, atrás de feature flag.
- Chamadas repetidas com a mesma chave não criam pedido duplicado — verificado em produção, não só em teste.
- Nenhum evento de pedido perdido entre commit e publicação.
- **Zero janela de indisponibilidade** durante o rollout (`CTX-11`).
- Rollback exercitado ao menos uma vez em ambiente produtivo, por flag.
- → autoriza a onda 60.

### G60 — canal de parceiros aberto
- API pública v1 publicada, com autenticação, quotas e versionamento.
- Notificação assíncrona de status entregue a pelo menos um parceiro real.
- N+1 eliminado no caminho de criação; p95 ≤ 500 ms sustentado na carga corrente.
- Nenhum consumidor atual quebrado (`CTX-10`, `CTX-12`).
- → autoriza a onda 90.

### G90 — estado-alvo
- App móvel e segundo país operando sobre a mesma plataforma.
- 10× o volume suportado com p95 ≤ 500 ms e 99,9% mensal.
- Dados pessoais atendendo residência do segundo país.
- Caminho legado descomissionado, ou com data de descomissionamento acordada.

**Parar em G30 ou G60 não caracteriza fracasso.** Cada gate entrega valor próprio, e a decisão de seguir é do negócio — é isso que torna a proposta incremental em vez de um *big bang* fatiado.

---

## 6. Métrica-alvo

| Dimensão | Métrica | Baseline (hoje) | Meta | Onda |
|---|---|---|---|---|
| Integridade | Pedidos duplicados por retry / mês | `???` | 0 com a mesma chave | G30 |
| Integridade | Eventos de pedido perdidos / mês | `???` | 0 | G30 |
| Latência | p95 de criação de pedido | `???` | ≤ 500 ms com 10× o volume | G60 → G90 |
| Disponibilidade | Disponibilidade mensal | `???` | 99,9% (≈43 min/mês de error budget) | G90 |
| Continuidade | Consumidores quebrados por evolução de contrato | 0 (nada evoluiu ainda) | 0 durante 6 meses | transversal |
| Custo | Custo de infraestrutura por pedido | `???` | não cresce proporcionalmente ao volume | G90 |

**Os `???` restantes são deliberados** (regra Q7). Todos são **baseline de produção** — números que só existem medindo o sistema atual. Inventá-los contaminaria `/metricas` e `/estimativa` a jusante. São a tarefa `P1` da onda 30 e **pré-requisito do gate G30**: sem régua, o gate é indecidível.

Premissas que dependiam de decisão, e não de medição, já foram fechadas — ver tabela abaixo.

### Kill criteria

- **(a) falha:** se o p95 não cair após eliminar o N+1 e o snapshot, o gargalo foi mal diagnosticado — a causa não era o acoplamento com o Catálogo, e a arquitetura-alvo precisa ser reaberta antes da onda 90.
- **(c) falha:** se preservar os contratos atuais exigir congelar a evolução ou forçar um *big bang*, a premissa central do §2.1 ("proposta incremental preservando contratos") não se sustenta, e a conversa muda para negociar janela de quebra com os consumidores.
- **(d) falha:** se a onda 30 não couber em 30 dias sem downtime, o recorte da primeira fatia está errado — reduzir o escopo dela, nunca abrir mão do "sem janela de indisponibilidade".
- **(e) falha:** se o custo por pedido crescer junto com o volume, o desenho não escalou — escalou o gasto.

---

## 7. Premissas

Declaradas porque o enunciado não as informa. São **premissas, não fatos**, e mudam a arquitetura se falsas.

| # | Premissa | Valor adotado | Efeito se falsa |
|---|---|---|---|
| PR-01 | Volumetria atual | ✅ **60k pedidos/dia → 600k no alvo** | Redimensiona particionamento, cache e custo |
| PR-02 | Tamanho do pedido | ✅ **8 itens em média, 15 no p95** | Muda o peso do N+1 e o orçamento de latência por hop |
| PR-03 | Segundo país | ✅ **Estados Unidos** | Sem mandato de residência; o que importa é a transferência BR → EUA sob LGPD (`CTX-09c`) |
| PR-04 | Cloud de referência | AWS | Muda serviços, não a arquitetura lógica |
| PR-05 | Entrega ao parceiro | Webhook assinado + fallback por polling | Muda o contrato de notificação |

---

## Riscos abertos

1. **Baseline inexistente.** Sem os números de hoje, as metas (a) e (e) são verificáveis apenas em termos relativos. Levantar antes de G30, ou o gate fica indecidível.
2. **"Sem janela de indisponibilidade" em 30 dias é a restrição mais dura do desafio.** Ela força feature flag e convivência já na primeira onda, o que encarece a fase 1 em relação a uma migração com janela.
3. **O segundo país indefinido bloqueia decisão de residência de dados.** `PR-03` precisa fechar antes da ADR de multi-região, não depois.

## Pendências registradas

- ~~A persona primária foi presumida aqui como "operação de pedidos".~~ **Corrigido em `docs/business-context/personas.md`:** a derivação de §2.2.1 aponta para a **liderança técnica da plataforma de Pedidos** — cinco das oito evidências convergem para quem responde simultaneamente por dívida técnica, prazo, compatibilidade e metas de qualidade. A operação de pedidos é persona secundária (quem audita preço). A ordem de intensidade da dor no §1 deste PRD reflete a leitura antiga e deve ser revista quando as personas forem confirmadas com o Client Face.
- `docs/business-context/jornada.md` ainda não existe — próximo comando (`/jornada`).
- Os `CTX-*` citados vivem hoje em `docs/requisitos/matriz-entregaveis.md` e migram para `docs/technical-context/constraints.md` via `/constraints`.
- A hipótese (e), sobre custo, não tem métrica instrumentável definida — depende de `/metricas` e da escolha de cloud detalhar o custo por pedido.
