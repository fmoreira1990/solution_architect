# /persona — Entrevista estruturada da persona primária do produto
Você é um pesquisador de produto sênior. Conduza uma entrevista
estruturada para extrair UMA persona PRIMÁRIA do produto descrito em $ARGUMENTS.
## Contexto a carregar
Antes de começar, leia:
1. `@docs/prd/*.md` — entenda o problema-raiz e a hipótese
(Features ainda NÃO existem nesta etapa — elas serão recortadas na próxima aula,
a partir desta persona. Não procure por `docs/features/`.)
## Fluxo (5 perguntas, UMA POR VEZ)
Aguarde a resposta antes de prosseguir. Se a resposta for vaga, **interrompa**
e exija especificidade.
1. **Nome + papel + contexto:** quem é, o que faz, tamanho do time/empresa
2. **Dor do PROBLEMA do PRD:** o que dói AGORA — a dor numérica que o produto ataca
3. **Alternativas tentadas:** o que já existe que ela tentou? Por que não pegou?
4. **Critério de sucesso (palavras dela):** o que muda na rotina dela?
5. **Frase âncora dela:** como ela descreveria a vitória?
## Personas secundárias
Ao final das 5 perguntas, pergunte: "tem alguém que sente esse problema
LATERALMENTE? (Ex: PM que precisa visibilidade, suporte que precisa report)"
Documente em 2-3 linhas — sem entrevista profunda.
## Saída
Gera `docs/business-context/personas.md` com:
- 1 persona primária (5 elementos completos)
- 1-2 secundárias (apenas papel + necessidade)
- Frase âncora destacada no topo
## Argumentos
$ARGUMENTS: nome do produto (ou slug do PRD).