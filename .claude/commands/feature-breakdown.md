Você é tech lead. ANTES de decompor, leia:
- @docs/prd/*.md — o escopo IN e a hipótese.
- @docs/business-context/personas.md — quem sofre o problema.
- @docs/business-context/jornada.md — os momentos onde a persona trava.
- @docs/technical-context/constraints.md — as restrições `CTX-*` que limitam o recorte.
- @docs/requisitos/matriz-entregaveis.md — os entregáveis obrigatórios que cada feature deve cobrir.

Decompõe em 3-7 features concretas. **Cada feature deve destravar um momento
da jornada da persona** — não só cobrir um item do escopo IN. Feature que não
aponta pra nenhum passo da jornada é candidata a escopo creep: questione.

## Para cada feature, gera

- *Problema:* qual fatia da dor do PRD esta feature ataca? Cite número.
- *Escopo:* 1 frase + 3-5 sub-itens (verbo + objeto).
- *Valor:* qual momento da jornada da persona esta feature destrava? Cite @jornada.md.
- *Esforço:* P (≤ 1 fase) · M (2-3 fases) · G (4+ fases).
- *Dependências:* quais outras features precisam existir antes desta?
- *Onda:* 30, 60 ou 90 dias — e por que não pode ser antes nem depois.
- *Requisitos cobertos:* IDs de `@docs/requisitos/matriz-entregaveis.md`.

## Após decompor

Proponha *MoSCoW*:
- MUST (1-3 features): bloqueia hipótese do PRD se ausente.
- SHOULD: importante mas não bloqueante.
- COULD: nice-to-have.
- WON'T: explicitamente OUT.

Identifique candidata a *feature-âncora*:
- É MUST.
- Grau de entrada 0 no grafo (não depende de outras).
- Pelo menos 2 outras features dependem dela.
- Cabe em P ou M.
- Gera valor mesmo entregue sozinha.

Salva 1 arquivo docs/features/<slug>.md por feature.
Marca a âncora no header: > **TIPO:** feature-âncora.