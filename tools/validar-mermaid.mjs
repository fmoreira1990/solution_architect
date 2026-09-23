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

// Guarda contra falso-verde. Uma versão anterior deixou de encontrar metade
// dos diagramas (arquivos gravados com CRLF) e continuou passando, sem ter
// validado nada. Contagem mínima é a defesa contra esse modo de falha.
const MINIMO = Number(process.env.MERMAID_MINIMO ?? 10);

// Mermaid precisa de DOM para sanitizar rótulos HTML; Node puro não tem.
const dom = new JSDOM('<!DOCTYPE html><body></body>', { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true });
global.Element = dom.window.Element;
global.SVGElement = dom.window.SVGElement;

const mermaid = (await import('mermaid')).default;

const BLOCO = /```mermaid\n([\s\S]*?)```/g;

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
  // Normaliza CRLF antes de casar: sem isso, arquivo gravado no Windows
  // simplesmente não é visto, e o validador passa sem olhar.
  const texto = readFileSync(arquivo, 'utf8').split('\r\n').join('\n');
  const blocos = [...texto.matchAll(BLOCO)].map((m) => m[1]);

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

if (total < MINIMO) {
  console.log(`ERRO: esperado ao menos ${MINIMO} diagramas, encontrado ${total}.`);
  console.log('A varredura deixou de encontrar arquivos — build vermelho em vez de falso-verde.');
  process.exit(2);
}

process.exit(erros ? 1 : 0);
