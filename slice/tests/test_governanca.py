"""Fitness functions de governança — D-03.

Transformam as regras de `docs/CONVENCOES.md` em verificação executável.
Regra que não quebra o build é sugestão.
"""
import re
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parent.parent.parent
DOCS = RAIZ / "docs"
ADRS = DOCS / "decisions"
EXCECOES = DOCS / "governance" / "excecoes"

# Documentos que são índice ou meta, e não seguem o cabeçalho canônico.
ISENTOS = {"CONVENCOES.md"}


def docs_md():
    return [p for p in DOCS.rglob("*.md") if p.name not in ISENTOS]


# ------------------------------------------------ cabeçalho canônico (§2)

@pytest.mark.parametrize("doc", docs_md(), ids=lambda p: str(p.relative_to(DOCS)))
def test_documento_declara_escopo_fontes_e_data(doc):
    """Todo artefato diz o que cobre, de onde veio e quando.

    O campo Fontes é o que torna a cadeia auditável: nenhum documento
    aparece sem dizer de onde veio.
    """
    texto = doc.read_text(encoding="utf-8")
    assert texto.lstrip().startswith("# "), "sem H1"
    for campo in ("**Escopo deste documento:**", "**Fontes:**", "**Data:**"):
        assert campo in texto, f"cabeçalho canônico sem {campo}"


# -------------------------------------------------------- ADRs (§4, Q2–Q5)

def adrs():
    return sorted(ADRS.glob("ADR-*.md"))


def test_existem_pelo_menos_quatro_adrs():
    """P1-17 exige no mínimo quatro."""
    assert len(adrs()) >= 4, f"apenas {len(adrs())} ADRs"


@pytest.mark.parametrize("adr", adrs(), ids=lambda p: p.stem)
def test_adr_tem_as_secoes_obrigatorias(adr):
    texto = adr.read_text(encoding="utf-8")
    for secao in ("## Contexto", "## Decisão", "## Alternativas consideradas",
                  "## Trade-offs", "## Gatilho de revisão", "## Enforcement"):
        assert secao in texto, f"seção ausente: {secao}"
    assert "**Status:**" in texto


@pytest.mark.parametrize("adr", adrs(), ids=lambda p: p.stem)
def test_adr_rejeita_ao_menos_duas_alternativas(adr):
    """Q2 — ADR sem alternativa descartada com motivo não é decisão."""
    texto = adr.read_text(encoding="utf-8")
    rejeitadas = len(re.findall(r"❌\s*Rejeitada", texto))
    assert rejeitadas >= 2, f"apenas {rejeitadas} alternativas rejeitadas"
    assert "✅" in texto, "nenhuma alternativa marcada como escolhida"


@pytest.mark.parametrize("adr", adrs(), ids=lambda p: p.stem)
def test_adr_referenciada_existe(adr):
    """Integridade de referências cruzadas entre ADRs."""
    texto = adr.read_text(encoding="utf-8")
    existentes = {p.stem.split("-")[1] for p in adrs()}
    for numero in set(re.findall(r"ADR-(\d{4})", texto)):
        assert numero in existentes, f"referencia ADR-{numero}, que não existe"


# ------------------------------------------------------- exceções técnicas

def test_nenhuma_excecao_tecnica_vencida():
    """Exceção vencida quebra o build.

    Sem isso o processo de waiver vira formulário morto — que é como a
    maioria deles termina.
    """
    if not EXCECOES.exists():
        pytest.skip("nenhuma exceção registrada")

    hoje = date.today()
    vencidas = []
    for arq in EXCECOES.glob("EXC-*.md"):
        texto = arq.read_text(encoding="utf-8")
        if "**Status:** Ativa" not in texto:
            continue
        m = re.search(r"\*\*Válida até:\*\*\s*(\d{4}-\d{2}-\d{2})", texto)
        assert m, f"{arq.name}: exceção ativa sem data de validade"
        if date.fromisoformat(m.group(1)) < hoje:
            vencidas.append(f"{arq.name} (venceu em {m.group(1)})")

    assert not vencidas, "exceções técnicas vencidas: " + ", ".join(vencidas)


# ------------------------------------------------------------ contratos

def test_todo_contrato_citado_existe():
    """Documento que aponta para contracts/ não pode apontar para o vazio."""
    faltando = []
    for doc in docs_md():
        for ref in re.findall(r"`(contracts/[\w./-]+\.(?:yaml|json))`", doc.read_text(encoding="utf-8")):
            if not (RAIZ / ref).exists():
                faltando.append(f"{doc.name} -> {ref}")
    assert not faltando, "referências quebradas: " + ", ".join(faltando)


def test_todo_teste_citado_na_documentacao_existe():
    """Documento que cita um teste como evidência precisa que ele exista.

    É o que impede a documentação de alegar cobertura inexistente.
    """
    testes = set()
    for arq in (RAIZ / "slice" / "tests").glob("test_*.py"):
        testes.update(re.findall(r"^def (test_\w+)", arq.read_text(encoding="utf-8"), re.M))

    citados = set()
    for doc in docs_md():
        citados.update(re.findall(r"`(test_\w+)`", doc.read_text(encoding="utf-8")))

    inexistentes = citados - testes
    assert not inexistentes, f"documentação cita testes que não existem: {sorted(inexistentes)}"
