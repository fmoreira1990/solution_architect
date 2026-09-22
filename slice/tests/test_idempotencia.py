"""Idempotência — ADR-0001.

CRITÉRIO CRÍTICO (§2.4.2, parte 1):
    "chamadas repetidas com a mesma chave não podem criar pedidos duplicados"
"""
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import oferta  # noqa: E402
from conftest import contar  # noqa: E402


def corpo_pedido(skus=(("TV-55-QLED", 1),), cliente="cliente-001"):
    return {"cliente_id": cliente, "canal": "web", "oferta": oferta.emitir(list(skus))}


# ---------------------------------------------------------------- positivos

def test_criacao_simples_responde_201_e_recebido(servidor):
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    assert r.json()["status"] == "RECEBIDO"
    assert contar("pedido") == 1


def test_replay_com_mesma_chave_devolve_o_mesmo_pedido(servidor):
    chave = str(uuid.uuid4())
    corpo = corpo_pedido()
    h = {"Idempotency-Key": chave}

    primeira = httpx.post(f"{servidor}/v2/orders", json=corpo, headers=h)
    segunda = httpx.post(f"{servidor}/v2/orders", json=corpo, headers=h)

    assert primeira.status_code == 201
    assert segunda.status_code == 200
    assert segunda.headers.get("Idempotency-Replayed") == "true"
    assert primeira.json()["id"] == segunda.json()["id"]
    assert contar("pedido") == 1


# ---------------------------------------------------------- CRITÉRIO CRÍTICO

def test_vinte_requisicoes_concorrentes_criam_exatamente_um_pedido(servidor):
    """O teste que o desafio marca como critério crítico.

    Vinte threads disparam simultaneamente com a MESMA chave. Quem garante
    a unicidade é a PRIMARY KEY (chamador, chave) — não o código.
    """
    chave = str(uuid.uuid4())
    corpo = corpo_pedido()
    h = {"Idempotency-Key": chave}

    def enviar(_):
        return httpx.post(f"{servidor}/v2/orders", json=corpo, headers=h, timeout=30)

    with ThreadPoolExecutor(max_workers=20) as pool:
        respostas = list(pool.map(enviar, range(20)))

    codigos = [r.status_code for r in respostas]
    ids = {r.json()["id"] for r in respostas}

    assert contar("pedido") == 1, "mais de um pedido criado para a mesma chave"
    assert len(ids) == 1, f"ids divergentes entre as respostas: {ids}"
    assert codigos.count(201) == 1, f"mais de uma criação reportada: {codigos}"
    assert codigos.count(200) == 19
    # ADR-0002: um pedido, um evento de aceite.
    assert contar("outbox", "tipo = %s", ("PedidoRecebido",)) == 1


# ---------------------------------------------------------------- negativos

def test_mesma_chave_com_payload_diferente_responde_409(servidor):
    chave = str(uuid.uuid4())
    h = {"Idempotency-Key": chave}

    primeira = httpx.post(f"{servidor}/v2/orders", json=corpo_pedido(), headers=h)
    divergente = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(skus=(("CAFE-GRAO-1KG", 2),)),
        headers=h,
    )

    assert primeira.status_code == 201
    assert divergente.status_code == 409
    assert contar("pedido") == 1, "o payload divergente criou um segundo pedido"


def test_v2_sem_chave_de_idempotencia_e_recusada(servidor):
    r = httpx.post(f"{servidor}/v2/orders", json=corpo_pedido())
    assert r.status_code == 422
    assert contar("pedido") == 0


def test_oferta_expirada_e_recusada(servidor):
    corpo = {
        "cliente_id": "cliente-001",
        "canal": "web",
        "oferta": oferta.emitir([("TV-55-QLED", 1)], validade_segundos=-1),
    }
    r = httpx.post(
        f"{servidor}/v2/orders", json=corpo, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert r.status_code == 422
    assert r.json()["detail"]["erro"] == "oferta_expirada"
    assert contar("pedido") == 0


def test_oferta_adulterada_e_recusada(servidor):
    """Preço alterado depois da assinatura: a oferta deixa de conferir."""
    corpo = corpo_pedido()
    corpo["oferta"]["itens"][0]["preco_unitario"] = 1
    r = httpx.post(
        f"{servidor}/v2/orders", json=corpo, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert r.status_code == 422
    assert r.json()["detail"]["erro"] == "oferta_invalida"
    assert contar("pedido") == 0


def test_replay_devolve_estado_corrente_e_nao_o_gravado(servidor, broker, validador):
    """ADR-0001: com aceite assíncrono, replay literal mentiria sobre o estado."""
    from app import relay

    chave = str(uuid.uuid4())
    corpo = corpo_pedido()
    h = {"Idempotency-Key": chave}

    primeira = httpx.post(f"{servidor}/v2/orders", json=corpo, headers=h)
    assert primeira.json()["status"] == "RECEBIDO"

    relay.tick(broker)
    broker.entregar_pendentes()

    replay = httpx.post(f"{servidor}/v2/orders", json=corpo, headers=h)
    assert replay.status_code == 200
    assert replay.json()["status"] == "CONFIRMADO", "replay devolveu estado vencido"
