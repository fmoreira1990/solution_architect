# Uso de IA na elaboração do desafio

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** como a IA foi usada para produzir este repositório — ferramenta, modelo de trabalho, validação, decisões rejeitadas e cuidados com dados. Atende o §2.5.1 do enunciado e os itens `D-02` e `E-05`. O uso de IA **no produto** está em [`arquitetura-ia.md`](arquitetura-ia.md).
**Fontes:** `.claude/commands/`, `docs/CONVENCOES.md`, `docs/ai-context/prompts/`, `tools/conferir-entrega.py`, `slice/tests/`
**Data:** 2026-09-23

---

## 1. Ferramenta

**Claude (Opus), via Claude Code**, operando diretamente sobre o repositório.

A escolha se apoia em três propriedades:

1. **Lê e escreve o repositório.** Os artefatos são interdependentes — uma ADR cita uma restrição, um diagrama cita uma ADR, a estimativa cita a decomposição. Uma ferramenta de conversa obrigaria a recolar contexto a cada passo e perderia a rastreabilidade.
2. **O processo é versionado.** Cada tipo de artefato tem um comando em `.claude/commands/` que define entrevista, formato e critério de qualidade. Qualquer pessoa reproduz o mesmo processo e obtém um documento no mesmo formato.
3. **A saída é verificável.** Os mesmos testes e verificações que validam a entrega rodam sobre o que a IA produz.

---

## 2. Modelo de trabalho

**A IA propõe, deriva e verifica. A decisão é humana.**

O método é **desenvolvimento guiado por especificação** (*spec-driven development*, SDD): nada é escrito antes de a especificação que o justifica existir. Negócio, escopo, personas, jornada e restrições foram definidos em **entrevistas guiadas pelo Claude** — os comandos de `.claude/commands/` fazem uma pergunta por vez até a especificação fechar —, e só depois vieram arquitetura, decisões, contratos e código.

| Atividade | Responsável humano | Papel da IA |
|---|---|---|
| Escopo e prioridade | define | — |
| Decisão de arquitetura | decide e aprova | levanta alternativas e quantifica consequências |
| Números — dimensionamento, estimativa, custo | aprova as premissas | deriva e expõe a conta |
| Redação dos artefatos | revisa | redige a partir dos comandos |
| Código da fatia executável | define o que precisa ser provado | implementa e testa |
| Revisão da entrega | lê com olho de avaliador | confere números e referências contra a fonte |

Cada artefato segue o mesmo ciclo:

```
comando versionado → derivação ancorada no enunciado → rascunho → validação (§4) → aceite, correção ou rejeição
```

Quatro regras de `CONVENCOES.md` limitam o que a IA pode produzir:

| Regra | Efeito sobre a IA |
|---|---|
| **Q7** — `???` em vez de invenção | número sem fonte fica marcado como lacuna, não preenchido com valor plausível |
| **Q11** — nenhuma camada sem restrição que a justifique | componente proposto sem `CTX` correspondente é removido |
| **Derivar do enunciado, não escolher entre opções** | menu de alternativas plausíveis é substituído pela leitura do trecho que já contém a resposta |
| **Premissa que exclui escopo também é invenção** | exclusão recebe o mesmo escrutínio que inclusão |

---

## 3. Onde a IA atuou

| Atividade | Artefatos | Uso da IA | Validação principal |
|---|---|---|---|
| Requisitos | `requisitos/` | extração do enunciado em requisitos identificados | conferência item a item contra o enunciado |
| Produto e domínio | `prd/`, `business-context/` | entrevista guiada e derivação de evidências | cada afirmação amarrada a um trecho do enunciado |
| Arquitetura e decisões | `technical-context/`, `decisions/` | alternativas, contas e consequências | contas refeitas; toda ADR com ao menos duas alternativas rejeitadas |
| Contratos e fatia executável | `contracts/`, `slice/` | código, testes e dados sintéticos | 132 testes em PostgreSQL real; contrato comparado à implementação rodando |
| Segurança | `security-context/` | STRIDE por fronteira de confiança | ameaças verificáveis na fatia convertidas em teste |
| Estimativa e custo | `delivery/` | decomposição em tarefas e derivação de time, prazo e preço | conferência aritmética; premissas declaradas |
| Revisão da entrega | README, resumo, slides | leitura com olho de avaliador | conferência automatizada da entrega |

---

## 4. Como a saída foi validada

A validação é em camadas, e cada uma pega um tipo diferente de erro:

| Camada | O que verifica | Onde está |
|---|---|---|
| **Ancoragem no enunciado** | todo requisito tem artefato que o responde | [`rastreabilidade-pdf.md`](../requisitos/rastreabilidade-pdf.md) |
| **Testes da fatia** | a semântica das decisões — idempotência, outbox, snapshot, compatibilidade | `slice/tests/` |
| **Fitness functions** | convenções, contratos e referências cruzadas | [`fitness-functions.md`](../governance/fitness-functions.md) |
| **Conferência da entrega** | números citados, links, codificação, confidencialidade | `tools/conferir-entrega.py` |
| **Teste de mutação** | que a verificação sabe falhar | aplicado às verificações críticas |
| **Revisão humana** | o que nenhuma verificação cobre | concentrada em autorização, falha silenciosa e caminho de erro |

**O teste de mutação é a camada que valida as outras.** A verificação é quebrada de propósito para confirmar que o build fica vermelho. Uma verificação que não sabe falhar dá falsa segurança — pior que nenhuma, porque autoriza o merge.

### Defeitos que só a validação encontrou

| Defeito produzido com IA | Por que passou despercebido | O que o encontrou |
|---|---|---|
| Chave de idempotência sem escopo de autorização | todos os testes passavam | modelagem de ameaças |
| Validador de diagramas deixou de ler metade dos arquivos | continuou verde | guarda de contagem mínima |
| Mensagem de diagnóstico do `prova.py` quebrava no console Windows | caminho nunca exercitado | teste do caminho de erro em máquina limpa |
| Prazo de 16 dias calculado com o time errado | a conta parecia plausível | revisão da estimativa contra a tabela de time |

---

## 5. Decisões rejeitadas

Sugestões da IA recusadas, com o motivo:

| # | Sugestão | Motivo da rejeição |
|---|---|---|
| 1 | Decidir a stack da fatia antes de levantar requisitos | a stack é consequência das restrições, não premissa |
| 2 | Estreitar a hipótese do produto a uma aposta única | o §2.1 pede equilíbrio entre escala, disponibilidade, segurança, custo e prazo |
| 3 | Escolher a persona primária entre candidatas | a persona deve ser derivada das evidências do §2.2.1, não escolhida |
| 4 | Preencher tempos da jornada com valores plausíveis | viola a Q7 e contaminaria métricas e estimativa |
| 5 | Volumetria de 20 mil pedidos/dia | nessa faixa, a arquitetura proposta seria superdimensionamento (`AV-08`) |
| 6 | Read model por evento já na onda 30 | não cabe em 30 dias sem janela — registrado na ADR como rejeitado **por prazo, não por mérito** |
| 7 | Lock distribuído em Redis para idempotência | recolocaria dependência síncrona no caminho crítico; a `PRIMARY KEY` resolve |
| 8 | Replay literal da resposta gravada | com aceite assíncrono, devolveria um estado que já não é verdadeiro |
| 9 | BFF por canal e relay com deploy próprio | nenhuma restrição os justifica (Q11) |
| 10 | Subir a alocação do SRE para fechar a conta do prazo | mudar premissa para a conta caber é invenção |

**Correções vindas da direção humana.** Três mudanças de rumo partiram de quem conduziu o trabalho, não da IA: o desenho de cotação no carrinho e validação assíncrona, que reancorou a arquitetura; o recorte de escopo para Pedidos e Catálogo, que retirou Estoque, Pagamento e Carrinho introduzidos pela IA; e o fechamento do time em um SRE.

---

## 6. Prompts relevantes

A íntegra está em [`prompts/`](prompts/README.md). O critério de seleção é ter mudado o resultado — não há registro exaustivo de conversa.

| # | Prompt | Efeito |
|---|---|---|
| P1 | Congelar a escolha de stack | requisitos antes de tecnologia |
| P2 | Rejeitar a aposta única | hipótese composta de cinco pernas |
| P3 | Derivar em vez de escolher | personas deduzidas das evidências |
| P4 | O desenho da cotação e da validação assíncrona | arquitetura reancorada |
| P5 | O recorte de escopo | Pedidos e Catálogo apenas |
| P6 | Auditar lacunas contra o que já existe | rastreabilidade antes de produzir mais |
| P7 | Estimar na ordem certa | tarefas → esforço → time |

---

## 7. Cuidados com dados

- **Nenhum dado real.** O cenário é o do enunciado; volumetria e perfil de pedido são premissas declaradas, nunca apresentadas como fato.
- **Dados sintéticos na fatia executável**, sem PII. A chave de assinatura da cotação é fixa e sintética.
- **Nenhuma credencial, endpoint interno ou identificador real** entrou em prompt.
- **O enunciado não é versionado.** O CI verifica a versão publicada, e a conferência da entrega varre todo o histórico do repositório.

---

## 8. Limites observados

| Limite | Mitigação adotada |
|---|---|
| Código gerado passa nos testes e erra no que ninguém pensou em testar — autorização, falha silenciosa, caminho de erro | revisão sênior obrigatória nesses pontos, e modelagem de ameaças como etapa, não anexo |
| Tendência a oferecer menus de opções onde o enunciado já contém a resposta | releitura do trecho do enunciado antes de aceitar qualquer escolha |
| Tendência a completar lacunas com valores plausíveis | regra Q7 |
| A consistência entre documentos degrada com edições sucessivas | conferência automatizada de números, links e referências |

Os mesmos limites orientam a proposta de desenvolvimento assistido por IA para a fase 1, em [`impacto-ia-no-desenvolvimento.md`](../delivery/impacto-ia-no-desenvolvimento.md).
