"""Convivência e rollout progressivo — CTX-11, ADR-0001, ADR-0002.

A restrição é "primeira melhoria em produção em 30 dias, **sem janela de
indisponibilidade**". Isso obriga os dois caminhos a coexistirem, com
roteamento por flag e rollback sem deploy.

Estes testes provam três coisas:
  1. o rollout distribui conforme o percentual, de forma determinística
  2. o rollback reverte o roteamento sem deploy e sem perder pedido
  3. o caminho legado REALMENTE tem os defeitos que a onda 30 corrige
     — sem isso, não há o que comparar
"""
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import flag, legado, pedidos  # noqa: E402
from conftest import contar  # noqa: E402
from test_idempotencia import corpo_pedido  # noqa: E402


# --------------------------------------------------------------- roteamento

def test_flag_em_zero_roteia_tudo_para_o_legado(servidor):
    flag.definir(0)
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    # O legado não grava chave de idempotência nem outbox.
    assert contar("pedido") == 1
    assert contar("idempotency_key") == 0
    assert contar("outbox") == 0


def test_flag_em_cem_roteia_tudo_para_o_caminho_novo(servidor):
    flag.definir(100)
    r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert r.status_code == 201
    assert contar("idempotency_key") == 1
    assert contar("outbox") == 1


def test_roteamento_e_deterministico_pela_chave():
    """A propriedade que não é óbvia — e sem a qual a flag introduz o bug
    que a ADR-0001 elimina.

    Se o roteamento fosse aleatório, um retry poderia cair no legado e criar
    duplicata **apesar** da idempotência do caminho novo.
    """
    flag.definir(50)
    chave = str(uuid.uuid4())
    decisoes = {flag.usa_caminho_novo(chave) for _ in range(500)}
    assert len(decisoes) == 1, "a mesma chave trocou de caminho entre chamadas"


def test_rollout_progressivo_distribui_conforme_o_percentual():
    chaves = [str(uuid.uuid4()) for _ in range(400)]

    flag.definir(0)
    assert sum(flag.usa_caminho_novo(k) for k in chaves) == 0

    flag.definir(100)
    assert sum(flag.usa_caminho_novo(k) for k in chaves) == 400

    flag.definir(50)
    metade = sum(flag.usa_caminho_novo(k) for k in chaves)
    assert 140 < metade < 260, f"distribuição fora do esperado: {metade}/400"

    flag.definir(10)
    dez = sum(flag.usa_caminho_novo(k) for k in chaves)
    assert dez < metade, "10% roteou mais que 50%"


# ----------------------------------------------------------------- rollback

def test_rollback_desliga_a_flag_sem_deploy_e_sem_perder_pedido(servidor):
    """Critério do gate G30: rollback exercitado, por flag, sem deploy."""
    flag.definir(100)
    novo = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(cliente="cliente-A"),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    id_novo = novo.json()["id"]

    flag.desligar()  # rollback — nenhum deploy, nenhuma migração reversa

    legado_r = httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(cliente="cliente-B"),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert legado_r.status_code == 201

    # O pedido criado antes do rollback continua legível e íntegro.
    consulta = httpx.get(
        f"{servidor}/v2/orders/{id_novo}", headers={"X-Cliente-Id": "cliente-A"}
    )
    assert consulta.status_code == 200
    assert consulta.json()["itens"][0]["preco_unitario"] == 349900
    assert contar("pedido") == 2


def test_rollback_nao_apaga_o_outbox_ja_gravado(servidor):
    """Reverter o roteamento não pode descartar evento pendente."""
    flag.definir(100)
    httpx.post(
        f"{servidor}/v2/orders",
        json=corpo_pedido(),
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    pendentes_antes = contar("outbox", "publicado_em IS NULL")

    flag.desligar()

    assert contar("outbox", "publicado_em IS NULL") == pendentes_antes == 1


# ------------------------------------ o contraste: o legado tem os defeitos

def test_legado_duplica_pedido_em_retry_concorrente(servidor):
    """O problema que a onda 30 existe para resolver.

    Mesmo cenário do critério crítico — 20 requisições com a MESMA chave —
    mas roteado para o legado. Sem chave de idempotência, cada uma cria um
    pedido. É o contraste que dá sentido ao teste do caminho novo.
    """
    flag.definir(0)
    corpo = corpo_pedido()
    h = {"Idempotency-Key": str(uuid.uuid4())}

    with ThreadPoolExecutor(max_workers=20) as pool:
        respostas = list(pool.map(
            lambda _: httpx.post(f"{servidor}/v2/orders", json=corpo, headers=h, timeout=30),
            range(20),
        ))

    assert all(r.status_code == 201 for r in respostas)
    assert contar("pedido") == 20, "o legado deveria duplicar — o contraste se perdeu"
    assert len({r.json()["id"] for r in respostas}) == 20


def test_legado_perde_o_evento_se_a_publicacao_falha(broker):
    """O segundo defeito de CTX-07: publicação fora da transação."""
    corpo = corpo_pedido()

    with pytest.raises(legado.FalhaNaPublicacao):
        legado.aceitar(corpo, broker, falhar_ao_publicar=True)

    # O pedido existe. O evento não existe em lugar nenhum.
    assert contar("pedido") == 1
    assert contar("outbox") == 0
    assert broker.publicados == []


def test_caminho_novo_nao_perde_o_evento_no_mesmo_cenario(broker):
    """Mesmo cenário, caminho novo: o evento sobrevive no outbox."""
    from app import relay

    pedidos.aceitar("web", str(uuid.uuid4()), corpo_pedido())

    assert contar("outbox", "publicado_em IS NULL") == 1
    with pytest.raises(relay.CrashSimulado):
        relay.tick(broker, falhar_antes_de_marcar=True)

    # Continua pendente — será republicado. Nada se perdeu.
    assert contar("outbox", "publicado_em IS NULL") == 1
    assert relay.tick(broker) == 1


def test_saude_expoe_o_percentual_de_rollout(servidor):
    """Operação precisa ver em que degrau o rollout está."""
    flag.definir(37)
    r = httpx.get(f"{servidor}/saude")
    assert r.json()["rollout_percentual"] == 37
