#!/usr/bin/env python
"""Comando único da prova — P2-10.

    python prova.py

Instala dependências, prepara o schema, gera dados sintéticos e executa
todos os testes, imprimindo o que cada bloco demonstra.
"""
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

URL_PADRAO = "postgresql://prova:prova@127.0.0.1:5432/prova_pedidos"

# O PostgreSQL devolve mensagens de erro no idioma do servidor, com acento.
# No Windows o console usa cp1252 e a impressão quebra com UnicodeEncodeError
# ANTES de mostrar a ajuda — o leitor veria um traceback e concluiria que a
# prova está quebrada. Forçar UTF-8 com substituição resolve.
for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * len(texto))


def _limpo(e: Exception) -> str:
    """Mensagem legível mesmo se o servidor responder em outro charset."""
    try:
        return str(e).encode("utf-8", "replace").decode("utf-8", "replace").strip()
    except Exception:  # pragma: no cover
        return repr(e)


def _diagnosticar(url: str, erro: Exception) -> None:
    """Diz o que fazer, não apenas o que falhou."""
    msg = _limpo(erro)
    alvo = urlparse(url)
    host, porta = alvo.hostname or "127.0.0.1", alvo.port or 5432
    usuario, banco = alvo.username or "prova", (alvo.path or "/prova_pedidos").lstrip("/")

    print(f"\nNão foi possível conectar ao PostgreSQL em {host}:{porta}")
    print(f"  banco:   {banco}")
    print(f"  usuário: {usuario}")
    print(f"\n  {msg}\n")

    baixo = msg.lower()
    if "does not exist" in baixo or "no existe" in baixo or "existe" in baixo and banco in msg:
        causa, comandos = (
            f'O banco "{banco}" não existe.',
            [f'psql -U postgres -c "CREATE DATABASE {banco} OWNER {usuario};"'],
        )
    elif "password" in baixo or "authent" in baixo or "senha" in baixo:
        causa, comandos = (
            f'O usuário "{usuario}" não existe ou a senha não confere.',
            [
                f"psql -U postgres -c \"CREATE USER {usuario} WITH PASSWORD 'prova';\"",
                f'psql -U postgres -c "CREATE DATABASE {banco} OWNER {usuario};"',
            ],
        )
    elif "timeout" in baixo or "refused" in baixo or "recusou" in baixo or "connection failed" in baixo:
        causa, comandos = (
            f"Nenhum PostgreSQL respondendo em {host}:{porta} — o serviço pode estar parado.",
            [
                "# Windows:  Get-Service postgresql*   →   Start-Service postgresql-x64-18",
                "# Linux:    sudo systemctl start postgresql",
                "# Docker:   docker run -d --name prova-pg -p 5432:5432 \\",
                "#             -e POSTGRES_USER=prova -e POSTGRES_PASSWORD=prova \\",
                "#             -e POSTGRES_DB=prova_pedidos postgres:18",
            ],
        )
    else:
        causa, comandos = (
            "Falha de conexão não classificada.",
            [
                f"psql -U postgres -c \"CREATE USER {usuario} WITH PASSWORD 'prova';\"",
                f'psql -U postgres -c "CREATE DATABASE {banco} OWNER {usuario};"',
            ],
        )

    print(f"  {causa}\n")
    print("  Para resolver:\n")
    for c in comandos:
        print(f"    {c}")
    print(
        "\n  Outro banco? Aponte para ele:\n"
        '    PROVA_DATABASE_URL="postgresql://usuario:senha@host:porta/banco" python prova.py'
    )
    print(
        "\n  Por que PostgreSQL e não SQLite: o teste de idempotência concorrente\n"
        "  precisa que 20 escritas disputem de verdade. Em SQLite elas serializam,\n"
        "  e o teste passaria por serialização do banco, não pela constraint.\n"
        "  Ver docs/decisions/ADR-0005-stack-da-fatia-executavel.md"
    )


def main() -> int:
    url = os.environ.get("PROVA_DATABASE_URL", URL_PADRAO)
    os.environ["PROVA_DATABASE_URL"] = url

    titulo("1/4  Dependências")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(RAIZ / "requirements.txt")]
        )
    except subprocess.CalledProcessError as e:
        print(f"Falha ao instalar dependências (código {e.returncode}).")
        print(f"Tente manualmente:  {sys.executable} -m pip install -r {RAIZ / 'requirements.txt'}")
        return 2
    print("ok")

    titulo("2/4  Banco")
    from app import db

    try:
        print(db.ping().split(",")[0])
    except Exception as e:
        _diagnosticar(url, e)
        return 2

    try:
        db.criar_schema()
    except Exception as e:
        print(f"Conectou, mas falhou ao criar o schema:\n  {_limpo(e)}")
        print(f"\n  O usuário precisa ser dono do banco, ou ter permissão de CREATE.")
        return 2
    print("schema aplicado")

    titulo("3/4  Dados sintéticos")
    from app import catalogo

    catalogo.carregar()
    print("catálogo sintético carregado — nenhum dado real, nenhuma PII")

    titulo("4/4  Prova")
    print("Demonstrando:")
    print("  [critério crítico] 20 requisições concorrentes com a mesma chave -> 1 pedido")
    print("  [critério crítico] consumidor v1 não quebra com a v2 no ar")
    print("  queda do relay entre publicar e marcar não perde evento")
    print("  snapshot sobrevive à mudança de preço e ao Catálogo fora do ar")
    print("  chave de idempotência de outro cliente não devolve pedido alheio")
    print()

    return subprocess.call(
        [
            sys.executable, "-m", "pytest", str(RAIZ / "tests"),
            "-v", "--tb=short", "-p", "no:cacheprovider",
        ],
        cwd=str(RAIZ),
    )


if __name__ == "__main__":
    sys.exit(main())
