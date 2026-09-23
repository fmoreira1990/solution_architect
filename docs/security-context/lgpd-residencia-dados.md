# LGPD e residência de dados

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** classificação de dados pessoais, base legal, minimização, retenção e residência. O **padrão** de segregação regional é decidido na `ADR-0006`; aqui está o inventário que a sustenta.
**Requisitos cobertos:** `CTX-09`, `P2-03`
**Fontes:** `docs/technical-context/architecture.md`, `docs/security-context/threat-model.md` (F4, F5), `ADR-0003`
**Data:** 2026-09-23

---

## 1. Classificação

| Dado | Onde vive | Classificação | Base legal | Retenção |
|---|---|---|---|---|
| `cliente_id` | Pedidos, eventos | **pseudônimo** — identifica indiretamente | execução de contrato | vida do pedido + prazo fiscal |
| Nome, e-mail, telefone | **Identidade** *(não em Pedidos)* | **pessoal** | execução de contrato | enquanto houver relação + prazo legal |
| Endereço de entrega | Pedidos ou Logística | **pessoal** | execução de contrato | prazo fiscal |
| CPF / documento | Identidade, Fiscal | **pessoal sensível na prática** | obrigação legal (fiscal) | prazo fiscal — não expurgável antes |
| Dados de pagamento | **Pagamento** *(tokenizado)* | **pessoal** | execução de contrato | conforme PCI; nunca em Pedidos |
| Snapshot dos itens (SKU, preço, descrição) | Pedidos | **não pessoal** | — | vida do pedido |
| Histórico de compra | Pedidos | **pessoal por agregação** | execução de contrato / legítimo interesse | — |
| Log de acesso à API | Observabilidade | **pessoal** (IP, identificador) | legítimo interesse | 90 dias `???` |

**Decisão de desenho:** **Pedidos não armazena nome, e-mail, telefone nem documento.** Guarda `cliente_id` e consulta Identidade quando precisar. Isso reduz drasticamente a superfície do banco mais volumoso e mais replicado do sistema.

> ⚠️ **Endereço de entrega está sem dono definido.** Ele é dado pessoal e é necessário à execução do pedido. Ficar em Pedidos simplifica a operação e contamina o banco com PII; ficar em Logística preserva a limpeza e adiciona uma dependência. **Decisão pendente**, registrada como `V8` em `riscos-premissas.md`.

---

## 2. Minimização aplicada ao evento

O evento é o veículo de **maior replicação** do sistema: alcança todo consumidor, DLQ, backup e eventual reprocessamento. PII nele se espalha para lugares que ninguém inventariou.

```
PedidoRecebido.payload = {
    pedido_id, cliente_id,
    itens: [{ sku, quantidade }]
}
```

Identificadores, não dados pessoais. Quem precisa de PII consulta o dono do dado, **com autorização própria** — o evento não é um atalho para contornar controle de acesso.

Verificado por `test_evento_nao_carrega_pii`, que falha se qualquer campo de PII conhecido aparecer no payload.

---

## 3. Direitos do titular

| Direito | Como é atendido | Complicação |
|---|---|---|
| Acesso | Consulta consolidada por `cliente_id` nos contextos que o referenciam | exige inventário atualizado de quem guarda o quê |
| Correção | No dono do dado (Identidade); propaga por evento | **não retroage ao snapshot** — ver abaixo |
| **Eliminação** | Pseudonimização de `cliente_id`, não exclusão do pedido | **conflita com obrigação fiscal** |
| Portabilidade | Exportação por `cliente_id` | — |
| Oposição | Aplicável a tratamentos de legítimo interesse | — |

### O conflito entre eliminação e auditabilidade

O pedido é **registro fiscal e contábil**, com retenção obrigatória. Não pode ser apagado a pedido do titular durante esse prazo. E o snapshot (`ADR-0003`) é **imutável por contrato** — é o que prova o preço praticado.

**Resolução:** eliminação de dados pessoais é atendida por **pseudonimização** — o vínculo `cliente_id` → pessoa é rompido em Identidade; o pedido permanece, com o snapshot intacto, sem identificar ninguém. O registro fiscal sobrevive, a pessoa desaparece dele.

Isso exige que Pedidos **não** contenha PII direta — o que é exatamente a decisão da seção 1. Se o endereço de entrega ficar em Pedidos, a pseudonimização deixa de ser suficiente e passa a exigir expurgo seletivo de coluna.

---

## 4. Residência de dados

`CTX-09` exige atender requisitos de residência do segundo país. **`PR-03` — qual é o país — permanece `???`**, e o regime aplicável depende dele.

O que é possível afirmar sem saber o país:

| Categoria | Pode cruzar fronteira? |
|---|---|
| PII direta (nome, documento, endereço) | ❌ presumir que **não** |
| `cliente_id` pseudônimo | ⚠️ depende do regime |
| Snapshot de itens (SKU, preço) | ✅ não é dado pessoal |
| Telemetria e métricas agregadas | ✅ desde que sem identificador |
| Backup | ❌ segue a regra do dado que contém |

**Regra de projeto adotada enquanto `PR-03` estiver aberto:** desenhar para o regime **mais restritivo** (silo regional completo de PII). Relaxar depois é barato; apertar depois exige migração de dados em produção.

O padrão de segregação é decidido na `ADR-0006`.

---

## 5. Controles técnicos

| Controle | Estado |
|---|---|
| Criptografia em trânsito (TLS) | padrão, toda fronteira |
| Criptografia em repouso | requisito de infraestrutura — onda 30 |
| Chaves de criptografia **regionais** | depende da `ADR-0006` |
| Redação de PII em log | ⚠️ não implementado |
| Acesso ao banco por papel, sem credencial compartilhada | ⚠️ não implementado |
| Dados sintéticos em ambiente não produtivo | ✅ `slice/seed/` — nenhum dado real |
| Telemetria sem PII | ⚠️ não verificado |

---

## Riscos abertos

1. **`PR-03` bloqueia tudo da seção 4.** Sem saber o país, o regime é desconhecido e a `ADR-0006` não fecha. É o bloqueio mais consequente em aberto.
2. **Endereço de entrega sem dono.** Se cair em Pedidos, a estratégia de pseudonimização da seção 3 deixa de ser suficiente.
3. **Nenhum dos controles da seção 5 está verificado por teste**, exceto dados sintéticos e ausência de PII no evento. Redação de log e telemetria sem PII são débito.
4. **Retenção de log em 90 dias é `???`.** Foi escrito como proposta, não como política aprovada.

## Pendências registradas

- Definir o dono do endereço de entrega (`V8`).
- Fechar `PR-03` para destravar a `ADR-0006`.
- Aprovar prazos de retenção com jurídico — os desta página são propostas.
- Inventário de quem referencia `cliente_id` precisa existir antes do primeiro pedido de acesso do titular.
