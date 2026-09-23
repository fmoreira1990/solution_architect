# ADR-0008 — Stack de produção: .NET 10

**Status:** Aceita — 2026-09-23
**Slug do PRD:** pedidos-catalogo
**Requisitos cobertos:** `CTX-13`, `CTX-14`, `D-03`
**Fontes:** `ADR-0001`, `ADR-0002`, `ADR-0005`, `docs/technical-context/padroes-desenvolvimento.md`, `docs/technical-context/servicos-aws.md`
**Escopo deste documento:** a stack da **plataforma de produção**. A stack da fatia executável é outra decisão, com outro critério, na `ADR-0005`.
**Data:** 2026-09-23

---

## Contexto

A fatia executável foi escrita em Python porque era o único runtime completo no ambiente de desenvolvimento — critério de prova, não de produção. A `ADR-0005` registra isso e avisa que não serve de precedente.

A produção pede outra coisa. Os serviços são poucos — aceite, relay, validador, Catálogo —, mas carregam as garantias da proposta: a transação única do aceite (`ADR-0001`, `ADR-0003`), o relay com `FOR UPDATE SKIP LOCKED` (`ADR-0002`) e migrações de schema **sem janela de indisponibilidade** (`CTX-11`).

Critérios, nesta ordem:

1. Produtividade de backend e ecossistema maduro — biblioteca, documentação, gente no mercado
2. Migrações de schema versionadas, reproduzíveis no pipeline
3. Acesso a PostgreSQL com controle explícito de transação onde a garantia depende dele
4. Suporte de longo prazo, cobrindo as três ondas e a operação depois delas
5. Integração com os serviços AWS escolhidos — SQS, SNS, Secrets Manager, observabilidade

---

## Decisão

**.NET 10 (LTS), com ASP.NET Core e EF Core sobre PostgreSQL.**

Quatro razões sustentam a escolha:

1. **Comunidade ampla de desenvolvedores.** Contratar, substituir e dimensionar o time é mais fácil numa stack com muita gente no mercado — e o time desta proposta ainda não está formado (`CTX-13`, `CTX-14`).
2. **Tecnologia madura.** Plataforma estável, com ciclo de versões LTS previsível e bibliotecas consolidadas para o que a proposta usa: HTTP, PostgreSQL, mensageria AWS e observabilidade.
3. **Backend produtivo, com migrations integradas.** ASP.NET Core resolve API com pouco código, e o EF Core versiona o schema no mesmo projeto — o que, com a regra de migração aditiva, sustenta a evolução sem janela.
4. **Roda em Linux.** Imagem de contêiner Linux, sem licença de sistema operacional, no mesmo ECS Fargate dos demais serviços — inclusive em ARM64 (Graviton), mais barato por vCPU.

| Camada | Escolha | Por quê |
|---|---|---|
| Runtime | **.NET 10**, versão LTS | suporte de três anos, cobrindo as três ondas e a operação seguinte |
| HTTP | **ASP.NET Core**, Minimal APIs | pouco cerimonial para poucos endpoints; OpenAPI nativo |
| Dados | **EF Core + Npgsql** | modelo, consultas e **migrations** versionadas no mesmo projeto |
| Mensageria | AWS SDK for .NET | SQS e SNS, já escolhidos em `servicos-aws.md` |
| Observabilidade | OpenTelemetry .NET | traces e métricas para CloudWatch e X-Ray, sem acoplar o código ao fornecedor |
| Testes | xUnit + **Testcontainers** | PostgreSQL real em teste de integração — o mesmo princípio da fatia |
| Contêiner | imagem Linux, ECS Fargate | .NET roda em ARM64, o que permite Fargate Graviton, mais barato por vCPU |

### Onde o EF Core não decide sozinho

O ORM é produtivo no caso comum e perigoso onde a garantia mora no banco. Três pontos ficam com semântica **explícita**:

| Ponto | Regra | Por quê |
|---|---|---|
| **Transação do aceite** | transação explícita, chave de idempotência inserida **primeiro**; violação de unicidade (`23505`) tratada como replay | a garantia é a `PRIMARY KEY` (`ADR-0001`) — o código precisa mostrar isso, não esconder |
| **Relay do outbox** | SQL explícito com `FOR UPDATE SKIP LOCKED` | o EF Core não expressa esse lock; é ele que permite mais de uma instância sem trabalho duplicado (`ADR-0002`) |
| **Retry automático** | a estratégia de retry do EF Core (`EnableRetryOnFailure`) só é aceitável no aceite **porque** a chave entra primeiro | reexecutar uma transação que já commitou cai na `PRIMARY KEY` e vira replay. Sem essa ordem, o retry duplicaria pedido |

A fatia executável é a **especificação** desses três pontos: o SQL que ela executa é o comportamento que o código .NET precisa reproduzir, e os testes críticos dela são reescritos em xUnit contra PostgreSQL real.

### Migrations sem janela

As migrations do EF Core rodam **no pipeline**, como etapa própria antes do deploy — nunca na subida da aplicação, onde várias tarefas disputariam a mesma migração.

Toda migration é **aditiva** (*expand/contract*): acrescenta coluna, tabela ou índice; remoção e renomeação acontecem só depois que nenhuma versão em produção as usa. É o que `CTX-11` exige: a versão antiga e a nova convivem sobre o mesmo schema durante o rollout.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **.NET 10 + ASP.NET Core + EF Core** | ✅ **Escolhida** | ecossistema amplo, backend produtivo, migrations versionadas integradas, LTS |
| Java 21 + Spring Boot | ❌ Rejeitada | mérito técnico equivalente; perde no critério 1 pela cerimônia maior para poucos serviços e nas migrations, que dependem de ferramenta à parte (Flyway, Liquibase) |
| Node.js + TypeScript | ❌ Rejeitada | ORMs e migrations menos maduros; o modelo de concorrência exige mais cuidado exatamente no caminho transacional |
| Python + FastAPI, a stack da fatia | ❌ Rejeitada | escolhida para a prova por disponibilidade de ambiente, não por mérito para produção; tipagem e desempenho ficam abaixo das alternativas no núcleo transacional |
| Go | ❌ Rejeitada | ótimo desempenho, mas ecossistema de ORM e migrations mais fragmentado — perde no critério 2 |

---

## Trade-offs aceitos

- **O ORM pode esconder a semântica da transação.** Mitigado pela seção *"Onde o EF Core não decide sozinho"* e pelos testes de integração em banco real — o SQL gerado é conferido onde a garantia depende dele.
- **O conhecimento do time em .NET é desconhecido** (`CTX-14`). A escolha é por mérito, não por aderência declarada do time. Se o time não conhecer .NET, a rampa entra na estimativa como premissa `E5`.
- **Duas linguagens no repositório.** A fatia continua em Python, como prova; a produção é .NET. A fatia não evolui para produção — ela **especifica** o comportamento.
- **LTS de três anos** exige migração planejada para a LTS seguinte antes do fim do suporte.
- **A IDE é paga.** .NET e EF Core são MIT, mas o Visual Studio Community não pode ser usado por empresa desse porte: US$ 45 por desenvolvedor por mês, no Professional. Detalhe em `impacto-ia-no-desenvolvimento.md`.

---

## Gatilho de revisão

**Se o time designado não conhecer .NET** e a rampa estimada passar de 20% do esforço da fase 1 (`E5`).

**Se o SQL gerado pelo EF Core divergir** da semântica da fatia em algum dos três pontos explícitos e a correção exigir contornar o ORM de forma recorrente.

**Antes do fim do suporte do .NET 10**, com um ano de antecedência, para migrar à LTS seguinte.

---

## Enforcement

1. **Os testes críticos da fatia são reescritos em xUnit + Testcontainers** — 20 requisições concorrentes com a mesma chave criam um pedido; queda do relay não perde evento; consumidor v1 não quebra. Mesmo PostgreSQL real, mesmas asserções.
2. **Regra de dependência do domínio** (`padroes-desenvolvimento.md` §1) verificada por teste de arquitetura com ArchUnitNET: o projeto de domínio não referencia EF Core, AWS SDK nem ASP.NET Core.
3. **Migration destrutiva quebra o build.** Uma verificação no pipeline procura `DropColumn`, `DropTable` e `RenameColumn` em migration nova; a remoção só entra com exceção técnica registrada (`excecao-tecnica.md`).
4. **Nullable reference types e warnings como erro**, habilitados em todos os projetos.
