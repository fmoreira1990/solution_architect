"""API HTTP — duas versões com semânticas diferentes (ADR-0004).

  /v1/orders  fachada SÍNCRONA: espera a validação e devolve CONFIRMADO.
              Preserva a semântica que os consumidores atuais assumem.
  /v2/orders  aceitação ASSÍNCRONA: devolve RECEBIDO (ADR-0007).

O mesmo JSON sai das duas. A diferença é semântica — e é exatamente o que
nenhum diff de schema detecta, razão de existir o teste de compatibilidade.
"""
import uuid

from fastapi import FastAPI, Header, HTTPException, Response

from . import oferta, pedidos, relay
from .broker import BrokerStub
from .validador import Validador


def criar_app(broker=None, validador=None) -> FastAPI:
    app = FastAPI(title="Pedidos — fatia executável", version="2.0.0")

    app.state.broker = broker or BrokerStub()
    app.state.validador = validador or Validador()
    app.state.broker.assinar(app.state.validador)

    def _aceitar(chamador: str, chave: str, corpo: dict):
        try:
            return pedidos.aceitar(chamador, chave, corpo)
        except oferta.OfertaExpirada as e:
            raise HTTPException(422, {"erro": "oferta_expirada", "detalhe": str(e)})
        except oferta.OfertaInvalida as e:
            raise HTTPException(422, {"erro": "oferta_invalida", "detalhe": str(e)})
        except pedidos.ConflitoIdempotencia as e:
            raise HTTPException(409, {"erro": "chave_idempotencia_conflitante", "detalhe": str(e)})

    # ---------------------------------------------------------------- v2
    @app.post("/v2/orders", status_code=201)
    def criar_v2(
        corpo: dict,
        response: Response,
        idempotency_key: str = Header(..., alias="Idempotency-Key"),
        chamador: str = Header("web", alias="X-Chamador"),
    ):
        """Idempotency-Key é OBRIGATÓRIA em v2 (ADR-0001)."""
        pedido, replay = _aceitar(chamador, idempotency_key, corpo)
        if replay:
            response.status_code = 200
            response.headers["Idempotency-Replayed"] = "true"
        return pedido

    @app.get("/v2/orders/{pedido_id}")
    def consultar_v2(pedido_id: str):
        return _consultar(pedido_id)

    # ---------------------------------------------------------------- v1
    @app.post("/v1/orders", status_code=201)
    def criar_v1(
        corpo: dict,
        response: Response,
        idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
        chamador: str = Header("legado", alias="X-Chamador"),
    ):
        """Fachada síncrona (ADR-0004).

        Idempotency-Key é OPCIONAL aqui: torná-la obrigatória seria breaking
        change pela lista fechada da ADR-0004.
        """
        chave = idempotency_key or str(uuid.uuid4())
        pedido, replay = _aceitar(chamador, chave, corpo)

        if not replay:
            # A fachada espera o desfecho antes de responder.
            relay.tick(app.state.broker)
            app.state.broker.entregar_pendentes()

        if replay:
            response.status_code = 200
            response.headers["Idempotency-Replayed"] = "true"

        return pedidos.obter(pedido["id"])

    @app.get("/v1/orders/{pedido_id}")
    def consultar_v1(pedido_id: str):
        return _consultar(pedido_id)

    # -------------------------------------------------------------- comum
    def _consultar(pedido_id: str):
        pedido = pedidos.obter(pedido_id)
        if pedido is None:
            raise HTTPException(404, {"erro": "pedido_nao_encontrado"})
        return pedido

    @app.get("/saude")
    def saude():
        return {"ok": True, "pendentes_no_outbox": relay.pendentes()}

    return app
