# Personas — Plataforma de Pedidos e Catálogo

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** personas **derivadas** das restrições de §2.2.1 do desafio — não entrevistadas. São premissa, não fato, e precisam ser confirmadas com o Client Face antes de sustentarem decisão irreversível.
**Fontes:** `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf` (§2.2.1), `docs/prd/pedidos-catalogo.md`
**Data:** 2026-09-22

---

> ## Frase âncora *(derivada — a validar)*
> *"Eu preciso consertar o que está quebrado embaixo enquanto abro três canais novos em cima — e não posso derrubar ninguém no caminho."*

---

## Método de derivação

O desafio não apresenta persona. As sete restrições de §2.2.1 foram lidas como evidência indireta: cada uma descreve, por implicação, alguém que executa uma ação, sofre uma consequência ou responde por um prazo.

| # | Evidência (§2.2.1) | O que a frase implica sobre uma pessoa | Aponta para |
|---|---|---|---|
| 1 | "Pedidos consulta o Catálogo... pedidos grandes geram **padrão N+1**" | Alguém diagnosticou e **nomeou** o padrão — conhece o código, não só o sintoma | Primária |
| 2 | "Preço e descrição não são snapshot, **dificultando auditoria**" | Auditoria é atividade executada por alguém; "dificultando" implica tentativa frustrada **recorrente** | Secundária A |
| 3 | "Retries não possuem idempotency key e eventos... **sem garantia transacional**" | Diagnóstico de causa raiz no fluxo de publicação | Primária |
| 4 | "**Parceiros solicitam** API pública versionada e notificações" | Existe canal de demanda: parceiros pedem **a alguém** que prioriza roadmap | Secundária B + Primária |
| 5 | "Dados pessoais devem atender **LGPD e residência de dados**" | Obrigação regulatória tem dono nomeado | Secundária C |
| 6 | "Contratos atuais devem permanecer compatíveis por **pelo menos seis meses**" | Alguém **assumiu esse compromisso** com os consumidores | Primária |
| 7 | "Primeira melhoria segura em produção em **30 dias, sem janela**" | Alguém é **cobrado** pelo prazo e por não derrubar produção | Primária |
| 8 | Metas de cabeçalho: 10×, 99,9%, p95 ≤ 500 ms | Alguém carrega metas de atributo de qualidade | Primária |

**Cinco das oito evidências convergem para a mesma pessoa:** quem responde pela plataforma de Pedidos, simultaneamente por dívida técnica, prazo, compatibilidade e metas de qualidade. É a persona primária.

---

## Persona primária *(derivada)*

### Marina — líder técnica da plataforma de Pedidos

**1. Papel e contexto.**
Responde pela plataforma de Pedidos e Catálogo de uma rede de varejo omnichannel. Acumula decisão técnica e prioridade de roadmap: é para ela que os parceiros escalam pedido de integração (evidência 4), é dela o compromisso de seis meses de compatibilidade (evidência 6) e é ela quem responde pelo prazo de 30 dias sem janela (evidência 7). Tamanho do time: `???` — a levantar; a decomposição de `/estimativa` depende deste número.

**2. Dor do problema do PRD.**
Quatro dores simultâneas, todas com baseline `???` porque o enunciado não traz dado de produção:

| Dor | Origem | Custo hoje |
|---|---|---|
| Pedido duplicado por retry chega ao fluxo e alguém reconcilia | evidência 3 | `???` ocorrências/mês |
| Não consegue provar qual preço o cliente viu no momento da compra | evidência 2 | `???` disputas/mês sem resposta |
| Pedido grande degrada porque o Catálogo é consultado item a item | evidência 1 | `???` ms no p95 hoje |
| Parceiro esperando integração que não existe | evidência 4 | `???` receita bloqueada |

A dor **não é** que o sistema esteja caindo. É que ele funciona hoje e **não sobrevive ao 10×** — cada um dos quatro problemas escala com um multiplicador diferente (por item, por retry, por parceiro).

**3. Alternativas tentadas.** `???`
Não derivável de §2.2.1. O que o texto **sugere** e precisa ser confirmado, não assumido:
- A persistência dos quatro débitos junto a metas ambiciosas indica que existem paliativos operacionais em vigor (conciliação manual, congelamento de preço em campanha, integração ponto a ponto com parceiro). **Hipótese, não conclusão.**
- Perguntar ao Client Face: *o que já foi tentado e por que não pegou?* A resposta muda o apetite a risco da onda 30.

**4. Critério de sucesso, nas palavras dela.** *(derivado das evidências 6, 7 e 8)*
> "Em 30 dias eu ponho a primeira correção em produção e ninguém percebe — nenhum cliente, nenhum consumidor, nenhuma janela. Em 90 dias eu tenho três canais rodando e continuo conseguindo olhar nos olhos de quem integrou comigo há dois anos."

O sucesso dela é medido em **ausência de dano**, não em funcionalidade entregue. Isso explica por que "sem janela de indisponibilidade" aparece como restrição dura e não como preferência — e é o que justifica feature flag e convivência já na primeira onda, encarecendo a fase 1 em relação a uma migração com janela.

**5. Frase âncora.** *(derivada — a validar)*
> *"Eu preciso consertar o que está quebrado embaixo enquanto abro três canais novos em cima — e não posso derrubar ninguém no caminho."*

---

## Personas secundárias *(derivadas)*

**A. Quem audita preço** — analista de operação ou financeiro.
Deriva da evidência 2. Precisa responder "qual preço o cliente pagou e por quê" depois que o Catálogo mudou. Hoje não consegue, porque o dado não foi registrado no momento da compra. **É a única persona cuja dor é irreversível:** o histórico não pode ser reconstruído (ver escopo OUT nº 4 do PRD) — para ela, a solução só vale daqui para frente.

**B. Parceiro de marketplace** — integrador externo.
Deriva da evidência 4. É o único ator que o desafio mostra **pedindo** algo explicitamente. Precisa de API pública versionada e notificação assíncrona de status. Está fora da fronteira de confiança da plataforma, o que o torna também fonte de ameaça no `/threat-model` — conteúdo que ele envia não é confiável.

**C. Encarregado de dados / DPO** — compliance.
Deriva da evidência 5. Responde por LGPD e pela residência de dados do segundo país. Não usa o sistema, mas tem poder de veto sobre a arquitetura multi-região. Entra cedo: `PR-03` (qual é o segundo país) bloqueia a ADR de residência, e essa ADR não pode ser decidida sem esta persona.

---

## O que não é derivável de §2.2.1

Registrado para não ser preenchido por invenção (regra Q7 de `docs/CONVENCOES.md`):

- Nome, tamanho e senioridade do time da Marina — bloqueia `/estimativa` (`D-05`).
- Baselines numéricos das quatro dores — bloqueia a camada de valor de `/metricas` e os gates G30/G60.
- Alternativas já tentadas e por que falharam.
- Quem é o Client Face e qual o nível de maturidade técnica dos consumidores atuais.
- Se os "consumidores atuais" são internos, externos ou ambos — muda radicalmente a estratégia de compatibilidade de `CTX-10`.

---

## Riscos abertos

1. **Persona derivada, não entrevistada.** Toda a jornada e as métricas herdam essa fragilidade. Se a Marina real for, por exemplo, um PO sem autoridade técnica, a estratégia de convivência e o apetite a risco da onda 30 mudam.
2. **A convergência de cinco evidências pode ser artefato do texto, não da realidade.** O enunciado foi escrito por uma pessoa só, o que naturalmente produz uma voz única. A pessoa real pode ser duas — um PO e um tech lead — com prioridades conflitantes.
3. **A secundária C tem poder de veto e chega tarde.** Se a residência de dados for decidida sem ela, a ADR-0006 nasce inválida.

## Pendências registradas

- Confirmar as três personas com o Client Face antes de `/jornada` sustentar números.
- O item "se os consumidores atuais são internos ou externos" precisa ser respondido antes de `/contratos` — define se a política de deprecação é negociável ou contratual.
- A persona primária foi presumida no PRD como "operação de pedidos"; esta derivação a corrige para **liderança técnica da plataforma**. Atualizar a referência no PRD.
