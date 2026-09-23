# Estratégia de API pública

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** autenticação, autorização, quotas e versionamento da API exposta a parceiros — consolidados. Responde ao §2.3.2 do enunciado, que pede a estratégia como item próprio. O detalhe de cada decisão está nas ADRs e no threat model; aqui está a visão única.
**Requisitos cobertos:** `P1-16`, `CTX-08`, `CTX-10`
**Fontes:** `ADR-0004`, `docs/security-context/threat-model.md` (F2, F3), `docs/governance/politica-contratos.md`, `docs/technical-context/servicos-aws.md`
**Data:** 2026-09-24

---

## A premissa que organiza tudo

> **O parceiro está do outro lado de uma fronteira de confiança. O conteúdo que ele envia é dado, nunca instrução.**

Isso não é postura defensiva genérica — tem consequência concreta em quatro lugares: a identidade nunca vem do corpo da requisição, a quota é por parceiro e não global, o conteúdo dele não é interpolado em prompt de IA, e a autorização é verificada por dono mesmo quando o escopo já foi validado.

---

## 1. Autenticação

**OAuth2 *client credentials*** — é integração máquina-a-máquina, sem usuário final no fluxo.

| Decisão | Valor |
|---|---|
| Fluxo | `client_credentials` |
| Emissor | Amazon Cognito *(ver `servicos-aws.md` §5)* |
| Token | JWT, validade de **15 min** |
| Rotação de segredo | a cada 90 dias, com **janela de sobreposição** de 7 dias |
| mTLS | **opcional**, para parceiros de alto volume ou que exijam por contrato |
| IP allowlist | opcional, por parceiro |

**Por que 15 minutos:** token vazado tem valor por pouco tempo, e o custo de renovação é irrelevante para um integrador que já mantém estado. A janela de sobreposição na rotação existe porque troca de segredo sem sobreposição derruba o parceiro — e derrubar parceiro é o que `CTX-12` proíbe.

### O que a borda faz com a identidade

**A borda sobrescreve todo header de identidade vindo de fora.** Nunca repassa o que o cliente enviou.

Essa regra nasceu de um achado do threat model (**F3.2**, generalizando **F1.5**): na implementação inicial da fatia, `X-Chamador` era um header controlado pelo cliente — quem chamava **escolhia o próprio namespace** de chave de idempotência. Ver `ADR-0001`, revisão de 2026-09-23.

---

## 2. Autorização

Três camadas, e a terceira é a que não depende das outras darem certo.

| Camada | Verifica | Onde |
|---|---|---|
| **Escopo** | o token permite esta operação? | borda — `orders:write`, `orders:read` |
| **Dono** | este recurso pertence a quem está pedindo? | aplicação — `test_consulta_de_pedido_alheio_responde_404` |
| **Namespace** | a chave de idempotência é deste chamador? | banco — `PRIMARY KEY (chamador, chave)` |

### A decisão de responder `404`, não `403`

Pedido inexistente e pedido de outro titular respondem **exatamente a mesma coisa**.

Um `403` confirmaria que aquele UUID existe. A enumeração passaria a render informação — o atacante não veria o pedido, mas saberia quais identificadores são reais. Verificado por `test_pedido_inexistente_e_pedido_alheio_sao_indistinguiveis`.

---

## 3. Quotas e proteção de capacidade

Aplicadas na borda, **por parceiro**, nunca globalmente.

| Controle | Valor de partida | Protege contra |
|---|---|---|
| Taxa sustentada | por contrato, padrão **50 req/s** | consumo desproporcional |
| Burst | 2× a taxa contratada, por 10 s | pico legítimo de campanha |
| Quota diária | por contrato | uso acumulado fora do previsto |
| Workers de webhook por parceiro | **5 simultâneos** | parceiro lento monopolizar a entrega |
| Resposta ao exceder | `429` com `Retry-After` | — |

**Por parceiro é o ponto.** Quota global protegeria a plataforma e deixaria um parceiro abusivo degradar os demais. Por parceiro, o dano fica contido em quem o causou — é o mesmo raciocínio de bulkhead da `resiliencia.md`, aplicado à borda.

> Os 50 req/s de partida são **premissa**, não medição. O dimensionamento prevê 37,5 pedidos/s de pico para a plataforma inteira; um parceiro sozinho consumindo mais que isso é anomalia, não uso.

---

## 4. Versionamento

Regras completas em [`politica-contratos.md`](politica-contratos.md). O essencial para quem integra:

| | |
|---|---|
| Onde vive a versão | **caminho da URL** — `/v1/orders`, `/v2/orders` |
| Janela mínima de suporte | **6 meses** após a deprecação (`CTX-10`) |
| Aviso de deprecação | headers `Deprecation` e `Sunset` (RFC 8594) em **toda** resposta |
| Remoção | só após tráfego zero por 30 dias |

**O que torna esta política diferente:** compatibilidade é **estrutural e semântica**. A `ADR-0007` fez o `201` mudar de significado — de *"venda confirmada"* para *"pedido recebido"* — com JSON idêntico. Um diff de schema passa e o consumidor quebra. Por isso a v1 é uma **fachada síncrona** sobre o núcleo assíncrono durante a janela.

### Obrigações de quem integra

Declaradas no contrato, não em documentação à parte — são condição de corretude:

| # | Obrigação | Onde está no contrato |
|---|---|---|
| C1 | tolerar campos desconhecidos na resposta | OpenAPI |
| C2 | **deduplicar eventos por `event_id`** | AsyncAPI, `Envelope.event_id` |
| C3 | tratar todos os valores do enum `status`, inclusive futuros | OpenAPI |
| C4 | gerar `Idempotency-Key` **estável entre retries** | OpenAPI |
| C5 | não depender de ordenação entre pedidos distintos | AsyncAPI |

**C2 e C4 são as que mais falham em integração de terceiro.** Quem não deduplica está violando contrato; quem gera chave nova a cada retry anula a própria proteção.

---

## 5. Notificação de saída

`CTX-08` pede as duas direções. A de saída tem regras próprias:

| | |
|---|---|
| Entrega | webhook **assinado** (HMAC + timestamp) |
| Retry | 6 tentativas em ~30 min, backoff exponencial com jitter |
| Falha definitiva | DLQ + alerta |
| Circuit breaker | **por parceiro**, 5 falhas seguidas |
| Alternativa | polling, para quem não expõe endpoint |

**O breaker é por parceiro, não global.** Um parceiro fora do ar não pode abrir o circuito dos demais — é o que transforma o gateway de notificação num bulkhead de verdade.

---

## 6. Onboarding

| Etapa | O que acontece |
|---|---|
| 1 | Parceiro obtém credenciais em ambiente de sandbox |
| 2 | Testa contra a especificação publicada |
| 3 | Assina os eventos que quer receber |
| 4 | Contrato define quota e janela de suporte |
| 5 | Promoção para produção |

Self-service é **entrega da onda 60**. Hoje o processo existe como desenho, não como plataforma.

---

## Estado de implementação

Honesto, para não passar por cobertura que não existe:

| Item | Estado |
|---|---|
| Versionamento na URL, v1 e v2 | ✅ implementado e testado |
| Fachada síncrona v1 | ✅ implementada e testada |
| Autorização por dono, com `404` indistinguível | ✅ implementada e testada |
| Namespace de chave por chamador | ✅ implementado e testado |
| Headers `Deprecation` / `Sunset` | ✅ declarados no contrato · ⚠️ não emitidos pelo código |
| OAuth2, escopos, mTLS | ⚠️ **desenho — onda 60** |
| Quotas e `429` | ⚠️ **desenho — onda 60** |
| Webhook assinado, retry, DLQ | ⚠️ **desenho — onda 60** |
| Onboarding self-service | ⚠️ **desenho — onda 60** |

**Quatro de nove itens têm verificação executável.** Os cinco restantes são de borda e de notificação — escopo declarado da onda 60, não lacuna esquecida. A fatia prova idempotência, outbox e compatibilidade, que é o que o §2.4.2 pede.

## Riscos abertos

1. **Os 50 req/s de quota padrão são premissa**, não medição. Precisam vir do contrato comercial com cada parceiro.
2. **A rotação de segredo com sobreposição de 7 dias não está implementada** — se for feita sem sobreposição, derruba o parceiro e viola `CTX-12`.
3. **Não se sabe quantos parceiros virão.** O circuit breaker por parceiro exige estado por parceiro; com muitos, vira cardinalidade de métrica no gateway.

## Pendências registradas

- Emitir `Deprecation` e `Sunset` no código, não apenas declará-los no contrato.
- Definir quota por contrato, com o comercial.
- `V2` fechou como **consumidores mistos** — a comunicação de sunset precisa distinguir interno de externo.
