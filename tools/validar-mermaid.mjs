#!/usr/bin/env node
/**
 * Fitness function: valida os blocos Mermaid dos documentos com o parser
 * oficial do Mermaid — o mesmo que o GitHub usa para renderizar.
 *
 * Existe porque Mermaid falha em silêncio: um diagrama com erro de sintaxe
 * não gera aviso, apenas não aparece. Sem esta verificação, o entregável
 * poderia chegar ao avaliador com diagramas em branco.
 *
 *   node validar-mermaid.mjs [diretorio]
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = resolve(process.argv[2] ?? join(AQUI, '..', 'docs'));

// Mermaid precisa de DOM para sanitizar rótulos HTML; Node puro não tem.
const dom = new JSDOM('<!DOCTYPE html><body></body>', { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true });
global.Element = dom.window.Element;
global.SVGElement = dom.window.SVGElement;

const mermaid = (await import('mermaid')).default;

function varrer(dir, acc = []) {
  for (const entrada of readdirSync(dir)) {
    const p = join(dir, entrada);
    if (statSync(p).isDirectory()) varrer(p, acc);
    else if (entrada.endsWith('.md')) acc.push(p);
  }
  return acc;
}

let total = 0;
let erros = 0;

for (const arquivo of varrer(RAIZ).sort()) {
  const texto = readFileSync(arquivo, 'utf8');
  const blocos = [...texto.matchAll(/```mermaid\n([\s\S]*?)```/g)].map((m) => m[1]);
  for (let i = 0; i < blocos.length; i++) {
    total++;
    const nome = `${relative(RAIZ, arquivo)} [${i + 1}]`;
    try {
      await mermaid.parse(blocos[i]);
      console.log(`  ok    ${nome}`);
    } catch (e) {
      erros++;
      console.log(`  ERRO  ${nome}`);
      console.log('        ' + String(e?.message ?? e).split('\n').slice(0, 5).join('\n        '));
    }
  }
}

console.log(`\n${total} diagramas, ${erros} com erro`);
process.exit(erros ? 1 : 0);
