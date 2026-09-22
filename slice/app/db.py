"""Acesso ao banco e controle de transação — PostgreSQL.

Postgres é o alvo declarado na ADR-0002. Duas coisas dependem dele:
  - FOR UPDATE SKIP LOCKED no relay do outbox;
  - escritas concorrentes de verdade em paralelo, o que torna o teste de
    idempotência concorrente genuinamente adversarial.
"""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

_RAIZ = Path(__file__).resolve().parent.parent

URL_PADRAO = "postgresql://prova:prova@127.0.0.1:5432/prova_pedidos"
_url = os.environ.get("PROVA_DATABASE_URL", URL_PADRAO)

# Violação de constraint — é ela que sustenta a idempotência (ADR-0001).
ErroIntegridade = psycopg.errors.IntegrityError


def url() -> str:
    return _url


def definir_url(nova: str) -> None:
    global _url
    _url = nova


def conectar():
    return psycopg.connect(_url, row_factory=dict_row, autocommit=True)


@contextmanager
def transacao():
    """Transação explícita.

    É dentro dela que pedido, itens, snapshot, chave de idempotência e outbox
    são gravados. ADR-0001, ADR-0002 e ADR-0003 dependem de ser UMA só.
    """
    con = psycopg.connect(_url, row_factory=dict_row, autocommit=False)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def criar_schema() -> None:
    sql = (_RAIZ / "schema_postgres.sql").read_text(encoding="utf-8")
    with psycopg.connect(_url, autocommit=True) as con:
        con.execute(sql)


def limpar() -> None:
    with psycopg.connect(_url, autocommit=True) as con:
        con.execute("TRUNCATE outbox, idempotency_key, pedido_item, pedido RESTART IDENTITY CASCADE")


def ping() -> str:
    with psycopg.connect(_url, row_factory=dict_row, autocommit=True) as con:
        return con.execute("SELECT version() AS v").fetchone()["v"]
