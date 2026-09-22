# /threat-model — Modelo de ameaças por fronteira de confiança

Você é arquiteto de segurança. Produza um threat model **simples e acionável** —
não um catálogo genérico de ameaças.

## Contexto a carregar

- `@docs/technical-context/c4/*.md` — as fronteiras de confiança já desenhadas
- `@docs/technical-context/architecture.md` — componentes e integrações
- `@docs/technical-context/constraints.md` — restrições de regulação (LGPD, residência de dados)
- `@docs/decisions/*.md` — controles já decididos

## Fluxo — UMA fronteira por vez

Para cada fronteira do C4, aplique STRIDE e responda:

1. **Identidade:** quem atravessa esta fronteira e como é autenticado?
2. **Superfície:** qual é a entrada exposta (endpoint, tópico, arquivo, console)?
3. **Ameaça:** o que um adversário faria aqui? (Spoofing, Tampering, Repudiation, Information disclosure, DoS, Elevation)
4. **Impacto:** o que ele alcança se conseguir? Cite o dado ou a operação concreta.
5. **Mitigação:** qual controle existe ou será criado? Onde ele é verificado?
6. **Risco residual:** o que permanece aceito mesmo com a mitigação?

Cobertura mínima exigida pelo desafio: **identidade, APIs públicas, dados, eventos e dependências**.

## Regras de qualidade (recuse se faltar)

- ❌ Ameaça sem ativo concreto ("acesso indevido") → exija qual dado, qual operação.
- ❌ Mitigação sem local de verificação → onde isso falha ruidosamente?
- ❌ Risco residual vazio em todas as linhas → threat model honesto sempre aceita algo.
- ❌ Ameaça de livro que não se aplica a esta arquitetura → corta.
- ❌ Dado pessoal sem classificação e sem região de residência declarada.

## Saída

`docs/security-context/threat-model.md`, com cabeçalho canônico e uma tabela por fronteira:

| # | Ameaça (STRIDE) | Ativo alcançado | Mitigação | Onde é verificada | Risco residual |

Ao final: **Riscos abertos** numerados e **Pendências registradas**.
Dados pessoais e residência vão para `docs/security-context/lgpd-residencia-dados.md`.

## Argumentos

$ARGUMENTS: fronteira específica ou vazio para todas.
