#!/usr/bin/env python3
"""Generate the Software Factory model artifact page from the repo's own sources.

Reads docs/model/{README.md,diagrams.md,dpyc-factory.sysml} and emits one
self-contained HTML page. Regenerate after editing any source; never hand-edit
the output.

The only subtle part is the mermaid blocks: their source contains `<b>`, `<br/>`
and `&lt;!--`, so it must be HTML-escaped before landing inside
`<pre class="mermaid">` or the browser eats the tags before mermaid ever sees
the text.
"""

import html
import re
import sys
from pathlib import Path

# Sources sit beside this script, so the build runs from any working directory.
SRC = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC / "factory-model.html"


# --- inline markdown -------------------------------------------------------
def inline(text: str) -> str:
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "`":
            j = text.find("`", i + 1)
            if j != -1:
                out.append(f"<code>{html.escape(text[i + 1:j])}</code>")
                i = j + 1
                continue
        if text.startswith("**", i):
            j = text.find("**", i + 2)
            if j != -1:
                out.append(f"<strong>{inline(text[i + 2:j])}</strong>")
                i = j + 2
                continue
        if ch == "[":
            m = re.match(r"\[([^\]]*)\]\(([^)]+)\)", text[i:])
            if m:
                label, href = m.group(1), m.group(2)
                # Relative repo links do not resolve on a hosted page — keep the words.
                if href.startswith((".", "#")):
                    out.append(inline(label))
                else:
                    out.append(f'<a href="{html.escape(href)}">{inline(label)}</a>')
                i += m.end()
                continue
        if ch == "*" and not text.startswith("**", i):
            j = text.find("*", i + 1)
            if j != -1:
                out.append(f"<em>{inline(text[i + 1:j])}</em>")
                i = j + 1
                continue
        out.append(html.escape(ch))
        i += 1
    return "".join(out)


# --- label chips -----------------------------------------------------------
# The document's semantic colour is the fleet's own label palette
# (scripts/apply_labels.sh), so a label in the prose looks like the label in
# GitHub. Only routing-significant labels get a chip; the rest stay plain code.
LABEL_HEX = {
    "agent/fix": "5319e7", "agent/retriage": "5319e7", "agent/working": "1d76db",
    "agent/revising": "1d76db", "blocked/upstream": "e99695",
    "rejected/upstream": "e99695", "blocked/arbitration": "b60205",
    "qa/pass": "0e8a16", "qa/flag": "d93f0b", "awaiting-funds": "b60205",
    "factory/outage": "b60205", "rejected/needs-info": "fef2c0",
    "sev/critical": "b60205",
}


def chipify(fragment: str) -> str:
    def sub(m):
        name = m.group(1)
        hexv = LABEL_HEX.get(name)
        if not hexv:
            return m.group(0)
        return f'<span class="chip" style="--chip:#{hexv}">{name}</span>'
    return re.sub(r"<code>([a-z]+/[a-z-]+|awaiting-funds)</code>", sub, fragment)


# --- block markdown --------------------------------------------------------
def render(md: str, part_id: str) -> tuple[str, list]:
    lines = md.splitlines()
    out, toc = [], []
    i, n = 0, len(lines)
    sec = 0

    def flush_para(buf):
        if buf:
            out.append(f"<p>{chipify(inline(' '.join(buf)))}</p>")
            buf.clear()

    para: list[str] = []
    while i < n:
        line = lines[i]

        if line.startswith("```"):
            flush_para(para)
            lang = line[3:].strip()
            i += 1
            body = []
            while i < n and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1
            src = "\n".join(body)
            if lang == "mermaid":
                out.append(
                    '<figure class="diagram"><div class="scroll">'
                    f'<pre class="mermaid">{html.escape(src)}</pre>'
                    "</div></figure>"
                )
            else:
                out.append(
                    f'<div class="scroll"><pre class="code">{html.escape(src)}</pre></div>'
                )
            continue

        if line.startswith("#"):
            flush_para(para)
            level = len(line) - len(line.lstrip("#"))
            text = line[level:].strip()
            if level == 2:
                # diagrams.md numbers its own sections; adopt that number for the rail
                # mark rather than stacking a second one beside it.
                own = re.match(r"^(\d+)\.\s+(.*)$", text)
                if own:
                    sec, text = int(own.group(1)), own.group(2)
                else:
                    sec += 1
                anchor = f"{part_id}-{sec}"
                toc.append((sec, anchor, text))
                out.append(
                    f'<h2 id="{anchor}"><span class="mark">{part_id.upper()}.{sec}</span>'
                    f"<span>{inline(text)}</span></h2>"
                )
            else:
                out.append(f"<h{level + 1}>{inline(text)}</h{level + 1}>")
            i += 1
            continue

        if line.strip() == "---":
            flush_para(para)
            out.append('<hr />')
            i += 1
            continue

        if line.startswith("|"):
            flush_para(para)
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            head = cells[0]
            body = [r for r in cells[2:]] if len(cells) > 2 else []
            th = "".join(f"<th>{chipify(inline(c))}</th>" for c in head)
            trs = "".join(
                "<tr>" + "".join(f"<td>{chipify(inline(c))}</td>" for c in r) + "</tr>"
                for r in body
            )
            out.append(
                f'<div class="scroll"><table><thead><tr>{th}</tr></thead>'
                f"<tbody>{trs}</tbody></table></div>"
            )
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m or line.startswith("- "):
            flush_para(para)
            ordered = bool(m)
            items, cur = [], ""
            while i < n:
                ln = lines[i]
                mm = re.match(r"^(\d+)\.\s+(.*)$", ln)
                if mm and ordered:
                    if cur:
                        items.append(cur)
                    cur = mm.group(2)
                elif ln.startswith("- ") and not ordered:
                    if cur:
                        items.append(cur)
                    cur = ln[2:]
                elif ln.startswith("  ") and cur:
                    cur += " " + ln.strip()
                else:
                    break
                i += 1
            if cur:
                items.append(cur)
            tag = "ol" if ordered else "ul"
            lis = "".join(f"<li>{chipify(inline(t))}</li>" for t in items)
            out.append(f"<{tag}>{lis}</{tag}>")
            continue

        if not line.strip():
            flush_para(para)
            i += 1
            continue

        para.append(line.strip())
        i += 1

    flush_para(para)
    return "\n".join(out), toc


def strip_h1(md: str) -> str:
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip("\n")
    return md


# --- assemble --------------------------------------------------------------
readme = strip_h1((SRC / "README.md").read_text())
diagrams = strip_h1((SRC / "diagrams.md").read_text())
sysml = (SRC / "dpyc-factory.sysml").read_text()

# The intro paragraph of diagrams.md points at sibling files; on one page it is noise.
diagrams = re.sub(
    r"Mermaid renderings of the model.*?\n\n", "", diagrams, count=1, flags=re.DOTALL
)

body_a, toc_a = render(readme, "i")
body_b, toc_b = render(diagrams, "ii")

sysml_lines = "".join(
    f"<span class=\"ln\">{html.escape(ln) or '&nbsp;'}</span>\n"
    for ln in sysml.splitlines()
)

def _plain(text: str) -> str:
    """A contents entry wants the words, not the markup: convert, then drop the tags."""
    return re.sub(r"<[^>]+>", "", inline(text))


def toc_html(part, title, entries):
    items = "".join(
        f'<li><a href="#{a}"><span class="n">{part.upper()}.{k}</span>{_plain(t)}</a></li>'
        for k, a, t in entries
    )
    return f'<section class="toc-part"><h3>{title}</h3><ol>{items}</ol></section>'


HTML = f"""<title>DPYC Software Factory — architecture model</title>
<style>
{Path(__file__).with_name('page.css').read_text()}
</style>

<div class="page">

  <header class="masthead">
    <p class="eyebrow">lonniev/dpyc-community &middot; docs/model &middot; first draft</p>
    <h1>The DPYC<span class="tm">&trade;</span> Software Factory</h1>
    <p class="deck">A formal model of the unattended agentic crew that triages, fixes,
    reviews and lands work across the fleet &mdash; its roles, the common behavior every
    repository inherits, the guards on who may change what, both funding rails, the tech
    stack, and the state machines that govern an issue, a pull request and an outage.</p>
    <dl class="colophon">
      <div><dt>Notation</dt><dd>SysML v2 textual &middot; Mermaid</dd></div>
      <div><dt>Snapshot</dt><dd>main, 29 July 2026</dd></div>
      <div><dt>Scope</dt><dd>18 repositories &middot; 14 roles</dd></div>
      <div><dt>Status</dt><dd><span class="chip" style="--chip:#F7931A">draft &mdash; unverified grammar</span></dd></div>
    </dl>
  </header>

  <aside class="printhint">
    <strong>To keep a PDF:</strong> print this page and choose <em>Save as PDF</em>.
    The layout has a print stylesheet &mdash; the rail collapses, diagrams stay whole,
    and the appendix paginates as a listing.
  </aside>

  <nav class="contents">
    <h2 class="contents-title">Contents</h2>
    {toc_html('i', 'Part I &mdash; Overview', toc_a)}
    {toc_html('ii', 'Part II &mdash; Views', toc_b)}
    <section class="toc-part"><h3>Appendix</h3><ol>
      <li><a href="#attribution"><span class="n">&mdash;</span>Validated with nomograph-sysml</a></li>
      <li><a href="#appendix"><span class="n">A</span>The model, in full</a></li>
    </ol></section>
  </nav>

  <div class="part-rule"><span>Part I</span><h2>Overview</h2></div>
  <div class="prose">{body_a}</div>

  <div class="part-rule"><span>Part II</span><h2>Views</h2></div>
  <div class="prose">{body_b}</div>

  <section class="attribution" id="attribution">
    <p class="eyebrow">With thanks</p>
    <h2>Validated with nomograph-sysml</h2>
    <p>The SysML v2 in this document is machine-checked by
    <a href="https://github.com/nomograph-ai/sysml"><strong>nomograph-sysml</strong></a>,
    the CLI-native SysML v2 toolkit from <a href="https://nomograph.ai/">Nomograph Labs</a> —
    a Rust binary over <code>tree-sitter-sysml</code> that parses, indexes and checks a model,
    and doubles as an MCP server. Our thanks to its authors: a hand-authored model is a claim
    until something with a real grammar agrees with it, and this is what let us stop hedging.</p>

    <div class="scroll"><table class="attr-table">
      <thead><tr><th>Command</th><th>Result</th></tr></thead>
      <tbody>
        <tr><td><code>sysml validate</code></td>
            <td><span class="chip" style="--chip:#0e8a16">valid</span> &mdash; zero diagnostics</td></tr>
        <tr><td><code>sysml index</code></td>
            <td>455 elements, 890 relationships &mdash; all 14 requirements, 4 state machines
            with 42 transitions, 10 enumerations, 12 packages</td></tr>
        <tr><td><code>sysml check all</code></td>
            <td>255 findings, each traced to a limitation of <strong>v0.2.0</strong> rather
            than a defect in the model &mdash; the indexer emits only <code>Member</code> and
            <code>TypedBy</code>, so <code>Satisfy</code>, <code>Verify</code> and
            <code>Connect</code> edges are invisible to it, and unresolved
            <code>String</code>/<code>Integer</code> targets are the standard library sitting
            outside the index</td></tr>
      </tbody>
    </table></div>

    <p class="attr-foot">Each finding class was isolated to a minimal reproducer before being
    set aside; the workings are in &sect;I.5. A clean <code>validate</code> is the signal we
    act on today. Reproduce with
    <code>cargo install nomograph-sysml &amp;&amp; sysml validate docs/model/dpyc-factory.sysml</code>.</p>
  </section>

  <div class="part-rule" id="appendix"><span>Appendix A</span><h2>The model, in full</h2></div>
  <div class="prose">
    <p>The complete SysML v2 textual model, as written to
    <code>docs/model/dpyc-factory.sysml</code>. Every <code>doc</code> comment in it is
    rationale carried over from the source workflow&rsquo;s own header &mdash; the Factory
    documents its reasoning where it lives, and the model preserves that rather than
    paraphrasing it.</p>
  </div>
  <div class="scroll listing"><pre class="code sysml">{sysml_lines}</pre></div>

  <script type="module">
    // Diagrams are mermaid SOURCE, not pictures, so something has to draw them.
    // On the artifact host that happens natively and this CDN is blocked by CSP — the
    // import throws and is caught, which is the whole story there. On GitHub Pages there
    // is no such host, so the page fetches a renderer itself.
    // The wait-then-check means whichever draws first wins and nothing is drawn twice.
    window.addEventListener('load', async () => {{
      await new Promise(r => setTimeout(r, 400));
      const pending = [...document.querySelectorAll('pre.mermaid')]
        .filter(el => !el.querySelector('svg'));
      if (!pending.length) return;
      try {{
        const {{ default: mermaid }} =
          await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs');
        mermaid.initialize({{ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' }});
        await mermaid.run({{ querySelector: 'pre.mermaid' }});
      }} catch (e) {{
        // Offline, or blocked. The source stays legible as text — a degraded page, not a
        // broken one.
        console.warn('mermaid renderer unavailable:', e);
      }}
    }});
  </script>

  <footer class="colophon-end">
    <p>Generated from the repository&rsquo;s own sources: the 32-label taxonomy is
    <code>scripts/apply_labels.sh</code>, the role behavior is <code>factory/*.prompt.md</code>,
    the guards are <code>scripts/doctrine_lint.py</code> and the caller
    <code>if:</code> expressions. Semantic colours on this page are the fleet&rsquo;s
    actual label colours.</p>
  </footer>
</div>
"""

OUT.write_text(HTML)
print(f"wrote {OUT} ({len(HTML):,} bytes)")
