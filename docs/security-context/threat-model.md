# Threat model

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** STRIDE por fronteira de confiança, cobrindo identidade, APIs públicas, dados, eventos e dependências. Ameaça sem ativo concreto e mitigação sem local de verificação não entram.
**Requisitos cobertos:** `P2-03`, `CTX-09`
**Fontes:** `docs/technical-context/c4/`, `docs/technical-context/architecture.md`, ADRs 0001 a 0007
**Data:** 2026-09-23

---

## Fronteiras

| # | Fronteira | Confiança | Sensibilidade |
|---|---|---|---|
| F1 | Internet → cliente final | baixa | média |
| F2 | Internet → **parceiro de marketplace** | **nenhuma** — conteúdo dele é dado, nunca instrução | **alta** |
| F3 | Borda → serviços internos | média | média |
| F4 | Serviços → dados (PII) | alta | **alta** |
| F5 | Região Brasil ↔ Região EUA | alta | **alta** |
| F6 | Plataforma → Catálogo | média | média |

---

## F1 — Cliente final

| # | STRIDE | Ameaça | Ativo alcançado | Mitigação | Onde é verificada | Risco residual |
|---|---|---|---|---|---|---|
| 1.1 | **S** | Sequestro de sessão | pedidos e dados do cliente | sessão curta, cookie `HttpOnly`/`Secure`, reautenticação em ações sensíveis | borda — *onda 60* | phishing permanece |
| 1.2 | **T** | Adulterar preço no payload da oferta | valor cobrado | **oferta assinada com HMAC**; adulteração → `422` | ✅ `test_oferta_adulterada_e_recusada` | comprometimento da chave HMAC → item 1.3 |
| 1.3 | **T** | Vazamento da chave de assinatura da oferta | **preço de qualquer pedido** | chave em cofre gerenciado, rotação periódica, validade curta da oferta limita a janela | **não verificado** — a fatia usa chave fixa sintética | **alto se a chave vazar** |
| 1.4 | **I** | Enumerar UUID de pedido | pedido de terceiro | UUIDv4 + **autorização por dono** no `GET` | ⚠️ *não implementado na fatia* | exposição se a autorização faltar |
| 1.5 | **E** | ⚠️ **Reutilizar chave de idempotência de outro cliente** | **pedido de terceiro na resposta de replay** | ver achado abaixo | ✅ `test_chave_de_outro_cliente_nao_devolve_pedido_alheio` | — |

### ⚠️ Achado F1.5 — escopo da chave de idempotência

A `ADR-0001` definiu o escopo da chave como `(chamador, chave)`. Ao modelar esta fronteira, apareceu um problema que o desenho original não tratava:

> Se `chamador` identificar o **canal** (`web`) e não o **principal autenticado**, todos os clientes do canal compartilham o mesmo espaço de chaves. Um cliente que adivinhe ou obtenha a chave de outro receberia, no replay, **o pedido alheio completo** — com itens, valores e identificação.

Agrava o problema o fato de `X-Chamador` ser um **header controlado pelo cliente** na implementação da fatia. Quem chama escolhe o próprio namespace.

**Correção aplicada:**

1. `chamador` passa a ser derivado da **identidade autenticada** pela borda, nunca de header enviado pelo cliente. Na fatia, o header é aceito apenas como simulação e está documentado como tal.
2. O replay verifica, além do `payload_hash`, que o pedido recuperado **pertence ao solicitante**. Defesa em profundidade: se um dia `cliente_id` sair do hash canônico, a propriedade continua valendo.
3. Teste dedicado, que falha se a propriedade for perdida.

**Lição registrada:** a `ADR-0001` foi escrita para resolver duplicidade e tratou a chave como problema de integridade. Ela é também superfície de **autorização** — e isso só apareceu ao modelar ameaças, não ao modelar o fluxo.

---

## F2 — Parceiro de marketplace *(a mais sensível)*

| # | STRIDE | Ameaça | Ativo alcançado | Mitigação | Onde é verificada | Risco residual |
|---|---|---|---|---|---|---|
| 2.1 | **S** | Credencial de parceiro vazada | criar pedidos em nome dele | OAuth2 *client credentials*, rotação, IP allowlist opcional, mTLS para parceiros críticos | *onda 60* | válida até a revogação |
| 2.2 | **S** | Falsificar webhook **de saída** | parceiro aceitar notificação forjada | **assinatura HMAC + timestamp** no webhook; parceiro verifica | *onda 60* | depende do parceiro verificar |
| 2.3 | **T** | Enviar preço arbitrário no pedido | valor cobrado | parceiro **não tem oferta assinada**; preço é validado contra o Catálogo de forma assíncrona | ⚠️ *onda 60* | janela entre aceite e validação |
| 2.4 | **R** | Negar ter enviado um pedido | disputa comercial | log imutável de requisição com identidade, timestamp e hash do payload | *onda 60* | — |
| 2.5 | **I** | Consultar pedido de outro parceiro | pedido de concorrente | autorização por escopo **e por dono** | ⚠️ *não implementado na fatia* | — |
| 2.6 | **D** | Inundar a API pública | disponibilidade dos demais | quota por parceiro + **bulkhead** de workers | *onda 60* | — |
| 2.7 | **T** | **Injeção via conteúdo do parceiro** — descrição, nome, observação | log, painel, e futuro prompt de IA | tratar como **dado, nunca instrução**: escape na saída, sem interpolação em prompt | `docs/ai-context/arquitetura-ia.md` | — |

**F2.7 é a que mais cresce em importância.** Hoje o conteúdo do parceiro chega a log e painel. Com a capacidade de IA da onda 90, ele pode alcançar um prompt — e aí vira *prompt injection*. A regra precisa existir **antes** de a IA existir.

---

## F3 — Borda → serviços internos

| # | STRIDE | Ameaça | Ativo | Mitigação | Risco residual |
|---|---|---|---|---|---|
| 3.1 | **S** | Chamar serviço interno pulando a borda | qualquer operação | rede privada, mTLS entre serviços, sem IP público | erro de configuração |
| 3.2 | **E** | Confiar em header de identidade vindo de fora | **escalonar privilégio** | a borda **sobrescreve** headers de identidade; nunca repassa o que veio do cliente | — |

**F3.2 é a generalização do achado F1.5.** A regra vale para qualquer header de identidade, não só `X-Chamador`: se a borda não sobrescrever, o cliente escolhe quem ele é.

---

## F4 — Dados e PII

| # | STRIDE | Ameaça | Ativo | Mitigação | Risco residual |
|---|---|---|---|---|---|
| 4.1 | **I** | Vazamento do banco de Pedidos | **PII + histórico de compra** | criptografia em repouso, acesso por papel, sem credencial compartilhada | acesso administrativo legítimo |
| 4.2 | **I** | **PII no payload do outbox** | PII replicada a todo consumidor | payload do evento carrega **identificadores, não dados pessoais** | ver abaixo |
| 4.3 | **I** | PII em log ou DLQ | PII fora do ciclo de retenção | redação na saída; DLQ com a mesma política de retenção do dado original | — |
| 4.4 | **T** | Alterar snapshot após a compra | prova de auditoria | snapshot é **imutável por contrato**; `UPDATE` em coluna de snapshot é violação | ✅ `test_mudanca_de_preco_no_catalogo_nao_altera_o_pedido` |
| 4.5 | **I** | Retenção indefinida | LGPD | política de retenção e expurgo por tipo de dado | `lgpd-residencia-dados.md` |

**F4.2 tem consequência de desenho:** o evento `PedidoRecebido` carrega `pedido_id`, `cliente_id` e SKUs — **não** nome, e-mail, endereço ou documento. Quem precisa de PII consulta o dono do dado, com autorização própria. Evento é o veículo de maior replicação do sistema; PII nele se espalha para todos os consumidores, inclusive DLQ e backup.

---

## F5 — Travessia entre regiões

| # | STRIDE | Ameaça | Ativo | Mitigação | Risco residual |
|---|---|---|---|---|---|
| 5.1 | **I** | PII brasileira replicada para a região dos EUA sem instrumento | `CTX-09c` — transferência internacional sob LGPD | segregação por domicílio (`ADR-0006`) | **alto até `V9` existir** |
| 5.2 | **I** | Backup cruzando fronteira | idem | backup regional, chaves regionais | bloqueado |
| 5.3 | **I** | Observabilidade exportando PII entre regiões | idem | telemetria sem PII; identificadores apenas | — |

**`PR-03` fechou como Estados Unidos**, e o regime não é o presumido: não há mandato de residência, mas há transferência internacional sob LGPD na direção BR → EUA. A `ADR-0006` está aceita; o que falta é o instrumento jurídico (`V9`).

---

## F6 — Dependências

| # | STRIDE | Ameaça | Ativo | Mitigação | Risco residual |
|---|---|---|---|---|---|
| 6.1 | **T** | Catálogo comprometido devolvendo preço falso | valor cobrado | validação de faixa na cotação; alerta de variação anômala | ⚠️ não implementado |
| 6.2 | **D** | Dependência lenta derrubando a plataforma | disponibilidade | **o aceite não chama ninguém**; timeout, breaker e bulkhead nas bordas | `resiliencia.md` |
| 6.3 | **T** | Dependência de software comprometida | execução arbitrária | SBOM, verificação de integridade, pinagem de versão | não implementado |
| 6.4 | **S** | Consumidor não autorizado assinando o tópico de eventos | fluxo completo de pedidos | ACL por tópico no broker | *onda 60* |

**F6.2 já está resolvido por decisão arquitetural**, não por controle de segurança: sem chamada de saída no aceite, dependência lenta não derruba a criação de pedido.

---

## Resumo

| Fronteira | Ameaças | Mitigadas e **verificadas por teste** | Planejadas | Bloqueadas |
|---|---|---|---|---|
| F1 cliente | 5 | 2 | 2 | — |
| F2 parceiro | 7 | — | 7 | — |
| F3 borda | 2 | — | 2 | — |
| F4 dados | 5 | 1 | 4 | — |
| F5 regiões | 3 | — | — | **3** |
| F6 dependências | 4 | 1 *(por arquitetura)* | 3 | — |

**4 de 26 ameaças têm verificação executável hoje.** As demais dependem das ondas 60 e 90 ou da `ADR-0006`. Isso é coerente com o escopo da fatia, que prova idempotência, outbox e compatibilidade — não segurança de borda.

## Riscos abertos

1. **A chave HMAC da oferta (F1.3) é o ativo mais concentrado do desenho.** Quem a obtém falsifica preço em qualquer pedido. Na fatia ela é fixa e sintética; em produção exige cofre e rotação.
2. **Autorização por dono no `GET /orders/{id}` não existe na fatia** (F1.4, F2.5). Qualquer um com o UUID lê o pedido. É lacuna conhecida do escopo da prova, não do desenho.
3. **F5 depende do instrumento de transferência (`V9`)**, que ainda não existe. Enquanto isso, nenhuma PII brasileira deveria atravessar.
4. **Nenhum teste de segurança automatizado** além dos dois de oferta. SAST, verificação de dependências e teste de autorização ficam como débito.

## Pendências registradas

- Classificação de PII item a item e política de retenção: `lgpd-residencia-dados.md`.
- A regra de F2.7 — conteúdo de parceiro é dado, nunca instrução — precisa ser reafirmada em `arquitetura-ia.md`.
- A correção do achado F1.5 está aplicada na fatia e registrada na `ADR-0001`.
