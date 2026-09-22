"""Outbox transacional — ADR-0002.

Prova que estado e evento nunca divergem, inclusive sob queda do relay.
"""
import sys
import uuid
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, pedidos, relay  # noqa: E402
from conftest import contar  # noqa: E402
from test_idempotencia import corpo_pedido  # noqa: E402


def test_pedido_e_evento_nascem_na_mesma_transacao(servidor):
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    assert contar("pedido") == 1
    assert contar("outbox") == 1
    assert contar("outbox", "publicado_em IS NULL") == 1, "evento já marcado antes do relay"


def test_falha_no_meio_da_transacao_nao_deixa_evento_orfao():
    """Rollback tem de levar o outbox junto — fronteira ADR-0001 / ADR-0002."""
    corpo = corpo_pedido()
    chave = str(uuid.uuid4())

    pedidos.aceitar("web", chave, corpo)
    assert contar("pedido") == 1

    # Mesma chave, payload divergente: a transação inteira é revertida.
    with pytest.raises(pedidos.ConflitoIdempotencia):
        pedidos.aceitar("web", chave, corpo_pedido(skus=(("ARROZ-5KG", 3),)))

    assert contar("pedido") == 1, "pedido órfão criado pela transação revertida"
    assert contar("outbox") == 1, "evento órfão deixado pela transação revertida"


# ---------------------------------------------------------- CRITÉRIO CRÍTICO

def test_queda_entre_publicar_e_marcar_nao_perde_evento(broker):
    """A prova executável da ADR-0002.

    O relay cai DEPOIS de publicar e ANTES de marcar. Na retomada o evento
    sai de novo: duplicado (at-least-once), nunca perdido.
    """
    pedido, _ = pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())

    with pytest.raises(relay.CrashSimulado):
        relay.tick(broker, falhar_antes_de_marcar=True)

    # O broker recebeu; o banco não registrou a publicação.
    assert len(broker.publicados) == 1
    assert contar("outbox", "publicado_em IS NULL") == 1, "marcou apesar da queda"

    # Retomada: republica e agora marca.
    assert relay.tick(broker) == 1
    assert contar("outbox", "publicado_em IS NULL") == 0

    ids = broker.ids_publicados()
    assert len(ids) == 2, "esperado at-least-once (entrega dupla)"
    assert len(set(ids)) == 1, "o event_id mudou entre as tentativas"
    assert contar("outbox") == 1, "o evento foi duplicado no banco"


def test_consumidor_deduplica_a_entrega_duplicada(broker, validador):
    """At-least-once só é seguro porque o consumidor deduplica (ADR-0002)."""
    pedido, _ = pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())
    broker.assinar(validador)

    with pytest.raises(relay.CrashSimulado):
        relay.tick(broker, falhar_antes_de_marcar=True)
    relay.tick(broker)

    broker.entregar_pendentes()

    assert len(broker.ids_publicados()) == 2, "o cenário não gerou entrega dupla"
    assert validador.processados == 1, "o consumidor processou a duplicata"
    assert validador.ignorados_por_duplicata == 1
    assert pedidos.obter(pedido["id"])["status"] == "CONFIRMADO"


def test_transicao_invalida_e_recusada_pelo_dominio():
    pedido, _ = pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())
    pedidos.rejeitar(pedido["id"])

    with pytest.raises(pedidos.TransicaoInvalida):
        pedidos.confirmar(pedido["id"])

    assert pedidos.obter(pedido["id"])["status"] == "REJEITADO"


def test_sli_de_relay_parado_detecta_pendencia():
    """Relay parado é falha silenciosa: nada quebra, tudo atrasa."""
    assert relay.idade_do_mais_antigo_pendente() is None
    pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())
    assert relay.idade_do_mais_antigo_pendente() is not None
    assert relay.pendentes() == 1
