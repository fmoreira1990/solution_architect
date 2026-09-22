"""Compatibilidade de contrato — ADR-0004.

CRITÉRIO CRÍTICO (§2.4.2, parte 2):
    "a evolução de contrato não pode quebrar um consumidor atual
     demonstrado no teste"

O ponto destes testes é que a quebra que a ADR-0007 introduz é SEMÂNTICA:
o JSON de v1 e v2 é idêntico, e um diff de schema passa nos dois. O que
muda é o significado do 201 — de "venda confirmada" para "pedido recebido".
"""
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_idempotencia import corpo_pedido  # noqa: E402


class ConsumidorV1DeReferencia:
    """Consumidor atual, escrito ANTES da ADR-0007.

    Ele assume que criar pedido significa venda feita: emite nota e baixa
    comissão na resposta do POST. É este comportamento que não pode quebrar.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.notas_emitidas: list[str] = []

    def comprar(self, corpo: dict) -> dict:
        r = httpx.post(f"{self.base_url}/v1/orders", json=corpo, timeout=30)
        r.raise_for_status()
        pedido = r.json()

        # A premissa do consumidor legado, explícita:
        assert pedido["status"] == "CONFIRMADO", (
            "QUEBRA SEMÂNTICA: o consumidor v1 assume venda confirmada na "
            f"resposta do POST, mas recebeu status={pedido['status']}"
        )
        self.notas_emitidas.append(pedido["id"])
        return pedido


# ---------------------------------------------------------- CRITÉRIO CRÍTICO

def test_consumidor_v1_continua_passando_com_a_v2_no_ar(servidor):
    """Prova que a fachada síncrona protege o consumidor atual."""
    consumidor = ConsumidorV1DeReferencia(servidor)

    pedido_legado = consumidor.comprar(corpo_pedido(cliente="cliente-legado"))

    # A v2 existe e responde no mesmo processo, com a semântica nova.
    nova = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(cliente="cliente-app"),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    assert pedido_legado["status"] == "CONFIRMADO"
    assert nova.json()["status"] == "RECEBIDO"
    assert len(consumidor.notas_emitidas) == 1


def test_as_duas_versoes_divergem_em_semantica_e_nao_em_schema(servidor):
    """O que um diff de OpenAPI NÃO detectaria.

    Mesmos campos, mesmo status code, mesmos tipos. Só o significado muda —
    e é por isso que a ADR-0004 trata compatibilidade semântica como
    categoria própria de breaking change.
    """
    v1 = httpx.post(f"{servidor}/v1/orders", json=corpo_pedido(), timeout=30)
    v2 = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(cliente="cliente-002"),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    assert v1.status_code == v2.status_code == 201
    assert set(v1.json().keys()) == set(v2.json().keys()), "o schema divergiu"
    assert {type(v) for v in v1.json().values()} == {type(v) for v in v2.json().values()}

    # Idêntico na forma, diferente no significado:
    assert v1.json()["status"] == "CONFIRMADO"
    assert v2.json()["status"] == "RECEBIDO"


def test_idempotency_key_e_opcional_em_v1(servidor):
    """Torná-la obrigatória em v1 seria breaking change (ADR-0004)."""
    r = httpx.post(f"{servidor}/v1/orders", json=corpo_pedido(), timeout=30)
    assert r.status_code == 201


def test_idempotency_key_protege_v1_quando_fornecida(servidor):
    chave = str(uuid.uuid4())
    corpo = corpo_pedido()
    h = {"Idempotency-Key": chave}

    primeira = httpx.post(f"{servidor}/v1/orders", json=corpo, headers=h, timeout=30)
    segunda = httpx.post(f"{servidor}/v1/orders", json=corpo, headers=h, timeout=30)

    assert primeira.status_code == 201
    assert segunda.status_code == 200
    assert primeira.json()["id"] == segunda.json()["id"]
