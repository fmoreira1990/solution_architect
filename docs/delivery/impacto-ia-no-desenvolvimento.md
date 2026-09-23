# Impacto de IA assistida no prazo e no time

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** se desenvolver a onda 30 com assistência de IA reduz prazo e equipe, quanto, e o que **não** reduz. Inclui licenças no custo. É o cenário **adotado** na proposta; `estimativa-fase1.md` mantém o cenário sem IA como referência.
**Requisitos cobertos:** `D-05`
**Fontes:** `docs/delivery/decomposicao-onda-30.md`, `docs/technical-context/padroes-desenvolvimento.md` §7, `docs/ai-context/uso-de-ia.md`
**Data:** 2026-09-24

---

## A evidência que temos é este próprio repositório

Quase toda proposta que promete ganho com IA estima por analogia ou por material de fornecedor. Aqui há algo melhor: **a fatia executável foi construída com assistência de IA, e o processo está registrado.**

O que ela produziu: 132 testes em PostgreSQL real, 8 ADRs, 17 diagramas validados, 3 contratos versionados, 18 fitness functions — em cerca de **dois dias** de trabalho assistido.

E, mais importante para estimar: o registro em `uso-de-ia.md` mostra **onde a IA acelerou e onde ela errou**. É isso que permite projetar em vez de torcer.

---

## O ganho não é uniforme — e o prazo cai menos que o esforço

O erro comum é aplicar um percentual único sobre o total. A decomposição em 47 tarefas permite ser específico.

| Bloco | d.p. sem IA | Ganho | d.p. com IA | Por quê |
|---|---|---|---|---|
| **Pré-requisitos** (P1–P3) | 16 | **10%** | 14,5 | Medir duplicatas na base atual, instrumentar tracing e inventariar consumidores é trabalho de **descoberta**. A IA ajuda a escrever a consulta, não a descobrir o que medir |
| **A — Idempotência** | 11 | **35%** | 7 | Padrão conhecido, bem documentado. A canonicalização de payload (`A3`) ganha menos: é onde mora o caso de borda |
| **B — Snapshot e cotação** | 9,5 | **40%** | 5,5 | Migração aditiva, leitura em lote, assinatura HMAC — território onde a IA é forte |
| **C — Outbox e publicação** | 16 | **25%** | 12 | O relay ganha muito; **`A9.2`/`A9.3` ganham zero** — adequar consumidores depende de terceiros |
| **D — Convivência e rollout** | 11,5 | **20%** | 9 | Feature flag ganha; **rollout progressivo em produção não acelera** — os degraus levam o tempo que levam |
| **Transversal** | 15 | **0%** | 15 | Ver abaixo — e é o ponto mais importante deste documento |
| **Total** | **79** | **~20%** | **63** | |

### Por que o transversal não ganha nada

São 15 dias-pessoa de revisão de código, revisão de segurança, runbooks, acompanhamento de rollout e cerimônias.

**A revisão de código assistido por IA não é mais rápida — é diferente, e frequentemente mais lenta por linha.** Este projeto tem evidência direta disso. Três defeitos reais, todos produzidos com assistência de IA, **nenhum detectado por teste**:

| Defeito | Por que passou | O que o pegou |
|---|---|---|
| Chave de idempotência sem escopo de autorização (`F1.5`) | todos os testes passavam | **modelagem de ameaças** |
| Validador de diagramas parou de ver metade dos arquivos | **continuou verde** | conferir a contagem, não o resultado |
| Mensagem de erro quebrava com `UnicodeEncodeError` | caminho nunca exercitado | **testar o caminho de erro** |

O padrão: **código assistido por IA passa em teste com facilidade. O que ele erra é o que ninguém pensou em testar** — fronteira de autorização, modo de falha silenciosa, caminho de exceção.

Se a revisão for tratada como despesa a cortar, o ganho de ~20% vira dívida com juros. O transversal fica em 15 dias-pessoa **de propósito**, e a proporção dele sobe de 19% para **24%** do esforço total.

---

## Prazo: cai menos que o esforço

```
Sem IA:  SRE 20,5 d.p.  →  1,5 SRE para caber em 20 dias úteis
Com IA:  SRE 14   d.p.  ÷  (1 × 70%)  =  20 dias úteis, com 1 SRE
```

**O prazo não cai: fica em 20 dias úteis. O ganho vira uma pessoa a menos.**

O SRE define a data, e é o perfil que a IA menos acelera. Ele fecha em 14 d.p. porque os devs, desafogados pela IA, absorvem a instrumentação que mora no código — detalhe em [`estimativa-fase1.md`](estimativa-fase1.md) §2.

Daria para trocar: manter 1,5 SRE e cair para ~17,5 dias úteis. Não compensa, porque **o caminho crítico da onda 30 não é código**:

```
P1 baseline  →  P3 inventário  →  A9.2/A9.3 adequação de consumidores
   (medição)      (descoberta)        (depende de terceiros)
```

Nenhum dos três acelera com IA. Entregar o código três dias antes não antecipa um gate que espera terceiros; uma pessoa a menos é ganho que se realiza.

> **Mais gente ou mais IA não comprime prazo que depende de terceiros.** Isso já estava registrado como risco `R1` da estimativa; a IA não muda.

---

## Equipe: muda a forma, não só o tamanho

| Perfil | Sem IA | Ganho da IA | Com IA, 1 SRE |
|---|---|---|---|
| Arquiteto de Soluções | 9,5 | — | **9,5** |
| Dev Sênior | 33 | −21% → 26 | 28 |
| Dev Pleno | 16 | **−44% → 9** | 11,5 |
| SRE / DevOps | 20,5 | −10% → 18,5 | **14** |
| **Total** | **79** | −20% → 63 | **63** |
| **Pessoas** | **5,5** | | **4,5** — 5 cabeças, arquiteto em meio período |

A coluna do meio é o efeito da IA; a última, a redistribuição que ele permite: ~3,5 d.p. de instrumentação e ~1 d.p. de transversal saem do SRE para os devs.

### O que a tabela mostra

**O arquiteto não reduz.** Normalização de contrato, negociação com consumidores externos e revisão de segurança são exatamente o que a IA não faz — e o achado `F1.5` mostra que é onde ela erra.

**O pleno reduz quase pela metade.** Expurgo, backfill, reconciliação e job de adequação são tarefas bem especificadas, com padrão conhecido. É onde o ganho se concentra.

**O SRE quase não reduz.** Rollout progressivo em produção leva o tempo dos degraus. A redução para um SRE não vem da IA sobre o trabalho dele — vem da IA sobre o trabalho dos devs, que abre espaço para absorver a instrumentação.

**A proporção de sênior sobe** — de 42% para 44% do esforço, e de 36% para 44% das pessoas: dois sêniores num time de 4,5.

> **A conclusão desconfortável para quem vende IA:** ela reduz o trabalho que um pleno faria, não o que um sênior faz. **Time menor, mais sênior, revisão mais cara por linha.**

---

## Licenças e custo

### Licenças de ferramenta

Preços de tabela, cobrança mensal — a fase 1 dura um mês, e as ondas seguintes ainda não estão contratadas.

| Ferramenta | Assento | Quem | Qtd. | US$/mês |
|---|---|---|---|---|
| **Claude Team** — inclui Claude Code | premium, US$ 125 | quem escreve código: 2 sênior, 1 pleno, 1 SRE | 4 | 500 |
| **Claude Team** | standard, US$ 25 | arquiteto — revisão e redação, uso menor | 1 | 25 |
| **Visual Studio Professional** — IDE .NET (`ADR-0008`) | mensal, US$ 45 | 2 sênior, 1 pleno, 1 SRE | 4 | 180 |
| **Total** | | | | **US$ 705** |

**Por que assento premium para quem escreve código.** O assento standard tem o limite de uso de um plano individual; um desenvolvedor que trabalha o dia inteiro com o assistente o esgota. O premium tem 6,25 vezes esse limite.

**Por que a IDE é paga.** O Visual Studio Community é gratuito, mas não pode ser usado por organização com mais de 250 PCs ou mais de US$ 1 milhão de faturamento anual — e a extensão C# Dev Kit do VS Code segue a mesma licença. JetBrains Rider é alternativa equivalente; a escolha entre os dois é preferência do time, não de arquitetura.

**Cobrança anual reduz a linha da IA para US$ 420/mês** (US$ 100 o premium, US$ 20 o standard), mas compromete doze meses. Vale a partir da contratação das ondas 60 e 90. No Visual Studio o anual sai mais caro no primeiro ano e não compensa.

**O custo é fixo por assento.** Uso além do limite do plano só é cobrado se for habilitado — fica desabilitado, e o teto de gasto é o número de assentos.

### Efeito no custo total da fase 1

| | Sem IA | Com IA |
|---|---|---|
| Esforço | 79 d.p. | **63 d.p.** |
| Pessoas | 5,5 · 1,5 SRE | **4,5 · 1 SRE** |
| Prazo | 20 dias úteis | 20 dias úteis |
| Licenças — IA | — | **US$ 525/mês** |
| Licenças — IDE .NET | US$ 180/mês | US$ 180/mês |
| Infraestrutura AWS | US$ 1.812–3.034/mês | igual |
| Preço de pessoas *(faturado)* | R$ 149.832 | **R$ 123.374** |
| *com contingência de 15%* | *R$ 172.306* | ***R$ 141.880*** |

*Valores faturados, já com encargos CLT e com os tributos do Lucro Presumido — ver [taxas-de-mercado.md](taxas-de-mercado.md).*

**A licença é irrelevante diante da economia.** ~R$ 26,5 mil economizados em pessoas contra R$ 2.835/mês de licença de IA. A licença de IDE existe nos dois cenários.

### A economia em preço é menor que a economia em esforço

| | Sem IA | Com IA | Variação |
|---|---|---|---|
| Esforço | 79 d.p. | 63 d.p. | **−20,3%** |
| Preço de pessoas | R$ 149.832 | R$ 123.374 | **−17,7%** |

Os quase 3 pontos de diferença não são arredondamento: a IA reduz proporcionalmente mais o trabalho de **pleno** (−44%), o perfil mais barato, e **nada** do arquiteto, o mais caro.

> **Quanto mais sênior o time, menor o retorno financeiro da ferramenta** — ainda que o ganho de prazo permaneça. A taxa média ponderada sobe de R$ 1.897 para R$ 1.958 por dia-pessoa: o time fica menor e mais caro por cabeça.

> A economia **em margem** é menor ainda que a economia em preço. Cerca de 19,5% dos R$ 26,5 mil são tributos que deixam de ser recolhidos — dinheiro que nunca foi da empresa. O ganho líquido real para quem presta é da ordem de **R$ 21 mil**, e é esse o número a levar para discussão comercial.

> Licenças de runtime: **nenhuma**. .NET e EF Core são MIT (`ADR-0008`), PostgreSQL é livre, e a infraestrutura são serviços gerenciados AWS, cobrados na conta de infraestrutura.

---

## O que precisa mudar no processo para o ganho ser real

Não é só contratar ferramenta.

| # | Mudança | Por quê |
|---|---|---|
| 1 | **Fitness functions antes do código** | a IA acerta o que é verificado e erra o que não é. As 18 deste repositório são o piso, não o teto |
| 2 | **Revisão sênior obrigatória** em transação, autorização e contrato | os três defeitos reais estavam exatamente aí |
| 3 | **Teste de mutação nas verificações críticas** | *fitness function que não sabe falhar é decoração* — uma parou de verificar e ficou verde |
| 4 | **Caminho de erro é caminho** | o `prova.py` quebrava em dois dos três cenários mais prováveis |
| 5 | **Modelagem de ameaças como etapa, não anexo** | foi ela que achou `F1.5`; nenhum teste acharia |
| 6 | **Log de uso de IA com decisões rejeitadas** | `uso-de-ia.md` — é o que torna o processo auditável |

**Os seis já estão implementados neste repositório.** Não são promessa: são o que permitiu produzir a fatia em dois dias com defeito detectado e corrigido em vez de entregue.

---

## Riscos deste cenário

| # | Risco | Impacto | Resposta |
|---|---|---|---|
| **1** | **Cortar revisão para realizar o ganho** | Crítico — os três defeitos reais passariam | Transversal permanece em 15 d.p., inegociável |
| 2 | Ganho de ~20% não se confirmar | Alto — o SRE estoura primeiro | Recalibrar ao fim da semana 2; meio SRE nas semanas 3 e 4, pago pela contingência |
| 3 | **SRE único, sem folga** | Alto — define o prazo | Dedicação exclusiva; runbooks e sêniores no acompanhamento de rollout cobrem ausência curta |
| 4 | Ferramenta cobrada por consumo estourar | Baixo | Teto declarado no contrato |
| 5 | **Dependência de ferramenta externa** | Médio | O código resultante é convencional; não há *lock-in* técnico |
| 6 | Dado do cliente em prompt | **Crítico** | Regra já registrada: nenhum dado real, nenhuma credencial |

---

## Recomendação

**O cenário com IA é o da proposta, com o cenário sem IA mantido como referência.**

| | Sem IA *(referência)* | Com IA *(proposta)* |
|---|---|---|
| Esforço | 79 d.p. | 63 d.p. |
| Time | 5,5 · 1,5 SRE | 4,5 · 1 SRE |
| Prazo | 20 dias úteis | 20 dias úteis |

Como o risco foi tratado:

**O ganho de ~20% é derivado, não medido em projeto do cliente.** A âncora é a fatia deste desafio — evidência real, mas de escopo pequeno. Por isso a recalibração da semana 2 é marco do plano, e o meio SRE que o cenário sem IA pagaria sempre virou **gatilho** pago pela contingência.

**O prazo depende de terceiros, e isso não muda.** Por isso o ganho foi convertido em time menor, não em data mais cedo: prometer menos de 20 dias dependendo da adequação de consumidores externos seria assumir risco fora de controle.

**Um concorrente que prometer 40% de ganho estará ignorando o transversal.** Vale dizer isso na proposta: o ganho existe no código e **não existe na revisão** — e a revisão fica mais cara por linha, não mais barata.

## Pendências registradas

- Recalibrar o ganho de IA ao fim da semana 2, com dado real — é o que decide o gatilho de meio SRE.
- Confirmar que a política do cliente permite código assistido por IA e sob quais condições.
