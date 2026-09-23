# Resumo executivo — Evolução da Plataforma de Pedidos e Catálogo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** recomendação, investimento, riscos e decisões que dependem do cliente. Duas páginas, para quem decide — a profundidade está nos 38 documentos indexados no `README.md`.
**Fontes:** `docs/delivery/estimativa-fase1.md`, `docs/delivery/riscos-premissas.md`, ADRs 0001 a 0007
**Data:** 2026-09-23

---

## Recomendação

**Executar a evolução em três ondas de 30 dias, cada uma com valor próprio e gate de saída.** Parar em qualquer gate é decisão de negócio, não fracasso de projeto.

A ordem das ondas **não segue visibilidade, segue natureza do dano**:

> Três dos seis problemas atuais **corrompem dado** — pedido duplicado por retry, evento de pedido perdido e ausência de prova do preço praticado. Cada dia de operação produz estrago que nenhuma correção futura desfaz. Os outros três — N+1, canal de parceiros bloqueado, evolução travada — **degradam experiência**: doem continuamente, mas não deixam cicatriz.

Por isso a **onda 30 ataca idempotência, publicação confiável e snapshot de preço**, e não o N+1 — que é a dor mais visível e a mais fácil de demonstrar. Um pedido duplicado hoje não pode ser desduplicado depois.

---

## O achado que decidiu a arquitetura

Duas restrições que o edital apresenta separadamente, multiplicadas:

```
Pedidos 99,9%  ×  Catálogo 99,9%  =  99,8%
→ 86,4 min de indisponibilidade/mês
Error budget exigido: 43,2 min/mês
```

**A meta de disponibilidade é inatingível enquanto houver dependência síncrona no caminho crítico** — independentemente da qualidade do código. Duas vezes o orçamento, no cenário em que tudo o mais funciona.

A arquitetura proposta não é orientada a eventos por preferência de estilo. É a única forma de a conta fechar: tudo que exige resposta externa foi deslocado para **antes** da criação (cotação assinada) ou para **depois** dela (validação assíncrona). O aceite do pedido passa a ser uma operação **puramente local**.

O resultado mensurável: **de seis componentes, apenas um derruba a criação de pedido.**

---

## Investimento — fase 1 (30 dias)

| | |
|---|---|
| **Esforço** | **79 dias-pessoa**, decompostos em 47 tarefas |
| **Time** | 5,5 pessoas — 1 arquiteto (30%), 2 dev sênior, 1 dev pleno, 1,5 SRE |
| **Prazo** | 20 dias úteis · **cabe nos 30 corridos** |
| **Contingência** | +15% (12 d.p.), como linha separada e negociável |
| **Custo de pessoas** | 79 d.p. × taxa por senioridade — *insumo pronto; preço é decisão comercial* |
| **Custo de infraestrutura** | US$ 1.700–3.700/mês em regime, derivado do dimensionamento |

**A composição do time saiu do esforço, não o contrário.** E ela revelou algo contraintuitivo: **SRE consome 26%** — mais que o dobro do arquiteto. A causa é a exigência de *zero janela de indisponibilidade*: rollout progressivo com comparação a cada degrau, alertas de falha silenciosa e reversibilidade sem deploy são trabalho de operação, não de desenvolvimento.

Uma proposta dimensionada com "4 devs e apoio de infra" erraria exatamente na parte que sustenta o critério mais duro do gate.

### O que a restrição de continuidade custa

| Com janela de manutenção | Com "zero janela" |
|---|---|
| migração direta, deploy único, rollback por restore | migração aditiva, feature flag, rollout em 4 degraus, rollback exercitado em produção, observabilidade comparativa |
| | **+11,5 d.p. ≈ 15% do total** |

Não é desperdício — é o preço de uma restrição que o cliente impôs. Precisa estar visível: **um concorrente que não a respeitar parecerá 15% mais barato entregando outra coisa.**

---

## O que já está provado

A proposta não é apenas documental. A fatia executável roda em PostgreSQL real, com **111 testes**, e demonstra os dois critérios críticos do edital:

- **20 requisições concorrentes com a mesma chave criam exatamente um pedido.** As 19 respostas de replay só são alcançadas por violação da `PRIMARY KEY` — as threads competiram de verdade, e foi a constraint que segurou.
- **O consumidor legado não quebra com a versão nova no ar.** Um consumidor de referência que emite nota fiscal na resposta do POST continua passando.

Mais: queda do relay entre publicar e marcar **não perde evento**; consulta de pedido funciona **com o Catálogo fora do ar**; cotação assinada é honrada mesmo que o preço mude depois.

---

## Riscos principais

| # | Risco | Impacto | Resposta |
|---|---|---|---|
| **1** | **Existirem integrações no caminho de criação além do Catálogo** | Alto — cada uma reintroduz o problema de disponibilidade composta e adiciona ~4 d.p. | **Primeira pergunta ao Client Face.** Mapear antes de assumir a data |
| **2** | **Adequação dos consumidores depender de terceiros** | Alto — é prazo, não esforço; mais gente não acelera | Iniciar o inventário no dia 1 |
| **3** | **Alocação real abaixo de 72%** | Alto — a 50%, o prazo vai a 29 dias úteis e estoura | Confirmar dedicação **antes** de assumir a data |
| **4** | **Pico de demanda muito acima de 3×** | Alto — varejo tem Black Friday | Teste de carga com cenário de campanha, não de média |
| **5** | **Ausência de baseline tornar o gate indecidível** | Alto | Medição é **pré-requisito** do gate, não tarefa paralela |

**O maior risco da proposta foi eliminado, não mitigado.** Uma versão anterior supunha sistemas de Estoque e Pagamento como existentes — escopo que o edital não nomeia. Esses contextos foram removidos do desenho, e a decisão central sobreviveu reancorada no Catálogo. Uma decisão que sobrevive à remoção da premissa que a originou é mais sólida que uma que dependia dela.

---

## Decisões que precisam de validação

Nenhuma pode ser resolvida pela equipe técnica. As três primeiras afetam prazo e compromisso.

| # | Decisão | Quem decide | O que bloqueia |
|---|---|---|---|
| **V1** | Existem integrações no caminho de criação além do Catálogo? | Client Face / arquitetura da conta | **Prazo da onda 30** |
| **V3** | Baseline atual: duplicatas/mês, eventos perdidos, p95, disponibilidade | Operação | **Gate G30** — sem régua, indecidível |
| **V7** | Teto de custo de infraestrutura | Negócio | Uma das cinco dimensões do objetivo fica sem verificação |
| V8 | Dono do endereço de entrega — Pedidos ou Logística? | Arquitetura da conta | Estratégia de pseudonimização (LGPD) |
| V9 | Instrumento jurídico para transferência Brasil → EUA | Jurídico / DPO | Onda 90; nenhuma PII brasileira atravessa sem ele |
| V10 | Em quais estados dos EUA a operação estará sujeita | Jurídico / negócio | Quais leis estaduais se aplicam |

> **Sobre o segundo país.** O edital pede *"requisitos de residência de dados do novo país"*. Os Estados Unidos **não impõem residência** para dado comercial de varejo. A restrição real é outra e inverte de direção: dado pessoal **brasileiro** que vai para os EUA é transferência internacional sob a LGPD e exige instrumento jurídico. A segregação regional foi mantida — não por obrigação legal, mas porque minimiza transferência e simplifica a mecânica de direitos. *(Enquadramento de arquiteto, não parecer jurídico; requer validação do DPO.)*

---

## O que esta proposta assume e o que exclui

**Três premissas inventadas** por ausência de dado: volumetria (60k → 600k/dia), tamanho do pedido (8 itens, 15 no p95) e distribuição de pico (3×). A terceira é a mais frágil.

**Nove débitos aceitos**, entre eles: a fachada de compatibilidade reintroduz o acoplamento para consumidores antigos — consciente, minoritário e com data de vencimento; o snapshot desnormaliza ~1,1 TB/ano; rejeição pós-aceite vira modo de operação previsto, não incidente.

**Sete exclusões explícitas**, sendo uma definitiva: **o histórico de preços não pode ser reconstruído**. O dado do preço praticado nunca foi gravado — não é caro recuperar, é impossível. Pedidos anteriores à onda 30 seguem sem prova de preço, para sempre.

---

## Em uma frase

**A conta de disponibilidade não fecha com dependência síncrona no caminho crítico; a onda 30 corrige o que corrompe dado antes do que incomoda o usuário; e o custo de 15% da restrição de continuidade é o que separa esta proposta de uma que parece mais barata entregando outra coisa.**
