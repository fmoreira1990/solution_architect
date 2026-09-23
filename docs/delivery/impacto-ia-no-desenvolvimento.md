# Impacto de IA assistida no prazo e no time

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** se desenvolver a onda 30 com assistência de IA reduz prazo e equipe, quanto, e o que **não** reduz. Inclui licenças no custo. É cenário alternativo à `estimativa-fase1.md`, não substituição dela.
**Requisitos cobertos:** `D-05`
**Fontes:** `docs/delivery/decomposicao-onda-30.md`, `docs/technical-context/padroes-desenvolvimento.md` §7, `docs/ai-context/uso-de-ia.md`
**Data:** 2026-09-24

---

## A evidência que temos é este próprio repositório

Quase toda proposta que promete ganho com IA estima por analogia ou por material de fornecedor. Aqui há algo melhor: **a fatia executável foi construída com assistência de IA, e o processo está registrado.**

O que ela produziu: 114 testes em PostgreSQL real, 7 ADRs, 16 diagramas validados, 3 contratos versionados, 18 fitness functions — em cerca de **dois dias** de trabalho assistido.

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
| **Total** | **79** | **~22%** | **63** | |

### Por que o transversal não ganha nada

São 15 dias-pessoa de revisão de código, revisão de segurança, runbooks, acompanhamento de rollout e cerimônias.

**A revisão de código assistido por IA não é mais rápida — é diferente, e frequentemente mais lenta por linha.** Este projeto tem evidência direta disso. Três defeitos reais, todos produzidos com assistência de IA, **nenhum detectado por teste**:

| Defeito | Por que passou | O que o pegou |
|---|---|---|
| Chave de idempotência sem escopo de autorização (`F1.5`) | todos os testes passavam | **modelagem de ameaças** |
| Validador de diagramas parou de ver metade dos arquivos | **continuou verde** | conferir a contagem, não o resultado |
| Mensagem de erro quebrava com `UnicodeEncodeError` | caminho nunca exercitado | **testar o caminho de erro** |

O padrão: **código assistido por IA passa em teste com facilidade. O que ele erra é o que ninguém pensou em testar** — fronteira de autorização, modo de falha silenciosa, caminho de exceção.

Se a revisão for tratada como despesa a cortar, o ganho de 22% vira dívida com juros. O transversal fica em 15 dias-pessoa **de propósito**, e a proporção dele sobe de 19% para **24%** do esforço total.

---

## Prazo: cai menos que o esforço

```
63 d.p. ÷ alocação de 72%  ≈  16 dias úteis
```

**De 20 para 16 dias úteis — 20% de redução, contra 22% de esforço.**

A diferença não é arredondamento. É porque **o caminho crítico da onda 30 não é código**:

```
P1 baseline  →  P3 inventário  →  A9.2/A9.3 adequação de consumidores
   (medição)      (descoberta)        (depende de terceiros)
```

Nenhum dos três acelera com IA. Somados, são ~21 dias-pessoa que definem o piso do cronograma.

> **Mais gente ou mais IA não comprime prazo que depende de terceiros.** Isso já estava registrado como risco `R1` da estimativa; a IA não muda.

---

## Equipe: muda a forma, não só o tamanho

| Perfil | Sem IA | Com IA | Variação |
|---|---|---|---|
| Arquiteto de Soluções | 9,5 | **9,5** | — |
| Dev Sênior | 33 | 26 | −21% |
| Dev Pleno | 16 | **9** | **−44%** |
| SRE / DevOps | 20,5 | 18,5 | −10% |
| **Total** | **79** | **63** | −20% |
| **Pessoas** | **5,5** | **4,5** | **−1** |

### O que a tabela mostra

**O arquiteto não reduz.** Normalização de contrato, negociação com consumidores externos e revisão de segurança são exatamente o que a IA não faz — e o achado `F1.5` mostra que é onde ela erra.

**O pleno reduz quase pela metade.** Expurgo, backfill, reconciliação e job de adequação são tarefas bem especificadas, com padrão conhecido. É onde o ganho se concentra.

**A proporção de sênior sobe** — de 42% para 41% do esforço, mas de 2 para 2 pessoas num time menor. Em time de 4,5, dois sêniores são 44% das pessoas contra 36% antes.

> **A conclusão desconfortável para quem vende IA:** ela reduz o trabalho que um pleno faria, não o que um sênior faz. **Time menor, mais sênior, revisão mais cara por linha.**

---

## Licenças e custo

### Ferramentas de desenvolvimento assistido

| Item | Assentos | US$/mês |
|---|---|---|
| Assistente de código com contexto de repositório | 4,5 | **US$ 90–270** |
| Ambiente de execução para agentes *(opcional)* | — | US$ 0–50 |
| **Total** | | **US$ 90–320/mês** |

Faixa ampla porque o modelo de cobrança varia entre assento fixo, consumo e híbrido. Ferramentas de assento cobram ~US$ 20–60/mês; as de consumo dependem de volume e podem passar disso num mês intenso — **é custo variável, não fixo, e precisa de teto**.

### Efeito no custo total da fase 1

| | Sem IA | Com IA |
|---|---|---|
| Esforço | 79 d.p. | **63 d.p.** |
| Pessoas | 5,5 | **4,5** |
| Prazo | 20 dias úteis | **16 dias úteis** |
| Licenças de IA | — | **US$ 90–320/mês** |
| Infraestrutura AWS | US$ 835–1.489/mês | igual |
| Custo de pessoas | 79 × taxa | **63 × taxa** |

**A licença é irrelevante diante da economia.** 16 dias-pessoa economizados pagam a licença dezenas de vezes. O ponto de atenção não é o custo — é o **teto de consumo**, para que ferramenta cobrada por uso não vire surpresa.

> Outras licenças de software: **nenhuma identificada**. A stack de produção ainda não foi decidida (`CTX-13`/`CTX-14`), e a arquitetura usa serviços gerenciados AWS, sem licença própria. Se a escolha cair em runtime ou banco comercial, entra aqui.

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
| 2 | Ganho de 22% não se confirmar | Alto — prazo volta a 20 dias | Recalibrar ao fim da semana 2, como o fator de produção |
| 3 | Time de 4,5 pessoas ter menos folga para imprevisto | Médio | A contingência de 15% cobre |
| 4 | Ferramenta cobrada por consumo estourar | Baixo | Teto declarado no contrato |
| 5 | **Dependência de ferramenta externa** | Médio | O código resultante é convencional; não há *lock-in* técnico |
| 6 | Dado do cliente em prompt | **Crítico** | Regra já registrada: nenhum dado real, nenhuma credencial |

---

## Recomendação

**Propor o cenário com IA como alternativa declarada, não como o número principal.**

| | Conservador | Com IA |
|---|---|---|
| Esforço | 79 d.p. | 63 d.p. |
| Time | 5,5 | 4,5 |
| Prazo | 20 dias úteis | 16 dias úteis |

Razões para apresentar assim:

**O ganho de 22% é derivado, não medido em projeto do cliente.** A âncora é a fatia deste desafio — evidência real, mas de escopo pequeno.

**O prazo depende de terceiros, e isso não muda.** Prometer 16 dias e depender da adequação de consumidores externos é assumir risco que não está sob controle.

**Um concorrente que prometer 40% de ganho estará ignorando o transversal.** Vale dizer isso na proposta: o ganho existe no código e **não existe na revisão** — e a revisão fica mais cara por linha, não mais barata.

## Pendências registradas

- Recalibrar o ganho de 22% ao fim da semana 2, com dado real.
- Definir teto de consumo se a ferramenta for cobrada por uso.
- Confirmar que a política do cliente permite código assistido por IA e sob quais condições.
