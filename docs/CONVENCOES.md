# Convenções de Especificação

**Escopo deste documento:** define como todo artefato deste repositório é nomeado, cabeçalhado e considerado pronto.
**Fontes:** convenções de documentação de arquitetura adotadas neste projeto, alinhadas aos entregáveis exigidos pelo desafio.
**Data:** 2026-09-22

---

## 1. Organização de diretórios

```
.claude/commands/          # cada comando = entrevista guiada que produz UM artefato
docs/
├─ CONVENCOES.md           # este arquivo
├─ prd/                    # o problema: tese, hipótese, escopo IN/OUT, critério de pronto
├─ requisitos/             # matriz de entregáveis e rastreabilidade do desafio
├─ business-context/       # personas.md · jornada.md · metricas.md
├─ technical-context/      # constraints.md · stack.md · architecture.md · c4/ · consistencia.md · resiliencia.md
├─ features/               # decomposição em ondas 30/60/90
├─ decisions/              # ADR-NNN-<slug>.md
├─ security-context/       # threat-model.md · lgpd-residencia-dados.md
├─ ai-context/             # arquitetura-ia.md · uso-de-ia.md · prompts/
├─ governance/             # politica-contratos.md · excecao-tecnica.md · fitness-functions.md
└─ delivery/               # plano-30-60-90.md · estimativa-fase1.md · resumo-executivo.md · apresentacao/
contracts/                 # openapi/ · asyncapi/
slice/                     # fatia executável (stack definida no gate G2)
```

**Regras de nomenclatura**
- Pastas em inglês, conteúdo em português.
- Arquivos em `kebab-case`, sem prefixo numérico, exceto ADRs (`ADR-NNN-<slug>.md`).
- Um artefato por arquivo. Um comando produz um arquivo.

---

## 2. Cabeçalho canônico

Todo documento em `docs/` abre com H1 + bloco de metadados + `---`:

```markdown
# <Tipo> — <Nome>

**Slug do PRD:** <slug>
**Escopo deste documento:** <o recorte; o que está fora aparece como gatilho de revisão>
**Fontes:** `caminho/a.md`, `caminho/b.md`   ← os arquivos que alimentaram este
**Data:** AAAA-MM-DD

---
```

Campos adicionais quando aplicável: `**Persona:**`, `**Status:**` (ADRs), `**Requisitos cobertos:**` (IDs `CTX-*`, `P1-*`, `P2-*`, `D-*`).

O campo **Fontes** é obrigatório. Ele é o que torna a cadeia auditável: nenhum documento aparece sem dizer de onde veio.

---

## 3. Regras de qualidade — um artefato só está pronto se passar em todas

| # | Regra | Anti-padrão que ela bloqueia |
|---|---|---|
| Q1 | Toda decisão ancorada em restrição, incidente, número ou persona | "Escolhemos Kafka porque é robusto" |
| Q2 | Mínimo 2 alternativas rejeitadas, **com o motivo da rejeição**, em tabela | Decisão apresentada como se não houvesse opção |
| Q3 | Trade-off explícito: o que se sacrifica ao escolher | Só os benefícios listados |
| Q4 | **Gatilho de revisão**: sob qual condição reabrir esta decisão | Decisão tratada como permanente |
| Q5 | **Enforcement** (ADRs): hook, lint, fitness function ou checklist de review | ADR que ninguém verifica |
| Q6 | Números verificáveis, nunca adjetivos | "alta disponibilidade" em vez de "99,9% mensal" |
| Q7 | Lacuna conhecida marcada com `???` — nunca preenchida por invenção | Número inventado para parecer completo |
| Q8 | Rastreabilidade por citação de arquivo (e linha, quando útil) | Afirmação órfã |
| Q9 | Riscos abertos numerados ao final do documento, quando houver | Risco conhecido e não registrado |
| Q10 | Pendências registradas: o que ficou faltando e por quê | Documento que finge estar completo |
| Q11 | Arquitetura mínima que atende as constraints de hoje | Fila, cache ou mesh sem `CTX` que justifique |

**Q7 é a regra mais importante deste repositório.** `???` é uma resposta válida e sinaliza maturidade; um número inventado contamina todos os artefatos a jusante.

**Q11 é a que a banca avalia como `AV-08` (atuação sênior).** Toda camada precisa de um `CTX-*` que a justifique; sem isso, vai para "fora de escopo" documentado.

---

## 4. Padrão de decisão (blocos reutilizáveis)

Em `stack.md`, `architecture.md` e ADRs, toda decisão usa este bloco:

```markdown
*Escolha:* <o que foi decidido>
*Restrição (origem):* <CTX-NN ou persona que impõe>
*Restrição técnica:* <requisito não-funcional com número>
*Alternativas consideradas:* <X, Y, Z>
*Justificativa:* <por que esta venceu>
*Trade-off:* <o que sacrificamos>
*Gatilho de revisão:* <quando reabrir>
```

Nas ADRs, "Alternativas consideradas" vira tabela com coluna de status:

| Alternativa | Status | Por quê |
|---|---|---|
| **<escolhida>** | ✅ **Escolhida** | <motivo ancorado em restrição> |
| <outra> | ❌ Rejeitada | <motivo> |
| <outra> | ❌ Rejeitada — **indisponível** | <não é preterida: não existe neste contexto> |

A distinção entre *rejeitada* e *rejeitada — indisponível* importa: uma é escolha, a outra é limitação. Confundir as duas enfraquece a ADR.

---

## 5. Fluxo de trabalho dos comandos

Cada comando em `.claude/commands/` conduz **uma entrevista, uma pergunta por vez**, e grava um arquivo. Regras comuns:

- Carregar o contexto (`@docs/...`) **antes** da primeira pergunta.
- Esperar a resposta antes de avançar. Resposta vaga → exigir exemplo concreto.
- Não contradizer decisão já documentada sem explicar o motivo.
- Recusar a gravação se as regras de qualidade da seção 3 não forem atendidas.

### Ordem de execução

```
/prd → /persona → /jornada → /constraints → /metricas
      → /arquitetura → /c4 → /adr (×N) → /stack (gate G2)
      → /contratos → /feature-breakdown → /threat-model
      → /ia → /estimativa
```

`/stack` roda **depois** das ADRs de arquitetura, não antes: a tecnologia é consequência das restrições, não premissa.

---

## 6. Artefatos e seus comandos

| Artefato | Comando | Saída |
|---|---|---|
| PRD | `/prd` | `docs/prd/<slug>.md` |
| Persona | `/persona` | `docs/business-context/personas.md` |
| Jornada | `/jornada` | `docs/business-context/jornada.md` |
| Métricas / SLOs | `/metricas` | `docs/business-context/metricas.md` |
| Constraints | `/constraints` | `docs/technical-context/constraints.md` |
| Arquitetura | `/arquitetura` | `docs/technical-context/architecture.md` |
| Diagramas C4 e sequência | `/c4` | `docs/technical-context/c4/*.md` |
| ADR | `/adr` | `docs/decisions/ADR-NNN-<slug>.md` |
| Stack | `/stack` | `docs/technical-context/stack.md` |
| Features / ondas | `/feature-breakdown` | `docs/features/<slug>.md` |
| Contratos | `/contratos` | `contracts/` + `docs/governance/politica-contratos.md` |
| Threat model | `/threat-model` | `docs/security-context/threat-model.md` |
| Capacidade de IA | `/ia` | `docs/ai-context/arquitetura-ia.md` |
| Estimativa | `/estimativa` | `docs/delivery/estimativa-fase1.md` |

---

## 7. Log de uso de IA

`docs/ai-context/uso-de-ia.md` é alimentado **a cada comando executado**, não no final. Registro mínimo por entrada:

```markdown
### <data> · <comando ou tarefa>
- **Prompt:** <o que foi pedido> (íntegra em `prompts/<slug>.md`)
- **Saída aceita:** <o que foi aproveitado>
- **Validação:** <como foi conferido — leitura crítica, teste, checagem contra CTX>
- **Rejeitado:** <o que a IA sugeriu e foi descartado> — **motivo:** <por quê>
- **Dados expostos:** <nenhum dado real / sintético / pseudonimizado>
```

O campo **Rejeitado** é obrigatório e não pode ficar vazio em todas as entradas — o critério `AV-07` avalia justamente a capacidade de recusar saída de IA, não de aceitá-la.

---
