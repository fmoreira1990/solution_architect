# ADR-0006 — Segregação regional de dados pessoais (Brasil / Estados Unidos)

**Status:** Aceita — 2026-09-23 *(substitui a versão "Proposta" de 2026-09-23, escrita sob premissa de regime LGPD-like)*
**Slug do PRD:** pedidos-catalogo
**Requisitos cobertos:** `CTX-01`, `CTX-09a`, `CTX-09b`, `CTX-09c`, `CTX-09d`, `P2-03`
**Fontes:** `docs/security-context/lgpd-residencia-dados.md`, `docs/security-context/threat-model.md` (F5), `PR-03`
**Validação necessária:** o enquadramento regulatório desta ADR é leitura de arquiteto, **não parecer jurídico**. Precisa de validação pelo DPO antes de virar compromisso.

---

## Contexto

`PR-03` fechou: o segundo país são os **Estados Unidos**.

Isso muda a premissa da versão anterior desta ADR, que assumia regime **LGPD-like** com residência obrigatória. O enunciado fala em *"requisitos de residência de dados do novo país"* (`CTX-09`), e essa formulação não encontra correspondente direto nos EUA.

| | Premissa anterior (LATAM) | Estados Unidos |
|---|---|---|
| Lei nacional abrangente | sim | **não existe** no nível federal |
| Residência obrigatória | presumida | **não há exigência geral** para dado comercial de varejo |
| Regime aplicável | um país, uma lei | **mosaico estadual**: CCPA/CPRA, Virginia, Colorado, Texas, Connecticut e outros |
| Unidade de análise | país | **estado de residência do consumidor** |
| Direito novo | — | **opt-out de venda/compartilhamento** e sinal GPC honrado na Califórnia |
| Fluxo que importa | dado não pode sair | **BR → EUA é transferência internacional sob LGPD** (art. 33) |

**A direção da restrição se inverte.** Não é "o dado americano precisa ficar nos EUA". É "o dado **brasileiro** que for para os EUA vira transferência internacional, e precisa de instrumento jurídico".

---

## Decisão

**Segregação regional de dados pessoais, por domicílio do titular.** Dados transacionais não pessoais permanecem replicáveis entre regiões.

| Categoria | Onde vive |
|---|---|
| Identidade (nome, documento, contato) | **região do domicílio do titular** |
| Vínculo `cliente_id` → pessoa | **região do domicílio do titular** |
| **Preferências de privacidade** (opt-out de venda/compartilhamento, GPC) | região do titular, **propagadas globalmente como sinal** |
| Pedido, itens, snapshot, outbox | região de origem, replicável — não é dado pessoal |
| Catálogo | global |
| Telemetria e métricas | global, **sem identificador** |
| Chaves de criptografia | regionais |
| Backup | segue a região do dado que contém |

**A mesma estrutura de antes; justificativa diferente.** Não é conformidade com mandato de residência — é:

1. **Minimização de transferência internacional.** Quanto menos PII brasileira atravessar, menor o ônus de `CTX-09c`. A segregação transforma um problema contínuo de transferência num problema pontual e controlado.
2. **Latência e disponibilidade** para a operação americana. Motivo de engenharia, não de conformidade.
3. **Mecânica de direitos por jurisdição.** CCPA/CPRA exige atender exclusão, correção e opt-out para residentes de determinados estados. Saber **onde** o titular mora é pré-requisito para saber **qual regra** aplicar — e a segregação torna isso estrutural em vez de uma consulta a mais.

### O que muda na arquitetura, além do que já existia

**Serviço de preferências de privacidade** — `CTX-09d`. O opt-out de venda/compartilhamento não tem equivalente direto na LGPD e é **um requisito novo**: a preferência precisa ser consultável e honrada por **todo** consumidor de dado, inclusive parceiros de marketplace. Isso não é tela de configuração; é sinal que atravessa a cadeia.

**Roteamento por domicílio, não por geografia da requisição.** Um brasileiro comprando durante uma viagem aos EUA continua sendo dado brasileiro. Errar isso não gera erro — gera não conformidade silenciosa.

**Multi-moeda (USD)** entra no escopo. O snapshot já carrega `moeda` por item (`ADR-0003`), então o modelo suporta; o que falta é conversão, arredondamento e a regra de qual moeda vale na disputa.

**Tributação americana fica fora** — escopo OUT nº 3 do PRD. Vale registrar que o *sales tax* americano é por estado e município, e é um projeto próprio, não um campo a mais.

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **PII regional por domicílio + transacional replicável** | ✅ **Escolhida** | Minimiza transferência internacional, atende a mecânica de direitos por jurisdição e serve à latência. Custo concentrado na identidade, que é o menor volume |
| **Base global única, sem segregação** | ❌ Rejeitada | Tecnicamente **viável** nos EUA, já que não há mandato de residência — e é justamente por isso que merece ser confrontada. Rejeitada porque tornaria toda operação sobre PII brasileira uma transferência internacional contínua, ampliando a superfície de `CTX-09c` sem ganho arquitetural |
| **Silo regional completo** — stack inteira duplicada | ❌ Rejeitada | Sem mandato de residência, duplicar operação e deploy para dois países é custo sem contrapartida regulatória. Desproporcional (`AV-08`) |
| **Segregação por país da operação**, não por domicílio do titular | ❌ Rejeitada | Quebra no caso do brasileiro comprando dos EUA. Domicílio é o que define a lei aplicável |
| **Tokenização de PII em base global** | ❌ Rejeitada | Vários regimes consideram o token dado pessoal enquanto existir chave de reversão. Assume risco jurídico para economizar infraestrutura |

**A segunda linha é a mais importante desta tabela.** Com os EUA, "base global única" deixa de ser proibida e passa a ser legítima — o que obriga a decisão a se defender por mérito, não por imposição.

---

## Justificativa

A decisão é a mesma da versão anterior; o argumento, não. Antes era *"a lei obriga"*. Agora é *"a lei não obriga, e mesmo assim compensa"* — porque reduz transferência internacional, simplifica a mecânica de direitos e serve à latência.

Uma decisão que sobrevive à remoção da obrigação legal é mais sólida do que uma que dependia dela.

---

## Trade-offs aceitos

- **Consulta cross-região fica mais cara.** Visão consolidada com nome de cliente da outra região exige chamada. Aceito: é exceção, não caminho crítico.
- **Duas infraestruturas de identidade** para operar e auditar.
- **Roteamento por domicílio é sutil e fácil de errar.** Exige teste específico, porque a falha é silenciosa.
- **Preferências de privacidade viram dependência nova** no fluxo de uso de dado. Se o serviço cair, o padrão seguro é o **mais restritivo** — tratar como opt-out.
- **O mosaico estadual muda com o tempo.** Novos estados aprovam leis a cada ano. A arquitetura precisa suportar regra por jurisdição, não regra fixa por país.
- **Chaves regionais complicam recuperação de desastre.** Não existe chave única que destrave tudo — e essa é a intenção.

---

## Gatilho de revisão

**Se surgir lei federal americana abrangente de privacidade.** Unificaria o mosaico e provavelmente mudaria a granularidade de estado para país.

**Se algum estado adotar exigência de localização.** Hoje não existe para varejo; se passar a existir, a decisão migra para silo completo naquela jurisdição.

**Quando um terceiro país entrar.** Duas regiões funcionam com este padrão. A partir da terceira, o custo de identidade por região cresce e vale reavaliar federação.

**Se o endereço de entrega ficar em Pedidos** (`V8`). Isso torna Pedidos um armazém de PII e derruba a premissa de que ele é replicável.

---

## Enforcement

Nenhum existe hoje. Especificados para a onda 90:

1. **Teste de ausência de PII no schema de Pedidos.** Coluna com nome de campo pessoal falha o build. Extensão direta de `test_evento_nao_carrega_pii`, que já cobre o evento.
2. **Teste de roteamento por domicílio**, não por origem da requisição — com caso explícito do brasileiro comprando dos EUA.
3. **Teste de preferência restritiva por padrão**: serviço de preferências indisponível ⇒ tratar como opt-out.
4. **Verificação de telemetria sem identificador**, por amostragem.
5. **Checklist de revisão** para todo campo novo em Pedidos: é dado pessoal? Por que está aqui?

---

## Riscos abertos

1. **Este enquadramento é leitura de arquiteto, não parecer jurídico.** A afirmação central — que os EUA não impõem residência para dado comercial de varejo — precisa de confirmação do DPO. Se estiver errada, a decisão não muda, mas a justificativa sim.
2. **O instrumento de transferência BR → EUA (`V9`) não existe.** Sem ele, nenhuma PII brasileira deveria atravessar. É pré-requisito da onda 90, não detalhe jurídico posterior.
3. **Não sabemos em quais estados a operação estará sujeita** (`V10`). Os limiares de aplicabilidade da CCPA/CPRA dependem de receita e volume de consumidores.
4. **O serviço de preferências é escopo novo**, não estimado, e não estava no plano 30/60/90 original.

## Pendências registradas

- `V9` e `V10` são novas decisões para o cliente, registradas em `riscos-premissas.md`.
- O serviço de preferências precisa entrar no plano da onda 90.
- Escolha das regiões AWS (Brasil e EUA) não foi feita — é decisão de infraestrutura, não de arquitetura.
- `V8` (dono do endereço de entrega) continua aberto e continua sendo a premissa mais frágil.
