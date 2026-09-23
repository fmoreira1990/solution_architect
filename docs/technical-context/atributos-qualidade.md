# Atributos de qualidade → mecanismo → verificação

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** cada atributo de qualidade amarrado ao mecanismo arquitetural que o sustenta e ao lugar onde isso é verificado. Mecanismo sem verificação é intenção.
**Requisitos cobertos:** `P1-08`
**Fontes:** `docs/technical-context/constraints.md`, ADRs 0001 a 0007, `slice/tests/`
**Data:** 2026-09-23

---

## A tabela

| Atributo | Restrição | Mecanismo arquitetural | ADR | Métrica | Onde é verificado |
|---|---|---|---|---|---|
| **Disponibilidade** | 99,9% mensal · 43 min de budget (`CTX-03`) | Nenhuma chamada de saída no aceite — elimina a multiplicação de indisponibilidade | 0007 | uptime mensal, por versão de contrato | `test_pedido_e_evento_nascem_na_mesma_transacao` · aritmética em `constraints.md` §8 |
| | | Degradação controlada por nível | — | taxa de aceite sob falha de dependência | `resiliencia.md` §Degradação |
| | | Multi-AZ no banco (único SPOF) | — | RTO/RPO | — *(infra, fora da fatia)* |
| **Performance** | p95 ≤ 500 ms na **aceitação** (`CTX-04`) | Aceite local: sem I/O externo no caminho crítico | 0007 | p95 de aceitação | orçamento por hop em `constraints.md` §7.2 |
| | | Cotação em lote: 9 chamadas → 2 | 0003 | req/s no Catálogo | — *(onda 60)* |
| | | Snapshot elimina leituras futuras | 0003 | chamadas ao Catálogo por pedido | `test_consulta_de_pedido_funciona_com_o_catalogo_fora_do_ar` |
| | p95 de confirmação **≤ 30 s** | Validação assíncrona por evento | 0007 | p95 de confirmação | **a instrumentar** — onda 30 |
| **Escalabilidade** | 10× em 90 dias (`CTX-02`) | Eliminação do N+1 (multiplicava por item **e** por pedido) | 0003 | req/s no Catálogo sob carga | teste de carga — onda 90 |
| | | Validação assíncrona absorve pico sem bloquear o aceite | 0007 | profundidade da fila de validação | — |
| **Integridade** | zero pedido duplicado (`CTX-07`) | `PRIMARY KEY (chamador, chave)` — a constraint **é** a garantia | 0001 | duplicatas/mês | ⭐ `test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido` |
| | zero evento perdido | Outbox na mesma transação; publica antes de marcar | 0002 | divergência pedido ↔ evento | ⭐ `test_queda_entre_publicar_e_marcar_nao_perde_evento` |
| | | Deduplicação por `event_id` no consumidor | 0002 | reprocessamentos | `test_consumidor_deduplica_a_entrega_duplicada` |
| | | Reconciliação diária | 0007 | pedidos presos em `EM_VALIDACAO` | `test_sli_de_relay_parado_detecta_pendencia` |
| **Auditabilidade** | provar o preço praticado (`CTX-06`) | Snapshot imutável dos termos acordados | 0003 | % de pedidos com snapshot completo | `test_mudanca_de_preco_no_catalogo_nao_altera_o_pedido` |
| | | Colunas de snapshot `NOT NULL` no schema | 0003 | — | schema check no CI |
| | | `catalogo_versao` no item | 0003 | — | `test_snapshot_carrega_unidade_e_peso` |
| **Compatibilidade** | contratos válidos ≥ 6 meses (`CTX-10`, `CTX-12`) | Fachada síncrona v1 sobre núcleo assíncrono | 0004 | consumidores quebrados | ⭐ `test_consumidor_v1_continua_passando_com_a_v2_no_ar` |
| | | Lista fechada de breaking **semântico**, não só estrutural | 0004 | — | `test_v1_nunca_declara_recebido_como_status` |
| | | Expand-and-contract + `Deprecation`/`Sunset` | 0004 | tráfego por versão | `test_v1_esta_marcada_como_deprecada_com_sunset` |
| **Segurança** | LGPD e regime do 2º país (`CTX-09`) | Cotação assinada (HMAC): adulteração de preço é recusada | 0007 | tentativas rejeitadas | `test_oferta_adulterada_e_recusada` |
| | | OAuth2, escopos e quotas por parceiro na borda | — | 401/403/429 por parceiro | — *(onda 60)* |
| | | Segregação de PII por domicílio do titular | 0006 | — | — *(onda 90)* |
| **Observabilidade** | detectar falha silenciosa | SLI: idade do evento mais antigo não publicado | 0002 | idade em segundos | `test_sli_de_relay_parado_detecta_pendencia` |
| | | Observabilidade comparativa (caminho novo × antigo) | — | divergência de resultado | pré-requisito P2 da onda 30 |
| **Evolutibilidade** | evoluir sem quebrar | Fitness functions no CI comparando contrato × implementação | 0004 | build vermelho ao divergir | `test_schema_do_pedido_bate_com_a_resposta_real_da_api` |
| | | Bounded contexts com ownership explícito | — | — | `mapa-dominios.md` |
| **Custo** | não crescer proporcional ao volume (`CTX-16`) | Lote e cache antes de escala horizontal bruta | 0003 | custo por pedido | **`???` sem baseline** |

⭐ = critério crítico do §2.4.2.

---

## Onde os atributos conflitam

Tabela de atributo por atributo esconde o que mais importa em arquitetura: onde eles brigam.

| Conflito | Resolução adotada | Custo aceito |
|---|---|---|
| **Disponibilidade × consistência** | Aceite disponível, validação eventual (`ADR-0007`) | Oversell vira modo de operação; cliente não sabe na hora |
| **Compatibilidade × evolutibilidade** | Fachada v1 protege o legado enquanto v2 evolui | Duas semânticas no ar por 6 meses; fachada reintroduz `CTX-17` para v1 |
| **Auditabilidade × custo de armazenamento** | Snapshot desnormalizado em todo item | ~4,8M linhas/dia, ~1,1 TB/ano; exige particionamento |
| **Performance × frescor de preço** | Preço congelado na cotação, com validade | Cotação vence e obriga recotação |
| **Prazo × qualidade da migração** | Sem janela de indisponibilidade (`CTX-11`) | Fase 1 custa mais que uma migração com janela |
| **Integridade × latência de publicação** | Outbox por polling, não CDC | Latência de publicação = intervalo de poll |

**O conflito mais consequente é o primeiro.** Ele não é técnico: aceitar um pedido que pode ser rejeitado é decisão de negócio embutida numa decisão de arquitetura. Está registrado como tal na `ADR-0007`, com mitigação (cotação assinada nos canais próprios) e sem a pretensão de eliminá-lo.

---

## O que não tem verificação automatizada

Registrado para não passar por cobertura que não existe:

- **Disponibilidade e RTO/RPO** — dependem de infraestrutura, fora do escopo da fatia.
- **p95 sob carga de 10×** — exige teste de carga, previsto para a onda 90.
- **Custo por pedido** — sem baseline (`CTX-15` e `CTX-16` são `???`).
- **Segregação regional de PII** — onda 90, conforme `ADR-0006`.
- **Segurança de borda** (OAuth2, quotas) — onda 60.

Dos dez atributos, **seis têm verificação executável hoje**. Os quatro restantes dependem de infraestrutura, carga real ou decisão pendente — e estão nomeados, não omitidos.
