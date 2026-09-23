#!/usr/bin/env python
"""Conferência final da entrega.

Verifica o que é verificável por máquina, para que a revisão humana sobre
apenas o que exige julgamento. Procura inconsistência, não confirmação.

    python tools/conferir-entrega.py
"""
import io
import re
import subprocess
import sys
from pathlib import Path

# Mesmo cuidado do prova.py: o console do Windows usa cp1252 e quebraria
# ao imprimir os símbolos do relatório — escondendo justamente o resultado.
for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent.parent
problemas: list[str] = []
avisos: list[str] = []


def ler(p: Path) -> str:
    return io.open(p, encoding="utf-8").read()


def docs_md() -> list[Path]:
    return sorted(RAIZ.joinpath("docs").rglob("*.md")) + [RAIZ / "README.md"]


def secao(titulo: str) -> None:
    print(f"\n{titulo}")
    print("-" * len(titulo))


# ───────────────────────────────── 1. realidade: quanto de cada coisa existe
secao("1. Inventário real")

n_adrs = len(list(RAIZ.joinpath("docs/decisions").glob("ADR-*.md")))
n_docs = len(list(RAIZ.joinpath("docs").rglob("*.md")))
n_diagramas = sum(len(re.findall(r"```mermaid", ler(p))) for p in RAIZ.joinpath("docs").rglob("*.md"))
n_funcoes = sum(
    len(re.findall(r"^def (test_\w+)", ler(p), re.M))
    for p in RAIZ.joinpath("slice/tests").glob("test_*.py")
)

saida = subprocess.run(
    [sys.executable, "-m", "pytest", "tests", "-q", "--collect-only", "-p", "no:cacheprovider"],
    cwd=str(RAIZ / "slice"), capture_output=True, text=True,
)
m = re.search(r"(\d+) tests? collected", saida.stdout)
n_testes = int(m.group(1)) if m else 0

print(f"  ADRs:             {n_adrs}")
print(f"  documentos:       {n_docs}")
print(f"  diagramas:        {n_diagramas}")
print(f"  funções de teste: {n_funcoes}")
print(f"  testes coletados: {n_testes}")

if n_adrs < 4:
    problemas.append(f"P1-17 exige ao menos 4 ADRs; há {n_adrs}")
if n_testes == 0:
    problemas.append("pytest não coletou nenhum teste")


# ───────────────────────────────── 2. números citados batem com a realidade
secao("2. Números citados nos documentos")

# Só compara números que AFIRMAM O TOTAL. "10 testes cobrem o rollout" é
# contagem local e legítima; compará-la ao total geraria falso positivo — e
# verificador que grita sem motivo treina a pessoa a ignorá-lo.
esperado = {
    r"·\s*(\d+) testes": n_testes,
    r"\*\*(\d+) testes\*\*": n_testes,
    r"(\d+) testes em PostgreSQL": n_testes,
    r"(\d+) testes no total": n_testes,
    r"`slice/` com (\d+) testes": n_testes,
    r"(\d+) blocos Mermaid": n_diagramas,
    r"(\d+) documentos é": n_docs,
    r"\*\*(\d+) ADRs\*\*": n_adrs,
    r"(\d+) diagramas válidos": n_diagramas,
    r"(\d+) diagramas validados": n_diagramas,
    r"\*\*(\d+) diagramas\*\*": n_diagramas,
    r"\*\*(\d+) documentos\*\*": n_docs,
    r"os (\d+) documentos": n_docs,
}
# --corrigir atualiza os números em vez de só apontar. Existe porque o
# total de testes muda a cada documento novo — as fitness functions de
# governança são parametrizadas por documento —, e corrigir à mão em dez
# arquivos é como a inconsistência nasce.
CORRIGIR = "--corrigir" in sys.argv
corrigidos = 0

for p in docs_md():
    texto = ler(p)
    original = texto
    rel = p.relative_to(RAIZ)
    for padrao, valor in esperado.items():
        for achado in re.findall(padrao, texto):
            if int(achado) == valor:
                continue
            if CORRIGIR:
                texto = re.sub(
                    padrao,
                    lambda m: m.group(0).replace(m.group(1), str(valor), 1),
                    texto,
                )
                corrigidos += 1
            else:
                problemas.append(f"{rel}: cita {achado} onde a realidade é {valor} ({padrao})")
    if CORRIGIR and texto != original:
        io.open(p, "w", encoding="utf-8", newline="\n").write(texto)

# Saída do pytest citada em documento: "passed" + "skipped" é que soma o
# total. Exigir "N passed" igual ao coletado obrigava a citar uma saída que
# o pytest nunca imprime — o teste de exceção vencida é pulado sem exceção.
for p in docs_md():
    for passou, pulou in re.findall(r"(\d+) passed(?:, (\d+) skipped)?", ler(p)):
        total = int(passou) + int(pulou or 0)
        if total != n_testes:
            problemas.append(
                f"{p.relative_to(RAIZ)}: saída citada soma {total} onde a realidade é {n_testes}"
            )

if CORRIGIR:
    print(f"  {corrigidos} número(s) corrigido(s)")
else:
    print(f"  {'inconsistências: ' + str(len(problemas)) if problemas else 'todos conferem'}")


# ───────────────────────────────── 3. links internos resolvem
secao("3. Links internos")

quebrados = 0
for p in docs_md():
    for alvo in re.findall(r"\]\((?!https?:)([^)#]+)", ler(p)):
        destino = (p.parent / alvo).resolve()
        if not destino.exists():
            problemas.append(f"{p.relative_to(RAIZ)}: link quebrado -> {alvo}")
            quebrados += 1
print(f"  {'quebrados: ' + str(quebrados) if quebrados else 'todos resolvem'}")


# ───────────────────────────────── 4. caminhos e testes citados existem
secao("4. Referências citadas em crase")

testes_reais = set()
for arq in RAIZ.joinpath("slice/tests").glob("test_*.py"):
    testes_reais.update(re.findall(r"^def (test_\w+)", ler(arq), re.M))

for p in docs_md():
    texto, rel = ler(p), p.relative_to(RAIZ)
    for nome in set(re.findall(r"`(test_\w+)`", texto)):
        if nome not in testes_reais:
            problemas.append(f"{rel}: cita teste inexistente `{nome}`")
    for caminho in set(re.findall(r"`((?:docs|contracts|slice|tools|\.github)/[\w./-]+\.(?:md|yaml|yml|py|json|sql|mjs))`", texto)):
        if not (RAIZ / caminho).exists():
            problemas.append(f"{rel}: cita arquivo inexistente `{caminho}`")
print(f"  {len(testes_reais)} testes reais; referências conferidas")


# ───────────────────────────────── 5. cabeçalho canônico
secao("5. Cabeçalho canônico")

isentos = {"CONVENCOES.md", "README.md"}
faltando = 0
for p in docs_md():
    if p.name in isentos:
        continue
    texto = ler(p)
    for campo in ("**Escopo deste documento:**", "**Fontes:**", "**Data:**"):
        if campo not in texto:
            problemas.append(f"{p.relative_to(RAIZ)}: sem {campo}")
            faltando += 1
print(f"  {'faltas: ' + str(faltando) if faltando else 'todos completos'}")


# ───────────────────────────────── 6. encoding
secao("6. Codificação")

mojibake = 0
for p in list(RAIZ.rglob("*.md")) + list(RAIZ.rglob("*.py")) + list(RAIZ.rglob("*.yaml")):
    if any(x in p.parts for x in (".git", "node_modules", "__pycache__", "contexto")):
        continue
    if p.name == "conferir-entrega.py":
        continue  # contém os próprios marcadores de detecção
    try:
        t = ler(p)
    except UnicodeDecodeError:
        problemas.append(f"{p.relative_to(RAIZ)}: não é UTF-8 válido")
        continue
    for marca in ("Ã§", "Ã£", "Ã©", "Ãª", "Ã­", "Ã³", "Ãº", "\ufffd"):
        if marca in t:
            problemas.append(f"{p.relative_to(RAIZ)}: codificação corrompida ({marca!r})")
            mojibake += 1
            break
print(f"  {'corrompidos: ' + str(mojibake) if mojibake else 'todos limpos'}")


# ───────────────────────────────── 7. confidencialidade no histórico inteiro
secao("7. Confidencialidade — histórico completo, não só HEAD")

git = "C:/Program Files/Git/cmd/git.exe"
if not Path(git).exists():
    git = "git"
try:
    todos = subprocess.run(
        [git, "log", "--all", "--pretty=format:", "--name-only", "--diff-filter=A"],
        cwd=str(RAIZ), capture_output=True, text=True, check=True,
    ).stdout.split("\n")
    suspeitos = {
        a.strip() for a in todos
        if a.strip() and (
            a.startswith("contexto/") or a.lower().endswith(".pdf")
            or a.startswith(("RETOMAR-AQUI", "DIARIO-IA", "ROTEIRO-EXECUCAO", "TESTE-MERMAID", "diagramas.html"))
        )
    }
    if suspeitos:
        problemas.append(f"arquivo confidencial ou interno no histórico: {sorted(suspeitos)}")
    print(f"  {len(suspeitos) or 'nenhum'} arquivo suspeito em todo o histórico")
except Exception as e:  # pragma: no cover
    avisos.append(f"não foi possível varrer o histórico: {e}")
    print("  não verificado")

# menção textual à classificação
for p in docs_md():
    if re.search(r"Confidencial\s*·\s*Stefanini", ler(p)):
        problemas.append(f"{p.relative_to(RAIZ)}: reproduz a classificação do material de referência")


# ───────────────────────────────── 8. ADRs completas
secao("8. Formato das ADRs")

incompletas = 0
for adr in sorted(RAIZ.joinpath("docs/decisions").glob("ADR-*.md")):
    t = ler(adr)
    for s in ("## Contexto", "## Decisão", "## Alternativas consideradas",
              "## Trade-offs", "## Gatilho de revisão", "## Enforcement"):
        if s not in t:
            problemas.append(f"{adr.name}: sem seção {s}")
            incompletas += 1
    if len(re.findall(r"❌\s*Rejeitada", t)) < 2:
        problemas.append(f"{adr.name}: menos de 2 alternativas rejeitadas")
        incompletas += 1
print(f"  {'problemas: ' + str(incompletas) if incompletas else f'{n_adrs} ADRs completas'}")


# ───────────────────────────────── 9. estado final, não histórico de edição
secao("9. Narrativa de edição")

# O entregável descreve o estado final. Texto riscado e "fechado em <data>"
# contam como o arquivo foi editado, não como o sistema é. Ficam de fora a
# história do sistema (a seção superseded da ADR-0003, prática de ADR) e o
# registro de IA, que o §2.5.1 exige com as decisões rejeitadas.
PERMITIDOS = ("docs/ai-context/", "docs/decisions/ADR-0003-")
MARCA_DATADA = re.compile(r"(Fechad|Corrigid|Implementad|Removid|Resolvid|Testad)[oa]s? em 20\d\d-")
VERSAO_ANTERIOR = re.compile(r"vers[ãa]o anterior de(ste|sta)|premissa anterior", re.I)
narrativa = 0
for p in docs_md():
    rel = p.relative_to(RAIZ).as_posix()
    if rel.startswith(PERMITIDOS):
        continue
    for n, linha in enumerate(ler(p).splitlines(), 1):
        if "~~" in linha or MARCA_DATADA.search(linha) or VERSAO_ANTERIOR.search(linha):
            problemas.append(f"{rel}:{n}: narrativa de edição — {linha.strip()[:70]}")
            narrativa += 1
print(f"  {'ocorrências: ' + str(narrativa) if narrativa else 'nenhuma'}")


# ───────────────────────────────── resultado
print("\n" + "=" * 62)
if problemas:
    print(f"{len(problemas)} PROBLEMA(S):\n")
    for x in problemas:
        print(f"  ✗ {x}")
else:
    print("Nenhum problema encontrado.")
if avisos:
    print("\nAvisos:")
    for x in avisos:
        print(f"  ! {x}")
print("=" * 62)

sys.exit(1 if problemas else 0)
