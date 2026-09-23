# ADR-0006 — Residência de dados e operação multi-região

**Status:** **Proposta** — 2026-09-23 · aguarda `PR-03` (qual é o segundo país) para ser aceita
**Slug do PRD:** pedidos-catalogo
**Requisitos cobertos:** `CTX-01`, `CTX-09`, `P2-03`
**Fontes:** `docs/security-context/lgpd-residencia-dados.md`, `docs/security-context/threat-model.md` (F5), `docs/technical-context/constraints.md`

---

## Por que esta ADR não está "Aceita"

O regime de residência depende do país, e `PR-03` é `???`. Decidir o padrão em abstrato e carimbar como aceito seria fingir uma certeza que não existe — o que a regra Q7 de `docs/CONVENCOES.md` proíbe.

O que **é** possível decidir agora: o padrão de segregação, sob a premissa declarada de que o segundo país tem regime **LGPD-like** (exige que dados pessoais de residentes permaneçam no país, com transferência internacional condicionada). Se `PR-03` trouxer um regime diferente — mais permissivo, ou com exigências de soberania mais duras —, esta ADR muda antes de valer.

Registrá-la como proposta serve a dois propósitos: dizer o que fazer assim que `PR-03` fechar, e impedir que decisões da onda 30 fechem portas que a onda 90 vai precisar.

---

## Contexto

Em 90 dias a plataforma opera em um segundo país (`CTX-01`), e dados pessoais devem atender residência (`CTX-09`).

A fronteira **F5** do threat model está inteiramente bloqueada por isso: três ameaças — PII replicada entre regiões, backup cruzando fronteira, telemetria exportando identificadores — não têm mitigação definida.

O custo de errar é assimétrico. **Relaxar depois é barato; apertar depois exige migrar dado pessoal em produção**, com janela, risco e exposição regulatória.

---

## Decisão proposta

**Silo regional para dados pessoais; dados transacionais não pessoais podem ser globais.**

| Categoria | Onde vive |
|---|---|
| Identidade (nome, documento, contato, endereço) | **apenas na região do titular** |
| Vínculo `cliente_id` → pessoa | **apenas na região do titular** |
| Pedido, itens, snapshot, outbox | região de origem, **replicável** — não é dado pessoal |
| Catálogo | global |
| Telemetria e métricas | global, **sem identificador** |
| Chaves de criptografia | **regionais**, gerenciadas por região |
| Backup | segue a região do dado que contém |

O `cliente_id` pseudônimo **atravessa** a fronteira; o que ele significa, não. Uma consulta que precise do nome do cliente do país B é resolvida **na região B** — o dado não viaja, a pergunta viaja.

### O que isso exige do desenho

1. **Pedidos não pode conter PII direta.** Já é a decisão de `lgpd-residencia-dados.md` §1, e esta ADR a transforma de higiene em requisito de conformidade.
2. **O endereço de entrega precisa de dono.** É o único dado pessoal com risco real de cair em Pedidos. Decisão `V8`, ainda aberta.
3. **Roteamento por região na borda**, pelo domicílio do titular — não pela geografia de quem faz a requisição.
4. **Observabilidade sem PII**, senão a telemetria vira o caminho de vazamento (ameaça F5.3).

---

## Alternativas consideradas

| Alternativa | Status | Por quê |
|---|---|---|
| **PII regional + transacional replicável** | ✅ **Proposta** | Atende residência mantendo uma plataforma só. Custo concentrado na identidade, que é o menor volume |
| **Silo regional completo** — toda a stack duplicada por país | ❌ Rejeitada | Conformidade mais simples de argumentar, mas duplica operação, deploy e custo, e impede visão consolidada de pedidos. Desproporcional para dois países |
| **Base global com tokenização de PII** | ❌ Rejeitada | Elegante tecnicamente, mas vários regimes consideram o token dado pessoal enquanto existir chave de reversão. Assume risco jurídico para economizar infraestrutura |
| **Base global sem segregação** | ❌ Rejeitada — **indisponível** | `CTX-09` a exclui. Não é alternativa preterida |
| Adiar para depois da onda 90 | ❌ Rejeitada | Apertar depois exige migrar PII em produção. A assimetria de custo decide |

---

## Justificativa

A escolha é pelo **ponto de corte mais barato**: separar por natureza do dado, em vez de por sistema. PII é o menor volume e o maior risco; pedidos são o maior volume e o menor risco. Alinhar a fronteira regulatória com essa divisão concentra o custo onde ele é menor.

A alternativa do silo completo seria mais fácil de defender numa auditoria, mas duplicaria a operação inteira para atender dois países — e `AV-08` trata superdimensionamento como defeito.

---

## Trade-offs aceitos

- **Consulta cross-região fica mais cara.** Montar uma visão com nome do cliente de outra região exige chamada à região dele. Aceito: é caso de exceção, não caminho crítico.
- **Duas infraestruturas de identidade.** Mais superfície para operar e auditar.
- **Roteamento por domicílio do titular é sutil.** Um brasileiro comprando do país B continua sendo dado brasileiro. Errar isso é vazamento silencioso — não gera erro, gera não conformidade.
- **Chaves regionais complicam recuperação de desastre.** Não há chave única que destrave tudo, e isso é a intenção.

---

## Gatilho de revisão

**Quando `PR-03` fechar.** Se o regime for mais restritivo — exigindo, por exemplo, que o próprio `cliente_id` não saia do país —, o pedido também vira regional e a decisão muda de categoria.

**Quando um terceiro país entrar.** Duas regiões é gerenciável com este padrão; a partir da terceira, o custo de identidade por região cresce e vale reavaliar o silo completo ou uma abordagem por federação.

**Se o endereço de entrega ficar em Pedidos** (`V8`). Isso torna Pedidos um armazém de PII e derruba a premissa de que ele é replicável.

---

## Enforcement

Nenhum destes existe hoje. Estão especificados para serem implementados junto com a decisão:

1. **Teste de ausência de PII no schema de Pedidos.** Colunas com nome de campo pessoal (`nome`, `email`, `cpf`, `telefone`, `endereco`) falham o build. Extensão direta do `test_evento_nao_carrega_pii`, que já cobre o evento.
2. **Teste de roteamento por domicílio**, não por origem da requisição.
3. **Verificação de telemetria sem identificador**, por amostragem no pipeline.
4. **Checklist de revisão** para qualquer novo campo em Pedidos: é dado pessoal? Se sim, por que está aqui?

---

## Pendências registradas

- **`PR-03` é pré-requisito.** Sem o país, esta ADR não passa de proposta.
- `V8` — dono do endereço de entrega — precisa fechar antes, porque muda a premissa central.
- A escolha de região na AWS depende de `PR-03` e não foi feita.
- Transferência internacional de dados, quando necessária, exige instrumento jurídico (cláusulas contratuais padrão ou equivalente). Fora do escopo técnico, mas precisa ter dono.
