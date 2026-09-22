"""Relay do outbox — ADR-0002.

A ordem entre publicar (①) e marcar (②) é a decisão, não detalhe:

    publicar -> marcar   queda no meio => republica  => at-least-once  ✅
    marcar -> publicar   queda no meio => perde      => at-most-once   ❌

Escolhemos duplicar em vez de perder. Por isso o consumidor deduplica
por event_id — obrigação declarada no contrato AsyncAPI.
"""
from datetime import datetime, timezone

from . import db


class CrashSimulado(Exception):
    """Injetada pelo teste entre ① e ②."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def tick(broker, limite: int = 100, falhar_antes_de_marcar: bool = False) -> int:
    """Publica os eventos pendentes. Retorna quantos foram marcados."""
    publicados = 0
    with db.transacao() as con:
        linhas = con.execute(
            """SELECT * FROM outbox
               WHERE publicado_em IS NULL
               ORDER BY id
               LIMIT %s
               FOR UPDATE SKIP LOCKED""",
            (limite,),
        ).fetchall()

        for linha in linhas:
            broker.publicar(dict(linha))  # ① publica

            if falhar_antes_de_marcar:
                # A transação será revertida: publicado_em continua NULL e o
                # evento sai de novo na retomada. Duplicado, nunca perdido.
                raise CrashSimulado("queda entre publicar e marcar")

            con.execute(  # ② marca
                "UPDATE outbox SET publicado_em = %s WHERE id = %s",
                (_agora(), linha["id"]),
            )
            publicados += 1

    return publicados


def pendentes() -> int:
    with db.conectar() as con:
        return con.execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE publicado_em IS NULL"
        ).fetchone()["n"]


def idade_do_mais_antigo_pendente() -> str | None:
    """SLI da ADR-0002.

    Relay parado é falha SILENCIOSA: o aceite continua respondendo 201 e os
    pedidos apenas demoram mais a confirmar. Esta é a única métrica que detecta.
    """
    with db.conectar() as con:
        linha = con.execute(
            "SELECT MIN(criado_em) AS mais_antigo FROM outbox WHERE publicado_em IS NULL"
        ).fetchone()
    return linha["mais_antigo"]
