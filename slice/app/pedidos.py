"""Núcleo do aceite de pedido.

Uma transação, quatro garantias:
  ADR-0001  chave de idempotência gravada PRIMEIRO — falha rápido na PK
  ADR-0003  snapshot imutável dos termos acordados
  ADR-0002  registro no outbox no MESMO commit
  ADR-0007  nenhuma chamada de saída: o aceite é local
"""
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from . import db, oferta

TTL_IDEMPOTENCIA_HORAS = 24

# Máquina de estados (ADR-0007). Transição fora daqui é recusada pelo domínio.
TRANSICOES = {
    "RECEBIDO": {"CONFIRMADO", "REJEITADO"},
    "CONFIRMADO": set(),
    "REJEITADO": set(),
}


class ConflitoIdempotencia(Exception):
    """Mesma chave, payload diferente."""


class TransicaoInvalida(Exception):
    """Ex.: REJEITADO -> CONFIRMADO."""


class PedidoNaoEncontrado(Exception):
    pass


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(corpo: dict) -> str:
    """Impressão canônica: ordem de chaves e separadores fixos.

    Sem canonicalização, a mesma intenção com campos em ordem diferente
    produziria hashes distintos e um 409 falso (ADR-0001, trade-offs).
    """
    canonico = json.dumps(corpo, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def _gravar_outbox(con, tipo: str, pedido_id: str, payload: dict) -> None:
    con.execute(
        """INSERT INTO outbox (event_id, tipo, versao, chave_particao, payload, criado_em)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (str(uuid.uuid4()), tipo, "1.0", pedido_id, json.dumps(payload), _agora()),
    )


def aceitar(chamador: str, chave: str, corpo: dict):
    """Aceita o pedido. Retorna (pedido, foi_replay).

    Nenhuma chamada de saída acontece aqui — é a garantia da ADR-0007,
    verificada pelo teste que cria pedido com o Catálogo fora do ar.
    """
    oferta.validar(corpo["oferta"])  # local: assinatura e validade

    ph = _hash_payload(corpo)
    pedido_id = str(uuid.uuid4())
    agora = _agora()
    expira = (datetime.now(timezone.utc) + timedelta(hours=TTL_IDEMPOTENCIA_HORAS)).isoformat()
    itens = corpo["oferta"]["itens"]
    versao_catalogo = corpo["oferta"]["catalogo_versao"]

    try:
        with db.transacao() as con:
            # 1) ADR-0001 — a PRIMARY KEY (chamador, chave) é a garantia.
            con.execute(
                """INSERT INTO idempotency_key
                   (chamador, chave, payload_hash, pedido_id, criado_em, expira_em)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (chamador, chave, ph, pedido_id, agora, expira),
            )
            # 2) pedido
            con.execute(
                """INSERT INTO pedido (id, cliente_id, canal, status, criado_em, atualizado_em)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (pedido_id, corpo["cliente_id"], corpo.get("canal", "web"), "RECEBIDO", agora, agora),
            )
            # 3) ADR-0003 — snapshot dos termos acordados, copiado da oferta.
            for item in itens:
                con.execute(
                    """INSERT INTO pedido_item
                       (pedido_id, sku, quantidade, descricao, preco_unitario,
                        moeda, unidade, peso_gramas, promocao_id, catalogo_versao)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        pedido_id, item["sku"], item["quantidade"], item["descricao"],
                        item["preco_unitario"], item["moeda"], item["unidade"],
                        item["peso_gramas"], item.get("promocao_id"), versao_catalogo,
                    ),
                )
            # 4) ADR-0002 — outbox no MESMO commit.
            _gravar_outbox(con, "PedidoRecebido", pedido_id, {
                "pedido_id": pedido_id,
                "cliente_id": corpo["cliente_id"],
                # ADR-0007: pedido cotado tem o preço HONRADO na validação;
                # pedido sem cotação (parceiro) é conferido contra o Catálogo.
                "cotado": bool(corpo["oferta"].get("assinatura")),
                "itens": [{"sku": i["sku"], "quantidade": i["quantidade"]} for i in itens],
            })

        return obter(pedido_id), False

    except db.ErroIntegridade:
        # Chave já usada. A transação inteira foi revertida — inclusive o
        # outbox. Nunca sobra evento órfão (fronteira ADR-0001 / ADR-0002).
        existente = _buscar_chave(chamador, chave)
        if existente is None:
            raise
        if existente["payload_hash"] != ph:
            raise ConflitoIdempotencia("chave já utilizada com outro payload")

        pedido = obter(existente["pedido_id"])

        # Threat model F1.5 — defesa em profundidade.
        # O hash já cobre este caso, porque cliente_id faz parte do payload.
        # A verificação explícita existe para que a propriedade sobreviva a
        # uma mudança futura no que entra no hash canônico: chave de
        # idempotência é superfície de AUTORIZAÇÃO, não só de integridade.
        if pedido is not None and pedido["cliente_id"] != corpo["cliente_id"]:
            raise ConflitoIdempotencia("chave pertence a outro cliente")

        # ADR-0001: replay devolve o estado CORRENTE, não a resposta gravada.
        return pedido, True


def _buscar_chave(chamador: str, chave: str):
    with db.conectar() as con:
        return con.execute(
            "SELECT * FROM idempotency_key WHERE chamador = %s AND chave = %s",
            (chamador, chave),
        ).fetchone()


def obter(pedido_id: str):
    """Consulta do pedido. NENHUMA dependência do Catálogo (ADR-0003)."""
    with db.conectar() as con:
        pedido = con.execute("SELECT * FROM pedido WHERE id = %s", (pedido_id,)).fetchone()
        if pedido is None:
            return None
        itens = con.execute(
            "SELECT * FROM pedido_item WHERE pedido_id = %s ORDER BY id", (pedido_id,)
        ).fetchall()

    return {
        "id": pedido["id"],
        "cliente_id": pedido["cliente_id"],
        "canal": pedido["canal"],
        "status": pedido["status"],
        "criado_em": pedido["criado_em"],
        "itens": [
            {
                "sku": i["sku"],
                "quantidade": i["quantidade"],
                "descricao": i["descricao"],
                "preco_unitario": i["preco_unitario"],
                "moeda": i["moeda"],
                "unidade": i["unidade"],
                "peso_gramas": i["peso_gramas"],
                "promocao_id": i["promocao_id"],
                "catalogo_versao": i["catalogo_versao"],
            }
            for i in itens
        ],
    }


def _transicionar(pedido_id: str, novo: str) -> None:
    with db.transacao() as con:
        atual = con.execute(
            "SELECT status FROM pedido WHERE id = %s FOR UPDATE", (pedido_id,)
        ).fetchone()
        if atual is None:
            raise PedidoNaoEncontrado(pedido_id)
        if novo not in TRANSICOES.get(atual["status"], set()):
            raise TransicaoInvalida(f"{atual['status']} -> {novo}")

        con.execute(
            "UPDATE pedido SET status = %s, atualizado_em = %s WHERE id = %s",
            (novo, _agora(), pedido_id),
        )
        tipo = "PedidoConfirmado" if novo == "CONFIRMADO" else "PedidoRejeitado"
        _gravar_outbox(con, tipo, pedido_id, {"pedido_id": pedido_id, "status": novo})


def confirmar(pedido_id: str) -> None:
    _transicionar(pedido_id, "CONFIRMADO")


def rejeitar(pedido_id: str) -> None:
    _transicionar(pedido_id, "REJEITADO")
