# ADR-0005 — Stack da fatia executável

**Status:** Aceita — 2026-09-22
**Slug do PRD:** pedidos-catalogo
**Requisitos cobertos:** `P2-08`, `P2-09`, `P2-10`
**Fontes:** `ROTEIRO-EXECUCAO.md` §F2 (gate G2), `ADR-0001`, `ADR-0002`
**Escopo deste documento:** esta ADR decide a stack da **prova**, não a da plataforma. São coisas diferentes, e confundi-las seria erro de leitura.
**Data:** 2026-09-22

---

## Contexto

O gate G2 do roteiro congelou a escolha de tecnologia até depois das ADRs de arquitetura, por princípio: **a stack é consequência das restrições, não premissa**. Cinco ADRs foram escritas sem que ela existisse, o que confirma que a decisão podia esperar.

Critérios definidos **antes** de olhar as opções, nesta ordem:

1. A prova sobe em um comando, em menos de 5 minutos
2. Ferramental maduro de validação de contrato
3. Aderência ao histórico de quem mantém
4. Legibilidade para quem avalia

O critério 1 domina, porque `P2-10` exige *"um único comando documentado"* e a prova vale zero se não rodar na máquina do avaliador.

---

## Decisão

**Python 3.12 + FastAPI + PostgreSQL 18 + pytest.**

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.12 | única runtime completa no ambiente de desenvolvimento |
| HTTP | FastAPI + uvicorn | endpoints síncronos rodam em threadpool — concorrência **real** no teste das 20 requisições |
| Banco | **PostgreSQL 18** | `FOR UPDATE SKIP LOCKED` da `ADR-0002`; escritas concorrentes de verdade |
| Driver | psycopg 3 | SQL explícito, sem ORM — o avaliador lê a transação como ela é |
| Testes | pytest + httpx | servidor real em thread; o teste fala HTTP, não chama função |
| Comando único | `python prova.py` | instala, cria schema, semeia e executa |

### O que a decisão **não** é

Isto **não** recomenda Python para a plataforma de Pedidos. A stack de produção depende de `CTX-13` e `CTX-14` — tamanho e senioridade do time —, que só serão conhecidos depois da estimativa por tarefa. Decidir a stack de produção antes disso repetiria o erro que o gate G2 existe para evitar.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **Python + FastAPI + Postgres** | ✅ **Escolhida** | Único runtime completo disponível; atende os quatro critérios |
| .NET 8 | ❌ Rejeitada — **indisponível** | O comando `dotnet` existe na máquina, mas `dotnet --list-sdks` retorna vazio: **nenhum SDK instalado**. Não é preterida, não está lá |
| Node.js + TypeScript | ❌ Rejeitada — **indisponível na decisão** | Ausente no momento do gate. Foi instalado depois, para validar Mermaid — tarde demais para reabrir sem custo |
| Java + Spring Boot | ❌ Rejeitada — **indisponível** | Sem JDK |
| SQLite no lugar de Postgres | ❌ Rejeitada | Rodaria sem infraestrutura, mas **serializa as escritas**: o teste de concorrência passaria por serialização do banco, não por mérito da constraint. Enfraqueceria o critério crítico de `P2-11` |

### Duas rejeições que valem registro

**`make` como comando único.** O `make` disponível no ambiente de desenvolvimento **não é GNU Make**, e um `Makefile` teria falhado onde foi escrito. `python prova.py` não depende de ferramenta externa nem de variante de implementação.

**Broker real (Kafka, Redpanda).** Rejeitado por escopo, não por indisponibilidade. A decisão provada é *"pedido e evento nunca divergem"*, que vive na **transação** e no **relay** — não no transporte. Um broker real não fortaleceria a prova e quebraria o comando único. O stub registra publicações e entrega duplicatas, que é exatamente o que o at-least-once produz.

---

## Justificativa

A escolha foi **determinada pelo ambiente**, e isso está declarado em vez de racionalizado. Com 48 horas até a entrega, instalar Docker ou um SDK ausente consumiria horas de um orçamento que não existia.

Onde houve escolha real, ela foi feita por mérito: **Postgres em vez de SQLite**. O Postgres já estava instalado e rodando, e a diferença importa — em SQLite o teste das 20 requisições concorrentes passaria porque o banco serializa escritas, não porque a `PRIMARY KEY` faz seu trabalho. A asserção de **1 resposta `201` e 19 respostas `200`** só tem valor quando as escritas competem de verdade.

---

## Trade-offs aceitos

- **Python não é a escolha óbvia para núcleo transacional de varejo.** Para a prova é irrelevante — o que se demonstra é a semântica da transação, não a performance do runtime.
- **Sem ORM, o SQL é explícito e verboso.** É intencional: o avaliador precisa ver a transação única com pedido, itens, snapshot, chave e outbox sem atravessar uma camada de abstração.
- **A prova exige Postgres com o usuário `prova` já criado.** Numa máquina limpa isso falha. Mitigado por mensagem de erro com o comando exato de criação, mas **o caminho de erro não foi testado em máquina limpa** — débito registrado.
- **O broker stub não exercita serialização, ordenação nem particionamento reais.** Escopo declarado, não lacuna esquecida.

---

## Gatilho de revisão

**Se a plataforma de produção for definida.** Aí a pergunta muda: `CTX-13`/`CTX-14` entram, e o critério 3 (aderência ao time) passa a dominar o critério 1 (velocidade até rodar). Esta ADR **não** deve ser citada como precedente para essa decisão.

**Se a latência de publicação virar requisito da prova.** O stub não mede nada de transporte; medir exigiria broker real.

**Se a prova precisar rodar em CI sem Postgres gerenciado.** Aí entra serviço de banco no workflow — já previsto em `.github/workflows/ci.yml`.

---

## Enforcement

1. **A prova é o enforcement.** `python prova.py` executa os 37 testes; CI vermelho barra o merge.
2. **Postgres é verificado, não presumido.** `db.ping()` falha com mensagem acionável se o banco não responder.
3. **Sem ORM por convenção**, não por regra automatizada — é acordo de legibilidade, e está aqui para não ser desfeito sem discussão.

---

## Pendências registradas

- O caminho de erro do `prova.py` (Postgres ausente ou credencial errada) **não foi testado em máquina limpa**. É o risco mais concreto de a prova falhar na mão do avaliador.
- A stack de produção continua indefinida e **depende de `CTX-13`/`CTX-14`**.
- Node.js foi instalado depois do gate, para validar diagramas Mermaid. Vale registrar que isso **não** reabre a decisão: trocar a stack da prova depois dos testes verdes seria refazer trabalho sem ganho.
