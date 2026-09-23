# Uso de IA na elaboração do desafio

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** registro incremental de como a IA foi usada para produzir este repositório — ferramenta, prompts, validações, rejeições e cuidados com dados. Atende `D-02` / `E-05`.
**Fontes:** sessões de trabalho registradas abaixo; íntegra dos prompts em `docs/ai-context/prompts/`
**Data:** 2026-09-22 (documento vivo — alimentado a cada comando executado)

---

## Ferramenta escolhida

**Claude (Opus) via Claude Code**, operando diretamente sobre o repositório.

**Por que esta e não um chat genérico:** três razões, nesta ordem de peso.

1. **Lê e escreve o repositório.** Os artefatos deste desafio são interdependentes — um ADR cita uma constraint, um diagrama cita um ADR. Uma ferramenta que só conversa obriga a recolar contexto a cada passo e perde a rastreabilidade que `docs/CONVENCOES.md` exige.
2. **Comandos versionados como parte do repositório.** O padrão de `.claude/commands/` transforma o processo em artefato revisável: qualquer pessoa reproduz a mesma entrevista e obtém um documento no mesmo formato. Isso é governança de arquitetura aplicada à própria elaboração.
3. **O trabalho fica auditável.** Prompt, saída e arquivo gerado vivem no mesmo lugar, o que torna este registro verificável em vez de declaratório.

**Limitação assumida:** a ferramenta não tem acesso a dados de produção da plataforma fictícia, então todo baseline permanece `???`. Ver regra Q7 em `docs/CONVENCOES.md`.

---

## Cuidados com dados

- **Nenhum dado real foi usado.** A plataforma de Pedidos e Catálogo é o cenário fictício do enunciado; volumetria e perfil de pedido são premissas declaradas (`PR-01` a `PR-03`), marcadas como premissa e nunca apresentadas como fato.
- **Dados sintéticos na fatia executável.** `slice/seed/` usará dados gerados, sem PII real — exigência de `P2-10` e coerente com `CTX-09`.
- **O enunciado do desafio não é versionado neste repositório.** Ele permanece apenas como referência local, e uma varredura confirma sua ausência antes de cada publicação.
- Nenhuma credencial, endpoint interno ou identificador de cliente real entrou em prompt.

---

## Registro de sessões

### 2026-09-22 · Leitura do desafio e roteiro de execução

- **Prompt:** "ler o arquivo context.md e criar um roteiro de execução para atendermos ao que é pedido".
- **Saída aceita:** inventário rastreável de requisitos (`CTX`, `P1`, `P2`, `D`, `E`, `AV`) extraído do PDF, e roteiro em 8 frentes com gates e dependências.
- **Validação:** cada ID conferido linha a linha contra o PDF; a matriz existe justamente para que nenhum requisito dependa de memória da IA.
- **Rejeitado:** a IA propôs decidir a stack da fatia executável logo no início, oferecendo quatro opções. **Motivo da rejeição:** decisão de tecnologia antes do levantamento de requisitos inverte a ordem correta — a stack é consequência das restrições, não premissa. A escolha foi congelada até o gate G2, e o `/stack` foi reposicionado para depois das ADRs de arquitetura.
- **Dados expostos:** nenhum.

### 2026-09-22 · Adoção do padrão de especificação

- **Prompt:** definir um padrão de especificação único para todos os artefatos, antes de produzi-los.
- **Saída aceita:** estrutura `.claude/commands/` + `docs/` por contexto; cabeçalho canônico com campo **Fontes**; regras de qualidade Q1–Q11 formalizadas em `docs/CONVENCOES.md`.
- **Validação:** o padrão foi validado aplicando-o aos artefatos existentes antes de generalizá-lo, e depois transformado em fitness function (`test_documento_declara_escopo_fontes_e_data`), que encontrou 7 violações reais.
- **Rejeitado:** a IA propôs adotar configuração de hooks dependente de binário de outro sistema operacional. **Motivo:** copiaria configuração que não funcionaria neste ambiente. Descartada.
- **Dados expostos:** nenhum.

### 2026-09-22 · `/prd` — PRD da plataforma de Pedidos e Catálogo

- **Prompt:** "vamos começar pela parte de produtos, especificar as necessidades". Entrevista guiada conforme `.claude/commands/prd.md`.
- **Saída aceita:** `docs/prd/pedidos-catalogo.md` — tese, hipótese composta, escopo IN/OUT, critério de pronto por onda, métrica-alvo com kill criteria.
- **Validação:** cada item do escopo amarrado a um `CTX-*`; baselines mantidos como `???` por ausência de dado de produção (regra Q7).
- **Rejeitado — duas vezes, ambas por leitura do PDF:**
  1. A IA propôs estreitar a hipótese a **uma aposta central** entre três (integridade, latência ou compatibilidade). **Motivo da rejeição:** o §2.1 pede explicitamente equilíbrio entre escala, disponibilidade, segurança, custo e prazo. Reduzir a uma aposta otimizaria um eixo contra os outros e contrariaria o objetivo geral. Substituído por hipótese composta de cinco pernas verificáveis separadamente.
  2. A IA ofereceu três definições de "pronto" sem considerar que §2.5.3 e §4 já resolvem a questão. **Motivo:** o PDF separa **plano** (30/60/90, §4) de **compromisso estimado** (só a fase 1, §2.5.3). O critério de pronto passou a ser por onda com gate, e a onda 1 é a única precificada — distinção que as opções originais não continham.
- **Padrão observado:** a IA tendeu a oferecer menus de opções onde o enunciado já continha a resposta. A validação eficaz foi reler o PDF em vez de escolher entre alternativas plausíveis.
- **Dados expostos:** nenhum.

### 2026-09-22 · `/persona` — personas da plataforma

- **Prompt:** "sim" (seguir para `/persona` conforme a pendência do PRD). Entrevista guiada conforme `.claude/commands/persona.md`.
- **Saída aceita:** `docs/business-context/personas.md` — uma persona primária derivada, três secundárias, e uma tabela de método de derivação evidência a evidência.
- **Validação:** cada persona amarrada a uma frase literal de §2.2.1. Cinco das oito evidências convergem para a mesma pessoa, e essa convergência é o argumento — não a plausibilidade da descrição.
- **Rejeitado:** a IA ofereceu quatro candidatas a persona primária como se a escolha fosse preferência. **Motivo da rejeição:** não há base para escolher; o correto é **derivar** das restrições de §2.2.1 e marcar como presunção. A resposta foi "não sabemos, vamos precisar presumir junto aos requisitos que temos na 2.2.1" — o que mudou o método de seleção para dedução, e obrigou a registrar explicitamente o que **não** é derivável.
- **Correção gerada:** a derivação contradisse o PRD, que havia presumido "operação de pedidos" como primária. O PRD foi corrigido em vez de a persona ser ajustada para caber nele.
- **Dados expostos:** nenhum.

### 2026-09-22 · `/jornada` — jornada do problema

- **Prompt:** "sim" (seguir para `/jornada`). Fluxo conforme `.claude/commands/jornada.md`.
- **Saída aceita:** `docs/business-context/jornada.md` — ANTES/DURANTE/DEPOIS, tabela-resumo de fricção e a seção "o que medir para fechar os `???`".
- **Validação:** nenhum número inventado; todas as células de tempo permanecem `???`. O que substituiu o número foi a **forma da curva** de cada dor (por item, por retry, por promoção, por parceiro), que é derivável de §2.2.1 sem baseline.
- **Rejeitado:** a IA começou a preencher "tempo gasto" com valores plausíveis (ex: "~2h/semana de conciliação"). **Motivo:** viola a regra Q7 e contaminaria `/metricas` e `/estimativa`, que consomem esta jornada. Substituído por `???` mais uma tabela do que precisa ser medido e o que cada medida bloqueia.
- **Achado próprio da análise, não do enunciado:** separar as seis dores entre **irreversíveis** (duplicidade, perda de evento, ausência de snapshot) e **reversíveis** (N+1, canal bloqueado, evolução travada) produz o argumento de ordenação das ondas. Não estava no PDF; emergiu de classificar as dores por natureza do dano em vez de por severidade percebida.
- **Dados expostos:** nenhum.

### 2026-09-22 · `/constraints` — restrições e dimensionamento

- **Prompt:** "segue" (F0.4 + F0.5). Fluxo conforme `.claude/commands/constraints.md`.
- **Saída aceita:** `docs/technical-context/constraints.md` — cinco dimensões com número verificável, dimensionamento derivado e orçamento de latência por hop.
- **Validação:** todas as contas refeitas à mão a partir de `PR-01` e das premissas de distribuição declaradas. Os números do enunciado (10×, 99,9%, 500 ms) foram tratados como limites, não como resultado.
- **Rejeitado:** a IA propôs declarar volumetria de 20k/dia → 200k/dia, valor que havia sugerido antes sem análise. **Motivo:** nessa faixa o pico é de ~12 pedidos/s, que uma instância bem escrita atende — e uma arquitetura com broker, read model e multi-região pareceria justificada por futuro imaginado, não por restrição presente. Risco direto em `AV-08`. Substituído por 60k → 600k/dia, faixa em que os trade-offs são reais.
- **Achado próprio da análise:** a **indisponibilidade composta** (`CTX-17`). Com Pedidos e Catálogo a 99,9% cada e dependência síncrona no caminho crítico, a disponibilidade percebida é 99,8% — 86 min/mês contra um error budget de 43 min. `CTX-03` fica matematicamente inatingível, independentemente da qualidade do código. Não está no enunciado; emergiu de multiplicar duas restrições que o PDF apresenta separadamente.
- **Efeito na proposta:** esse cálculo transforma o argumento da ADR-0003 de "desacoplar é boa prática" em "com a dependência síncrona o SLA não fecha na aritmética" — e mostra que snapshot resolve `CTX-03`, `CTX-04`, `CTX-05` e `CTX-06` simultaneamente.
- **Dados expostos:** nenhum.

### 2026-09-22 · `/adr` — ADR-0003, snapshot e desacoplamento do Catálogo

- **Prompt:** diálogo sobre o que é N+1 e o que é snapshot, culminando na proposta do usuário: *"então dá pra fazer o snapshot de coisas que sempre vão mudar na negociação, e o cache pro catálogo no serviço de pedidos, pra reduzir a dependência, certo?"*
- **Saída aceita:** `ADR-0003` — decisão em duas partes (registro e caminho de leitura), seis alternativas confrontadas, enforcement executável.
- **Validação:** cada alternativa rejeitada recebeu o motivo quantitativo, não retórico. A conta de hit rate composto (0,9⁸) foi refeita à mão.
- **Correção gerada pela conversa:** a proposta do usuário estava certa na direção, mas tratava snapshot e cache como partes de uma mesma solução de acoplamento. São coisas distintas — **cache é otimização** (some, você busca de novo, mesmo resultado); **snapshot é registro** (some, a informação se perde, porque a fonte mudou). O snapshot não elimina a leitura da criação, elimina todas as futuras. Essa distinção virou o eixo da ADR.
- **Achado próprio da análise:** hit rate por SKU **não se traduz** em hit rate por pedido, porque o pedido precisa de todos os itens. Com 90% por SKU, só 43% dos pedidos de 8 itens ficam totalmente em cache (0,9⁸), e 21% nos de 15 itens. Como `CTX-04` cobra o **p95**, e o p95 é governado pelos misses, cache melhora a média e quase não move a métrica do SLA. Isso derrubou "apenas cache" como alternativa.
- **Rejeitado:** a IA propôs adotar read model por evento já na onda 30, por ser a solução tecnicamente superior. **Motivo:** não cabe em 30 dias sem janela (`CTX-11`) — exige contrato de evento do Catálogo, carga inicial e política de reconciliação. Registrado na ADR como "rejeitada **por prazo, não por mérito**", com reavaliação na onda 60. A distinção importa: esconder que a opção melhor existe enfraquece a ADR.
- **Desvio de processo registrado:** a ADR foi escrita na F0, fora da sequência do roteiro (ADRs são F2). Motivo: o argumento quantitativo do `CTX-17` foi derivado em `/constraints` e a decisão é consequência direta dele. A numeração seguiu o mapa de temas do roteiro, não a ordem de criação, para não quebrar referências já publicadas.
- **Dados expostos:** nenhum.

### 2026-09-22 · ADR-0007 e ADR-0004 — aceitação assíncrona e compatibilidade semântica

- **Prompt:** sequência de refinamentos do usuário sobre o desenho: cache compartilhado com invalidação por CDC; preço vindo do carrinho e não relido na criação; verificação de estoque assíncrona, "como os marketplaces fazem".
- **Saída aceita:** `ADR-0007` (aceitação assíncrona), `ADR-0004` (versionamento e compatibilidade semântica), e revisão da `ADR-0003`.
- **O desenho veio do usuário, não da IA.** As três propostas foram dele; o papel da IA foi quantificar consequências e apontar o que cada uma deslocava em vez de resolver.
- **Rejeitado — proposta do usuário refinada, não aceita como estava:** cache compartilhado entre vitrine e Pedidos, com invalidação por CDC, "para garantir que não tenhamos preço divergente do escolhido pelo cliente". **Motivo:** resolve a divergência de infraestrutura (dois caches dessincronizados), mas não a temporal — entre o que o cliente viu em T0 e o que Pedidos leria em T1. E há um paradoxo: **invalidação mais rápida piora a fidelidade à oferta**, porque destrói o preço ofertado mais cedo. Frescor e estabilidade de oferta são requisitos opostos. A conversa levou à oferta no carrinho, que elimina a leitura em vez de otimizá-la.
- **Rejeitado — segundo ponto:** CDC lendo tabelas do Catálogo para invalidar cache de outro serviço cria acoplamento de **schema interno**, pior que acoplamento de API: o Catálogo refatora uma coluna e a invalidação quebra em silêncio. Deve passar por evento de domínio publicado pelo Catálogo.
- **Rejeitado — terceiro ponto, contra o próprio usuário:** a proposta de manter unidade de medida e peso fora do snapshot, servidos por cache. **Motivo:** "quantidade 2" não significa nada sem "kg" ou "un", e o peso é base do frete cobrado. Ambos são base de compromisso com o cliente. A tabela original da ADR-0003 estava incompleta por ter tratado só os casos óbvios.
- **Achado próprio da análise — o mais consequente:** a ADR-0007 produz **quebra semântica sob schema compatível**. O `201` deixa de significar "venda confirmada" e passa a significar "pedido recebido". O JSON é idêntico, o contract test de `P2-11` passa, e todo consumidor que trata `201` como venda feita quebra em produção. Isso violaria `CTX-10` e `CTX-12` sem nenhum alarme. Gerou a ADR-0004, com a fachada síncrona v1 e a lista fechada de quebras semânticas.
- **Correção de rota registrada na própria ADR-0003:** a seção (b) foi marcada superseded **com o texto original preservado e tachado**, em vez de reescrita. Motivo: `AV-03` avalia alternativas e consequências reais; ADR reescrita para parecer certa desde o início esconde o raciocínio que produziu a mudança de posição.
- **Dados expostos:** nenhum.

### 2026-09-22 · `/arquitetura` — mapa de domínios, arquitetura e glossário

- **Prompt:** "sim" (consolidar o desenho após as ADRs 0003, 0004 e 0007). Fluxo conforme `.claude/commands/arquitetura.md`.
- **Saída aceita:** `docs/business-context/mapa-dominios.md`, `docs/technical-context/architecture.md`, `docs/business-context/glossario.md`.
- **Validação:** cada componente amarrado a um `CTX` ou ADR que o justifique. A seção "O que **não** está nesta arquitetura" foi escrita com gatilho de retorno por item, para que a ausência seja decisão e não esquecimento.
- **Rejeitado:** a IA propôs BFF separado para web e para app móvel, e relay do outbox como serviço com deploy próprio. **Motivo:** nenhuma restrição atual justifica nenhum dos dois; `CTX-01` pede que a plataforma **atenda** os dois canais, não que tenha um BFF para cada. Ambos foram reduzidos ao mínimo, com gatilho de divisão registrado. Regra Q11 aplicada diretamente.
- **Achado próprio da análise:** a tabela de pontos de falha mostrou que, dos sete componentes, **apenas um** (o store de Pedidos) derruba a criação. Broker, relay, Catálogo, Estoque, Pagamento e o gateway de parceiros degradam sem interromper o aceite. Essa é a propriedade que o desenho compra em troca da complexidade assíncrona — e vale mais como argumento do que a descrição dos componentes.
- **Achado secundário:** o glossário revelou três termos que vinham sendo usados de forma ambígua nos próprios artefatos — "criação" (aceite ou confirmação?), "preço" (acordado ou vigente?) e "disponibilidade" (SLA ou saldo?). Viraram seção de termos proibidos sem qualificação.
- **Dados expostos:** nenhum.

### 2026-09-22 · ADR-0001 e ADR-0002 — idempotência e outbox

- **Prompt:** "pode escrever", após conversa sobre o que é o relay do outbox.
- **Saída aceita:** `ADR-0001` (idempotência) e `ADR-0002` (outbox). Escritas juntas por compartilharem a transação de criação.
- **Validação:** a fronteira comum entre as duas foi declarada explicitamente em ambas — violação da `UNIQUE` de idempotência reverte a transação inteira, inclusive o outbox, e nunca deixa evento órfão.
- **Rejeitado:** a IA propôs lock distribuído em Redis para resolver a concorrência de chaves de idempotência. **Motivo:** adicionaria dependência externa síncrona no caminho crítico — exatamente o que a `ADR-0007` eliminou. A `UNIQUE (chamador, chave)` do banco resolve de forma determinística e sem componente novo.
- **Rejeitado — segundo ponto:** replay literal da resposta gravada, convenção de mercado (Stripe e similares). **Motivo:** com aceite assíncrono, a resposta original foi `RECEBIDO` e o pedido pode já estar `CONFIRMADO`. Devolver o texto gravado mentiria sobre o estado. Optou-se por devolver o estado corrente, com o desvio da convenção declarado na ADR.
- **Achado próprio da análise:** tornar `Idempotency-Key` obrigatória é **breaking change** pela lista fechada da `ADR-0004` ("tornar obrigatório um campo que era opcional na requisição"). A primeira versão do texto a definia como obrigatória sem notar a contradição com a ADR escrita horas antes. Corrigido para opcional em v1 e obrigatória em v2.
- **Achado secundário:** o outbox mudou de natureza com a `ADR-0007`. Antes era correção de dívida técnica; agora é mecanismo de continuidade do processo — se `PedidoRecebido` não sair, o pedido nunca valida, nunca confirma e nunca chega ao cliente. Evento perdido deixou de ser aviso perdido e virou venda parada. Isso elevou o peso da ADR e justificou o SLI de falha silenciosa.
- **Dados expostos:** nenhum.

---

### 2026-09-23 · Recorte de escopo — Pedidos e Catálogo apenas

- **Prompt:** *"vamos trabalhar apenas com catálogo e pedidos, nada de falar de estoque, pagamento, carrinho"*.
- **O corte veio do usuário e estava certo.** A IA havia introduzido Estoque, Pagamento e Carrinho como bounded contexts. O enunciado descreve uma *"plataforma de Pedidos e Catálogo"* e nunca os menciona — eram escopo inventado, registrados como `PR-07` e `PR-08`, a premissa mais perigosa da proposta.
- **Rejeitado:** a IA propôs, como alternativa barata, alterar só o mapa de domínios e deixar arquitetura, ADRs e código citando Estoque e Pagamento. **Motivo:** criaria inconsistência visível entre artefatos — exatamente o que `AV-01` avalia. O recorte foi aplicado aos 27 arquivos afetados.
- **Consequência de projeto:** a `ADR-0007` precisou ser reancorada. O argumento central dela — dependência síncrona no caminho crítico torna `CTX-03` inatingível — **não dependia do Estoque**. Depende de haver dependência síncrona, e o Catálogo cumpre o papel: conferir os termos submetidos contra o Catálogo de forma síncrona reintroduz a mesma aritmética. A decisão sobreviveu à remoção da premissa que a originou.
- **Ganho:** `PR-07` deixou de ser risco administrado e passou a **não existir**. O risco foi eliminado, não mitigado.
- **Validação:** 127 testes passando, incluindo três novos que provam a assimetria entre canais — cotação assinada é honrada mesmo com o Catálogo mudando; parceiro sem cotação com preço divergente é rejeitado **após** o aceite.
- **Achado próprio, durante a validação:** o validador de Mermaid **deixou de encontrar metade dos diagramas e continuou verde**. Os scripts de varredura regravaram arquivos com CRLF, e a regex procurava `
`. Uma fitness function que silenciosamente para de verificar é pior que nenhuma — foi adicionada uma guarda de contagem mínima que quebra o build se a varredura encolher.
- **Dados expostos:** nenhum.

---

### 2026-09-23 · Revisão de leitura — README, resumo executivo e apresentação

- **Prompt:** *"siga com a revisão de leitura"* — ler os três documentos de entrada com olho de avaliador, conferindo cada número contra a fonte.
- **Achados corrigidos:**
  - A apresentação mostrava `128 passed`, saída que o pytest nunca imprime: o real é `127 passed, 1 skipped`. A causa era o próprio `conferir-entrega.py`, que exigia `N passed` igual ao total coletado e **empurrava o documento para o número errado**. A verificação passou a somar os pulados, validada por mutação.
  - Arquiteto a **30%** no time, mas 9,5 d.p. em 20 dias úteis é ~50%, e só com 50% a alocação média dá os 72% que sustentam o prazo. Corrigido na estimativa, no resumo e nos slides; esforço e preço não mudam.
  - `V11` descrito como *"~80 a 90% da conta de infraestrutura"*. A conta é outra: o Catálogo é ~45% do total, ou **+79 a 92%** sobre o escopo só de Pedidos. Reescrito como *"quase dobra a conta"*.
  - O resumo chamava três premissas de *"inventadas"*; a fonte classifica só `PR-06` assim.
  - O resumo falava em *"seis problemas"* logo depois de o README e o slide 1 apresentarem *"quatro débitos"*, sem ponte entre os dois números.
- **Rejeitado:** reescrever a prosa dos três documentos para uniformizar o estilo. **Motivo:** o risco era de inconsistência, não de estilo; reescrever a prosa abriria superfície nova de erro na véspera da entrega.
- **Dados expostos:** nenhum.

---

### 2026-09-23 · Time com um SRE — o cenário com IA passa a ser a proposta

- **Prompt:** *"pode fechar em 1 SRE, organize o prazo pra que dê certo, com uso de IA"*.
- **A decisão veio do usuário**, a partir de uma pergunta sobre o "1,5 SRE" do resumo.
- **Achado próprio, antes de mexer:** o cenário com IA prometia **16 dias úteis com 4,5 pessoas**. A conta só fecha com 5,5 — com 4,5, dá ~19,5. E a estimativa afirmava que o cenário pessimista, de 28 dias úteis, *"cabe em 30 corridos"*, que têm 21.
- **Derivação:** 1 SRE só fecha com IA. Sem ela, 20,5 d.p. levam 29 dias úteis. Com ela, o SRE cai só para 18,5 — rollout não acelera. O que fecha a conta é a folga que a IA abre nos devs: `P1.3`, `A3.3`, `P1.4` e `A11.1`, métricas emitidas pela aplicação, passam a quem escreve o código. O SRE fica com 14 d.p., exatos 20 dias úteis.
- **Rejeitado:** usar o ganho da IA para encurtar o prazo mantendo 1,5 SRE (~17,5 dias úteis). **Motivo:** o gate G30 espera inventário e adequação de consumidores; entregar código três dias antes não o antecipa. Uma pessoa a menos é ganho que se realiza.
- **Rejeitado:** subir a alocação do SRE de 70% para 80% para caber sem redistribuir. **Motivo:** mudaria uma premissa para fazer a conta fechar — o mesmo tipo de invenção que a regra Q7 proíbe.
- **Consequência:** o meio SRE deixou de ser custo fixo e virou gatilho, acionado na recalibração da semana 2 e pago pela contingência. Preço com contingência: R$ 172.306 → R$ 141.880.
- **Dados expostos:** nenhum.

---

### 2026-09-23 · Catálogo no diagrama de implantação — mesma VPC, banco próprio

- **Prompt:** *"o catálogo e o pedidos não podem estar na mesma região, mesmo RDS, mesma VPC? No desenho da AWS ele está como opcional, não entendi"*.
- **A pergunta do usuário expôs uma lacuna real.** O diagrama desenhava o Catálogo solto, fora da VPC, porque `V11` estava em aberto — mas a proposta já assume o escopo B. E nenhum documento justificava o RDS separado: a decisão estava certa e sem argumento escrito.
- **Resposta:** região, VPC e subredes são as mesmas; o banco não. O motivo decisivo é específico do desenho: o banco de Pedidos é o único componente que derruba o aceite, e dividir a instância devolveria ao aceite, pela infraestrutura, a dependência do Catálogo que a `ADR-0007` tirou do código.
- **Rejeitado:** justificar o banco separado apenas por *database per service*. **Motivo:** é regra genérica, que um avaliador reconhece como citação; o argumento que se sustenta é o do `CTX-17` voltando por baixo.
- **Decisão seguinte do usuário:** *"assuma que os dois estão na mesma infra hoje, e continuarão"*. `V11` fechada: conta de infraestrutura única, sem escopo A/B e sem esforço de migração. O RDS próprio do Catálogo foi mantido — "mesma infra" é conta, região e VPC, e o argumento contra dividir a instância não depende de quem hospeda.
- **Achado próprio, ao fechar `V11`:** o resumo e os slides chamavam de `V3` a decisão de baseline, mas em `riscos-premissas.md` `V3` é o segundo país — e o baseline nem constava ali. Virou `V12`, registrada na fonte.
- **Dados expostos:** nenhum.

---

### 2026-09-23 · Narrativa de edição — limpeza e verificação automática

- **Contexto:** a regra *"o entregável descreve o estado final"* já havia sido aplicada, mas a limpeza foi manual e deixou 13 trechos riscados ou com *"fechado em <data>"* em sete documentos.
- **Achado junto:** o PRD listava como pendentes a jornada e a migração dos `CTX` — as duas feitas há dias — e tratava o segundo país como indefinido. `riscos-premissas.md` ainda contava `PR-07`, premissa eliminada, entre as "três premissas inventadas".
- **Correção:** cada trecho reescrito como estado final; itens resolvidos saíram das pendências. Nova seção 9 no `conferir-entrega.py` quebra o build com texto riscado ou marca datada de fechamento, exceto em `ai-context/` e na `ADR-0003`. Validada por mutação.
- **Rejeitado:** proibir só o `~~`. **Motivo:** metade das ocorrências era *"Fechado em 2026-09-24"* sem riscado; a verificação pegaria o sintoma mais visível e deixaria o outro.
- **Dados expostos:** nenhum.

---

## Pendências registradas

- A íntegra dos prompts ainda não foi extraída para `docs/ai-context/prompts/`. Fazer ao final de cada frente, não no fechamento.
- Falta registrar o uso de IA na fatia executável (`slice/`) — geração de código e de dados sintéticos tem critério de validação diferente do usado em documentos: ali a validação é o teste automatizado, não a leitura crítica.
