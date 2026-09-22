"""Catálogo — existe apenas para PROVAR que Pedidos não depende dele.

Dois usos nos testes:
  - alterar_preco(): muda o preço depois do pedido; o snapshot não muda (ADR-0003)
  - definir_disponibilidade(False): simula o Catálogo fora do ar; consultar
    pedido continua funcionando (enforcement primário da ADR-0003)
"""
import json
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_produtos: dict = {}
_disponivel = True
_versao = "2026-09-22T14:03:00Z"


class CatalogoIndisponivel(Exception):
    pass


def carregar(caminho: str | None = None) -> None:
    global _produtos, _disponivel
    arquivo = Path(caminho) if caminho else _RAIZ / "seed" / "catalogo.json"
    _produtos = {p["sku"]: p for p in json.loads(arquivo.read_text(encoding="utf-8"))}
    _disponivel = True


def obter(sku: str) -> dict:
    if not _disponivel:
        raise CatalogoIndisponivel("Catálogo fora do ar")
    return dict(_produtos[sku])


def alterar_preco(sku: str, centavos: int) -> None:
    global _versao
    _produtos[sku]["preco_unitario"] = centavos
    _versao = _versao[:-1] + "-alterado"


def definir_disponibilidade(flag: bool) -> None:
    global _disponivel
    _disponivel = flag


def versao() -> str:
    return _versao
