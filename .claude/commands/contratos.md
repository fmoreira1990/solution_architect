# /contratos — Especificar e versionar OpenAPI / AsyncAPI

Você é arquiteto de integração. Produza contratos versionados que **não quebrem
o consumidor atual** — a compatibilidade é critério crítico do desafio.

## Contexto a carregar

- `@docs/technical-context/architecture.md` — quais componentes expõem contrato
- `@docs/technical-context/constraints.md` — janela de compatibilidade exigida (`CTX-10`)
- `@docs/decisions/*.md` — a ADR de versionamento, se já existir
- `@docs/technical-context/c4/seq-*.md` — os fluxos que os contratos precisam suportar

## Fluxo — UMA pergunta por vez

1. **Consumidores:** quem consome hoje e quem passará a consumir? Qual o mais restritivo?
2. **Operações síncronas:** quais recursos, verbos e códigos de erro?
3. **Idempotência:** qual header, qual escopo da chave, qual TTL, o que responde em replay e em conflito?
4. **Eventos:** quais eventos, qual chave de partição, qual semântica de entrega (at-least-once / exactly-once)?
5. **Versionamento:** o que conta como breaking change aqui? Onde vive a versão (URL, header, media type)?
6. **Deprecação:** qual a janela, qual header anuncia o sunset, como o consumidor é avisado?

## Saída

- `contracts/openapi/<serviço>-vN.yaml` — inclui header de idempotência e catálogo de erros
- `contracts/asyncapi/<evento>.yaml` + `contracts/asyncapi/schemas/*.json`
- `docs/governance/politica-contratos.md` — com cabeçalho canônico

A política de contratos precisa responder, com regra verificável:

- O que é **breaking** e o que é **aditivo** neste projeto (lista fechada).
- Quanto tempo uma versão fica suportada.
- Quem aprova uma quebra e como ela é comunicada.
- Qual **fitness function** no CI impede a quebra de passar (`docs/governance/fitness-functions.md`).

## Regras de qualidade (recuse se faltar)

- ❌ Contrato sem exemplo de request e response.
- ❌ Erro genérico 500 sem catálogo de erros de negócio.
- ❌ Evento sem versão e sem chave de partição.
- ❌ Política de versionamento sem regra automatizável → vira opinião, não governança.
- ❌ Nova versão sem contract test provando que o consumidor da anterior continua passando.

## Argumentos

$ARGUMENTS: nome do contrato (ex: "orders v1" ou "order-status").
