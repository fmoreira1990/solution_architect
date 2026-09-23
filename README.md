# Evolução da Plataforma de Pedidos e Catálogo

> Desafio técnico — Arquitetura de Soluções
> **Prova executável:** `cd slice && python prova.py` · 128 testes

[![CI](https://github.com/fmoreira1990/solution_architect/actions/workflows/ci.yml/badge.svg)](https://github.com/fmoreira1990/solution_architect/actions/workflows/ci.yml)

---

## O problema

Uma plataforma de Pedidos e Catálogo atende hoje um único canal web nacional e carrega **quatro débitos estruturais**:

1. Consulta o Catálogo de forma síncrona, **uma vez por item** — padrão N+1
2. **Não registra snapshot** de preço: uma mudança no Catálogo reescreve retroativamente o que o cliente viu
3. Retries **sem chave de idempotência** e eventos publicados **sem garantia transacional**
4. **Sem API pública versionada** nem notificação assíncrona para parceiros

Em 90 dias precisa atender **app móvel**, **parceiros de marketplace** e um **segundo país**, com **10× o volume** — e os consumidores atuais **não podem ser interrompidos**.

Os quatro débitos são toleráveis hoje e deixam de ser ao 10×, porque cada um escala por um multiplicador diferente: por item, por retry, por mudança de preço, por parceiro na fila.

---

## A restrição que decidiu a arquitetura

Multiplicando duas restrições que o enunciado apresenta separadamente — 99,9% de disponibilidade e dependência síncrona no caminho crítico — aparece isto:

```
Pedidos 99,9%  ×  Catálogo 99,9%  =  99,8%
99,8% de 43.200 min/mês  →  86,4 min indisponível
Error budget exigido      →  43,2 min

Estouro de 2×, no cenário em que tudo o mais funciona.
```

**O SLA não fecha na aritmética**, independentemente da qualidade do código. Isso transforma "desacoplar é boa prática" em restrição dura, e é o que sustenta as decisões abaixo.

Derivação completa em [`constraints.md` §8](docs/technical-context/constraints.md).

---

## A prova

O desafio pede a validação de **uma decisão crítica**. A fatia em [`slice/`](slice/) prova três, em PostgreSQL real — e os **dois critérios críticos** do enunciado:

| | Teste | O que prova |
|---|---|---|
| ⭐ | `test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido` | 20 threads, mesma chave → **1 pedido**, 1× `201` e 19× `200` |
| ⭐ | `test_consumidor_v1_continua_passando_com_a_v2_no_ar` | consumidor legado que emite nota no `201` **não quebra** |
| | `test_queda_entre_publicar_e_marcar_nao_perde_evento` | relay derrubado entre publicar e marcar: evento duplica, **nunca se perde** |
| | `test_consulta_de_pedido_funciona_com_o_catalogo_fora_do_ar` | pedido é autocontido |
| | `test_cotacao_assinada_e_honrada_mesmo_com_o_catalogo_mudando` | cotação é compromisso |
| | `test_chave_de_outro_cliente_nao_devolve_pedido_alheio` | chave de idempotência é superfície de **autorização** |

As 19 respostas `200` do primeiro teste só existem pelo caminho de replay, que só é alcançado por **violação da `PRIMARY KEY`**. As 20 threads competiram de verdade, e foi a constraint que segurou — não o código.

### Como rodar

**Pré-requisito:** PostgreSQL acessível, com banco e usuário da prova. Se algo faltar, o `prova.py` **diagnostica a causa e imprime o comando exato** — incluindo alternativa via Docker.

```sql
CREATE USER prova WITH PASSWORD 'prova';
CREATE DATABASE prova_pedidos OWNER prova;
```

```bash
cd slice
python prova.py          # instala, cria schema, semeia e executa
```

Variável opcional: `PROVA_DATABASE_URL` (padrão `postgresql://prova:prova@127.0.0.1:5432/prova_pedidos`).

Dados são **sintéticos** — nenhum dado real, nenhuma PII.

O ciclo foi validado do zero: banco e usuário destruídos, prova executada, instruções da própria saída seguidas.

Resultado esperado: **127 passed, 1 skipped**. O teste pulado é a verificação de exceção técnica vencida — ele só tem o que conferir quando alguma exceção estiver registrada, e hoje nenhuma está.

---

## As sete decisões

| ADR | Decisão | Por quê |
|---|---|---|
| [0001](docs/decisions/ADR-0001-idempotencia-na-criacao-de-pedido.md) | Idempotência pela `PRIMARY KEY (chamador, chave)` | A constraint **é** a garantia; sem lock distribuído no caminho crítico |
| [0002](docs/decisions/ADR-0002-publicacao-confiavel-de-eventos-via-outbox.md) | Outbox transacional; publica **antes** de marcar | Duplicar é escolha; perder seria acidente |
| [0003](docs/decisions/ADR-0003-snapshot-de-termos-e-desacoplamento-do-catalogo.md) | Snapshot imutável dos termos acordados | Uma decisão fecha auditabilidade, N+1, latência e SLA |
| [0004](docs/decisions/ADR-0004-versionamento-e-compatibilidade-semantica.md) | Compatibilidade **semântica**, não só estrutural | O `201` mudou de significado com JSON idêntico |
| [0005](docs/decisions/ADR-0005-stack-da-fatia-executavel.md) | Stack da prova: Python + FastAPI + PostgreSQL | Determinada pelo ambiente, e declarada como tal |
| [0006](docs/decisions/ADR-0006-residencia-de-dados-multi-regiao.md) | Segregação de PII por **domicílio do titular** | EUA não exigem residência — a decisão se defende por mérito |
| [0007](docs/decisions/ADR-0007-aceitacao-assincrona-com-validacao-posterior.md) | Aceite local, validação assíncrona | Elimina a multiplicação de indisponibilidade em vez de deslocá-la |

**A 0004 é a menos óbvia e a mais perigosa.** A `ADR-0007` faz o `201` deixar de significar "venda confirmada" e passar a significar "pedido recebido". O JSON é idêntico — mesmos campos, mesmo status code. **Um diff de schema passa**, e todo consumidor que emite nota no `201` quebra em produção. Daí a fachada síncrona v1.

---

## Roteiro de leitura

Um avaliador tem tempo limitado. Em ordem de retorno:

**10 minutos**
[Resumo executivo](docs/delivery/resumo-executivo.md) → [ADR-0007](docs/decisions/ADR-0007-aceitacao-assincrona-com-validacao-posterior.md) → rodar a prova

**30 minutos**
\+ [C4 do estado-alvo](docs/technical-context/c4/containers-to-be.md) → [sequência de criação](docs/technical-context/c4/seq-criacao-pedido.md) → [ADR-0001](docs/decisions/ADR-0001-idempotencia-na-criacao-de-pedido.md), [0002](docs/decisions/ADR-0002-publicacao-confiavel-de-eventos-via-outbox.md), [0003](docs/decisions/ADR-0003-snapshot-de-termos-e-desacoplamento-do-catalogo.md)

**2 horas**
\+ [threat model](docs/security-context/threat-model.md) → [plano 30/60/90](docs/delivery/plano-30-60-90.md) → [decomposição](docs/delivery/decomposicao-onda-30.md) → [estimativa](docs/delivery/estimativa-fase1.md)

---

## Estrutura

`docs/` é organizado por contexto. Todo documento abre com escopo, fontes e data — regra de [`CONVENCOES.md`](docs/CONVENCOES.md).

```
docs/
├── prd/                 problema, hipótese, escopo e gates
├── business-context/    personas, jornada, domínios, glossário, métricas
├── technical-context/   restrições, arquitetura, C4, qualidade, resiliência, serviços AWS
├── decisions/           as sete ADRs
├── security-context/    threat model, LGPD e regime dos EUA
├── delivery/            a proposta: plano, decomposição, estimativa, preço, riscos, resumo, slides
├── governance/          API pública, política de contratos, exceção técnica, fitness functions
├── ai-context/          IA no produto e registro do uso de IA no projeto
├── requisitos/          a entrega frente ao enunciado: rastreabilidade, matriz, checklist
└── CONVENCOES.md        cabeçalho canônico e regras Q1–Q11

contracts/               OpenAPI v1 e v2, AsyncAPI
slice/                   a fatia executável — mapa de módulos em slice/README.md
tools/                   conferência da entrega e validador de diagramas
.github/workflows/       CI: prova, diagramas, confidencialidade
.claude/commands/        comandos que produziram os artefatos
```

Mapa da fatia: [`slice/README.md`](slice/README.md) — cada módulo, a decisão que implementa e o teste que a prova.

---

## Índice dos artefatos

### A entrega frente ao enunciado
| | |
|---|---|
| [Rastreabilidade do enunciado](docs/requisitos/rastreabilidade-pdf.md) | cada tópico do PDF e o artefato que o responde |
| [Checklist de avaliação](docs/requisitos/checklist-avaliacao.md) | os 8 critérios, a evidência de cada um e **onde ainda é fraco** |
| [Matriz de entregáveis](docs/requisitos/matriz-entregaveis.md) | inventário do que o desafio exige e do critério de pronto de cada item |

### Problema e domínio
| | |
|---|---|
| [PRD](docs/prd/pedidos-catalogo.md) | tese, hipótese composta, escopo IN/OUT, gates |
| [Personas](docs/business-context/personas.md) | derivadas de §2.2.1, evidência a evidência |
| [Jornada](docs/business-context/jornada.md) | ANTES / DURANTE / DEPOIS |
| [Mapa de domínios](docs/business-context/mapa-dominios.md) | bounded contexts, ownership, context map |
| [Glossário](docs/business-context/glossario.md) | linguagem ubíqua e termos proibidos |
| [Métricas](docs/business-context/metricas.md) | SLIs, SLOs e cenários de qualidade, com critério de aceite por gate |

### Arquitetura
| | |
|---|---|
| [Constraints](docs/technical-context/constraints.md) | restrições com número + dimensionamento + `CTX-17` |
| [Arquitetura](docs/technical-context/architecture.md) | componentes, fluxo, trade-offs, e o que **não** está nela |
| [C4 as-is](docs/technical-context/c4/contexto-as-is.md) · [contêineres](docs/technical-context/c4/containers-as-is.md) | estado atual, com os quatro débitos localizados |
| [C4 to-be](docs/technical-context/c4/contexto-to-be.md) · [contêineres](docs/technical-context/c4/containers-to-be.md) | estado-alvo, com o delta marcado |
| [Sequência: criação](docs/technical-context/c4/seq-criacao-pedido.md) | três faixas — antes, caminho crítico, depois |
| [Sequência: status](docs/technical-context/c4/seq-status-notificacao.md) | queda do relay, parceiro fora, reconciliação |
| [Atributos de qualidade](docs/technical-context/atributos-qualidade.md) | atributo → mecanismo → métrica → **onde é verificado** |
| [Resiliência](docs/technical-context/resiliencia.md) | timeout, retry, breaker e bulkhead com **valor por dependência** |
| [Serviços AWS](docs/technical-context/servicos-aws.md) | capacidade → serviço → tier → custo, com alternativa confrontada |
| [Padrões de desenvolvimento](docs/technical-context/padroes-desenvolvimento.md) | Ports & Adapters, SOLID aplicado a decisões reais, revisão de código de IA |

### Decisões
[ADR-0001](docs/decisions/ADR-0001-idempotencia-na-criacao-de-pedido.md) · [0002](docs/decisions/ADR-0002-publicacao-confiavel-de-eventos-via-outbox.md) · [0003](docs/decisions/ADR-0003-snapshot-de-termos-e-desacoplamento-do-catalogo.md) · [0004](docs/decisions/ADR-0004-versionamento-e-compatibilidade-semantica.md) · [0005](docs/decisions/ADR-0005-stack-da-fatia-executavel.md) · [0006](docs/decisions/ADR-0006-residencia-de-dados-multi-regiao.md) · [0007](docs/decisions/ADR-0007-aceitacao-assincrona-com-validacao-posterior.md)

### Contratos e prova
| | |
|---|---|
| [OpenAPI v1](contracts/openapi/orders-v1.yaml) | fachada síncrona, deprecada, com `Sunset` |
| [OpenAPI v2](contracts/openapi/orders-v2.yaml) | aceite assíncrono, `Idempotency-Key` obrigatória |
| [AsyncAPI](contracts/asyncapi/order-status.yaml) | eventos, at-least-once, dedup **obrigatória no contrato** |
| [`slice/`](slice/) | 128 testes em PostgreSQL real |

### Segurança
| | |
|---|---|
| [Threat model](docs/security-context/threat-model.md) | STRIDE por fronteira · **26 ameaças** |
| [LGPD e regime dos EUA](docs/security-context/lgpd-residencia-dados.md) | classificação, minimização, transferência internacional |

### Evolução e proposta
| | |
|---|---|
| [Plano 30/60/90](docs/delivery/plano-30-60-90.md) | ondas, gates, convivência, descomissionamento |
| [Decomposição da onda 30](docs/delivery/decomposicao-onda-30.md) | 47 tarefas estimáveis |
| [Estimativa da fase 1](docs/delivery/estimativa-fase1.md) | 63 d.p. com IA (79 sem), time de 1 SRE derivado, custos, faixa de confiança |
| [Impacto de IA no desenvolvimento](docs/delivery/impacto-ia-no-desenvolvimento.md) | −20% de esforço convertido em um SRE a menos, e o que **não** acelera |
| [Taxas de mercado](docs/delivery/taxas-de-mercado.md) | salário → encargos CLT → overhead → tributos, em camadas substituíveis |
| [Riscos e premissas](docs/delivery/riscos-premissas.md) | premissas, débitos aceitos, fora de escopo, decisões do cliente |
| [Resumo executivo](docs/delivery/resumo-executivo.md) | **2 páginas** — recomendação, investimento, riscos |

### Governança e IA
| | |
|---|---|
| [Estratégia de API pública](docs/governance/estrategia-api-publica.md) | autenticação, autorização, quotas e versionamento, com estado por item |
| [Política de contratos](docs/governance/politica-contratos.md) | lista fechada de breaking **estrutural e semântico** |
| [Exceção técnica](docs/governance/excecao-tecnica.md) | waiver com validade; vencido **quebra o build** |
| [Fitness functions](docs/governance/fitness-functions.md) | as verificações e os testes de mutação que as validam |
| [Arquitetura de IA](docs/ai-context/arquitetura-ia.md) | RAG + ferramenta, guardrails, avaliação |
| [Uso de IA](docs/ai-context/uso-de-ia.md) | modelo de trabalho, validação em camadas e **decisões rejeitadas** |
| [Convenções](docs/CONVENCOES.md) | cabeçalho canônico e regras Q1–Q11 |

---

## Premissas

Declaradas porque o enunciado não as informa. Lista completa com o efeito de cada uma em [riscos-premissas.md](docs/delivery/riscos-premissas.md).

| # | Premissa | Valor |
|---|---|---|
| PR-01 | Volumetria | 60k pedidos/dia → **600k** no alvo |
| PR-02 | Tamanho do pedido | 8 itens em média, 15 no p95 |
| PR-03 | Segundo país | **Estados Unidos** |
| PR-04 | Cloud de referência | AWS |
| PR-06 | Distribuição | 60% em 8h comerciais, pico de 3× |

> **PR-06 é a premissa mais frágil.** Varejo tem Black Friday. Se o pico real for 10× ou 20×, o dimensionamento muda inteiro.

### O que permanece `???` — e por quê

47 ocorrências, **todas de baseline de produção**: duplicatas por retry, eventos perdidos, p95 atual, disponibilidade atual, custo por pedido, inventário de consumidores.

São números que **só existem medindo o sistema atual**. Inventá-los contaminaria métricas e estimativa a jusante. São a tarefa `P1` da onda 30 e **pré-requisito do gate G30** — sem régua, o gate é indecidível.

Marcar a lacuna é decisão, não omissão: é a regra **Q7** das [convenções](docs/CONVENCOES.md).

---

## Verificação automatizada

O que o CI quebra, e não apenas o que ele roda:

| Verificação | Protege |
|---|---|
| 128 testes da fatia, **em CI** | os dois critérios críticos |
| Contrato **×** implementação rodando | spec drift |
| `RECEBIDO` ausente do enum da v1 | a fachada síncrona |
| Toda ADR com ≥ 2 alternativas rejeitadas | regra Q2 |
| Testes citados na documentação **existem** | alegar cobertura inexistente |
| Exceção técnica vencida | waiver virar formulário morto |
| Sintaxe Mermaid pelo parser oficial | diagrama em branco no GitHub |
| Varredura de confidencialidade | material de referência versionado |
| Números citados, links e narrativa de edição | documento desatualizado ou contraditório |

As três primeiras foram validadas por **teste de mutação** — quebra-se o que protegem e confirma-se o build vermelho. Detalhe em [fitness-functions.md](docs/governance/fitness-functions.md).
