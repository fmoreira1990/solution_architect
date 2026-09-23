"""Caminho legado — o comportamento ANTES da onda 30.

Existe para que a convivência seja **demonstrável**: sem ele não há o que
comparar, nem para onde reverter. Reproduz os dois débitos de `CTX-07`:

  - **sem chave de idempotência**: retry cria pedido novo
  - **publica APÓS o commit**: falha na publicação perde o evento

Não é código morto nem simulação decorativa. É o outro lado do rollout
progressivo, e os testes o usam para mostrar o contraste com o caminho novo.
"""
import json
import uuid
from datetime import datetime, timezone

from . import db


class FalhaNaPublicacao(Exception):
    """Injetada pelo teste entre o commit e o publish."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def aceitar(corpo: dict, broker, falhar_ao_publicar: bool = False) -> dict:
    """Comportamento legado. Retorna o pedido criado.

    Note o que NÃO acontece aqui: nenhuma consulta à chave de idempotência,
    e nenhuma gravação no outbox.
    """
    from . import pedidos

    pedido_id = str(uuid.uuid4())
    agora = _agora()
    itens = corpo["oferta"]["itens"]
    versao = corpo["oferta"].get("catalogo_versao", "legado")

    with db.transacao() as con:
        con.execute(
            """INSERT INTO pedido (id, cliente_id, canal, status, criado_em, atualizado_em)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (pedido_id, corpo["cliente_id"], corpo.get("canal", "web"), "RECEBIDO", agora, agora),
        )
        for item in itens:
            con.execute(
                """INSERT INTO pedido_item
                   (pedido_id, sku, quantidade, descricao, preco_unitario,
                    moeda, unidade, peso_gramas, promocao_id, catalogo_versao)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    pedido_id, item["sku"], item["quantidade"], item["descricao"],
                    item["preco_unitario"], item["moeda"], item["unidade"],
                    item["peso_gramas"], item.get("promocao_id"), versao,
                ),
            )

    # O defeito de CTX-07: a publicação acontece FORA da transação.
    # Uma falha aqui deixa o pedido no banco e o evento em lugar nenhum.
    if falhar_ao_publicar:
        raise FalhaNaPublicacao("falha entre o commit e a publicação")

    broker.publicar({
        "event_id": str(uuid.uuid4()),
        "tipo": "PedidoRecebido",
        "versao": "1.0",
        "chave_particao": pedido_id,
        "payload": json.dumps({"pedido_id": pedido_id, "cliente_id": corpo["cliente_id"]}),
        "criado_em": agora,
        "publicado_em": agora,
    })

    return pedidos.obter(pedido_id)
