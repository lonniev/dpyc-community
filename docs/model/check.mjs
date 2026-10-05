import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

// Verifies every fenced mermaid block in diagrams.md: grammar first, then a full
// render — in a real Chromium, with the mermaid this directory's lockfile pins.
// Run:  npm install && npx playwright install chromium && node check.mjs
//
// It used to render under jsdom with a fake getBBox. That harness lied in both
// directions once mermaid 11.17 landed: with no layout engine the edge painter
// was handed garbage points and died in btoa on an emoji, while the same six
// diagrams drew cleanly in Chrome. A check that fails on diagrams the page
// renders fine, or the reverse, is worse than no check; the browser is the only
// honest renderer. The page itself (factory-model.html) imports the same pinned
// version, so what passes here is what readers get.
const here = path.dirname(fileURLToPath(import.meta.url));
const md = fs.readFileSync(path.join(here, 'diagrams.md'), 'utf8');
const blocks = [...md.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m => m[1]);
const version = JSON.parse(fs.readFileSync(path.join(here, 'node_modules/mermaid/package.json'), 'utf8')).version;

// Serve node_modules over loopback so the page can `import` the locked build:
// a module script cannot import from file:// out of about:blank.
const root = path.join(here, 'node_modules');
const types = { '.mjs': 'text/javascript', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css' };
const server = http.createServer((req, res) => {
  const file = path.normalize(path.join(root, decodeURIComponent(req.url.split('?')[0])));
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'content-type': types[path.extname(file)] ?? 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(`${base}/mermaid/package.json`); // any same-origin document; import() needs an origin
const results = await page.evaluate(async ([base, blocks]) => {
  const { default: mermaid } = await import(`${base}/mermaid/dist/mermaid.esm.min.mjs`);
  mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
  const out = [];
  for (const [i, src] of blocks.entries()) {
    const kind = src.trim().split('\n')[0];
    try {
      await mermaid.parse(src);
      const { svg } = await mermaid.render('d' + i, src);
      const shapes = (svg.match(/<(g|rect|path|text)\b/g) || []).length;
      out.push({ i, kind, ok: true, bytes: svg.length, shapes });
    } catch (e) {
      out.push({ i, kind, ok: false, error: String(e?.message || e) });
    }
  }
  return out;
}, [base, blocks]);
await browser.close();
server.close();

console.log(`mermaid ${version} in Chromium ${browser.version()}`);
let bad = 0;
for (const r of results) {
  if (r.ok) console.log(`  ${r.i + 1}  ${r.kind.padEnd(16)} OK   svg ${String(r.bytes).padStart(6)}B  ${r.shapes} shapes`);
  else { bad++; console.log(`  ${r.i + 1}  ${r.kind.padEnd(16)} FAIL\n${r.error.split('\n').slice(0, 6).map(l => '        ' + l).join('\n')}`); }
}
console.log(bad ? `\n${bad} diagram(s) still failing` : `\nall ${results.length} parse and render clean`);
process.exit(bad ? 1 : 0);
