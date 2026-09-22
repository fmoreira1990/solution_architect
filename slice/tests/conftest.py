import socket
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import api, catalogo, db  # noqa: E402
from app.broker import BrokerStub  # noqa: E402
from app.validador import Validador  # noqa: E402


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session", autouse=True)
def schema():
    db.criar_schema()


@pytest.fixture(autouse=True)
def base_limpa(schema):
    db.limpar()
    catalogo.carregar()
    yield
    db.limpar()


@pytest.fixture
def broker():
    return BrokerStub()


@pytest.fixture
def validador():
    return Validador()


@pytest.fixture
def servidor(broker, validador):
    """Sobe a aplicação de verdade, em HTTP.

    Endpoints síncronos do FastAPI rodam em threadpool, então o teste de
    concorrência exercita escrita paralela real no Postgres — não uma
    simulação em processo único.
    """
    app = api.criar_app(broker=broker, validador=validador)
    porta = _porta_livre()
    config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{porta}"
    limite = time.time() + 20
    while time.time() < limite:
        try:
            httpx.get(f"{url}/saude", timeout=1)
            break
        except Exception:
            time.sleep(0.05)
    else:  # pragma: no cover
        raise RuntimeError("servidor não subiu")

    yield url

    server.should_exit = True
    thread.join(timeout=5)


def contar(tabela: str, onde: str = "", params=()) -> int:
    sql = f"SELECT COUNT(*) AS n FROM {tabela}"
    if onde:
        sql += f" WHERE {onde}"
    with db.conectar() as con:
        return con.execute(sql, params).fetchone()["n"]
