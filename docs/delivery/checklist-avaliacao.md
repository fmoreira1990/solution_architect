# Revisão cruzada — critérios de avaliação

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** para cada critério do §3 do enunciado, o artefato que o prova — e onde a entrega continua fraca. Não é autoavaliação otimista: as lacunas estão nomeadas.
**Requisitos cobertos:** `AV-01` a `AV-08`
**Fontes:** todos os artefatos do repositório
**Data:** 2026-09-23

---

## AV-01 · Arquitetura de solução
> *coerência entre contexto, requisitos, componentes, integrações e atributos de qualidade*

| Evidência | Onde |
|---|---|
| Restrições com número, não adjetivo | [`constraints.md`](../technical-context/constraints.md) |
| **Dimensionamento derivado** — RPS, orçamento de latência por hop, volume de dados | `constraints.md` §7 |
| Componentes, fluxo, integrações, pontos de falha | [`architecture.md`](../technical-context/architecture.md) |
| C4 as-is e to-be, com o **delta marcado** | [`c4/`](../technical-context/c4/) |
| Atributo → mecanismo → métrica → **onde é verificado** | [`atributos-qualidade.md`](../technical-context/atributos-qualidade.md) |

**O que sustenta este critério:** a derivação do `CTX-17`. Multiplicando duas restrições que o enunciado apresenta separadamente — 99,9% e dependência síncrona — a meta fica **matematicamente inatingível**. Isso amarra contexto a componente por aritmética, não por narrativa.

**Onde ainda é fraco:** a tabela de atributos marca 6 de 10 com verificação executável. Disponibilidade, carga a 10×, custo por pedido e segregação regional dependem de infraestrutura ou de medição que não existe na fatia. Estão **nomeados**, não omitidos.

---

## AV-02 · Modelagem de domínio e dados
> *clareza dos bounded contexts, ownership e decisões de consistência*

| Evidência | Onde |
|---|---|
| Bounded contexts, context map com tipo de relacionamento | [`mapa-dominios.md`](../business-context/mapa-dominios.md) |
| Ownership de dados — quem pode escrever o quê | `mapa-dominios.md` §3 |
| Síncrono × assíncrono, com trade-off por integração | `mapa-dominios.md` §4 |
| Linguagem ubíqua, termos ambíguos e **termos proibidos** | [`glossario.md`](../business-context/glossario.md) |
| Deduplicação, reconciliação, snapshot | `architecture.md` §Consistência · `ADR-0002` · `ADR-0003` |

**O que sustenta este critério:** o recorte. O mapa contém **apenas o que o enunciado nomeia** — Pedidos e Catálogo, mais as capacidades que §2.2.1 exige. Contextos inventados foram removidos, e a decisão central sobreviveu reancorada.

E o glossário faz algo que raramente aparece: uma seção de **termos proibidos sem qualificação**. "Criação" é ambígua entre aceite e confirmação — e o p95 de `CTX-04` mede aceite.

**Onde ainda é fraco:** a fronteira entre a capacidade de cotação e o núcleo de Pedidos é lógica, não física. Se na prática forem o mesmo deploy, o context map descreve uma separação que o código não tem — aceitável, mas precisaria ser dito no dia 1 do projeto real.

---

## AV-03 · Decisões e trade-offs
> *ADRs objetivos, alternativas reais e consequências técnicas e operacionais explícitas*

| Evidência | Onde |
|---|---|
| **7 ADRs** (mínimo exigido: 4) | [`decisions/`](../decisions/) |
| Cada uma com ≥ 2 alternativas rejeitadas, **com motivo** | verificado por `test_adr_rejeita_ao_menos_duas_alternativas` |
| Trade-offs, gatilho de revisão e **enforcement** em todas | `test_adr_tem_as_secoes_obrigatorias` |
| Distinção entre *rejeitada* e *rejeitada — indisponível* | `ADR-0005`, `ADR-0004` |

**Três coisas que este critério costuma não ver:**

**Rejeição por prazo, declarada como tal.** O CDC (`ADR-0002`) e o read model (`ADR-0003`) foram rejeitados **por prazo, não por mérito** — e isso está escrito. Esconder que a opção melhor existe enfraquece a ADR.

**Uma ADR superseded com o raciocínio preservado.** A seção (b) da `ADR-0003` está tachada, não apagada, com a explicação de por que caiu. ADR reescrita para parecer certa desde o início esconde o que produziu a mudança de posição.

**Uma decisão que sobreviveu à remoção da premissa que a originou.** A `ADR-0007` foi justificada pelo Estoque; com o recorte de escopo, foi reancorada no Catálogo sem perder o argumento.

**Onde ainda é fraco:** a `ADR-0006` depende de enquadramento regulatório que é **leitura de arquiteto, não parecer jurídico**. Está marcado no documento, mas é a ADR com maior risco de estar errada na premissa.

---

## AV-04 · Estratégia de evolução
> *migração incremental, compatibilidade, observabilidade, rollback e redução de risco*

| Evidência | Onde |
|---|---|
| Três ondas com gate de saída observável | [`plano-30-60-90.md`](plano-30-60-90.md) |
| **47 tarefas** decompostas, com perfil e dependência | [`decomposicao-onda-30.md`](decomposicao-onda-30.md) |
| Convivência, rollback por flag, descomissionamento em 5 passos | `plano-30-60-90.md` |
| Resiliência com **valor por dependência**, não padrão genérico | [`resiliencia.md`](../technical-context/resiliencia.md) |
| Riscos, débitos aceitos, fora de escopo | [`riscos-premissas.md`](riscos-premissas.md) |

**O argumento que sustenta este critério:** a ordem das ondas segue **natureza do dano**, não visibilidade. Três problemas corrompem dado (irreversível), três degradam experiência (reversível). Por isso a onda 30 **não** ataca o N+1, que é a dor mais visível.

E a honestidade de dizer que **a fricção piora antes de melhorar**: reconciliar entre dois caminhos é trabalho novo, criado pela migração.

**A feature flag foi implementada e testada.** 10 testes cobrem rollout por percentual, roteamento determinístico pela chave, rollback sem deploy e preservação do outbox já gravado.

O teste mais valioso é o **contraste**: `test_legado_duplica_pedido_em_retry_concorrente` roda o mesmo cenário do critério crítico — 20 requisições com a mesma chave — pelo caminho legado, e **cria 20 pedidos**. Sem ele, o teste do caminho novo prova que funciona; com ele, prova o que muda.

**Onde ainda é fraco:** o rollout progressivo em produção (degraus de 1% → 100% com comparação a cada passo) não é simulável na fatia — depende de tráfego real.

---

## AV-05 · Segurança e privacidade
> *threat model, identidade, autorização, proteção de dados e atendimento à LGPD*

| Evidência | Onde |
|---|---|
| STRIDE por fronteira — **26 ameaças, 6 fronteiras** | [`threat-model.md`](../security-context/threat-model.md) |
| Classificação de PII, base legal, retenção | [`lgpd-residencia-dados.md`](../security-context/lgpd-residencia-dados.md) |
| Segregação por domicílio do titular | [`ADR-0006`](../decisions/ADR-0006-residencia-de-dados-multi-regiao.md) |
| **9 testes de segurança** derivados do threat model | `slice/tests/test_seguranca.py` |

**O que distingue este critério aqui: o threat model encontrou três defeitos no próprio desenho, e os três foram corrigidos e testados.**

| Achado | O que era | Correção |
|---|---|---|
| **F1.5** | chave de idempotência tratada como integridade, sendo também **autorização** — quem adivinhasse a chave de outro receberia o pedido alheio | defesa em profundidade + 3 testes, validados por mutação |
| **F1.4** | `GET` sem autorização por dono | `404` **indistinguível** entre pedido alheio e inexistente |
| **F4.2** | PII poderia entrar no evento, o veículo de maior replicação do sistema | allowlist de campos, testada |

**Sobre o segundo país:** o enunciado pede *"requisitos de residência de dados"*, e os EUA **não impõem residência** para dado comercial de varejo. A restrição real inverte de direção — é a transferência BR → EUA sob LGPD. A segregação foi mantida por mérito, não por obrigação.

**Onde ainda é fraco:** 7 de 26 ameaças têm verificação executável. OAuth2, quotas, mTLS e assinatura de webhook são onda 60. A chave HMAC da cotação é fixa e sintética na fatia — **em produção é o ativo mais concentrado do desenho**. Não há SAST nem verificação de dependências.

---

## AV-06 · Qualidade da prova
> *contratos versionados, teste executável e evidência de idempotência ou compatibilidade*

| Evidência | Onde |
|---|---|
| OpenAPI v1 e v2, AsyncAPI, versionados | [`contracts/`](../../contracts/) |
| **127 testes** em PostgreSQL real | [`slice/`](../../slice/) |
| Um comando documentado | `python prova.py` |
| Dados sintéticos, sem PII | `slice/seed/` |
| CI com Postgres, diagramas e varredura de confidencialidade | `.github/workflows/ci.yml` — **verde em 5 execuções** |

**Os dois critérios críticos do §2.4.2:**

| | Teste |
|---|---|
| chamadas repetidas com a mesma chave não duplicam pedido | `test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido` |
| evolução de contrato não quebra consumidor atual | `test_consumidor_v1_continua_passando_com_a_v2_no_ar` |

**Por que o primeiro não passa por acidente:** a asserção exige **1 resposta `201` e 19 respostas `200`**. As 19 só chegam ao caminho de replay por violação da `PRIMARY KEY` — as threads competiram de verdade em Postgres, e foi a constraint que segurou.

**E três fitness functions foram validadas por teste de mutação** — quebra-se o que protegem e confirma-se o build vermelho. Uma delas **encontrou 7 violações reais** logo na primeira execução: nenhuma ADR declarava `Escopo` nem `Data`.

**O caminho de erro foi testado — e estava quebrado.** Dois dos três cenários mais prováveis (banco inexistente, usuário inexistente) terminavam em `UnicodeEncodeError` antes de imprimir qualquer ajuda: o PostgreSQL responde em português com acento e o console do Windows usa cp1252. O avaliador veria um traceback e concluiria que a prova não funciona.

Corrigido com saída UTF-8 tolerante e **diagnóstico por tipo de falha** — banco ausente, usuário ausente ou serviço parado geram instruções diferentes, com o comando exato. Ciclo completo validado: banco e usuário destruídos, prova executada, instruções seguidas ao pé da letra, **127 testes verdes do zero**.

**O CI está verde em 5 execuções**, com os três jobs. A prova roda em Linux sem ajuste — o que também demonstra que ela não depende do ambiente onde foi escrita.

Permanece: broker stub, não real — escopo declarado na `ADR-0005`.

---

## AV-07 · Uso eficaz de IA
> *prompts e decisões documentados, validação das saídas e proteção de informações sensíveis*

| Evidência | Onde |
|---|---|
| Log incremental, alimentado a cada comando | [`uso-de-ia.md`](../ai-context/uso-de-ia.md) |
| **7 prompts que mudaram o rumo**, na forma literal | [`prompts/`](../ai-context/prompts/) |
| Capacidade de IA para o produto | [`arquitetura-ia.md`](../ai-context/arquitetura-ia.md) |
| Cuidados com dados | `uso-de-ia.md` §Cuidados |

**O critério pede decisões rejeitadas, e elas são o corpo do documento.** Entre elas: estreitar a hipótese a uma aposta única, oferecer menu de personas onde cabia dedução, lock distribuído para idempotência, read model na onda 30, preencher "tempo gasto" com valores plausíveis.

**Um padrão foi registrado por escrito:** a IA tendeu a oferecer menus de alternativas onde o enunciado já continha a resposta. A validação eficaz foi reler o PDF, não escolher entre opções plausíveis.

Na capacidade de IA proposta, a conclusão desconfortável está escrita: **a maior parte do ganho vem sem IA**. Autoatendimento e notificação proativa resolvem quase tudo, mais barato.

**Onde ainda é fraco:** a capacidade de IA é proposta arquitetural **sem teste executável** — ao contrário do resto da fatia. E o log é honesto sobre o processo, mas não inclui transcrição integral; inclui os prompts que mudaram o resultado, com o critério de seleção declarado.

---

## AV-08 · Atuação sênior
> *autonomia, pragmatismo, comunicação clara e capacidade de orientar a implementação sem superdimensionar*

| Evidência | Onde |
|---|---|
| Seção **"o que não está nesta arquitetura"**, com gatilho de retorno por item | `architecture.md` |
| Recorte de escopo eliminando contextos inventados | `mapa-dominios.md` §"A linha de corte" |
| `???` como decisão, não omissão — regra **Q7** | [`CONVENCOES.md`](../CONVENCOES.md) |
| Roteiro de leitura por tempo disponível | [`README.md`](../../README.md) |
| Processo de exceção técnica com validade obrigatória | [`excecao-tecnica.md`](../governance/excecao-tecnica.md) |

**Pragmatismo, concretamente:** service mesh, CQRS, event sourcing, sharding e BFF por canal estão **ausentes com gatilho numérico** que os traria de volta. Ausência registrada como decisão.

**Comunicação:** o README não conta a história inteira — ele dá o arco em 2 minutos e manda para o lugar certo, com roteiro de 10 min, 30 min e 2 h. Um avaliador tem tempo limitado e vários candidatos.

**Autonomia com limite declarado:** 8 decisões estão listadas como dependentes do cliente, e nenhuma foi decidida por conta própria.

**Onde ainda é fraco — e é justo perguntar:** são **45 documentos**. O enunciado pede um conjunto específico de artefatos, e este repositório entrega mais que o mínimo. A defesa é que cada documento tem destinatário e nenhum repete outro — mas *"menos documento, mais denso"* é uma crítica legítima, e o roteiro de leitura existe justamente porque o volume é real.

---

## Resumo honesto

| Critério | Força | Lacuna principal |
|---|---|---|
| AV-01 Arquitetura | derivação do `CTX-17` amarra tudo | 4 de 10 atributos sem verificação executável |
| AV-02 Domínio | recorte ao que o enunciado nomeia | fronteira da cotação é lógica, não física |
| AV-03 Decisões | 7 ADRs; rejeição por prazo declarada | `ADR-0006` depende de enquadramento não jurídico |
| AV-04 Evolução | ordem por natureza do dano + **flag testada, com contraste legado** | rollout em produção não é simulável |
| AV-05 Segurança | **3 defeitos próprios achados e corrigidos** | 19 de 26 ameaças sem verificação |
| AV-06 Prova | 2 critérios críticos + mutação + ciclo do zero + **CI verde** | broker stub, não real — escopo declarado |
| AV-07 IA | rejeições são o corpo do log | capacidade de IA sem teste |
| AV-08 Sênior | ausências com gatilho numérico | 45 documentos é muito |

**A lacuna que era mais urgente — `AV-06` — está fechada.** O caminho de erro foi testado, estava quebrado, e foi corrigido.

**A feature flag do `AV-04` também foi fechada**, com 10 testes e o caminho legado implementado para dar o contraste.

O que resta é **escopo declarado de onda futura** — gateway de notificação e segurança de borda, ambos da onda 60. Implementá-los agora seria construir a onda 60 numa prova que o enunciado pediu para cobrir **uma** decisão crítica.
