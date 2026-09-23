"""Cotação assinada — ADR-0007.

Capacidade do próprio Pedidos, não de um contexto separado: `POST /v2/quotes`
lê o Catálogo e devolve os termos assinados com validade. A criação valida a
assinatura LOCALMENTE — é isto que tira a leitura do Catálogo do caminho
crítico e mantém `CTX-04` alcançável.

O canal de parceiro não cota: submete os termos do sistema dele, sem
assinatura. Esses são conferidos contra o Catálogo na validação assíncrona.
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
    """Cotação: lê o Catálogo em LOTE e congela os termos, assinados.

    Validade de 30 min: curta demais aumenta recotação, longa demais aumenta
    o risco de honrar preço defasado. Precisa de confirmação do negócio.
    """
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
    """Validação LOCAL. Nenhuma chamada de saída (ADR-0007).

    Termos SEM assinatura são aceitos: é o canal de parceiro, que submete os
    termos do sistema dele. A conferência contra o Catálogo acontece depois,
    de forma assíncrona. Termos COM assinatura precisam conferir e estar
    dentro da validade.
    """
    if not isinstance(oferta, dict) or "itens" not in oferta:
        raise OfertaInvalida("termos ausentes ou malformados")

    if "assinatura" not in oferta:
        return  # canal de parceiro: conferido na validação assíncrona

    if not hmac.compare_digest(_assinar(oferta), oferta["assinatura"]):
        raise OfertaInvalida("assinatura não confere")
    if float(oferta.get("expira_em", 0)) < time.time():
        raise OfertaExpirada("cotação expirada — recotar")
