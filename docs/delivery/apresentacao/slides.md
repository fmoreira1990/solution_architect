# Apresentação — Evolução da Plataforma de Pedidos e Catálogo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** 12 slides cobrindo arquitetura atual, alvo, implantação na AWS, estratégia de migração, demonstração da prova, trade-offs e o uso de IA na elaboração. Feitos para leitura autônoma, sem narração: cada slide traz no rodapé o documento com o detalhe, e a profundidade está nos documentos indexados no `README.md`.
**Fontes:** todos os artefatos do repositório
**Data:** 2026-09-23

> Separador `---` marca troca de slide. Para apresentar, `python tools/gerar-slides.py` gera a versão em HTML, com os diagramas desenhados.

---

## 1 · O problema

Plataforma de **Pedidos e Catálogo**, hoje um único canal web nacional.

**Quatro débitos estruturais:**

| # | Débito | Escala por |
|---|---|---|
| 1 | Consulta o Catálogo **1× por item** — N+1 | item |
| 2 | **Sem snapshot** de preço — auditoria impossível | mudança de preço |
| 3 | Retry **sem chave**; evento **sem garantia transacional** | retry e volume |
| 4 | **Sem API pública** para parceiros | parceiro na fila |

**Em 90 dias:** app móvel, marketplace, segundo país, **10× o volume** — sem interromper ninguém.

> Toleráveis hoje. Deixam de ser ao 10× **ao mesmo tempo**, porque cada um tem multiplicador próprio.

Detalhe: `README.md` · `docs/prd/pedidos-catalogo.md`

---

## 2 · A restrição que decidiu tudo

Duas exigências do enunciado, multiplicadas:

```
Pedidos 99,9%  ×  Catálogo 99,9%  =  99,8%

99,8% de 43.200 min/mês  →  86,4 min indisponível
Error budget exigido      →  43,2 min

Estouro de 2×, com tudo o mais funcionando.
```

**O SLA não fecha na aritmética** — não importa quão bem o código seja escrito.

> Isso transforma *"desacoplar é boa prática"* em **restrição dura**.

Detalhe: `docs/technical-context/constraints.md` §8 — e §8.1, a mesma conta aplicada aos serviços da AWS

---

## 3 · Onde estamos

```mermaid
flowchart LR
    cliente(["Cliente"]) --> web["Site<br/><i>único canal</i>"]
    web --> pedidos["<b>Serviço de Pedidos</b>"]
    pedidos ==>|"🔴 pergunta o preço item a item<br/>9 chamadas num pedido de 8 itens"| catalogo["Serviço de Catálogo"]
    pedidos -->|"🔴 grava só o código do produto<br/>sem o preço pago"| db[("Banco de Pedidos")]
    pedidos -.->|"🔴 avisa os outros sistemas<br/>depois de gravar — pode se perder"| broker{{"Fila de eventos"}}
    parceiro(["Parceiro"]) -.->|"❌ não tem API"| pedidos

    style pedidos stroke-width:3px
    linkStyle 2 stroke:#c00,stroke-width:3px
    linkStyle 3 stroke:#c00,stroke-width:2px
    linkStyle 4 stroke:#c00,stroke-width:2px,stroke-dasharray: 5 5
```

**Criar um pedido depende do Catálogo responder, item a item.** Com 10× o volume, o Catálogo passa a receber **~338 requisições por segundo** para 37,5 pedidos por segundo — satura primeiro e derruba a criação de pedidos junto.

Detalhe: `docs/technical-context/c4/containers-as-is.md`

---

## 4 · Para onde vamos

```mermaid
flowchart TB
    cliente(["Cliente<br/>site · app"]) --> pedidos
    parceiro(["Parceiro"]) --> pedidos
    legado(["Sistemas que usam<br/>a API atual"]) -->|"versão atual mantida<br/>por 6 meses"| pedidos

    pedidos["<b>Serviço de Pedidos</b><br/><i>cria o pedido sem depender<br/>de outro sistema</i>"]

    pedidos -->|"1. cotação — ANTES<br/>preços em lote"| catalogo["Serviço de Catálogo"]
    pedidos -.->|"3. conferência — DEPOIS<br/>sem o cliente esperar"| catalogo
    pedidos ==>|"2. pedido — só grava<br/>nenhuma chamada externa"| db[("Banco de Pedidos<br/>1 transação")]
    pedidos -->|"evento"| notif["Notificação<br/>ao parceiro"]
    notif --> parceiro

    style pedidos stroke-width:4px
    linkStyle 5 stroke:#080,stroke-width:4px
```

**O que depende de outro sistema acontece antes de criar o pedido (a cotação, que traz os preços assinados) ou depois (a conferência) — nunca durante.** Os sistemas que já usam a API continuam funcionando por 6 meses, sem mudar nada.

Detalhe: `docs/technical-context/c4/containers-to-be.md` · `architecture.md`

---

## 5 · Criar o pedido não depende de ninguém

```mermaid
sequenceDiagram
    participant B as App ou parceiro
    participant P as Serviço de Pedidos
    participant DB as Banco de Pedidos

    rect rgb(232, 245, 233)
    note over B,DB: p95 ≤ 500 ms · nenhuma chamada a outro sistema
    B->>P: cria pedido + chave de idempotência + cotação assinada
    P->>P: confere a assinatura da cotação (sem rede)
    P->>DB: BEGIN
    P->>DB: chave · pedido · itens com o preço · evento
    P->>DB: COMMIT
    P-->>B: 201 — pedido recebido
    end
```

**Uma transação só, quatro garantias:**

- **A mesma chave nunca cria dois pedidos** — o banco recusa a repetição (idempotência)
- **O preço acordado fica gravado e não muda depois** (snapshot)
- **O evento é gravado junto com o pedido**, então não se perde (outbox)
- **Nenhum outro sistema é chamado**: com o Catálogo fora do ar, pedidos continuam sendo criados

> **Só um componente pode impedir a criação de pedido: o próprio banco**, que roda em duas zonas de disponibilidade.

Detalhe: `docs/technical-context/c4/seq-criacao-pedido.md` · ADRs 0001, 0002, 0003 e 0007

---

## 6 · Como roda na AWS

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 30, "rankSpacing": 45}}}%%
flowchart LR
    u(["Cliente<br/>Parceiro"])
    entrada["<b>Entrada</b><br/>Route 53 · CloudFront + WAF<br/>API Gateway · ALB interno"]

    subgraph sinc["O cliente espera"]
        ped["<b>Serviço de Pedidos</b><br/><i>2 → 6 tarefas</i>"]
        cache[("Cache do Catálogo<br/><i>TTL 5 min</i>")]
        rds[("<b>Banco de Pedidos</b><br/>Multi-AZ")]
    end

    subgraph assinc["Depois da resposta — assíncrono"]
        relay["Relay"]
        fila{{"SNS + SQS"}}
        valid["Validador"]
        cat["Serviço de Catálogo"]
    end

    u --> entrada --> ped
    ped -->|"① cotação"| cache
    ped ==>|"② pedido"| rds
    rds -->|"③ evento"| relay --> fila --> valid
    valid -->|"④ confere preço"| cat
    valid -->|"⑤ confirma ou rejeita"| rds
    cat -.->|"preço mudou: invalida"| cache

    style ped stroke-width:3px
    style rds stroke-width:4px
    linkStyle 3 stroke:#080,stroke-width:4px
```

**① e ② são o que o cliente espera** — a cotação lê o cache; o pedido só confere a assinatura e grava. **③ a ⑤ acontecem depois.** Só o banco de Pedidos derruba a criação. **US$ 1,8–3,0 mil/mês.**

Detalhe: `docs/technical-context/servicos-aws.md` — rede, escala, invalidação do cache, custos e alternativas

---

## 7 · Migração em três ondas

| Onda | Ataca | Critério para avançar |
|---|---|---|
| **30** | idempotência · outbox · snapshot | 0 duplicatas · 0 eventos perdidos · **0 downtime** |
| **60** | API de parceiros · fim do N+1 | 1 parceiro integrado · **0 consumidor quebrado** |
| **90** | app · segundo país · 10× | 99,9% · legado descomissionado |

**A ordem segue natureza do dano, não visibilidade:**

> Duplicidade, evento perdido e ausência de snapshot **corrompem dado** — irreversível.
> N+1, canal bloqueado e evolução travada **degradam experiência** — reversível.

Por isso a onda 30 **não** ataca o N+1, que é a dor mais visível.

Detalhe: `docs/delivery/plano-30-60-90.md`

---

## 8 · A prova — 132 testes em PostgreSQL real

**Como rodar:** com PostgreSQL local, um comando instala, cria o banco de teste, gera dados sintéticos e executa tudo. O mesmo roda a cada push, no CI.

```
$ cd slice && python prova.py
131 passed, 1 skipped
```

| | O teste | O que prova |
|---|---|---|
| ⭐ | 20 requisições **simultâneas** com a mesma chave | cria **1 pedido**: uma resposta `201`, dezenove `200` |
| ⭐ | um sistema que usa a **versão atual** da API, com a nova no ar | **continua funcionando** |
| | o publicador de eventos **cai no meio do envio** | o evento pode sair duas vezes, mas **nunca se perde** |
| | consulta de pedido com o **Catálogo fora do ar** | funciona — o pedido guarda o que precisa |

⭐ = os dois critérios críticos do enunciado. O teste pulado verifica exceções técnicas vencidas, e nenhuma está registrada.

> **Das 20 requisições, 19 foram barradas pelo próprio banco.** A garantia é da `PRIMARY KEY`, não de código que poderia falhar.

Detalhe: `slice/README.md` — cada módulo, a decisão que implementa e o teste que a prova

---

## 9 · O trade-off que mais custa

**`201 Created` mudou de significado** — de *"venda confirmada"* para *"pedido recebido"*.

| | v1 | v2 |
|---|---|---|
| JSON | idêntico | idêntico |
| Status code | `201` | `201` |
| **Significado** | venda feita | pedido recebido |

**Um diff de schema passa.** E todo consumidor que emite nota fiscal no `201` quebra em produção.

**Solução:** durante os 6 meses de compatibilidade, a v1 só responde depois da confirmação, como hoje — uma fachada sobre o fluxo novo. Débito **com data de vencimento**.

> Compatibilidade é **estrutural e semântica**. Validar só schema entrega falsa segurança — pior que nenhuma, porque o pipeline verde autoriza o merge.

Detalhe: `docs/decisions/ADR-0004-versionamento-e-compatibilidade-semantica.md`

---

## 10 · Como o projeto foi feito — especificação antes do código

**Desenvolvimento guiado por especificação (SDD), com o Claude conduzindo entrevistas.** Cada artefato nasce de um comando versionado no repositório, que faz uma pergunta por vez até a especificação fechar:

| Etapa | Comando | O que define |
|---|---|---|
| Negócio | `/prd` | tese, hipótese, escopo dentro e fora, critério de pronto |
| Pessoas | `/persona` · `/jornada` | para quem é, e onde dói hoje |
| Restrições | `/constraints` | cada exigência do enunciado vira número verificável |
| Decisões | `/adr` · `/arquitetura` · `/c4` | alternativas confrontadas e o porquê de cada escolha |
| Entrega | `/contratos` · `/estimativa` | contratos, tarefas, time e custo |

Só depois vem o código — e ele é verificado pelos testes e pela conferência automática da entrega.

> **A IA propõe, calcula e verifica. A decisão é humana** — 10 sugestões da IA foram rejeitadas, cada uma com o motivo registrado.

Detalhe: `docs/ai-context/uso-de-ia.md` · comandos em `.claude/commands/`

---

## 11 · Investimento — fase 1

| | |
|---|---|
| **R$ 155–162 mil** | total da fase 1 — pessoas, licenças e infraestrutura |
| **5 pessoas · 20 dias úteis** | arquiteto em meio período, 2 sênior, 1 pleno, 1 SRE |
| **63 dias-pessoa** | 47 tarefas decompostas, com desenvolvimento assistido por IA |

**Quem define o prazo é o SRE, não o dev.** Zero janela de indisponibilidade é trabalho de operação — rollout em degraus, alerta de falha silenciosa, reversão sem deploy — e a IA quase não o acelera.

> A IA vira **uma pessoa a menos**, não uma data mais cedo.

Detalhe: `docs/delivery/estimativa-fase1.md` · `taxas-de-mercado.md` · `resumo-executivo.md`

---

## 12 · O que o cliente precisa decidir

| Pergunta | Por que importa |
|---|---|
| **Existem outros sistemas chamados na criação do pedido**, além do Catálogo? | cada um traz de volta a dependência do slide 2 — e muda o prazo da primeira onda |
| **Quantos pedidos duplicam e quantos eventos se perdem hoje?** | sem o número de hoje, não há como provar que a primeira onda resolveu |
| **Qual o teto de custo de infraestrutura?** | sem teto, não dá para dizer se US$ 1,8–3,0 mil/mês cabe no orçamento |

O que não tem dado **ficou marcado como desconhecido, não inventado**: são números que só existem medindo o sistema atual.

> Marcar a lacuna é decisão, não omissão.

Detalhe: `docs/delivery/riscos-premissas.md` §5

---

## Para levar

1. **A disponibilidade exigida não fecha com o Catálogo no caminho do pedido.** Por isso criar o pedido virou uma operação local — e só o banco de Pedidos pode derrubá-la.
2. **A primeira onda corrige o que corrompe dado**, não o que é mais visível.
3. **Está provado:** 132 testes em PostgreSQL real, rodando a cada push.

**Para aprofundar, o `README.md` organiza a leitura em três níveis:**

| Tempo | O que ler |
|---|---|
| **10 minutos** | resumo executivo → ADR-0007 → rodar a prova |
| **30 minutos** | + C4 do estado-alvo → sequência de criação → ADRs 0001, 0002 e 0003 |
| **2 horas** | + threat model → plano 30/60/90 → decomposição → estimativa |

Detalhe: `README.md` — roteiro de leitura e índice de todos os artefatos
