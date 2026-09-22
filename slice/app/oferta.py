"""Oferta assinada — ADR-0007.

O preço é estabelecido no carrinho e CARREGADO pela criação, não relido.
É isto que remove a leitura do Catálogo do caminho crítico.
"""
import hashlib
import hmac
import json
import time

from . import catalogo

# Em produção seria chave gerenciada; aqui é fixa e sintética, de propósito.
_SEGREDO = b"prova-stefanini-oferta-hmac"


class OfertaInvalida(Exception):
    pass


class OfertaExpirada(Exception):
    pass


def _assinar(corpo: dict) -> str:
    base = json.dumps(
        {k: v for k, v in corpo.items() if k != "assinatura"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(_SEGREDO, base, hashlib.sha256).hexdigest()


def emitir(skus_e_quantidades: list[tuple[str, float]], validade_segundos: int = 1800) -> dict:
    """Papel do Carrinho: cota o preço no Catálogo e congela os termos."""
    itens = []
    for sku, quantidade in skus_e_quantidades:
        p = catalogo.obter(sku)
        itens.append(
            {
                "sku": p["sku"],
                "quantidade": quantidade,
                "descricao": p["descricao"],
                "preco_unitario": p["preco_unitario"],
                "moeda": p["moeda"],
                "unidade": p["unidade"],
                "peso_gramas": p["peso_gramas"],
                "promocao_id": p.get("promocao_id"),
            }
        )
    corpo = {
        "itens": itens,
        "catalogo_versao": catalogo.versao(),
        "expira_em": time.time() + validade_segundos,
    }
    corpo["assinatura"] = _assinar(corpo)
    return corpo


def validar(oferta: dict) -> None:
    """Validação LOCAL: assinatura e validade. Nenhuma chamada de saída."""
    if not isinstance(oferta, dict) or "assinatura" not in oferta:
        raise OfertaInvalida("oferta ausente ou malformada")
    if not hmac.compare_digest(_assinar(oferta), oferta["assinatura"]):
        raise OfertaInvalida("assinatura não confere")
    if float(oferta.get("expira_em", 0)) < time.time():
        raise OfertaExpirada("oferta expirada — recotar")
