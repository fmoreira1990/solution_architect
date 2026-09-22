"""Snapshot dos termos acordados — ADR-0003."""
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import catalogo  # noqa: E402
from test_idempotencia import corpo_pedido  # noqa: E402


def test_mudanca_de_preco_no_catalogo_nao_altera_o_pedido(servidor):
    """A dor irreversível de CTX-06, resolvida."""
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    pedido_id = r.json()["id"]
    preco_na_compra = r.json()["itens"][0]["preco_unitario"]
    assert preco_na_compra == 349900

    catalogo.alterar_preco("TV-55-QLED", 429900)

    consulta = httpx.get(f"{servidor}/v2/orders/{pedido_id}")
    assert consulta.json()["itens"][0]["preco_unitario"] == preco_na_compra


def test_consulta_de_pedido_funciona_com_o_catalogo_fora_do_ar(servidor):
    """ENFORCEMENT PRIMÁRIO da ADR-0003.

    Se este teste falhar, alguma leitura de pedido voltou a depender do
    Catálogo — exatamente a regressão que a ADR existe para impedir.
    """
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    pedido_id = r.json()["id"]

    catalogo.definir_disponibilidade(False)

    consulta = httpx.get(f"{servidor}/v2/orders/{pedido_id}")
    assert consulta.status_code == 200

    item = consulta.json()["itens"][0]
    assert item["preco_unitario"] == 349900
    assert item["descricao"] == 'Smart TV 55" QLED 4K'
    assert item["unidade"] == "un"
    assert item["peso_gramas"] == 18400


def test_snapshot_carrega_unidade_e_peso(servidor):
    """Unidade e peso congelam: 'quantidade 2' não significa nada sem 'kg',
    e o peso é base do frete cobrado (revisão da ADR-0003)."""
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(skus=(("CAFE-GRAO-1KG", 2.5),)),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    item = r.json()["itens"][0]
    assert item["unidade"] == "kg"
    assert item["quantidade"] == 2.5
    assert item["peso_gramas"] == 1000
    assert item["catalogo_versao"]
