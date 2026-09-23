# Política de evolução de contratos

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** o que é breaking change neste projeto, quanto tempo uma versão vive, quem aprova o quê e qual verificação automatizada impede a quebra. Regra que não é verificável é opinião.
**Requisitos cobertos:** `D-04`, `CTX-10`, `CTX-12`, `P1-16`
**Fontes:** `ADR-0004`, `contracts/`, `docs/governance/fitness-functions.md`
**Data:** 2026-09-23

---

## 1. A regra que distingue esta política das demais

> **Compatibilidade é estrutural *e* semântica.**

A maioria das políticas de contrato cobre só a primeira. Este projeto existe com um caso concreto que prova por que isso não basta:

A `ADR-0007` mudou o significado de `201 Created` — de *"venda confirmada"* para *"pedido recebido"*. O JSON é idêntico: mesmos campos, mesmos tipos, mesmo status code. **Um diff de schema passa.** E todo consumidor que emite nota fiscal na resposta do POST quebra em produção.

Uma política que valida apenas schema entrega **falsa segurança** — pior que nenhuma, porque o pipeline verde autoriza o merge.

---

## 2. Lista fechada de breaking changes

### Estrutural — detectável por diff

| # | Mudança |
|---|---|
| E1 | Remover campo, endpoint ou valor de enum |
| E2 | Tornar **opcional** um campo obrigatório na **resposta** |
| E3 | Tornar **obrigatório** um campo opcional na **requisição** |
| E4 | Estreitar tipo, formato ou faixa de valores |
| E5 | Alterar status code de sucesso |
| E6 | Renomear qualquer identificador público |

### Semântica — **não** detectável por diff

| # | Mudança | Exemplo real deste projeto |
|---|---|---|
| S1 | Alterar o **significado** de um status code | `201` deixa de significar venda confirmada (`ADR-0007`) |
| S2 | Alterar o **momento do ciclo de vida** em que a resposta é emitida | resposta antes da validação, em vez de depois |
| S3 | Alterar a **garantia de entrega** de um evento | exactly-once → at-least-once |
| S4 | Alterar unidade, moeda ou fuso **sem renomear** o campo | preço em reais → centavos |
| S5 | Alterar **ordem ou cardinalidade** esperada de eventos | evento que era único passa a repetir |
| S6 | Alterar o **efeito colateral** de uma operação | `POST /quotes` que congelava o preço passa a apenas consultá-lo |

**Qualquer item das duas listas exige nova versão e ADR.** Não há exceção por "mudança pequena" — o tamanho da mudança não tem relação com o tamanho da quebra.

### O que **não** é breaking

- Acrescentar campo **opcional** na requisição
- Acrescentar campo na resposta *(consumidores devem tolerar campos desconhecidos — declarado no contrato)*
- Acrescentar endpoint ou valor de enum em campo **de saída** que o consumidor trata por `default`
- Relaxar validação, ampliar faixa, tornar opcional campo obrigatório da **requisição**

---

## 3. Versionamento

**Versão no caminho da URL**: `/v1/orders`, `/v2/orders`.

Escolhido por ser visível em log, roteável na borda sem inspecionar header, trivial de testar e de documentar para parceiro externo. O trade-off — proliferação de caminhos e menor pureza REST — está aceito na `ADR-0004`.

**Eventos** versionam pelo campo `versao` no envelope. Mudança semântica em evento exige bump, mesmo com payload idêntico.

---

## 4. Ciclo de vida de uma versão

```
ATIVA  ──►  DEPRECADA  ──►  SUNSET  ──►  REMOVIDA
            │               │            │
            Deprecation     data         só após
            + Sunset        anunciada    tráfego = 0
```

| Estado | Obrigações |
|---|---|
| **Ativa** | suportada integralmente; correções e adições compatíveis |
| **Deprecada** | headers `Deprecation` e `Sunset` (RFC 8594) em **toda** resposta; sem novas funcionalidades; comunicação ativa aos consumidores com tráfego |
| **Sunset** | data anunciada atingida; desligamento por *kill switch* reversível antes da remoção de código |
| **Removida** | somente após tráfego zero por 30 dias consecutivos |

**Janela mínima de suporte: 6 meses** após a deprecação (`CTX-10`).

> ⚠️ **Seis meses é piso, não teto.** Se os consumidores forem **externos**, a janela vira matéria contratual e pode ser maior. A decisão `V2` — se os consumidores atuais são internos ou externos — **ainda está aberta**, e até fechar, a política trata todos como externos.

---

## 5. Quem aprova o quê

| Mudança | Aprovação | Registro |
|---|---|---|
| Aditiva compatível | revisão de par | PR |
| Nova versão | arquiteto responsável | **ADR** |
| Quebra semântica | arquiteto + Client Face | **ADR** + comunicação ativa |
| Antecipar sunset | arquiteto + Client Face + consumidores afetados | `excecao-tecnica.md` |
| Quebrar sem nova versão | **não existe** | — |

A última linha é literal. Não há caminho de aprovação para quebrar contrato sem versionar — se a necessidade aparecer, ela é tratada como **exceção técnica**, com validade e plano de saída.

---

## 6. Obrigações do consumidor

Declaradas no contrato, não em documentação à parte — porque são **condição de corretude**, não boa prática:

| # | Obrigação | Onde está declarada |
|---|---|---|
| C1 | Tolerar campos desconhecidos na resposta | OpenAPI, descrição |
| C2 | **Deduplicar eventos por `event_id`** | AsyncAPI, `Envelope.event_id` |
| C3 | Tratar todos os valores do enum `status`, inclusive futuros | OpenAPI, `Pedido.status` |
| C4 | Gerar `Idempotency-Key` **estável entre retries** | OpenAPI, parâmetro |
| C5 | Não depender de ordenação entre agregados distintos | AsyncAPI, `chave_particao` |

**C2 e C4 são as que mais falham em integração de terceiro.** Consumidor que não deduplica está violando contrato; cliente que gera chave nova a cada retry anula a própria proteção.

---

## 7. Verificação automatizada

Regra sem verificação é opinião. Cada item desta política tem um mecanismo — detalhados em [`fitness-functions.md`](fitness-functions.md):

| Regra | Verificação | Estado |
|---|---|---|
| Estrutural E1–E6 | diff de OpenAPI contra a versão publicada | 🔜 CI |
| **S1 semântica** | consumidor v1 de referência recebe pedido **confirmado** | ✅ `test_consumidor_v1_continua_passando_com_a_v2_no_ar` |
| S1 no contrato | `RECEBIDO` não pode aparecer no enum da v1 | ✅ `test_v1_nunca_declara_recebido_como_status` |
| Contrato × implementação | campos declarados == campos devolvidos | ✅ `test_schema_do_pedido_bate_com_a_resposta_real_da_api` |
| E3 em v1 | `Idempotency-Key` permanece opcional | ✅ `test_idempotency_key_obrigatoria_em_v2_e_opcional_em_v1` |
| Sunset | versão deprecada declara `Sunset` | ✅ `test_v1_esta_marcada_como_deprecada_com_sunset` |
| C2 declarada | AsyncAPI declara `event_id` como chave de dedup | ✅ `test_asyncapi_declara_event_id_como_chave_de_deduplicacao` |

**Seis das sete regras já falham o build se violadas.** A sétima — diff estrutural — depende de uma versão publicada como linha de base, e entra quando houver.

### O que **não** é automatizável

A lista semântica S2–S6 não tem detector genérico. Depende do **checklist de revisão** obrigatório em todo PR que toque `contracts/`:

- [ ] O significado de algum status code mudou?
- [ ] O momento do ciclo de vida em que a resposta é emitida mudou?
- [ ] A garantia de entrega de algum evento mudou?
- [ ] Alguma unidade, moeda ou fuso mudou sem renomear o campo?
- [ ] A ordem ou a cardinalidade esperada de eventos mudou?
- [ ] O efeito colateral de alguma operação mudou?

Qualquer **sim** exige nova versão e ADR.

Isso depende de disciplina, e a limitação está registrada: é governança leve, não barreira técnica. Quando um caso concreto de S2–S6 aparecer, ele vira teste específico — foi exatamente assim que S1 virou `test_v1_nunca_declara_recebido_como_status`.

---

## Riscos abertos

1. **`V2` em aberto.** Sem saber se os consumidores são internos ou externos, a janela de 6 meses pode estar subdimensionada.
2. **Não existe inventário de consumidores.** Sem ele, "tráfego zero por 30 dias" não é verificável e a versão nunca sai do estado Sunset. É a tarefa **P3** da onda 30.
3. **O checklist depende de disciplina.** Governança leve por escolha; se a taxa de quebra semântica subir, vira barreira técnica.

## Pendências registradas

- O diff estrutural automatizado precisa de uma versão publicada como linha de base.
- A comunicação ativa a consumidores deprecados não tem dono nomeado — depende do inventário de consumidores (tarefa `P3`).
