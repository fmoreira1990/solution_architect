"""Validação assíncrona contra o Catálogo — ADR-0007.

Prova a assimetria deliberada entre canais:
  canal próprio cota antes  -> preço HONRADO, mesmo que o Catálogo mude
  parceiro submete os termos -> CONFERIDO contra o preço vigente
"""
import sys
import uuid
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import catalogo, oferta, pedidos, relay  # noqa: E402
from test_idempotencia import corpo_pedido  # noqa: E402


def corpo_de_parceiro(sku="TV-55-QLED", preco=349900, quantidade=1):
    """Parceiro submete os termos do sistema dele — SEM assinatura."""
    p = catalogo.obter(sku)
    return {
        "cliente_id": "cliente-parceiro",
        "canal": "parceiro",
        "oferta": {
            "itens": [{
                "sku": sku, "quantidade": quantidade,
                "descricao": p["descricao"], "preco_unitario": preco,
                "moeda": p["moeda"], "unidade": p["unidade"],
                "peso_gramas": p["peso_gramas"],
            }],
            "catalogo_versao": catalogo.versao(),
        },
    }


def validar(broker, validador):
    relay.tick(broker)
    broker.entregar_pendentes()


# ------------------------------------------------------- cotação honrada

def test_cotacao_assinada_e_honrada_mesmo_com_o_catalogo_mudando(servidor, broker, validador):
    """A cotação é compromisso: mudar o preço depois não afeta o pedido."""
    r = httpx.post(f"{servidor}/v2/orders", json=corpo_pedido(),
                   headers={"Idempotency-Key": str(uuid.uuid4())})
    pedido_id = r.json()["id"]

    catalogo.alterar_preco("TV-55-QLED", 429900)  # sobe 23% depois do aceite
    validar(broker, validador)

    pedido = pedidos.obter(pedido_id)
    assert pedido["status"] == "CONFIRMADO", "cotação assinada não foi honrada"
    assert pedido["itens"][0]["preco_unitario"] == 349900


# --------------------------------------------- parceiro conferido depois

def test_parceiro_com_preco_correto_e_confirmado(servidor, broker, validador):
    r = httpx.post(f"{servidor}/v2/orders", json=corpo_de_parceiro(),
                   headers={"Idempotency-Key": str(uuid.uuid4()), "X-Chamador": "parceiro-alfa"})
    assert r.status_code == 201
    assert r.json()["status"] == "RECEBIDO"

    validar(broker, validador)
    assert pedidos.obter(r.json()["id"])["status"] == "CONFIRMADO"


def test_parceiro_com_preco_divergente_e_rejeitado_apos_o_aceite(servidor, broker, validador):
    """Rejeição pós-aceite é modo de operação previsto, não incidente."""
    r = httpx.post(f"{servidor}/v2/orders", json=corpo_de_parceiro(preco=100),
                   headers={"Idempotency-Key": str(uuid.uuid4()), "X-Chamador": "parceiro-alfa"})

    # O aceite NÃO recusa: ele é local e não conhece o preço vigente.
    assert r.status_code == 201
    assert r.json()["status"] == "RECEBIDO"

    validar(broker, validador)

    pedido = pedidos.obter(r.json()["id"])
    assert pedido["status"] == "REJEITADO"
    assert any("preço divergente" in m for m in validador.rejeitados)


def test_sku_inexistente_e_rejeitado_na_validacao(servidor, broker, validador):
    corpo = corpo_de_parceiro()
    corpo["oferta"]["itens"][0]["sku"] = "SKU-QUE-NAO-EXISTE"
    r = httpx.post(f"{servidor}/v2/orders", json=corpo,
                   headers={"Idempotency-Key": str(uuid.uuid4()), "X-Chamador": "parceiro-alfa"})
    assert r.status_code == 201

    validar(broker, validador)
    assert pedidos.obter(r.json()["id"])["status"] == "REJEITADO"


# ----------------------------------------------------- degradação (P2-04)

def test_catalogo_fora_do_ar_nao_impede_o_aceite(servidor):
    """CTX-17: o aceite não depende do Catálogo."""
    catalogo.definir_disponibilidade(False)
    corpo = {"cliente_id": "c-1", "canal": "parceiro",
             "oferta": {"itens": [{"sku": "TV-55-QLED", "quantidade": 1,
                                   "descricao": "TV", "preco_unitario": 349900,
                                   "moeda": "BRL", "unidade": "un", "peso_gramas": 18400}],
                        "catalogo_versao": "congelada"}}
    r = httpx.post(f"{servidor}/v2/orders", json=corpo,
                   headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, "o Catálogo fora do ar impediu o aceite"
    assert r.json()["status"] == "RECEBIDO"


def test_catalogo_fora_do_ar_deixa_o_pedido_em_recebido(servidor, broker, validador):
    """Não se rejeita pedido por indisponibilidade NOSSA.

    O pedido permanece em RECEBIDO e a reconciliação assume (P1-15).
    """
    r = httpx.post(f"{servidor}/v2/orders", json=corpo_pedido(),
                   headers={"Idempotency-Key": str(uuid.uuid4())})
    pedido_id = r.json()["id"]

    catalogo.definir_disponibilidade(False)
    with pytest.raises(catalogo.CatalogoIndisponivel):
        validar(broker, validador)

    assert pedidos.obter(pedido_id)["status"] == "RECEBIDO"


def test_cotacao_indisponivel_quando_o_catalogo_cai(servidor):
    catalogo.definir_disponibilidade(False)
    r = httpx.post(f"{servidor}/v2/quotes", json={"itens": [{"sku": "TV-55-QLED", "quantidade": 1}]})
    assert r.status_code == 503


def test_endpoint_de_cotacao_devolve_termos_assinados(servidor):
    r = httpx.post(f"{servidor}/v2/quotes",
                   json={"itens": [{"sku": "CAFE-GRAO-1KG", "quantidade": 2.5}]})
    assert r.status_code == 201
    cot = r.json()
    assert cot["assinatura"] and cot["expira_em"]
    assert cot["itens"][0]["unidade"] == "kg"
    oferta.validar(cot)  # não levanta
