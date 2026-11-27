#!/usr/bin/env python3
"""Generate the on-site Verification guide and Self-assessment pages.

Usage:
    python tools/site/gen_doc_pages.py          # write verification/ and self-assessment/
    python tools/site/gen_doc_pages.py --check  # exit 1 if either page is stale

Standard library only. CHECKLIST-VERIFICATION.md and SELF-ASSESSMENT.md stay the
sources of truth; these pages keep their words and change only the presentation.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_checklist_page as base  # noqa: E402  (shared markdown, links and item names)

ROOT = base.ROOT
PAGES = [
    {"src": ROOT / "ANTI-PATTERNS.md", "out": ROOT / "anti-patterns" / "index.html",
     "path": "/anti-patterns/", "crumb": "Anti-patterns", "eyebrow": "BRACE · Agent security anti-patterns",
     "desc": "The setups that most often turn an AI agent into a security incident, and what to do instead.",
     "cards": False},
    {"src": ROOT / "STARTER.md", "out": ROOT / "starter" / "index.html",
     "path": "/starter/", "crumb": "Starter", "eyebrow": "BRACE · Starter",
     "desc": "Ten checks before an AI agent touches anything real.", "cards": False},
    {"src": ROOT / "CHECKLIST-VERIFICATION.md", "out": ROOT / "verification" / "index.html",
     "path": "/verification/", "crumb": "Verification guide", "eyebrow": "BRACE · Verification guide",
     "desc": "A test, the expected result and the evidence to keep for each of the 53 BRACE checklist items.",
     "cards": True},
    {"src": ROOT / "SELF-ASSESSMENT.md", "out": ROOT / "self-assessment" / "index.html",
     "path": "/self-assessment/", "crumb": "Self-assessment", "eyebrow": "BRACE · Self-assessment",
     "desc": "Score the 53 BRACE checklist items for a deployment or a vendor.",
     "cards": False},
    {"src": ROOT / "otel-conventions.md", "out": ROOT / "otel-conventions" / "index.html",
     "path": "/otel-conventions/", "crumb": "OpenTelemetry conventions", "eyebrow": "BRACE · OpenTelemetry conventions",
     "desc": "The proposed agent.* OpenTelemetry attributes for agent identity and provenance.", "cards": False},
    {"src": ROOT / "VENDOR-MATRIX.md", "out": ROOT / "vendor-matrix" / "index.html",
     "path": "/vendor-matrix/", "crumb": "Vendor matrix", "eyebrow": "BRACE · Vendor matrix",
     "desc": "The evidence to request, for each BRACE control, when you evaluate an agent vendor or platform.", "cards": False},
    {"src": ROOT / "SOURCE-REVIEW.md", "out": ROOT / "source-review" / "index.html",
     "path": "/source-review/", "crumb": "Source review", "eyebrow": "BRACE · Source review",
     "desc": "How BRACE's recommendations were checked against current sources, and the limits of that review.", "cards": False},
    {"src": ROOT / "mappings" / "nist-ai-rmf.md", "out": ROOT / "mappings" / "nist-ai-rmf" / "index.html",
     "path": "/mappings/nist-ai-rmf/", "crumb": "NIST AI RMF mapping", "eyebrow": "BRACE · Standards mapping",
     "desc": "Every NIST AI RMF subcategory mapped to the BRACE checklist items that produce evidence for it.", "cards": False},
    {"src": ROOT / "mappings" / "iso-iec-42001.md", "out": ROOT / "mappings" / "iso-iec-42001" / "index.html",
     "path": "/mappings/iso-iec-42001/", "crumb": "ISO/IEC 42001 mapping", "eyebrow": "BRACE · Standards mapping",
     "desc": "ISO/IEC 42001 clause headings and Annex A controls mapped to BRACE checklist items.", "cards": False},
    {"src": ROOT / "mappings" / "mitre-atlas.md", "out": ROOT / "mappings" / "mitre-atlas" / "index.html",
     "path": "/mappings/mitre-atlas/", "crumb": "MITRE ATLAS mapping", "eyebrow": "BRACE · Standards mapping",
     "desc": "Every MITRE ATLAS technique mapped to the BRACE checklist items that prevent or contain it.", "cards": False},
    {"src": ROOT / "mappings" / "owasp-agentic-top-10.md", "out": ROOT / "mappings" / "owasp-agentic-top-10" / "index.html",
     "path": "/mappings/owasp-agentic-top-10/", "crumb": "OWASP Agentic Top 10 mapping", "eyebrow": "BRACE · Standards mapping",
     "desc": "Each OWASP Top 10 for Agentic Applications (2026) risk mapped to BRACE controls and checklist items.", "cards": False},
    {"src": ROOT / "mappings" / "owasp-mcp-top-10.md", "out": ROOT / "mappings" / "owasp-mcp-top-10" / "index.html",
     "path": "/mappings/owasp-mcp-top-10/", "crumb": "OWASP MCP Top 10 mapping", "eyebrow": "BRACE · Standards mapping",
     "desc": "Each OWASP MCP Top 10 (2025, beta) risk mapped to BRACE controls and checklist items.", "cards": False},
]


class DocError(Exception):
    pass


def titles() -> dict[str, str]:
    doc = base.parse(base.SOURCE.read_text(encoding="utf-8"))  # also fills base.ITEM_IDS
    return {it["id"]: base.plain(it["title"]) for a in doc["aspects"] for g in a["groups"] for it in g["items"]}


def split(text: str) -> tuple[str, list[str], list[tuple[str, list[str]]]]:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise DocError("document must start with a '# ' title")
    pre: list[str] = []
    secs: list[tuple[str, list[str]]] = []
    fenced = False
    for line in lines[1:]:
        if line.strip().startswith("```"):
            fenced = not fenced
        if line.startswith("## ") and not fenced:
            secs.append((line[3:].strip(), []))
        elif secs:
            secs[-1][1].append(line)
        else:
            pre.append(line)
    return lines[0][2:].strip(), pre, secs


def recipe_cards(lines: list[str], names: dict[str, str]) -> str:
    """Turn the 'Item | Test and expected result | Evidence to keep' table into cards."""
    out, rest, seen = [], [], 0
    for line in lines:
        m = re.match(r"^\| ([BRACE]\d\d) \|(.*)\|\s*$", line)
        if m:
            iid = m.group(1)
            test, ev = [c.strip() for c in m.group(2).split("|")]
            seen += 1
            out.append(
                f'<div class="recipe" id="{iid}"><h3><a href="/checklist/#{iid}">'
                f'<span class="rn">{base.rule_name(iid)}</span> {html.escape(names[iid])}</a></h3>'
                f'<div class="rl">Test and expected result</div><p>{base.inline(test)}</p>'
                f'<div class="rl">Evidence to keep</div><p>{base.inline(ev)}</p></div>')
        elif re.match(r"^\| ?(Item|---)", line):
            continue
        else:
            rest.append(line)
    if not seen:
        return base.blocks(lines)
    return base.blocks(rest) + '\n<div class="recipes">' + "\n".join(out) + "</div>"


def labelled_tables(body: str) -> str:
    """Give each table cell its column name so narrow screens can show rows as cards."""
    def table(m: re.Match) -> str:
        t = m.group(0)
        heads = [re.sub(r"<[^>]+>", "", h) for h in re.findall(r"<th>(.*?)</th>", t)]

        def row(r: re.Match) -> str:
            cells = re.findall(r"<td>(.*?)</td>", r.group(1))
            return "<tr>" + "".join(
                f'<td data-label="{html.escape(heads[i] if i < len(heads) else "", quote=True)}">{c}</td>'
                for i, c in enumerate(cells)) + "</tr>"
        return re.sub(r"<tr>((?:<td>.*?</td>)+)</tr>", row, t)
    return re.sub(r"<table>.*?</table>", table, body, flags=re.S)


def render(cfg: dict, names: dict[str, str]) -> str:
    title, pre, secs = split(cfg["src"].read_text(encoding="utf-8"))
    parts, toc = [], []
    for name, lines in secs:
        slug = base.gh_slug(name)
        m = re.match(r"^([BRACE]) — ", name)
        letter = m.group(1) if m else ""
        aspect = f' data-aspect="{letter}"' if letter else ""
        body = recipe_cards(lines, names) if cfg["cards"] and letter else base.blocks(lines)
        badge = f'<span class="aletter" aria-hidden="true">{letter}</span>' if letter else ""
        parts.append(f'<section class="doc" id="{slug}"{aspect}><div class="dhead">{badge}<h2>{base.inline(name)}</h2></div>\n{body}\n</section>')
        cls = f' class="chip-{letter}"' if letter else ""
        label = f"<b>{letter}</b> {html.escape(name[4:])}" if letter else html.escape(name)
        toc.append(f'<a href="#{slug}"{cls}>{label}</a>')
    # Self-assessment worksheet: its aspect headings are ### inside one section.
    content = labelled_tables("\n".join(parts))
    content = re.sub(r'<h4 id="([brace])--([a-z-]+)">([BRACE]) — ([^<]+)</h4>',
                     lambda m: f'<h3 class="wsh" id="{m.group(1)}--{m.group(2)}" data-aspect="{m.group(3)}">'
                               f'<span class="aletter" aria-hidden="true">{m.group(3)}</span>{m.group(4)}</h3>', content)
    page = (TEMPLATE.replace("@@TITLE@@", html.escape(title))
            .replace("@@PARENT@@", '<a href="/checklist/">Sign-off checklist</a> <span aria-hidden="true">›</span> ' if cfg["path"] in ("/verification/", "/self-assessment/") else "")
            .replace("@@CRUMB@@", cfg["crumb"]).replace("@@EYEBROW@@", cfg["eyebrow"])
            .replace("@@DESC@@", html.escape(cfg["desc"])).replace("@@PATH@@", cfg["path"])
            .replace("@@INTRO@@", base.blocks(pre)).replace("@@TOC@@", "".join(toc))
            .replace("@@BODY@@", content))
    if "github.com/brace-ai-security" in page:
        raise DocError(f"{cfg['path']} would link to the BRACE source repository")
    return page


def check_links(page: str, path: str) -> None:
    """Every on-site anchor we generate must exist."""
    for url, frag in re.findall(r'href="(/[a-z0-9/-]*/)#([^"]+)"', page):
        text = page if url == path else targets_text(url)
        if text and f'id="{frag}"' not in text:
            raise DocError(f"{path} links to {url}#{frag}, which does not exist")


def targets_text(path: str) -> str:
    f = ROOT / path.strip("/") / "index.html"
    return f.read_text(encoding="utf-8") if f.exists() else ""


TEMPLATE = r"""<!DOCTYPE html>
<!-- Generated by tools/site/gen_doc_pages.py. Do not edit by hand. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@CRUMB@@ — BRACE Framework</title>
<meta name="description" content="@@DESC@@">
<link rel="canonical" href="https://braceframework.org@@PATH@@">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="BRACE Framework">
<meta property="og:title" content="@@TITLE@@">
<meta property="og:description" content="@@DESC@@">
<meta property="og:url" content="https://braceframework.org@@PATH@@">
<meta property="og:image" content="https://braceframework.org/og-checklist.png">
<meta name="twitter:card" content="summary_large_image">
<style>
  :root{
    --ink:#1a1a1a; --muted:#555a63; --primary:#1a4d6e; --accent:#2e8bc0;
    --tint:#eef5fc; --tint2:#dde9f3; --rule:#c8d4df; --bg:#ffffff; --card:#ffffff; --head:#15384f;
    --aB:#4338ca; --aR:#0f766e; --aA:#7e22ce; --aC:#a1530a; --aE:#15803d;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --ink:#e4e8ec; --muted:#9aa4ae; --primary:#7fb8de; --accent:#6cb6e6;
      --tint:#16222c; --tint2:#1c2b37; --rule:#2c3b47; --bg:#0f161c; --card:#131d25; --head:#cfe3f2;
      --aB:#a5b4fc; --aR:#5eead4; --aA:#d8b4fe; --aC:#fbbf24; --aE:#86efac;
    }
  }
  :root[data-theme="dark"]{
    --ink:#e4e8ec; --muted:#9aa4ae; --primary:#7fb8de; --accent:#6cb6e6;
    --tint:#16222c; --tint2:#1c2b37; --rule:#2c3b47; --bg:#0f161c; --card:#131d25; --head:#cfe3f2;
    --aB:#a5b4fc; --aR:#5eead4; --aA:#d8b4fe; --aC:#fbbf24; --aE:#86efac;
  }
  [data-aspect="B"],.chip-B{--a:var(--aB)} [data-aspect="R"],.chip-R{--a:var(--aR)} [data-aspect="A"],.chip-A{--a:var(--aA)}
  [data-aspect="C"],.chip-C{--a:var(--aC)} [data-aspect="E"],.chip-E{--a:var(--aE)}
  [data-aspect],[class^="chip-"]{--at:color-mix(in srgb, var(--a) 11%, var(--card)); --ar:color-mix(in srgb, var(--a) 35%, var(--card))}
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0; color:var(--ink); background:var(--bg); font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  a{color:var(--accent); text-decoration:none}
  a:hover{text-decoration:underline}
  code{background:var(--tint2); border-radius:4px; padding:1px 5px; font:13.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; overflow-wrap:anywhere}
  pre.code{background:var(--tint2); border-radius:6px; padding:12px 14px; overflow-x:auto; margin:0 0 1em}
  pre.code code{background:none; padding:0; overflow-wrap:normal; white-space:pre}
  .wrap{max-width:800px; margin:0 auto; padding:0 24px}
  main p,.intro p{max-width:68ch}
  .crumb{background:#1a4d6e; color:#fff; font-size:13px; padding:10px 0}
  .crumb a{color:#cfe2f1}
  header.hero{background:#1a4d6e; color:#fff; padding:40px 0 34px}
  .eyebrow{letter-spacing:.18em; text-transform:uppercase; font-size:12px; opacity:.85; margin:0 0 10px}
  h1{font-size:40px; line-height:1.06; margin:0; font-weight:800; letter-spacing:-.5px}
  .intro{padding-top:24px; font-size:16.5px}
  .intro p{margin:10px 0}
  nav.toc{display:flex; flex-wrap:wrap; gap:6px; margin:18px 0 6px}
  nav.toc a{display:inline-flex; align-items:center; gap:6px; font-size:13px; padding:3px 10px; border-radius:999px; color:var(--ink); white-space:nowrap; background:var(--at, var(--tint)); border:1px solid var(--ar, var(--rule))}
  nav.toc a[class]{padding-left:3px}
  nav.toc a:hover{text-decoration:none; border-color:var(--a, var(--accent))}
  nav.toc b{display:inline-grid; place-items:center; width:20px; height:20px; border-radius:50%; background:var(--a); color:var(--card); font-size:11.5px}
  section.doc{padding:30px 0 18px; border-bottom:1px solid var(--rule); scroll-margin-top:16px}
  .dhead{display:flex; align-items:center; gap:12px}
  .aletter{display:inline-grid; place-items:center; flex:none; width:34px; height:34px; border-radius:10px; background:var(--a); color:var(--card); font-weight:800; font-size:17px}
  h2{font-size:24px; color:var(--primary); margin:0; letter-spacing:-.3px}
  section.doc[data-aspect] h2{color:var(--ink)}
  h3.wsh{display:flex; align-items:center; gap:10px; font-size:20px; margin:28px 0 8px; scroll-margin-top:16px}
  h3.wsh .aletter{width:28px; height:28px; font-size:14px; border-radius:8px}
  h4{font-size:16px; color:var(--head); margin:20px 0 6px}
  section.doc p{margin:10px 0}
  .recipes{display:grid; gap:12px; margin-top:16px}
  .recipe{border:1px solid var(--rule); border-radius:12px; padding:6px 18px 10px; background:var(--card); box-shadow:inset 4px 0 0 var(--a); scroll-margin-top:16px}
  .recipe:target{background:var(--at)}
  .recipe h3{font-size:17px; margin:8px 0 4px; line-height:1.4}
  .recipe h3 a{color:var(--ink)}
  .rn{display:block; font-size:12.5px; font-weight:700; color:var(--a)}
  .rl{font-size:12.5px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); font-weight:700; margin-top:10px}
  .recipe p{margin:2px 0 6px; font-size:16px}
  a.iref{white-space:nowrap; font-weight:600}
  .tablewrap{overflow-x:auto}
  table{border-collapse:collapse; width:100%; font-size:14.5px; margin:10px 0}
  th,td{border:1px solid var(--rule); padding:7px 10px; text-align:left; vertical-align:top}
  th{background:var(--tint2)}
  footer{padding:30px 0; color:var(--muted); font-size:14px}
  @media (max-width:640px){
    h1{font-size:30px}
    .wrap{padding:0 16px}
    nav.toc{flex-wrap:nowrap; overflow-x:auto; padding-bottom:4px}
    .recipe{padding:4px 14px 8px}
    table,thead,tbody,tr,td{display:block; width:100%}
    thead{display:none}
    table{border:0}
    tr{border:1px solid var(--rule); border-radius:10px; margin:0 0 10px; padding:6px 12px; background:var(--card)}
    td{border:0; padding:3px 0}
    td[data-label]::before{content:attr(data-label); display:block; font-size:11.5px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; color:var(--muted)}
    td:empty{display:none}
  }
  @media print{
    .crumb,nav.toc{display:none}
    header.hero{background:none; color:#000; padding:0}
    body{font-size:11pt; background:#fff; color:#000}
    .recipe{break-inside:avoid}
    a{color:#000}
  }
</style>
</head>
<body>
<div class="crumb"><div class="wrap"><a href="/">BRACE</a> <span aria-hidden="true">›</span> @@PARENT@@<span>@@CRUMB@@</span></div></div>
<header class="hero"><div class="wrap"><p class="eyebrow">@@EYEBROW@@</p><h1>@@TITLE@@</h1></div></header>
<div class="wrap intro">
@@INTRO@@
<nav class="toc" aria-label="On this page">@@TOC@@</nav>
</div>
<main class="wrap">
@@BODY@@
</main>
<footer><div class="wrap">The BRACE Framework · <a href="/">braceframework.org</a> · <a href="/checklist/">Sign-off checklist</a> · Content CC BY 4.0 · Code Apache-2.0.</div></footer>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if a page is out of date")
    args = ap.parse_args()
    try:
        names = titles()
        pages = [(cfg, render(cfg, names)) for cfg in PAGES]
        if not args.check:
            for cfg, page in pages:
                cfg["out"].parent.mkdir(parents=True, exist_ok=True)
                cfg["out"].write_text(page, encoding="utf-8")
                print(f"wrote {cfg['out'].relative_to(ROOT)}")
        for cfg, page in pages:
            check_links(page, cfg["path"])
        check_links(targets_text("/checklist/"), "/checklist/")
    except (DocError, base.ChecklistError) as e:
        print(f"gen_doc_pages: {e}", file=sys.stderr)
        return 2
    if args.check:
        stale = [cfg for cfg, page in pages
                 if not cfg["out"].exists() or cfg["out"].read_text(encoding="utf-8") != page]
        for cfg in stale:
            print(f"{cfg['out'].relative_to(ROOT)} is out of date; run python tools/site/gen_doc_pages.py", file=sys.stderr)
        if stale:
            return 1
        print(f"{len(pages)} document pages are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
