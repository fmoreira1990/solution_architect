# Padrões de desenvolvimento — plataforma de produção

**Slug do PRD:** pedidos-catalogo
**Escopo deste documento:** os padrões que valem para a **plataforma de produção**. Não descrevem a fatia executável, que segue outras regras e por outro motivo — a seção final explica a diferença e por que ela é deliberada.
**Requisitos cobertos:** `P1-17` *(enforcement das ADRs)*, `D-03`
**Fontes:** `docs/technical-context/architecture.md`, `docs/business-context/glossario.md`, ADRs 0001 a 0008
**Data:** 2026-09-24

---

## O princípio que ordena os demais

> **O código precisa tornar difícil violar uma ADR sem perceber.**

Padrão que existe para "ser boa prática" é preferência. Padrão que existe para proteger uma decisão arquitetural tem dono, motivo e verificação. Cada regra abaixo aponta a decisão que ela protege.

---

## 1. Arquitetura de código — Ports & Adapters

**O domínio não conhece infraestrutura.** Nem banco, nem broker, nem HTTP.

```
dominio/          pedido, item, snapshot, máquina de estados, cotação
                  ↑ nenhum import de infraestrutura
aplicacao/        casos de uso: aceitar, confirmar, rejeitar, cotar
                  ↑ orquestra domínio e portas
portas/           interfaces: RepositorioDePedidos, PublicadorDeEventos,
                  ConsultaDeCatalogo
adaptadores/      EF Core, SQS, HTTP, Cognito — implementam as portas
```

**Por que, aqui, não é dogma:**

A `ADR-0002` rejeitou o CDC **por prazo, não por mérito**, e registrou gatilho para reabrir. Trocar polling por CDC deve ser trocar um adaptador — não reescrever o domínio. Mesma coisa com SQS → MSK, se alguém pedir replay histórico.

**Verificação:** teste de arquitetura com ArchUnitNET no CI. O projeto de domínio não referencia EF Core, AWS SDK nem ASP.NET Core. Falha o build. A stack está na `ADR-0008`.

---

## 2. SOLID, aplicado a decisões reais

Não como recitação. Cada princípio abaixo protege algo concreto deste sistema.

### S · Responsabilidade única

**Aceitar um pedido e validá-lo são responsabilidades diferentes** — é literalmente a `ADR-0007`. O aceite persiste e publica; o validador confere contra o Catálogo. Se estivessem na mesma classe, a validação voltaria ao caminho crítico e o `CTX-17` voltaria junto.

O mesmo vale para **cotar** e **aceitar**: cotar lê o Catálogo, aceitar não lê nada. Fundi-las seria desfazer a decisão.

> **Teste que protege:** `test_catalogo_fora_do_ar_nao_impede_o_aceite`.

### O · Aberto/fechado

**Acrescentar um tipo de evento não pode mudar o relay.** Ele lê `outbox`, publica e marca — não conhece `PedidoRecebido` de `PedidoConfirmado`. Um `if tipo == ...` dentro do relay é sinal de que a abstração quebrou.

**Acrescentar um canal não pode mudar o núcleo.** Web, app e parceiro diferem em *como chegam* (cota ou não cota), não em *o que o núcleo faz*.

### L · Substituição de Liskov — e onde ela **não** se aplica

Este é o ponto mais interessante do sistema, e é um caso de **não usar polimorfismo**.

> A v1 **não** é substituível pela v2. Elas têm a mesma forma e **significados diferentes** — o `201` da v1 é venda confirmada; o da v2 é pedido recebido.

Tratá-las como implementações intercambiáveis da mesma interface seria exatamente o erro que a `ADR-0004` existe para impedir. Por isso são **versões separadas com fachada**, e não uma hierarquia de classes.

Liskov aqui é usado para decidir o que **não** unificar.

### I · Segregação de interface

**O contrato do parceiro não é o contrato interno.** O AsyncAPI declara o que o consumidor precisa — `event_id`, `tipo`, `chave_particao`, payload mínimo — e nada do modelo interno.

É o mesmo raciocínio que mantém PII fora do evento (`F4.2`): expor só o necessário não é higiene de design, é redução de superfície.

### D · Inversão de dependência

O caso de uso depende de `PublicadorDeEventos`, não de SQS. É o que permite o broker stub da fatia e a troca de transporte em produção sem tocar no domínio.

---

## 3. Modelagem: a linguagem do código é a do glossário

| No código | Nunca |
|---|---|
| `aceitar_pedido()` | `criar_pedido()` — "criação" é ambígua entre aceite e confirmação |
| `Cotacao` | `Oferta`, `Quote`, `Preco` |
| `cotado` | `tem_preco`, `validado` |
| `preco_unitario` em **centavos**, `int` | `float` para dinheiro, **nunca** |

O `glossario.md` tem uma seção de **termos proibidos sem qualificação**. Ela vale para o código, não só para os documentos — o p95 de `CTX-04` mede **aceite**, e um método chamado `criar` torna impossível saber o que foi cronometrado.

**Dinheiro é `int` em centavos.** Não é preferência: ponto flutuante em valor cobrado produz divergência de centavo que a auditoria do `CTX-06` teria de explicar.

---

## 4. Transação: a regra que não admite exceção

> **Pedido, itens com snapshot, chave de idempotência e registro no outbox entram em UMA transação.** Nunca em duas. Nunca em ordem diferente.

A ordem importa: a chave de idempotência entra **primeiro**, para falhar rápido na `PRIMARY KEY`. Se falhar, a transação inteira reverte — inclusive o outbox — e nunca sobra evento órfão.

| Proibido | Por quê |
|---|---|
| `commit()` dentro de laço | quebra a atomicidade |
| retry de transação que pode ter commitado | **é como se duplica pedido** |
| publicar no broker dentro da transação | é o problema de escrita dupla que o outbox resolve |
| `UPDATE` em coluna de snapshot | o snapshot é imutável por contrato (`ADR-0003`) |
| `SaveChanges()` fora da transação explícita do aceite | o EF Core abriria transações separadas, e a atomicidade some |
| `EnableRetryOnFailure` sem a chave de idempotência inserida primeiro | o retry reexecutaria uma transação que pode ter commitado (`ADR-0008`) |

**Verificação:** `test_falha_no_meio_da_transacao_nao_deixa_evento_orfao` e o *schema check* que exige `NOT NULL` nas colunas de snapshot.

---

## 5. Erros: falhar alto, com contexto, sem PII

| Regra | Motivo |
|---|---|
| Exceção de domínio ≠ exceção de infraestrutura | `ConflitoIdempotencia` é `409`; falha de banco é `503` |
| Nunca engolir exceção silenciosamente | relay parado é falha silenciosa — `except: pass` a torna invisível |
| Mensagem de erro **sem PII** | ela vai para log, que tem retenção própria |
| Erro de negócio com **código estável** | o catálogo de erros faz parte do contrato |
| Nunca inventar valor no fallback | *"inventar preço é pior que recusar a venda"* (`resiliencia.md`) |

---

## 6. Testes: o que provar e onde

| Nível | Prova | Proporção |
|---|---|---|
| **Domínio** (unidade, sem I/O) | máquina de estados, regras de cotação, canonicalização de payload | ~50% |
| **Integração** (banco real) | atomicidade da transação, `SKIP LOCKED`, constraints | ~35% |
| **Contrato** | contrato × implementação rodando; consumidor v1 contra v2 | ~10% |
| **Ponta a ponta** | os caminhos críticos, poucos | ~5% |

**Banco real na integração, nunca *fake*.** A garantia de idempotência **é** a `PRIMARY KEY`; testá-la contra um repositório em memória testaria o *mock*, não a garantia. É a mesma razão pela qual a `ADR-0005` rejeitou SQLite: lá as escritas serializam, e o teste passaria por serialização do banco.

**Todo defeito encontrado em produção vira teste antes da correção.** Sem exceção.

---

## 7. Revisão de código

| Todo PR responde | |
|---|---|
| Que ADR isto toca? | se toca, o comportamento continua coerente com ela? |
| A transação continua única? | |
| Algum campo novo entra no evento? | é PII? |
| Alguma leitura de pedido passou a depender do Catálogo? | |
| Contrato mudou de forma **ou** de significado? | ver checklist de `politica-contratos.md` |

### Revisão de código gerado por IA — regra própria

Este projeto tem evidência direta de que a revisão precisa ser **diferente**, não apenas mais rápida. Três defeitos reais, todos produzidos com assistência de IA e nenhum detectado por teste:

| Defeito | Como escapou | O que o pegou |
|---|---|---|
| Chave de idempotência sem escopo de autorização (`F1.5`) | todos os testes passavam | **modelagem de ameaças**, não teste |
| Validador de Mermaid parou de ver metade dos diagramas | **continuou verde** | conferir a contagem, não o resultado |
| Mensagem de erro quebrava com `UnicodeEncodeError` | caminho nunca exercitado | **testar o caminho de erro** |

**A regra que sai disso:** código assistido por IA passa em teste com facilidade. O que ele erra é **o que ninguém pensou em testar** — fronteira de autorização, modo de falha silenciosa, caminho de exceção.

Portanto:

1. **Revisor sênior obrigatório** em tudo que toque transação, autorização ou contrato
2. **Perguntar o que não foi testado**, não só ler o que foi
3. **Fitness function que não sabe falhar é decoração** — validar por mutação
4. **O caminho de erro é caminho**, e tem de ser exercitado

---

## 8. Observabilidade no código

| Regra | Motivo |
|---|---|
| `pedido_id` em todo log do fluxo | correlação entre aceite, evento e desfecho |
| Nunca logar PII | ver `lgpd-residencia-dados.md` |
| Tracing atravessa a fronteira assíncrona | sem isso, o desfecho não se liga ao aceite |
| SLI de negócio é código, não painel | `relay.idade_do_mais_antigo_pendente()` existe porque o alerta precisa dele |
| Métrica por **versão de contrato** | a fachada v1 não pode se esconder na média |

---

## 9. O que a fatia executável faz diferente — e por quê

A fatia **não segue** estes padrões, deliberadamente.

| Padrão | Fatia | Motivo |
|---|---|---|
| Ports & Adapters, em .NET | Python procedural, SQL direto | o avaliador precisa **ver a transação** sem atravessar três camadas de abstração |
| EF Core, com SQL explícito nos pontos críticos | `psycopg` cru | na prova, nenhuma camada entre o leitor e a `PRIMARY KEY` |
| Broker real | stub em memória | a decisão provada é transacional, não de transporte |
| Injeção de dependência | import direto | poucos módulos não pagam o custo |
| Estado global | `flag._percentual` em memória | em produção, a flag vem de serviço de configuração com propagação; na prova, o que importa é o **roteamento determinístico** |

**Isto é decisão de escopo de prova, não descuido** — está registrado na `ADR-0005`.

A prova existe para demonstrar **uma garantia**, e abstração demais entre o leitor e o `COMMIT` enfraquece a demonstração. Ports & Adapters numa prova de 4 arquivos seria exatamente o superdimensionamento que `AV-08` pune.

> **Inversão que vale registrar:** o padrão certo depende do que o código precisa provar. Na produção, o domínio precisa sobreviver à troca de infraestrutura — daí Ports & Adapters. Na prova, o leitor precisa enxergar a transação — daí SQL explícito.

---

## 10. O que fica de fora

| Ausente | Por quê | Traria de volta se |
|---|---|---|
| Arquitetura hexagonal completa com CQRS | leitura e escrita têm o mesmo modelo e volume | leitura superar escrita em uma ordem de grandeza |
| Event sourcing | o snapshot já resolve auditoria | exigência de reconstruir estado em qualquer ponto |
| Repositório genérico | esconde a semântica da transação, que é o núcleo | nunca |
| Cobertura mínima como gate | cobertura alta com teste fraco é pior que baixa com teste forte | — |

---

## Riscos abertos

1. **Estes padrões nunca foram exercitados em produção.** São derivados das decisões, não de operação — a primeira onda vai revelar onde atrapalham.
2. **A regra de dependência do §1 depende de disciplina de projeto.** O teste de arquitetura pega referência proibida; não pega domínio anêmico com a lógica escorrida para os adaptadores.
3. **A proporção de testes do §6 é referência, não meta.** Transformá-la em gate produziria teste escrito para a estatística.

## Pendências registradas

- O catálogo de códigos de erro de negócio (§5) não existe — precisa entrar na OpenAPI.
