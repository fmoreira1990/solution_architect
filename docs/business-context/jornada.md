# Jornada · Marina evoluindo a plataforma sem quebrar quem já depende dela

**Slug do PRD:** pedidos-catalogo
**Persona:** Marina, líder técnica da plataforma de Pedidos (`docs/business-context/personas.md`)
**Escopo deste documento:** a jornada do **problema** — conviver com quatro débitos estruturais e evoluir sob restrição de continuidade. Não é a jornada de uso do sistema pelo cliente final.
**Fontes:** `contexto/desafio-tecnico-arquiteto-senior-coe 2.pdf` (§2.2, §2.2.1), `docs/prd/pedidos-catalogo.md`, `docs/business-context/personas.md`
**Data:** 2026-09-22

---

## ANTES — hoje, canal web nacional com os quatro débitos ativos

**Onde:** plataforma de Pedidos servindo um único canal web nacional. Catálogo em serviço separado, consultado de forma síncrona item a item. Eventos de pedido publicados no broker após o commit, sem garantia transacional.

**O que Marina e o time fazem:**

1. Recebe chamado da operação sobre pedido duplicado e **investiga log** para distinguir retry de pedido legítimo.
2. **Reconcilia manualmente** o duplicado — cancelamento, estorno, comunicação ao cliente. `???` qual o processo exato.
3. **Consulta o Catálogo** para responder disputa de preço e descobre que o valor **já mudou** — não há o que apresentar.
4. **Adia pedido de integração** de parceiro de marketplace, porque não existe API pública versionada para oferecer.
5. **Evita tocar no contrato atual**, mesmo sabendo que ele limita a evolução, por não ter como provar que uma mudança não quebra consumidor.
6. **Acompanha a latência** da criação de pedido degradar conforme o pedido cresce, sem orçamento de latência por hop para saber onde ela se perde.
7. **Planeja a expansão** (app, marketplace, segundo país) sabendo que o desenho atual não absorve 10×.

**Dor neste momento:**

| Dor | Como escala | Reversível? |
|---|---|---|
| Retry vira pedido duplicado; conciliação é manual | por **retry** — e retry cresce com instabilidade e com volume | ❌ **Não** — corrompe dado |
| Evento de pedido se perde entre commit e publicação | por **volume** | ❌ **Não** — o evento não existe mais |
| Não há prova de qual preço o cliente viu | por **mudança de preço** — promoção multiplica | ❌ **Não** — o dado nunca foi gravado |
| Criação degrada em pedido grande (N+1) | por **item do pedido** | ✅ Sim — degrada experiência |
| Canal de parceiro bloqueado | por **parceiro na fila** | ✅ Sim — receita adiada |
| Evolução travada por medo de quebrar consumidor | por **consumidor integrado** | ✅ Sim |

**Tempo gasto:** `???` em todas as linhas. O enunciado não traz dado de produção, e o baseline é a primeira pergunta ao Client Face (ver `docs/prd/pedidos-catalogo.md` §6).

O que **é** conhecido sem baseline é a **forma** de cada curva: quatro multiplicadores diferentes (por item, por retry, por promoção, por parceiro) que hoje coexistem em escala tolerável e, ao 10×, deixam de ser toleráveis ao mesmo tempo.

---

## DURANTE — as três ondas, com dois caminhos no ar

**Onde:** caminho legado e caminho novo **convivendo**, separados por feature flag. Contratos v1 e v2 publicados simultaneamente. Observabilidade comparando os dois.

**O que Marina e o time fazem:**

1. **Ativa a flag** por percentual de tráfego, em vez de virar a chave de uma vez — imposto por `CTX-11` ("sem janela de indisponibilidade").
2. **Compara dashboards** do caminho novo contra o antigo, procurando divergência de resultado, não só de latência.
3. **Reverte por flag** ao primeiro sinal de divergência, sem deploy.
4. **Mantém v1 e v2 no ar** e acompanha quem ainda consome a versão antiga.
5. **Reconcilia pedidos entre os dois caminhos** durante a convivência — trabalho que **não existia antes** e que só existe por causa da migração.
6. **Negocia a janela de deprecação** com os consumidores atuais, dentro do compromisso de seis meses.
7. **Atravessa os gates** G30, G60 e G90, cada um autorizando o seguinte.

**Dor neste momento:**

- **Duas superfícies de falha simultâneas.** Convivência dobra o custo cognitivo e a área de diagnóstico: um incidente agora tem duas origens possíveis.
- **Reconciliação entre caminhos é trabalho novo.** A migração cria uma dor temporária que não existia no ANTES — custo legítimo da estratégia incremental, e precisa aparecer na estimativa de `D-05`.
- **Sem baseline, provar melhora é difícil.** Marina precisa demonstrar no gate que o caminho novo é melhor, mas os `???` do ANTES tiram a régua. Isso torna o levantamento de baseline **pré-requisito do G30**, não tarefa paralela.
- **Rollout progressivo é mais lento que janela de manutenção.** A restrição de continuidade encarece a fase 1 — o desenho correto custa mais que o desenho rápido, e isso precisa estar explícito na proposta.
- **A observabilidade necessária ainda não existe.** Comparar dois caminhos exige instrumentação que a plataforma atual não tem; ela é pré-requisito da onda 30, não entrega dela.

**Tempo gasto:** 90 dias de calendário, com gates em 30, 60 e 90. Apenas a onda 30 tem esforço estimado (§2.5.3).

---

## DEPOIS — estado-alvo, três canais e duas regiões

**Onde:** plataforma servindo web, app móvel e parceiros de marketplace, em duas regiões, com residência de dados pessoais atendida.

**O que Marina e o time fazem:**

1. **Onboarda parceiro novo** pelo contrato público versionado, sem abrir projeto de integração.
2. **Responde disputa de preço** consultando o snapshot gravado no próprio pedido — sem depender do estado atual do Catálogo.
3. **Deixa o retry acontecer.** A idempotência absorve; não há mais conciliação manual de duplicado.
4. **Evolui o contrato de forma aditiva**, com contract test no CI barrando a quebra antes do merge — o medo vira verificação automatizada.
5. **Descomissiona o caminho legado**, ou acorda data para isso.

**Dor neste momento — residual, não eliminada:**

- **Convivência de versões tem custo permanente.** Os seis meses são o mínimo contratual, e **cada nova versão reabre a janela**. A dor muda de natureza: deixa de ser medo e passa a ser custo previsível de manutenção.
- **O snapshot não é retroativo.** Disputa sobre pedido anterior à onda 30 continua sem resposta, para sempre. É a única dor do ANTES que a solução **não** resolve — ver escopo OUT nº 4 do PRD.
- **O outbox adiciona latência de publicação.** O evento passa a ser confiável, mas não instantâneo; consumidores que assumiam publicação síncrona precisam absorver consistência eventual.
- **Multi-região adiciona custo fixo e complexidade de residência.** Foi escolha, não acidente — mas aparece na conta todo mês.

**Tempo gasto:** `???` — a meta é que as linhas de conciliação manual e disputa de preço caiam a zero para pedidos novos.

---

## Tabela-resumo · Fricção total mapeada

| Momento | Conciliação de duplicado | Auditoria de preço | Canal de parceiro | Evolução de contrato |
|---|---|---|---|---|
| **ANTES** | manual, `???` ocorrências/mês | impossível — dado não existe | bloqueado | travada por medo |
| **DURANTE** | manual **+ reconciliação entre caminhos** (pior que o ANTES) | idem, para pedidos legados | v1 em produção na onda 60 | flag + contract test |
| **DEPOIS** | zero para pedidos novos | por snapshot, para pedidos novos | self-service por contrato público | aditiva, verificada no CI |

**A fricção piora antes de melhorar.** O DURANTE é pior que o ANTES na coluna de conciliação — e essa é a característica honesta de uma migração incremental sob restrição de continuidade. Esconder isso da proposta seria vender a estratégia pelo benefício sem o custo.

---

## Fricção principal a resolver

Das seis dores do ANTES, **três corrompem dado e três degradam experiência**. A distinção define a ordem das ondas:

> **Duplicidade, perda de evento e ausência de snapshot são irreversíveis** — cada dia de operação produz dano que nenhuma correção futura desfaz. N+1, canal bloqueado e evolução travada são reversíveis: doem continuamente, mas não deixam cicatriz.

Por isso a onda 30 ataca **idempotência, outbox e snapshot**, e não o N+1 — que é a dor mais visível e a mais fácil de demonstrar. O N+1 pode esperar 30 dias; um pedido duplicado hoje não pode ser desduplicado depois.

Esse é também o argumento que sustenta a escolha da fatia executável (`P2-08`): a prova valida a decisão que para o sangramento, não a que melhora o número de vitrine.

---

## O que medir para fechar os `???`

Pré-requisito do gate G30, não tarefa paralela:

| Medida | Por quê | Bloqueia |
|---|---|---|
| Pedidos duplicados por retry / mês | é a meta primária da onda 30 | G30 |
| Eventos publicados vs. pedidos commitados (divergência) | quantifica a perda que o outbox elimina | G30 |
| p95 de criação por faixa de itens no pedido | isola o custo do N+1 do resto do caminho | G60 |
| Nº de consumidores integrados e quais versões consomem | define se a deprecação é negociável ou contratual | `/contratos` |
| Disputas de preço sem resposta / mês | dimensiona a dor da secundária A | resumo executivo |

## Riscos abertos

1. **A jornada herda a fragilidade da persona derivada.** Se Marina real for duas pessoas com prioridades conflitantes, o DURANTE muda — a decisão de reverter por flag pressupõe uma única pessoa com autoridade para isso.
2. **O DURANTE assume que a observabilidade fica pronta a tempo.** Se ela escorregar, a comparação entre caminhos não existe e o G30 vira decisão por fé.
3. **A negociação de deprecação com consumidores não tem dono identificado.** Marina conduz tecnicamente, mas se os consumidores forem externos, isso é conversa contratual — e o Client Face precisa entrar.

## Pendências registradas

- Os cinco itens de "o que medir" precisam virar backlog real antes da onda 30.
- O passo 2 do ANTES ("reconcilia manualmente") está sem detalhe de processo — confirmar com a operação antes de estimar o ganho da onda 30.
