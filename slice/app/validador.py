"""Validação assíncrona dos termos do pedido — ADR-0007.

Consome `PedidoRecebido` e confere o snapshot contra o Catálogo. Só existe
porque fazer essa conferência de forma síncrona reintroduziria o `CTX-17`:
Pedidos 99,9% × Catálogo 99,9% = 99,8%, o dobro do error budget.

Regra de negócio, e a assimetria entre canais:

  - Pedido COM cotação assinada  -> o preço cotado é HONRADO, mesmo que o
    Catálogo tenha mudado depois. A cotação é um compromisso.
  - Pedido SEM cotação (parceiro) -> os termos submetidos são conferidos
    contra o preço vigente. Divergência ⇒ REJEITADO.

Deduplica por `event_id`. Isso não é zelo: é obrigação declarada no contrato
AsyncAPI, porque o relay entrega at-least-once (ADR-0002).
"""
import json

from . import catalogo, pedidos


class Validador:
    def __init__(self, tolerancia_centavos: int = 0):
        self.tolerancia_centavos = tolerancia_centavos
        self.vistos: set[str] = set()
        self.processados = 0
        self.ignorados_por_duplicata = 0
        self.rejeitados: list[str] = []

    def __call__(self, evento: dict) -> None:
        if evento["tipo"] != "PedidoRecebido":
            return

        if evento["event_id"] in self.vistos:
            self.ignorados_por_duplicata += 1
            return
        self.vistos.add(evento["event_id"])

        payload = json.loads(evento["payload"])
        pedido_id = payload["pedido_id"]
        motivo = self._conferir(pedido_id, cotado=payload.get("cotado", False))

        if motivo is None:
            pedidos.confirmar(pedido_id)
        else:
            self.rejeitados.append(f"{pedido_id}: {motivo}")
            pedidos.rejeitar(pedido_id)
        self.processados += 1

    def _conferir(self, pedido_id: str, cotado: bool) -> str | None:
        """Devolve o motivo da rejeição, ou None se os termos conferem."""
        pedido = pedidos.obter(pedido_id)
        if pedido is None:
            return "pedido inexistente"

        for item in pedido["itens"]:
            try:
                produto = catalogo.obter(item["sku"])
            except KeyError:
                return f"SKU {item['sku']} não existe no Catálogo"
            except catalogo.CatalogoIndisponivel:
                # Catálogo fora: a validação não conclui e o pedido PERMANECE
                # em RECEBIDO. Não rejeitamos por indisponibilidade nossa —
                # a reconciliação assume (P1-15).
                raise

            if cotado:
                # Cotação assinada é compromisso: o preço é honrado.
                continue

            divergencia = abs(produto["preco_unitario"] - item["preco_unitario"])
            if divergencia > self.tolerancia_centavos:
                return (
                    f"preço divergente em {item['sku']}: "
                    f"submetido {item['preco_unitario']}, vigente {produto['preco_unitario']}"
                )
        return None
