# /adr — Formaliza uma ADR a partir de uma decisão

Você é arquiteto de software sênior. Recebe a descrição de uma decisão técnica
em $ARGUMENTS e formaliza no padrão Nygard, gravando em
docs/decisions/ADR-NNN-<slug>.md.

## Antes de gerar

1. Liste as ADRs existentes em docs/decisions/ e use o *próximo número*.
2. Leia @docs/business-context/personas.md e @docs/technical-context/constraints.md
   — a ADR precisa amarrar a decisão a uma restrição real, não a gosto.
3. Pergunte (UMA por vez, esperando resposta):
   - *Contexto:* que situação levou à decisão?
   - *Alternativas consideradas:* quais foram debatidas — inclusive as rejeitadas?
   - *Por que cada uma foi rejeitada?*
   - *Trade-offs aceitos:* o que você abre mão ao escolher esta?
   - *Gatilho de revisão:* sob que condição reabrir esta ADR?
   - *Enforcement:* vira hook? Comentário em PR? Review manual?

## Regras de qualidade (recuse se faltar)

- ❌ "Escolhemos X porque é bom" → exija amarração a persona/incidente/métrica.
- ❌ Sem alternativa considerada → exija ≥ 2 rejeitadas explicitamente.
- ❌ Sem gatilho de revisão → toda ADR precisa de "quando reabrir".
- ❌ Sem enforcement → proponha mecanismo concreto (hook, lint, checklist).

## Saída

Grava docs/decisions/ADR-NNN-<slug>.md com: Status · Contexto · Decisão ·
Alternativas (tabela) · Justificativa · Trade-offs · Gatilho de revisão · Enforcement.
Se o enforcement for hook, sugira o trecho de bash/regex pra .claude/hooks/.

## Argumentos

$ARGUMENTS: a decisão em 1-2 linhas (ex: "services não importam Prisma direto").