# LGPD e residência de dados

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** classificação de dados pessoais, base legal, minimização, retenção e residência. O **padrão** de segregação regional é decidido na `ADR-0006`; aqui está o inventário que a sustenta.
**Requisitos cobertos:** `CTX-09`, `P2-03`
**Fontes:** `docs/technical-context/architecture.md`, `docs/security-context/threat-model.md` (F4, F5), `ADR-0003`
**Data:** 2026-09-23 *(seção 4 revista após `PR-03` fechar como Estados Unidos)*

---

## 1. Classificação

| Dado | Onde vive | Classificação | Base legal | Retenção |
|---|---|---|---|---|
| `cliente_id` | Pedidos, eventos | **pseudônimo** — identifica indiretamente | execução de contrato | vida do pedido + prazo fiscal |
| Nome, e-mail, telefone | **Identidade** *(não em Pedidos)* | **pessoal** | execução de contrato | enquanto houver relação + prazo legal |
| Endereço de entrega | Pedidos ou Logística | **pessoal** | execução de contrato | prazo fiscal |
| CPF / documento | Identidade, Fiscal | **pessoal sensível na prática** | obrigação legal (fiscal) | prazo fiscal — não expurgável antes |
| Dados de pagamento | sistema de pagamento externo *(tokenizado)* | **pessoal** | execução de contrato | conforme PCI; **nunca em Pedidos** |
| Snapshot dos itens (SKU, preço, descrição) | Pedidos | **não pessoal** | — | vida do pedido |
| Histórico de compra | Pedidos | **pessoal por agregação** | execução de contrato / legítimo interesse | — |
| Log de acesso à API | Observabilidade | **pessoal** (IP, identificador) | legítimo interesse | **90 dias** |

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

## 4. Regime do segundo país: Estados Unidos

`PR-03` fechou em 2026-09-23. E a resposta **muda a natureza da restrição**.

O enunciado fala em *"requisitos de residência de dados do novo país"*. Essa formulação pressupõe um regime que obrigue o dado a permanecer no território. **Os Estados Unidos não têm isso** para dado comercial de varejo: não existe lei federal abrangente de privacidade nem exigência geral de localização.

> ⚠️ Esta é leitura de arquiteto, **não parecer jurídico**. Precisa de confirmação do DPO.

### O que existe no lugar

| Aspecto | Consequência para a arquitetura |
|---|---|
| **Mosaico estadual** — CCPA/CPRA, Virginia, Colorado, Texas, Connecticut e outros | A regra aplicável depende do **estado de residência** do consumidor, não do país |
| **Opt-out de venda/compartilhamento** + sinal GPC na Califórnia | Requisito **novo**, sem equivalente direto na LGPD: a preferência precisa propagar a todo consumidor de dado, inclusive parceiros |
| **Sem mandato de residência** | Segregação regional deixa de ser obrigação e vira **escolha justificada** |
| **Notificação de incidente** por lei estadual | Processo de resposta precisa mapear jurisdições |
| **PCI DSS** para dados de cartão | Contratual, não legal; atendido por tokenização no provedor de pagamento, fora desta plataforma |

### A restrição que de fato aparece: a transferência

O fluxo que importa **inverte de direção**. Não é "o dado americano precisa ficar nos EUA" — é:

> **Dado pessoal brasileiro que vai para os EUA é transferência internacional sob a LGPD** (art. 33), e exige instrumento jurídico: cláusulas-padrão contratuais da ANPD ou equivalente (`CTX-09c`, decisão `V9`).

Isso torna a minimização de PII brasileira atravessando a fronteira um objetivo **arquitetural**, não apenas higiene.

### O que pode cruzar

| Categoria | Cruza? |
|---|---|
| PII brasileira (nome, documento, endereço) | ❌ **não**, enquanto `V9` não existir |
| PII americana | ⚠️ pode, mas não há motivo para trazer |
| `cliente_id` pseudônimo | ✅ sim — é o identificador, não o significado |
| Snapshot de itens (SKU, preço, moeda) | ✅ não é dado pessoal |
| **Preferências de privacidade** | ✅ **precisa** cruzar — é sinal que todos honram |
| Telemetria e métricas | ✅ desde que sem identificador |
| Backup | segue a regra do dado que contém |

**A linha das preferências é a única que precisa atravessar por obrigação**, não por conveniência: um opt-out registrado nos EUA tem de ser honrado por qualquer consumidor do dado, onde quer que esteja.

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

1. **O enquadramento da seção 4 é leitura de arquiteto, não parecer jurídico.** A afirmação central — EUA sem mandato de residência para dado comercial de varejo — precisa de confirmação do DPO. Se estiver errada, a `ADR-0006` não muda de decisão, mas muda de justificativa.
2. **Endereço de entrega sem dono.** Se cair em Pedidos, a estratégia de pseudonimização da seção 3 deixa de ser suficiente.
3. **Nenhum dos controles da seção 5 está verificado por teste**, exceto dados sintéticos e ausência de PII no evento. Redação de log e telemetria sem PII são débito.
4. **A retenção de 90 dias precisa de aprovação do jurídico.** Ela acompanha a retenção do outbox, para que auditoria de acesso e rastreio de evento cubram a mesma janela — mas o prazo legal aplicável pode ser outro.
5. **Sem instrumento de transferência BR → EUA (`V9`), nenhuma PII brasileira deveria atravessar.** É pré-requisito da onda 90, não formalidade posterior.
6. **Não se sabe em quais estados americanos a operação estará sujeita (`V10`).** Os limiares da CCPA/CPRA dependem de receita e de volume de consumidores.
7. **O serviço de preferências de privacidade é escopo novo**, exigido por `CTX-09d`, e não estava no plano 30/60/90 original.

## Pendências registradas

- Definir o dono do endereço de entrega (`V8`).
- Aprovar prazos de retenção com jurídico — os desta página são propostas.
- Inventário de quem referencia `cliente_id` precisa existir antes do primeiro pedido de acesso do titular.
