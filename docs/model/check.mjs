import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

// Verifies every fenced mermaid block in diagrams.md: grammar first, then a full
// render. Run:  npm install && node check.mjs   (from this directory)
const dom = new JSDOM('<!doctype html><body></body>', {pretendToBeVisual:true});
for (const k of ['window','document','Element','SVGElement','HTMLElement','DOMParser','Node','getComputedStyle','MutationObserver','requestAnimationFrame','CSSStyleSheet','CSSStyleDeclaration','SVGSVGElement','DocumentFragment','Event','CustomEvent'])
  Object.defineProperty(globalThis, k, {value: k==='window' ? dom.window : dom.window[k], configurable:true, writable:true});
// jsdom has no layout engine, so SVG measurement is absent. A fixed box lets the
// rest of the render pipeline run; geometry is meaningless, thrown errors are not.
for (const proto of [dom.window.SVGElement.prototype, dom.window.Element.prototype]) {
  proto.getBBox = function(){ const n=(this.textContent||'').length; return {x:0,y:0,width:Math.max(8,n*7),height:18}; };
  proto.getComputedTextLength = function(){ return (this.textContent||'').length*7; };
}
const here = path.dirname(fileURLToPath(import.meta.url));
const md = fs.readFileSync(path.join(here, 'diagrams.md'), 'utf8');
const blocks = [...md.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m=>m[1]);
const mermaid = (await import('mermaid')).default;
mermaid.initialize({startOnLoad:false, securityLevel:'loose'});
let bad = 0;
for (const [i,src] of blocks.entries()) {
  const kind = src.trim().split('\n')[0];
  try {
    await mermaid.parse(src);
    const {svg} = await mermaid.render('d'+i, src);
    const nodes = (svg.match(/<(g|rect|path|text)\b/g)||[]).length;
    console.log(`  ${i+1}  ${kind.padEnd(16)} OK   svg ${String(svg.length).padStart(6)}B  ${nodes} shapes`);
  }
  catch (e) { bad++; console.log(`  ${i+1}  ${kind.padEnd(16)} FAIL\n${String(e.message||e).split('\n').slice(0,6).map(l=>'        '+l).join('\n')}`); }
}
console.log(bad ? `\n${bad} diagram(s) still failing` : '\nall 6 parse clean');

process.exit(bad ? 1 : 0);
