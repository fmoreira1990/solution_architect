"""Broker stub — registra publicações em memória.

Escolha deliberada de escopo: a decisão crítica sendo provada é
"pedido e evento nunca divergem", que vive na TRANSAÇÃO e no RELAY,
não no transporte. Um broker real (Kafka, SNS/SQS) não tornaria a prova
mais forte e exigiria infraestrutura que `python prova.py` não teria.

O stub entrega TUDO que foi publicado, inclusive duplicatas: quem deduplica
é o consumidor, conforme a ADR-0002.
"""


class BrokerStub:
    def __init__(self):
        self.publicados: list[dict] = []
        self._assinantes: list = []
        self._entregues = 0

    def publicar(self, evento: dict) -> None:
        """Chamado pelo relay. Pode receber o mesmo event_id mais de uma vez
        se o relay cair entre publicar e marcar — isso é at-least-once."""
        self.publicados.append(evento)

    def assinar(self, funcao) -> None:
        self._assinantes.append(funcao)

    def entregar_pendentes(self) -> int:
        """Simula o consumidor recebendo o que já foi publicado."""
        entregues = 0
        while self._entregues < len(self.publicados):
            evento = self.publicados[self._entregues]
            self._entregues += 1
            for assinante in self._assinantes:
                assinante(evento)
            entregues += 1
        return entregues

    def ids_publicados(self) -> list[str]:
        return [e["event_id"] for e in self.publicados]

    def publicacoes_de(self, tipo: str) -> list[dict]:
        return [e for e in self.publicados if e["tipo"] == tipo]
