# /constraints — mapear as 4 dimensões de restrição

Mapeie as 4 dimensões de restrição do projeto. Cada uma com
NÚMERO ou critério verificável — não descrição vaga.

## Contexto a carregar

- `@docs/prd/*.md` — escopo e critério de sucesso
- `@docs/requisitos/matriz-entregaveis.md` — os drivers `CTX-*` já extraídos do desafio

Toda restrição registrada aqui deve receber um ID `CTX-NN` e ser referenciável
pelo restante dos artefatos.

## Fluxo — UMA pergunta por vez

1. **Performance:** p95, throughput, concorrência esperada, fator de crescimento
2. **Equipe:** tamanho, senioridade, conhecimento atual, disponibilidade
3. **Orçamento:** infra/mês, licenças, ferramentas
4. **Regulação:** LGPD, residência de dados, compliance, retenção
5. **Prazo e compatibilidade:** janelas de entrega, tempo de suporte a contratos legados

## Saída

Grave em `docs/technical-context/constraints.md` com NÚMEROS, aplicando o
cabeçalho canônico de `@docs/CONVENCOES.md`.

Formato por restrição:

| ID | Restrição | Número/critério verificável | Origem | Consequência arquitetural |

## Anti-padrão

- Não aceite "alta performance" — peça "p95 < 500 ms na criação de pedido".
- Não aceite "time pequeno" — peça "8 devs, média de 3 anos".
- Não aceite "precisa escalar" — peça o fator ("10× o volume atual em 90 dias").
- Restrição sem consequência arquitetural declarada é anotação, não restrição.
