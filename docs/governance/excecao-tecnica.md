# Processo de exceção técnica

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** como violar deliberadamente uma regra de arquitetura sem que isso vire dívida invisível. Processo leve, com validade obrigatória.
**Requisitos cobertos:** `D-04`
**Fontes:** `docs/governance/politica-contratos.md`, `docs/CONVENCOES.md`, todas as ADRs
**Data:** 2026-09-23

---

## Por que existe

Toda governança de arquitetura enfrenta o mesmo dilema: **regra sem válvula de escape é contornada em silêncio.** Quando o prazo aperta e a regra atrapalha, o time não pede permissão — ele desativa o teste, adiciona um `# noqa`, ou simplesmente não menciona.

O resultado é pior que a exceção: a violação existe, ninguém registrou, e ninguém sabe quando cobrá-la.

Este processo troca **proibição por prazo**. A regra continua valendo; o desvio é permitido, nomeado, datado e com dono.

---

## O que exige exceção

| Situação | Exemplo concreto |
|---|---|
| Violar um **enforcement** de ADR | pular o teste com o Catálogo desligado (`ADR-0003`) |
| Quebrar contrato **sem** nova versão | ver `politica-contratos.md` §5 — não há caminho normal para isso |
| Ignorar **fitness function** no CI | desabilitar o detector de drift |
| Colocar **PII em Pedidos** | endereço de entrega, antes de `V8` fechar |
| Adicionar dependência **síncrona** no aceite | contraria a `ADR-0007` |
| Antecipar sunset de versão | encurtar a janela de `CTX-10` |

**Não exige exceção:** decisão nova em área ainda não coberta por ADR. Isso é uma ADR nova, não um desvio.

---

## O formulário — cabe em uma página

Arquivo em `docs/governance/excecoes/EXC-NNN-<slug>.md`:

```markdown
# EXC-NNN — <título>

**Regra violada:** <ADR, política ou fitness function>
**Solicitante:** <nome> · **Aprovador:** <nome>
**Aberta em:** AAAA-MM-DD · **Válida até:** AAAA-MM-DD
**Status:** Ativa | Encerrada | Vencida

## Por que
<qual restrição real força o desvio — prazo, dependência externa, bloqueio de terceiro>

## O que exatamente é violado
<escopo preciso: quais arquivos, quais rotas, qual teste. "Parcialmente a ADR-0003" não serve>

## Risco assumido
<o que pode dar errado enquanto a exceção vigorar, e quem sente>

## Mitigação enquanto dura
<o que reduz o risco sem remover a exceção>

## Plano de saída
<o que precisa acontecer para fechar, e quem faz>

## Verificação
<como saber que foi encerrada — de preferência, um teste que volta a passar>
```

---

## Regras do processo

**1. Validade é obrigatória, e tem teto de 90 dias.**
Exceção sem data é dívida disfarçada de decisão. Precisar de mais de 90 dias significa que não é exceção — é arquitetura, e merece ADR.

**2. Renovação exige nova aprovação, não é automática.**
Renovar é permitido. Renovar sem que alguém olhe de novo, não.

**3. Exceção vencida quebra o build.**
Uma fitness function varre `docs/governance/excecoes/` e falha o CI quando encontra exceção `Ativa` com `Válida até` no passado. Sem isso, o processo vira formulário morto — que é como a maioria dos processos de waiver termina.

**4. O escopo tem de ser preciso.**
"Parcialmente a ADR-0003" não é escopo. "O endpoint `GET /orders/{id}` não passa pelo teste com o Catálogo desligado" é.

**5. Aprovador não pode ser o solicitante.**
Duas pessoas, sempre. Em time pequeno, o arquiteto aprova o desenvolvedor e o Client Face aprova o arquiteto.

**6. Toda exceção ativa aparece no índice do repositório.**
Não é possível ter exceção que só quem abriu conhece.

---

## Quem aprova

| Tipo de exceção | Aprovador |
|---|---|
| Enforcement de ADR técnica | arquiteto responsável |
| Contrato, versão ou sunset | arquiteto **+ Client Face** |
| PII, dado pessoal, residência | arquiteto **+ DPO** |
| Prazo ou escopo de onda | Client Face |

---

## Exceções ativas

Nenhuma até o momento.

Três candidatas já identificadas, que virarão exceção se forem adiante:

| Candidata | Regra que violaria | Gatilho |
|---|---|---|
| Endereço de entrega em Pedidos | `ADR-0006` e a estratégia de pseudonimização | se `V8` decidir por Pedidos |
| Consumidor que não deduplica em produção | obrigação **C2** da política de contratos | se um consumidor externo não se adequar a tempo |
| Antecipar sunset da v1 | janela de 6 meses de `CTX-10` | se o custo da fachada superar o de migrar os consumidores |

Registrá-las antes de acontecerem torna a decisão futura mais barata: o risco já está analisado.

---

## O que este processo **não** resolve

- **Não impede violação silenciosa.** Quem quiser burlar, burla — o processo reduz o atrito de fazer certo, não elimina o de fazer errado.
- **Depende de alguém revisar.** Se toda exceção for aprovada automaticamente, o processo é teatro.
- **Não substitui ADR.** Exceção é desvio temporário de uma decisão; ADR é a decisão.

A limitação está registrada de propósito: governança leve é escolha, e o custo dela é depender de disciplina. Se a taxa de exceções subir, o certo não é endurecer o processo — é revisar a regra que está sendo contornada com frequência.
