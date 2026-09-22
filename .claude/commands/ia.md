# /ia — Capacidade de IA e registro do uso de IA

Dois papéis em um comando:

- **(a) Arquitetar** uma capacidade de IA para o produto.
- **(b) Registrar** o uso de IA na elaboração deste próprio trabalho.

## Contexto a carregar

- `@docs/technical-context/architecture.md` — onde a capacidade de IA se encaixa
- `@docs/security-context/threat-model.md` — a IA adiciona fronteira de confiança nova
- `@docs/technical-context/constraints.md` — LGPD, residência de dados, orçamento

---

## (a) Arquitetar a capacidade — UMA pergunta por vez

1. **Tarefa:** qual trabalho humano concreto a IA reduz? Qual o custo dele hoje?
2. **Alternativa não-IA:** o que resolveria isso sem modelo? Por que não basta?
3. **Padrão:** RAG, agente com ferramentas, classificação ou chamada direta — e por quê?
4. **Isolamento:** o modelo alcança qual dado? O que fica **fora** da fronteira dele?
5. **Minimização:** qual PII é redigida antes do prompt? Qual a retenção de prompt e resposta?
6. **Guardrails:** quais ações são permitidas? O agente escreve em base transacional? (default: não)
7. **Prompt injection:** conteúdo de terceiro (parceiro, cliente) chega ao prompt? Como é neutralizado?
8. **Observabilidade:** o que é tracejado — prompt, custo, latência, taxa de recusa?
9. **Avaliação:** qual o eval set? Qual métrica e qual limiar libera subir uma versão de prompt?
10. **Custo e degradação:** qual o teto de gasto e o que acontece quando o modelo está indisponível?

**Saída:** `docs/ai-context/arquitetura-ia.md` com cabeçalho canônico, diagrama da
fronteira de dados em Mermaid, e o bloco de decisão do `@docs/CONVENCOES.md` §4.

### Regras de qualidade (recuse se faltar)

- ❌ IA sem alternativa não-IA avaliada → provavelmente é solução procurando problema.
- ❌ Agente com acesso de escrita a base transacional sem justificativa explícita.
- ❌ Capacidade sem eval set → não há como saber se regrediu.
- ❌ Sem plano de degradação quando o modelo cai → vira ponto único de falha novo.
- ❌ PII cruzando fronteira de residência de dados.

---

## (b) Registrar o uso de IA na elaboração

Acrescente uma entrada em `docs/ai-context/uso-de-ia.md` **a cada sessão de trabalho**,
com a íntegra dos prompts relevantes em `docs/ai-context/prompts/<slug>.md`.

Formato definido em `@docs/CONVENCOES.md` §7. O campo **Rejeitado** é obrigatório:
o critério de avaliação mede a capacidade de recusar saída de IA, não de aceitá-la.

O documento precisa responder, no topo: qual ferramenta, por que ela, como as saídas
foram validadas e quais cuidados com dados foram tomados.

## Argumentos

$ARGUMENTS: `capacidade` (parte a), `log` (parte b), ou vazio para ambas.
