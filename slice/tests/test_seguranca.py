"""Testes de segurança derivados do threat model.

Cada teste cita a ameaça que verifica em `docs/security-context/threat-model.md`.
"""
import sys
import uuid
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import pedidos  # noqa: E402
from conftest import contar  # noqa: E402
from test_idempotencia import corpo_pedido  # noqa: E402


# ------------------------------------------------- F1.5 escopo da chave

def test_chave_de_outro_cliente_nao_devolve_pedido_alheio(servidor):
    """Ameaça F1.5 — chave de idempotência como superfície de AUTORIZAÇÃO.

    Se `chamador` identificar o canal e não o principal autenticado, todos
    os clientes compartilham espaço de chaves. Quem adivinhar a chave de
    outro não pode receber o pedido dele no replay.
    """
    chave = str(uuid.uuid4())
    h = {"Idempotency-Key": chave, "X-Chamador": "web"}

    vitima = httpx.post(
        f"{servidor}/v2/orders", json=corpo_pedido(cliente="cliente-VITIMA"), headers=h
    )
    assert vitima.status_code == 201
    pedido_da_vitima = vitima.json()["id"]

    # Atacante reusa a MESMA chave, no MESMO namespace de chamador.
    atacante = httpx.post(
        f"{servidor}/v2/orders", json=corpo_pedido(cliente="cliente-ATACANTE"), headers=h
    )

    assert atacante.status_code == 409, "o replay devolveu resposta a outro cliente"
    corpo = atacante.text
    assert pedido_da_vitima not in corpo, "vazou o id do pedido da vítima"
    assert "cliente-VITIMA" not in corpo, "vazou o cliente da vítima"
    assert contar("pedido") == 1


def test_defesa_em_profundidade_independe_do_hash(servidor, monkeypatch):
    """A propriedade de F1.5 não pode depender de cliente_id estar no hash.

    O hash canônico sozinho já barra este caso, porque cliente_id faz parte
    do payload. Para verificar a CAMADA NOVA isoladamente, o hash é
    neutralizado — simulando um futuro em que cliente_id saia dele.

    Sem `monkeypatch`, este teste passaria pela verificação de hash e não
    exercitaria nada do que o nome promete.
    """
    chave = str(uuid.uuid4())
    corpo_a = corpo_pedido(cliente="cliente-A")
    pedidos.aceitar("web", chave, corpo_a)

    # Hash constante: a primeira verificação deixa de barrar.
    monkeypatch.setattr(pedidos, "_hash_payload", lambda _: "hash-constante")
    pedidos.aceitar("web", str(uuid.uuid4()), corpo_a)  # grava com o hash fixo

    chave2 = str(uuid.uuid4())
    pedidos.aceitar("web", chave2, corpo_a)
    corpo_b = dict(corpo_a, cliente_id="cliente-B")

    with pytest.raises(pedidos.ConflitoIdempotencia, match="outro cliente"):
        pedidos.aceitar("web", chave2, corpo_b)


def test_namespaces_de_chamadores_distintos_nao_colidem(servidor):
    """O escopo (chamador, chave) isola parceiros entre si."""
    chave = str(uuid.uuid4())
    corpo = corpo_pedido(cliente="cliente-001")

    p1 = httpx.post(
        f"{servidor}/v2/orders", json=corpo,
        headers={"Idempotency-Key": chave, "X-Chamador": "parceiro-alfa"},
    )
    p2 = httpx.post(
        f"{servidor}/v2/orders", json=corpo,
        headers={"Idempotency-Key": chave, "X-Chamador": "parceiro-beta"},
    )

    assert p1.status_code == 201 and p2.status_code == 201
    assert p1.json()["id"] != p2.json()["id"]
    assert contar("pedido") == 2


# --------------------------------------------- F1.2 integridade da oferta

def test_preco_adulterado_apos_assinatura_e_recusado(servidor):
    """Ameaça F1.2 — adulterar preço no payload da oferta."""
    corpo = corpo_pedido()
    corpo["oferta"]["itens"][0]["preco_unitario"] = 1  # R$ 0,01
    r = httpx.post(
        f"{servidor}/v2/orders", json=corpo, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert r.status_code == 422
    assert contar("pedido") == 0


def test_item_injetado_na_oferta_e_recusado(servidor):
    """Acrescentar item depois da assinatura quebra o HMAC."""
    corpo = corpo_pedido()
    corpo["oferta"]["itens"].append({
        "sku": "TV-55-QLED", "quantidade": 99, "descricao": "gratis",
        "preco_unitario": 0, "moeda": "BRL", "unidade": "un", "peso_gramas": 1,
    })
    r = httpx.post(
        f"{servidor}/v2/orders", json=corpo, headers={"Idempotency-Key": str(uuid.uuid4())}
    )
    assert r.status_code == 422
    assert contar("pedido") == 0


# ------------------------------------------------------- F4.2 PII em evento

def test_evento_nao_carrega_pii(broker):
    """Ameaça F4.2 — evento é o veículo de maior replicação do sistema.

    Payload carrega identificadores, não dados pessoais: PII em evento se
    espalha para todo consumidor, DLQ e backup.
    """
    import json as _json
    from app import relay

    pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())
    relay.tick(broker)

    payload = _json.loads(broker.publicados[0]["payload"])
    proibidos = {"nome", "email", "cpf", "documento", "telefone", "endereco", "cep"}
    assert not (proibidos & set(payload)), f"PII no evento: {proibidos & set(payload)}"
    # Allowlist: todo campo novo no evento exige decisão consciente.
    # `cotado` (bool) entrou com a ADR-0007 e não é dado pessoal.
    assert set(payload) <= {"pedido_id", "cliente_id", "itens", "cotado"}
