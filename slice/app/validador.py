"""Validador assíncrono — ADR-0007.

Consome PedidoRecebido e decide o desfecho. Em produção seriam Estoque,
Pagamento e Antifraude; aqui é um stub com resultado controlável pelo teste.

Deduplica por event_id. Isso não é zelo do consumidor: é obrigação declarada
no contrato, porque o relay entrega at-least-once (ADR-0002).
"""
import json

from . import pedidos


class Validador:
    def __init__(self, estoque_disponivel: bool = True):
        self.estoque_disponivel = estoque_disponivel
        self.vistos: set[str] = set()
        self.processados = 0
        self.ignorados_por_duplicata = 0

    def __call__(self, evento: dict) -> None:
        if evento["tipo"] != "PedidoRecebido":
            return

        if evento["event_id"] in self.vistos:
            self.ignorados_por_duplicata += 1
            return
        self.vistos.add(evento["event_id"])

        pedido_id = json.loads(evento["payload"])["pedido_id"]
        if self.estoque_disponivel:
            pedidos.confirmar(pedido_id)
        else:
            pedidos.rejeitar(pedido_id)
        self.processados += 1
