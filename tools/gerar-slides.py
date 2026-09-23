#!/usr/bin/env python
"""Gera a apresentação em HTML a partir de docs/delivery/apresentacao/slides.md.

    python tools/gerar-slides.py

O Markdown continua sendo a única fonte. O HTML é derivado, mas versionado
para quem avalia poder baixar e abrir: gere de novo sempre que os slides
mudarem — o conferir-entrega.py quebra se os dois divergirem. Mermaid e marked vêm
de tools/node_modules (npm ci em tools/) e são embutidos no arquivo — a
apresentação abre sem internet, que é o que se quer na hora de gravar.
"""
import io
import json
import re
import sys
from pathlib import Path

for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "docs/delivery/apresentacao/slides.md"
DESTINO = RAIZ / "docs/delivery/apresentacao/slides.html"
MODULOS = RAIZ / "tools/node_modules"
LIBS = [MODULOS / "marked/lib/marked.umd.js", MODULOS / "mermaid/dist/mermaid.min.js"]


def ler(p: Path) -> str:
    return io.open(p, encoding="utf-8").read()


faltando = [p for p in LIBS if not p.exists()]
if faltando:
    print("Dependências ausentes. Rode antes:  cd tools && npm ci")
    for p in faltando:
        print(f"  falta {p.relative_to(RAIZ)}")
    sys.exit(1)

# Cada linha que é só "---" troca de slide. O primeiro bloco é o cabeçalho
# canônico do documento (slug, escopo, fontes): dele só o título vira slide.
blocos = re.split(r"^---[ \t]*$", ler(ORIGEM), flags=re.M)
cabecalho, slides = blocos[0], [b.strip() for b in blocos[1:] if b.strip()]
titulo = re.search(r"^# (.+)$", cabecalho, re.M).group(1)
titulo = re.sub(r"^Apresentação\s+—\s+", "", titulo)

html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title>
<style>
  :root {
    --fundo: #eef1f5; --papel: #ffffff; --texto: #1d2733; --suave: #5b6878;
    --linha: #d8dee6; --destaque: #1f5fa8; --destaque-fundo: #eaf2fb;
    --codigo-fundo: #f4f6f9;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: var(--fundo); overflow: hidden;
    font-family: "Segoe UI", system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif; }
  #palco { position: absolute; width: 1280px; height: 720px; left: 50%; top: 50%;
    transform-origin: center center; }
  .slide { position: absolute; inset: 0; background: var(--papel); color: var(--texto);
    border-radius: 10px; box-shadow: 0 10px 40px rgba(20, 30, 45, .14);
    padding: 52px 72px 60px; display: none; overflow: hidden; }
  .slide.ativo { display: block; }
  .conteudo { transform-origin: top left; }
  .capa { display: flex; flex-direction: column; justify-content: center; }
  .capa h1 { font-size: 54px; line-height: 1.15; margin: 0 0 18px; letter-spacing: -0.5px; }
  .capa p { font-size: 22px; color: var(--suave); margin: 0; }
  .capa .faixa { width: 90px; height: 6px; background: var(--destaque); border-radius: 3px; margin-bottom: 28px; }
  h2 { font-size: 34px; margin: 0 0 22px; color: var(--destaque); letter-spacing: -0.3px; }
  h3 { font-size: 30px; margin: 0 0 20px; color: var(--destaque); }
  p, li { font-size: 21px; line-height: 1.45; margin: 0 0 14px; }
  strong { color: #0f1a26; }
  table { border-collapse: collapse; margin: 6px 0 18px; font-size: 18px; width: 100%; }
  th, td { border-bottom: 1px solid var(--linha); padding: 8px 12px; text-align: left; vertical-align: top; }
  th { background: var(--codigo-fundo); font-weight: 600; }
  blockquote { margin: 14px 0; padding: 12px 20px; background: var(--destaque-fundo);
    border-left: 5px solid var(--destaque); border-radius: 4px; }
  blockquote p { margin: 4px 0; }
  code { font-family: Consolas, "Cascadia Mono", Menlo, monospace; background: var(--codigo-fundo);
    padding: 1px 6px; border-radius: 4px; font-size: .9em; }
  pre { background: #1d2733; color: #e8edf3; padding: 18px 22px; border-radius: 8px;
    font-size: 19px; line-height: 1.5; margin: 6px 0 18px; }
  pre code { background: none; padding: 0; color: inherit; font-size: inherit; }
  .mermaid { display: flex; justify-content: center; margin: 4px 0 14px; }
  /* Tabela sem cabeçalho = lista de números-chave: a primeira coluna é o número. */
  table.chave td { border-bottom: none; padding: 10px 12px; font-size: 20px; color: var(--suave); vertical-align: middle; }
  table.chave td:first-child { font-size: 30px; white-space: nowrap; color: var(--texto); width: 1%; padding-right: 32px; }
  .mermaid svg { max-width: 100%; height: auto; max-height: 490px; }
  .fonte { position: absolute; left: 72px; right: 72px; bottom: 20px; font-size: 14px; color: var(--suave);
    border-top: 1px solid var(--linha); padding-top: 8px; }
  .fonte code { font-size: 13px; }
  #rodape { position: fixed; right: 18px; bottom: 12px; font-size: 13px; color: var(--suave); }
  #barra { position: fixed; left: 0; bottom: 0; height: 4px; background: var(--destaque); transition: width .2s; }
</style>
</head>
<body>
<div id="palco"></div>
<div id="barra"></div>
<div id="rodape"></div>
<script>__MARKED__</script>
<script>__MERMAID__</script>
<script>
const TITULO = __TITULO_JSON__;
const SLIDES = __SLIDES_JSON__;

marked.use({ renderer: {
  code(token) {
    const lang = typeof token === "object" ? token.lang : arguments[1];
    const text = typeof token === "object" ? token.text : token;
    if (lang === "mermaid") return '<div class="mermaid">' + text + '</div>';
    return false;
  }
}});
mermaid.initialize({ startOnLoad: false, securityLevel: "loose", theme: "default",
  flowchart: { htmlLabels: true }, fontFamily: "Segoe UI, system-ui, sans-serif" });

const palco = document.getElementById("palco");
const capa = document.createElement("section");
capa.className = "slide capa";
capa.innerHTML = '<div class="conteudo"><div class="faixa"></div><h1>' + TITULO +
  '</h1><p>Desafio técnico — Arquitetura de Soluções</p></div>';
palco.appendChild(capa);
for (const md of SLIDES) {
  const s = document.createElement("section");
  s.className = "slide";
  s.innerHTML = '<div class="conteudo">' + marked.parse(md) + '</div>';
  s.querySelectorAll("table").forEach(tab => {
    const cab = tab.querySelector("thead");
    if (cab && !cab.textContent.trim()) { cab.remove(); tab.classList.add("chave"); }
  });
  // "Detalhe: <documento>" vira rodapé do slide, fora da área de conteúdo.
  s.querySelectorAll(".conteudo > p").forEach(par => {
    if (par.textContent.startsWith("Detalhe:")) {
      const rod = document.createElement("div");
      rod.className = "fonte";
      rod.innerHTML = par.innerHTML;
      par.remove();
      s.appendChild(rod);
    }
  });
  palco.appendChild(s);
}
const todos = [...palco.querySelectorAll(".slide")];
let atual = 0;

function escala() {
  const k = Math.min(window.innerWidth / 1320, window.innerHeight / 760);
  palco.style.transform = "translate(-50%, -50%) scale(" + k + ")";
}

// Conteúdo mais alto que o slide encolhe até caber, em vez de ser cortado.
function caber(slide) {
  const c = slide.querySelector(".conteudo");
  c.style.transform = "none";
  const livre = 720 - 52 - 60, usado = c.scrollHeight;
  if (usado > livre) c.style.transform = "scale(" + Math.max(livre / usado, 0.55) + ")";
}

// Mermaid só desenha direito em elemento visível: cada slide é desenhado
// na primeira vez que aparece.
async function mostrar(i) {
  atual = Math.max(0, Math.min(i, todos.length - 1));
  todos.forEach((s, k) => s.classList.toggle("ativo", k === atual));
  const slide = todos[atual];
  const pendentes = [...slide.querySelectorAll(".mermaid:not([data-processed])")];
  if (pendentes.length) await mermaid.run({ nodes: pendentes });
  caber(slide);
  document.getElementById("rodape").textContent = (atual + 1) + " / " + todos.length;
  document.getElementById("barra").style.width = ((atual + 1) / todos.length * 100) + "%";
  history.replaceState(null, "", "#" + (atual + 1));
}

document.addEventListener("keydown", e => {
  if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(e.key)) { e.preventDefault(); mostrar(atual + 1); }
  else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(e.key)) { e.preventDefault(); mostrar(atual - 1); }
  else if (e.key === "Home") mostrar(0);
  else if (e.key === "End") mostrar(todos.length - 1);
  else if (e.key === "f" || e.key === "F") {
    if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen();
  }
});
document.addEventListener("click", e => { if (e.button === 0) mostrar(atual + 1); });
window.addEventListener("resize", () => { escala(); caber(todos[atual]); });

escala();
mostrar((parseInt(location.hash.slice(1), 10) || 1) - 1);
</script>
</body>
</html>
"""

html = (html
        .replace("__TITULO__", titulo)
        .replace("__TITULO_JSON__", json.dumps(titulo, ensure_ascii=False))
        .replace("__SLIDES_JSON__", json.dumps(slides, ensure_ascii=False).replace("</", "<\\/"))
        .replace("__MARKED__", ler(LIBS[0]))
        .replace("__MERMAID__", ler(LIBS[1])))

io.open(DESTINO, "w", encoding="utf-8", newline="\n").write(html)
print(f"{len(slides) + 1} slides (capa + {len(slides)}) -> {DESTINO.relative_to(RAIZ)}")
print(f"{DESTINO.stat().st_size // 1024} KB, abre sem internet")
