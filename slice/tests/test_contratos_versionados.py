"""Fitness functions de contrato — D-03 / ADR-0004.

Não validam apenas a sintaxe dos specs. Comparam o contrato declarado com a
implementação REAL rodando — é o que detecta spec drift, o defeito em que a
documentação e o código divergem sem ninguém perceber.
"""
import sys
import uuid
from pathlib import Path

import httpx
import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_idempotencia import corpo_pedido  # noqa: E402

CONTRATOS = Path(__file__).resolve().parent.parent.parent / "contracts"


def carregar(caminho: Path) -> dict:
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def v1():
    return carregar(CONTRATOS / "openapi" / "orders-v1.yaml")


@pytest.fixture(scope="module")
def v2():
    return carregar(CONTRATOS / "openapi" / "orders-v2.yaml")


@pytest.fixture(scope="module")
def eventos():
    return carregar(CONTRATOS / "asyncapi" / "order-status.yaml")


# ------------------------------------------------------------- specs válidos

def test_specs_existem_e_sao_parseaveis(v1, v2, eventos):
    assert v1["openapi"].startswith("3.")
    assert v2["openapi"].startswith("3.")
    assert eventos["asyncapi"].startswith("3.")


def test_todas_as_respostas_documentadas_em_ambas_as_versoes(v1, v2):
    for spec, rota in ((v1, "/v1/orders"), (v2, "/v2/orders")):
        respostas = spec["paths"][rota]["post"]["responses"]
        assert {"200", "201", "409", "422"} <= set(respostas), (
            f"{rota} não documenta todos os desfechos implementados"
        )


# --------------------------------------------- ADR-0004: compatibilidade v1

def test_idempotency_key_obrigatoria_em_v2_e_opcional_em_v1(v1, v2):
    """Torná-la obrigatória em v1 seria breaking change."""
    def obrigatoriedade(spec, nome):
        for p in spec["components"]["parameters"].values():
            if p["name"] == nome:
                return p.get("required", False)
        raise AssertionError(f"parâmetro {nome} ausente do spec")

    assert obrigatoriedade(v2, "Idempotency-Key") is True
    assert obrigatoriedade(v1, "Idempotency-Key") is False


def test_v1_nunca_declara_recebido_como_status(v1, v2):
    """A garantia semântica da fachada, escrita no contrato.

    Se `RECEBIDO` aparecer no enum da v1, a fachada síncrona caiu e o
    consumidor atual quebrou — mesmo com o schema continuando válido.
    """
    status_v1 = v1["components"]["schemas"]["Pedido"]["properties"]["status"]["enum"]
    status_v2 = v2["components"]["schemas"]["Pedido"]["properties"]["status"]["enum"]

    assert "RECEBIDO" not in status_v1
    assert "RECEBIDO" in status_v2


def test_v1_esta_marcada_como_deprecada_com_sunset(v1):
    post = v1["paths"]["/v1/orders"]["post"]
    assert post.get("deprecated") is True
    assert "Sunset" in post["responses"]["201"]["headers"]


# ----------------------------------------- contrato x implementação (drift)

def test_schema_do_pedido_bate_com_a_resposta_real_da_api(servidor, v2):
    """Detecta spec drift: campo que existe no código e não no contrato."""
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    real = r.json()

    declarado = set(v2["components"]["schemas"]["Pedido"]["properties"])
    assert set(real) == declarado, (
        f"contrato e implementação divergiram. "
        f"só na API: {set(real) - declarado} | só no contrato: {declarado - set(real)}"
    )

    item_declarado = set(v2["components"]["schemas"]["ItemDoPedido"]["properties"])
    assert set(real["itens"][0]) == item_declarado


def test_status_devolvido_pertence_ao_enum_declarado(servidor, v1, v2):
    nova = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    legada = httpx.post(
        f"{servidor}/v1/orders", json=corpo_pedido(cliente="legado"), timeout=30
    )

    assert nova.json()["status"] in v2["components"]["schemas"]["Pedido"]["properties"]["status"]["enum"]
    assert legada.json()["status"] in v1["components"]["schemas"]["Pedido"]["properties"]["status"]["enum"]


# ------------------------------------------------------- AsyncAPI x eventos

def test_envelope_declarado_bate_com_o_que_o_relay_publica(broker, eventos):
    """O contrato do evento precisa descrever o que realmente é publicado."""
    from app import pedidos, relay

    pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())
    relay.tick(broker)

    publicado = broker.publicados[0]
    declarado = set(eventos["components"]["schemas"]["Envelope"]["properties"])

    assert declarado <= set(publicado) | {"publicado_em"}, (
        f"campos declarados e não publicados: {declarado - set(publicado)}"
    )
    assert publicado["tipo"] == "PedidoRecebido"
    assert publicado["chave_particao"] == publicado["chave_particao"]


def test_asyncapi_declara_event_id_como_chave_de_deduplicacao(eventos):
    """A obrigação de deduplicar vive no CONTRATO, não em documentação à parte."""
    envelope = eventos["components"]["schemas"]["Envelope"]
    assert "event_id" in envelope["required"]
    assert "dedup" in envelope["properties"]["event_id"]["description"].lower()


def test_tipos_de_evento_do_contrato_existem_na_implementacao(eventos):
    from app import pedidos

    declarados = set(eventos["components"]["schemas"]["Envelope"]["properties"]["tipo"]["enum"])
    estados = set(pedidos.TRANSICOES) | {"RECEBIDO"}
    for tipo in declarados:
        assert tipo.replace("Pedido", "").upper() in estados
