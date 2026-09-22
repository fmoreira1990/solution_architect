# /jornada — Jornada da persona resolvendo o problema do PRD

Você é um pesquisador de produto. Mapeie a jornada da persona resolvendo o
problema central do produto.

## Contexto a carregar (antes de perguntar qualquer coisa)

1. `@docs/prd/*.md` — o problema-raiz que a jornada precisa resolver.
2. `@docs/business-context/personas.md` — a persona cuja jornada você vai mapear.
3. `@docs/technical-context/constraints.md` — as restrições numéricas do cenário.

Se a persona ou o PRD não existirem, instrua a rodar `/persona` ou `/prd` antes.

## Importante

A jornada é de como a **persona resolve o problema HOJE** (sem o produto) e
como resolveria DEPOIS (com o produto). É a jornada do PROBLEMA — não de uma
feature específica. Os momentos de maior fricção desta jornada são o que vai
**gerar** as ondas de migração.

## 3 momentos

Para cada momento, extraia:

1. **Onde:** ferramenta/lugar/canal físico ou digital
2. **O que ela faz:** lista concreta de ações (verbos)
3. **Dor neste momento:** o que trava, irrita ou consome tempo
4. **Tempo gasto:** unidade clara (min/dia, h/semana) ou métrica técnica (p95, taxa de erro)

### ANTES
Quando o produto AINDA não existe. Hoje, como ela resolve o problema?

### DURANTE
Quando o produto ESTÁ rodando (aqui: durante a migração 30/60/90). Como ela resolve o problema agora?

### DEPOIS
Pós-adoção do produto. O que muda na rotina dela?

## Regras

- Use `???` quando não souber. Não invente.
- Cada ação = verbo + objeto + ferramenta
- Dor com custo mensurável (tempo, frustração, retrabalho, pedido perdido, chamado aberto)

## Saída

Gera `docs/business-context/jornada.md` no formato dos 3 momentos.
Ao final, tabela-resumo com fricção total mapeada.

Aplique o cabeçalho canônico de `@docs/CONVENCOES.md`.

## Argumentos

$ARGUMENTS: persona alvo (default = persona primária do projeto).
