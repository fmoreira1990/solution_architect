# Glossário — Linguagem Ubíqua

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** termos do domínio com significado preciso e único. Quando um termo significa coisas diferentes em contextos diferentes, isso está declarado.
**Requisitos cobertos:** `P1-09`
**Fontes:** `docs/business-context/mapa-dominios.md`, `ADR-0003`, `ADR-0007`
**Data:** 2026-09-22

---

| Termo | Definição | Contexto dono |
|---|---|---|
| **Pedido** | Registro de uma intenção de compra aceita pela plataforma. Existe a partir do aceite, **antes** de ser confirmado. | Pedidos |
| **Aceite** | Ato de receber e persistir o pedido. Local, sem chamada externa. Responde `201 RECEBIDO`. **Não significa venda concluída.** | Pedidos |
| **Confirmação** | Desfecho positivo da validação assíncrona. É quando a venda passa a existir comercialmente. | Pedidos |
| **Oferta** | Preço cotado para um conjunto de itens, com validade e assinatura. Imutável após emissão; expira por tempo. | Carrinho e Oferta |
| **Reserva** | Bloqueio temporário de saldo de estoque, com TTL. Existe apenas em canais próprios. | Estoque |
| **Snapshot** | Cópia **imutável** dos termos acordados, gravada no item do pedido. É registro, não cache: se sumir, a informação se perde, porque a fonte já mudou. | Pedidos |
| **Cache** | Otimização de leitura. Se sumir, busca-se de novo e obtém-se o mesmo resultado. **Nunca serve como registro.** | vários |
| **Termo acordado** | Qualquer atributo que serviu de base a um compromisso com o cliente — preço, descrição, unidade, peso, promoção. Congela no snapshot. | Pedidos |
| **Chave de idempotência** | Identificador fornecido pelo cliente que garante que chamadas repetidas não criem pedidos distintos. | Pedidos |
| **Outbox** | Tabela de eventos gravada na **mesma transação** do pedido, lida depois pelo relay. Garante que evento e estado nunca divirjam. | Pedidos |
| **Relay** | Processo que lê o outbox e publica no broker, marcando o que já saiu. | Pedidos |
| **Rejeição pós-aceite** | Pedido aceito e depois recusado na validação. É modo de operação previsto, não incidente. | Pedidos |
| **Consumidor** | Sistema que consome o contrato de Pedidos — API ou evento. Pode ser interno ou externo: **ainda `???`**. | — |
| **Parceiro** | Marketplace externo que envia pedidos pela API pública. Não tem carrinho, logo não tem oferta nem reserva. Seu conteúdo é **não confiável**. | Notificação e Parceiros |
| **Canal próprio** | Web e app móvel da própria rede. Tem carrinho, oferta e reserva. | Carrinho e Oferta |

---

## Termos ambíguos, desambiguados

| Termo | Em Pedidos significa | Em outro contexto significa |
|---|---|---|
| **Preço** | o valor **acordado**, congelado no snapshot | em Catálogo: o valor **vigente**, que muda |
| **Disponibilidade** | atributo de qualidade — 99,9% mensal (`CTX-03`) | em Estoque: haver saldo para venda |
| **Item** | linha do pedido, com snapshot | em Catálogo: produto cadastrado (SKU) |
| **Status** | estado na máquina de estados do pedido | em Notificação: payload entregue ao parceiro |
| **Versão** | versão do contrato (`v1`, `v2`) | em Catálogo: `catalogo_versao`, evidência de auditoria |

---

## Termos proibidos

Palavras que causaram confusão e não devem aparecer nos artefatos sem qualificação:

- **"Criação"** sozinha — ambígua entre aceite e confirmação. Use um dos dois. O p95 de `CTX-04` mede **aceite**.
- **"Cache do pedido"** — não existe. O pedido é autocontido; o que existe é cache de atributos operacionais do Catálogo.
- **"Validar o pedido"** sem dizer o quê — a validação de oferta é local e síncrona; a de estoque e pagamento é assíncrona.

## Pendências registradas

- **Consumidor** permanece `???` quanto a ser interno ou externo. É a pendência mais consequente em aberto: muda `CTX-10` de negociável para contratual (`ADR-0004`).
- Termos de logística e fiscal não entraram por serem escopo OUT; entram se o escopo mudar.
