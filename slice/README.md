# Fatia executável

A prova de que as decisões centrais funcionam — em PostgreSQL real, com escritas concorrentes de verdade.

```bash
python prova.py
```

Instala as dependências, cria o schema, semeia dados sintéticos e roda a suíte. Pré-requisitos e diagnóstico de falha estão no [README principal](../README.md#como-rodar).

---

## Os dois critérios críticos do enunciado

| Critério | Teste |
|---|---|
| Chamadas repetidas com a mesma chave não criam pedido duplicado | `tests/test_idempotencia.py::test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido` |
| A evolução de contrato não quebra um consumidor atual | `tests/test_compatibilidade_contrato.py::test_consumidor_v1_continua_passando_com_a_v2_no_ar` |

Para rodar só os dois:

```bash
python -m pytest tests -v -k "vinte_requisicoes or consumidor_v1_continua"
```

---

## Módulo → decisão → teste

| Módulo | O que faz | Decisão | Provado em |
|---|---|---|---|
| `app/pedidos.py` | Aceite do pedido: chave, pedido, snapshot e outbox **numa transação**, sem chamada de saída | [ADR-0001](../docs/decisions/ADR-0001-idempotencia-na-criacao-de-pedido.md), [0003](../docs/decisions/ADR-0003-snapshot-de-termos-e-desacoplamento-do-catalogo.md), [0007](../docs/decisions/ADR-0007-aceitacao-assincrona-com-validacao-posterior.md) | `test_idempotencia.py`, `test_snapshot.py` |
| `app/relay.py` | Publica o outbox **antes** de marcar — duplica, nunca perde | [ADR-0002](../docs/decisions/ADR-0002-publicacao-confiavel-de-eventos-via-outbox.md) | `test_outbox.py` |
| `app/oferta.py` | Cotação assinada, validada localmente na criação | [ADR-0007](../docs/decisions/ADR-0007-aceitacao-assincrona-com-validacao-posterior.md) | `test_validacao_assincrona.py`, `test_seguranca.py` |
| `app/validador.py` | Confere os termos contra o Catálogo **depois** do aceite | [ADR-0007](../docs/decisions/ADR-0007-aceitacao-assincrona-com-validacao-posterior.md) | `test_validacao_assincrona.py` |
| `app/api.py` | `/v1` síncrona (fachada) e `/v2` assíncrona — mesmo JSON, semânticas diferentes | [ADR-0004](../docs/decisions/ADR-0004-versionamento-e-compatibilidade-semantica.md) | `test_compatibilidade_contrato.py`, `test_contratos_versionados.py` |
| `app/flag.py` | Roteamento por percentual; rollback sem deploy | `CTX-11` — zero janela | `test_convivencia.py` |
| `app/legado.py` | O caminho **antes** da onda 30, com os débitos originais — o outro lado do rollout | `CTX-11` | `test_convivencia.py` |
| `app/catalogo.py` | Catálogo simulado: muda preço e sai do ar sob comando | apoio de teste | `test_snapshot.py`, `test_validacao_assincrona.py` |
| `app/broker.py` | Broker em memória que entrega duplicatas, como o at-least-once real | [ADR-0005](../docs/decisions/ADR-0005-stack-da-fatia-executavel.md) — escopo da prova | `test_outbox.py` |
| `app/db.py` | Conexão e transação PostgreSQL | [ADR-0005](../docs/decisions/ADR-0005-stack-da-fatia-executavel.md) | — |

Além desses, `test_governanca.py` transforma as convenções da documentação em verificação: toda ADR com alternativas rejeitadas, todo teste citado existente, exceção técnica vencida quebra o build.

---

## Arquivos de apoio

| | |
|---|---|
| `schema_postgres.sql` | Cada tabela cita a ADR que a exige |
| `seed/catalogo.json` | Catálogo **sintético** — nenhum dado real, nenhuma PII |
| `requirements.txt` | FastAPI e uvicorn, psycopg 3, pytest e httpx, PyYAML para ler os contratos |

## O que a fatia não é

Não é a stack de produção. A [ADR-0005](../docs/decisions/ADR-0005-stack-da-fatia-executavel.md) decide a stack **da prova**; a produção é **.NET 10** ([ADR-0008](../docs/decisions/ADR-0008-stack-de-producao.md)), e a fatia serve de especificação para ela: os testes críticos daqui são reescritos em xUnit contra PostgreSQL real. O broker é stub, o Catálogo é simulado e a chave HMAC é fixa: o que se prova é a **semântica da transação**, não transporte, escala nem gestão de segredo.
