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

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

URL_PADRAO = "postgresql://prova:prova@127.0.0.1:5432/prova_pedidos"


def titulo(texto: str) -> None:
    print(f"\n\033[1m{texto}\033[0m" if os.name != "nt" else f"\n{texto}")
    print("-" * len(texto))


def main() -> int:
    url = os.environ.get("PROVA_DATABASE_URL", URL_PADRAO)
    os.environ["PROVA_DATABASE_URL"] = url

    titulo("1/4  Dependências")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(RAIZ / "requirements.txt")]
    )
    print("ok")

    titulo("2/4  Banco")
    from app import db

    try:
        print(db.ping().split(",")[0])
    except Exception as e:
        print(f"ERRO ao conectar em {url}\n{e}\n")
        print("Crie o banco da prova com:")
        print('  psql -U postgres -c "CREATE USER prova WITH PASSWORD \'prova\';"')
        print('  psql -U postgres -c "CREATE DATABASE prova_pedidos OWNER prova;"')
        return 2
    db.criar_schema()
    print("schema aplicado")

    titulo("3/4  Dados sintéticos")
    from app import catalogo

    catalogo.carregar()
    print(f"catálogo sintético carregado — nenhum dado real, nenhuma PII")

    titulo("4/4  Prova")
    print("Demonstrando:")
    print("  [critério crítico] 20 requisições concorrentes com a mesma chave -> 1 pedido")
    print("  [critério crítico] consumidor v1 não quebra com a v2 no ar")
    print("  queda do relay entre publicar e marcar não perde evento")
    print("  snapshot sobrevive à mudança de preço e ao Catálogo fora do ar")
    print()

    return subprocess.call(
        [sys.executable, "-m", "pytest", str(RAIZ / "tests"), "-v", "--tb=short", "-p", "no:cacheprovider"],
        cwd=str(RAIZ),
    )


if __name__ == "__main__":
    sys.exit(main())
