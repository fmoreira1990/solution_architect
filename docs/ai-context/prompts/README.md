# Prompts relevantes

**Escopo deste documento:** os prompts que produziram mudança de rumo no projeto, na forma como foram dados. Atende `E-05` — *"prompts relevantes, validações e cuidados com dados"*.
**Fontes:** transcrição das sessões de trabalho
**Data:** 2026-09-23

---

## Critério de seleção

Não estão aqui todos os prompts — estão os que **mudaram o resultado**. Um log completo de conversa é ruído; o que informa o avaliador é onde a direção humana corrigiu a máquina.

Cada entrada traz o prompt **literal**, o que a IA havia proposto, e o que mudou por causa dele.

---

## P1 · Congelar a decisão de tecnologia

> *"vamos deixar a escolha das stacks pra depois, primeiro vamos levantar os requisitos"*

**A IA havia proposto:** escolher a stack da fatia executável no primeiro turno, oferecendo quatro opções com recomendação.

**O que mudou:** a decisão foi congelada até o gate G2, depois das ADRs de arquitetura. Cinco ADRs foram escritas sem que a stack existisse — o que confirmou que ela podia esperar. O comando `/stack` foi reposicionado na ordem de execução das convenções.

**Por que importa:** tecnologia é consequência de restrição, não premissa dela. A `ADR-0005` registra que a escolha final foi determinada pelo ambiente, e declara isso em vez de racionalizar.

---

## P2 · Rejeitar a aposta única

> *"2.1. Objetivo geral — Definir a evolução arquitetural da plataforma de Pedidos e Catálogo, equilibrando escala, disponibilidade, segurança, custo e prazo."*

**A IA havia proposto:** estreitar a hipótese do PRD a **uma aposta central**, escolhida entre integridade, latência ou compatibilidade.

**O que mudou:** a resposta foi uma citação literal do enunciado. O §2.1 pede **equilíbrio** entre cinco dimensões; reduzir a uma aposta otimizaria um eixo contra os outros. A hipótese virou composta, com cinco pernas verificáveis separadamente.

**Padrão que este prompt revelou:** a IA tendia a oferecer menus de alternativas onde o enunciado já continha a resposta. A validação eficaz passou a ser reler o PDF, não escolher entre opções plausíveis.

---

## P3 · Derivar em vez de escolher

> *"não sabemos, vamos precisar presumir junto aos requisitos que temos na 2.2.1"*

**A IA havia proposto:** quatro candidatas a persona primária, como se a escolha fosse preferência.

**O que mudou:** o método passou de seleção para **dedução**. Cada uma das sete restrições de §2.2.1 foi lida como evidência indireta de alguém que executa uma ação, sofre uma consequência ou responde por um prazo. Cinco das oito evidências convergiram para a mesma pessoa — e a convergência virou o argumento, não a plausibilidade da descrição.

**Efeito colateral:** a derivação **contradisse o PRD**, que havia presumido "operação de pedidos" como persona primária. O PRD foi corrigido, em vez de a persona ser ajustada para caber nele.

---

## P4 · O desenho que reancorou a arquitetura

> *"o pedido é o que o carrinho fez usando o cache, ao registrar o pedido, não consulta novamente o preço do pedido, vai verificar disponibilidade de estoque e vetar ou não a venda, mas o preço é o que veio do carrinho"*

e, na sequência:

> *"a verificação se tem em estoque ou não seria assíncrona, hoje nos marketplaces você envia e eles validam posteriormente, pagamento, estoque, etc"*

**A IA havia proposto:** resolver o acoplamento com o Catálogo por cache com invalidação, mantendo a leitura de preço no caminho de criação.

**O que mudou:** os dois prompts, em sequência, produziram a `ADR-0007`. O preço passou a ser **carregado** pela criação em vez de relido, e a validação foi deslocada para depois do aceite. O aceite virou operação puramente local.

**O que a IA acrescentou:** a quantificação de por que o cache não bastava — hit rate de 90% por SKU vira 43% por pedido de 8 itens (0,9⁸), e como `CTX-04` cobra p95, que é governado pelos misses, o cache melhora a média e quase não move a métrica do SLA.

**E o que a IA encontrou depois:** a decisão produz **quebra semântica sob schema compatível**. O `201` deixa de significar "venda confirmada". O JSON é idêntico, o contract test passa, e o consumidor quebra em produção. Isso gerou a `ADR-0004`.

---

## P5 · O recorte de escopo

> *"aqui vamos trabalhar apenas com catálogo e pedidos, nada de falar de estoque, pagamento, carrinho"*

**A IA havia proposto:** Estoque, Pagamento e Carrinho como bounded contexts — escopo que o enunciado nunca nomeia, e que a própria IA havia registrado como `PR-07` e `PR-08`, as premissas mais perigosas da proposta.

**O que mudou:** os contextos saíram dos 27 arquivos afetados. A `ADR-0007` foi **reancorada no Catálogo** — o argumento dela nunca dependeu do Estoque, e sim de haver dependência síncrona. A decisão sobreviveu à remoção da premissa que a originou.

**Rejeitado pela IA, e registrado:** a proposta de alterar só o mapa de domínios, deixando arquitetura, ADRs e código citando Estoque. Criaria inconsistência visível entre artefatos — exatamente o que `AV-01` avalia.

---

## P6 · Auditar as lacunas contra o que já existe

> *"não tem como ir revisando tudo e ver se já não respondemos isso em outra parte do projeto, com os testes, algo do tipo?"*

**O que mudou:** uma auditoria cruzada dos 84 `???` contra código, testes e outros documentos. Encontrou quatro inconsistências reais:

1. `PR-01`, `PR-02` e `PR-03` marcados `???` em dois arquivos **depois de já terem sido decididos** em `constraints.md`
2. Colisão de IDs — `PR-07` significava coisas diferentes em dois documentos
3. Um `???` **órfão**: a `ADR-0003` ainda perguntava o limite tolerável do fallback, mas o fallback fora superseded. A pergunta sobreviveu à resposta
4. TTL de idempotência e validade da cotação decididos no código, abertos na documentação

Resultado: 84 → 47 `???`, todos os restantes sendo baseline de produção.

---

## P7 · Estimar na ordem certa

> *"já fizemos a separação das tasks pra execução? como vamos estimar tempo e equipe sem o que precisamos fazer pra resolver o problema?"*

**A IA havia proposto:** declarar uma composição de time e estimar em cima dela.

**O que mudou:** a ordem foi invertida — decompor em 47 tarefas, somar esforço por perfil, e **derivar** o time do resultado. Isso revelou que SRE consome 26% do esforço, mais que o dobro do arquiteto, como consequência direta da exigência de zero janela de indisponibilidade.

Uma proposta dimensionada com "4 devs e apoio de infra" erraria exatamente na parte que sustenta o critério mais duro do gate.

---

## Cuidados com dados, em todos os prompts

- Nenhum dado real foi usado. Volumetria e perfil de pedido são premissas declaradas.
- Nenhuma credencial, endpoint interno ou identificador de cliente real entrou em prompt.
- O enunciado do desafio não é versionado neste repositório.
- Dados da fatia executável são sintéticos, sem PII.
