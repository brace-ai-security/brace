#!/usr/bin/env python3
"""Generate the on-site sign-off checklist page from CHECKLIST.md.

Usage:
    python tools/site/gen_checklist_page.py          # write checklist/index.html
    python tools/site/gen_checklist_page.py --check  # exit 1 if the page is stale

Standard library only. CHECKLIST.md is the single source of truth; the page
keeps every word of every item and only changes the presentation.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "CHECKLIST.md"
OUTPUT = ROOT / "checklist" / "index.html"

ASPECTS = {"B": "Build-time", "R": "Run-time", "A": "Agent", "C": "Configuration", "E": "Ecosystem"}
ITEM_RE = re.compile(r"^- \[ \] \*\*([BRACE]\d\d) · (Blocker|Required|Detection) · (.+?) — (.+?)\*\*\s*(.*)$")
NOTE_LABELS = ("Why this is hard", "If you can't fully do it", "Tradeoffs you can accept")


class ChecklistError(Exception):
    pass


# ---------------------------------------------------------------- inline markdown

def rewrite_link(target: str) -> str | None:
    """Map a CHECKLIST.md link to an on-site URL, or None to render plain text.

    Repository files are never linked: the site must not point at source hosting.
    """
    if target.startswith("#priority-gates"):
        return "#priority-gates"
    if target.startswith("#"):
        return target
    m = re.match(r"guides/([a-z-]+)/index\.html$", target)
    if m:
        return f"/guides/{m.group(1)}/"
    if target.startswith("README.md#the-framework-in-one-screen"):
        return "/#controls"
    if target == "README.md":
        return "/"
    if re.match(r"https?://", target) and "github.com" not in target:
        return target
    return None



@__import__("functools").lru_cache(None)
def control_names() -> dict[str, str]:
    """Control and observability names from the home page cards, e.g. C4 -> Harness."""
    page = (ROOT / "index.html").read_text()
    names = dict(re.findall(r'<span class="n">((?:C|Obs-T)\d+)</span><h3>([^<]+)</h3>', page))
    if len(names) < 12:
        sys.exit("Could not read the control names (C1-C9, Obs-T1-T3) from index.html")
    return {k: html.unescape(v) for k, v in names.items()}


def ref_links(refs: str) -> str:
    """Each control as a link to its card on the home page."""
    return "; ".join(f'<a href="/#{c.lower()}">{html.escape(label)}</a>' for c, label in ref_labels(refs, control_names()))


def ref_labels(refs: str, names: dict[str, str]) -> list[tuple[str, str]]:
    """'C1–C3/Obs-T1' -> ['Control 1 – Architecture', ..., 'Observability requirement 1 – ...']."""
    codes = []
    for part in refs.split("/"):
        part = part.strip()
        m = re.fullmatch(r"C(\d+)[–-]C(\d+)", part)
        codes += [f"C{n}" for n in range(int(m[1]), int(m[2]) + 1)] if m else [part]
    labels = []
    for code in codes:
        if code not in names:
            sys.exit(f"Unknown control code {code!r} in CHECKLIST.md")
        kind, num = ("Control", code[1:]) if code.startswith("C") else ("Observability requirement", code[5:])
        labels.append((code, f"{kind} {num} – {names[code]}"))
    return labels

def inline(text: str) -> str:
    out = []
    pos = 0
    token = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)")
    for m in token.finditer(text):
        out.append(emphasis(html.escape(text[pos:m.start()], quote=False)))
        if m.group(1) is not None:
            out.append(f"<code>{html.escape(m.group(1), quote=False)}</code>")
        else:
            label = emphasis(html.escape(m.group(2), quote=False))
            href = rewrite_link(m.group(3))
            if href is None:
                out.append(label)
            else:
                ext = ' rel="noopener"' if href.startswith("http") else ""
                out.append(f'<a href="{html.escape(href)}"{ext}>{label}</a>')
        pos = m.end()
    out.append(emphasis(html.escape(text[pos:], quote=False)))
    return "".join(out)


def emphasis(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    return s


def unbold(s: str) -> str:
    s = s.strip()
    if s.startswith("**") and s.endswith("**") and s.count("**") == 2:
        return s[2:-2]
    return s


# ---------------------------------------------------------------- block markdown

def blocks(lines: list[str]) -> str:
    """Render paragraphs, lists, tables and minor headings."""
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s or s == "---" or s.startswith("*Part of [BRACE]"):
            i += 1
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[2:]]
            t = ['<div class="tablewrap"><table><thead><tr>']
            t += [f"<th>{inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        m = re.match(r"^(#{3,4}) (.*)$", s)
        if m:
            out.append(f"<h4>{inline(unbold(m.group(2)))}</h4>")
            i += 1
            continue
        if re.match(r"^(- |\d+\. )", s):
            ordered = bool(re.match(r"^\d+\. ", s))
            tag = "ol" if ordered else "ul"
            items = []
            while i < len(lines) and re.match(r"^(- |\d+\. )", lines[i].strip()):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i].strip()))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        para = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(\||#|- |\d+\. )", lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


# ---------------------------------------------------------------- parsing

def split_sections(text: str) -> tuple[str, list[str], list[tuple[str, list[str]]]]:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ChecklistError("CHECKLIST.md must start with a '# ' title")
    title = lines[0][2:].strip()
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    for line in lines[1:]:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif sections:
            sections[-1][1].append(line)
        else:
            preamble.append(line)
    return title, preamble, sections


def parse_aspect(letter: str, lines: list[str]) -> dict:
    aspect = {"letter": letter, "question": "", "links": "", "groups": [], "evidence": ""}
    group = None
    item = None
    for line in lines:
        s = line.strip()
        if s.startswith("**Question:**"):
            aspect["question"] = s[len("**Question:**"):].strip()
            continue
        if s.startswith("[Read the") or (s.startswith("[") and not aspect["links"] and group is None):
            aspect["links"] = s
            continue
        if s.startswith("**Evidence to attach:**"):
            aspect["evidence"] = s[len("**Evidence to attach:**"):].strip()
            item = None
            continue
        m = re.match(r"^#{3,4} (.*)$", s)
        if m:
            name = unbold(m.group(1))
            if name == "Remaining checks":
                # Sections with subheadings get their groups from those; sections without
                # them still need the remaining items kept out of the top-3 box.
                group = {"name": "Other checks", "top": False, "items": []}
                aspect["groups"].append(group)
                item = None
                continue
            group ={"name": name, "top": "DO NOTHING ELSE" in name, "items": []}
            aspect["groups"].append(group)
            item = None
            continue
        m = ITEM_RE.match(s)
        if m:
            if group is None:
                group = {"name": "Checks", "top": False, "items": []}
                aspect["groups"].append(group)
            iid, gate, refs, head, body = m.groups()
            if iid[0] != letter:
                raise ChecklistError(f"{iid} appears under aspect {letter}")
            item = {"id": iid, "gate": gate, "refs": refs, "title": head.rstrip("."),
                    "body": unbold(body), "notes": [], "extra": [], "top": group["top"]}
            group["items"].append(item)
            continue
        if s.startswith("- [ ]"):
            raise ChecklistError(f"unparsed checklist item: {s[:80]}")
        if item is not None and line.startswith("  ") and s:
            nm = re.match(r"^\*\*(.+?):\*\*\s*(.*)$", s)
            if nm and nm.group(1) in NOTE_LABELS:
                item["notes"].append((nm.group(1), nm.group(2)))
            elif item["notes"]:
                label, txt = item["notes"][-1]
                item["notes"][-1] = (label, txt + "\n\n" + s)
            else:
                item["extra"].append(s)
            continue
        if s and group is not None and item is None:
            raise ChecklistError(f"unexpected text in aspect {letter}: {s[:80]}")
    return aspect


def parse(text: str) -> dict:
    title, preamble, sections = split_sections(text)
    doc = {"title": title, "preamble": preamble, "howto": [], "aspects": [], "tail": []}
    for name, lines in sections:
        m = re.match(r"^([BRACE]) — (.+)$", name)
        if m:
            if ASPECTS.get(m.group(1)) != m.group(2):
                raise ChecklistError(f"unknown aspect heading: {name}")
            doc["aspects"].append(parse_aspect(m.group(1), lines))
        elif name.lower().startswith("how to use"):
            doc["howto"] = (name, lines)
        else:
            doc["tail"].append((name, lines))
    if [a["letter"] for a in doc["aspects"]] != list("BRACE"):
        raise ChecklistError("expected aspects B, R, A, C, E in order")
    ids = [it["id"] for a in doc["aspects"] for g in a["groups"] for it in g["items"]]
    if len(ids) != len(set(ids)):
        raise ChecklistError("duplicate item IDs")
    doc["count"] = len(ids)
    return doc


# ---------------------------------------------------------------- rendering

def paras(text: str) -> str:
    return "".join(f"<p>{inline(p)}</p>" for p in text.split("\n\n"))


NOTE_STYLE = {
    "Why this is hard": ("hard", '<path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17.5v.01"/>'),
    "If you can't fully do it": ("fallback", '<path d="M4 7h11a5 5 0 0 1 0 10H8"/><path d="M8 13l-4 4 4 4" transform="translate(0 -4)"/>'),
    "Tradeoffs you can accept": ("trade", '<path d="M12 4v16M6 20h12M4 9l4-4 4 4M12 9l4-4 4 4"/><path d="M2 13a2.5 2.5 0 0 0 5 0L4.5 8zM17 13a2.5 2.5 0 0 0 5 0L19.5 8z"/>'),
}


def icon(paths: str) -> str:
    return ('<svg class="ic" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')


LINK_ICON = icon('<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>')


def plain(s: str) -> str:
    return re.sub(r"<[^>]+>", "", inline(s))


def render_item(it: dict) -> str:
    iid = it["id"]
    aspect = ASPECTS[iid[0]]
    num = int(iid[1:])
    title = plain(it["title"])
    notes = ""
    for label, txt in it["notes"]:
        cls, paths = NOTE_STYLE.get(label, NOTE_STYLE["Tradeoffs you can accept"])
        notes += f'<div class="note {cls}"><div class="nl">{icon(paths)}{html.escape(label)}</div>{paras(txt)}</div>'
    extra = "".join(f"<p>{inline(x)}</p>" for x in it["extra"])
    return f"""<li class="item" id="{iid}" data-gate="{it['gate']}">
<input type="checkbox" class="cb" id="cb-{iid}" data-key="{iid}" aria-label="Mark “{title}” done">
<details>
<summary><span class="ttl">{inline(it['title'])}</span></summary>
<div class="body">
<p class="meta"><a class="self" href="#{iid}" title="{iid}: link to this check">{aspect} rule {num} · {inline(it['title'])}<span class="sid">{LINK_ICON}{iid}</span></a></p>
<p class="refs">Controls and requirements: {ref_links(it['refs'])}</p>
<p class="req">{inline(it['body'])}</p>{extra}{notes}
</div>
</details>
</li>"""


def render_aspect(a: dict) -> str:
    letter = a["letter"]
    name = ASPECTS[letter]
    n = sum(len(g["items"]) for g in a["groups"])
    parts = [f"""<section class="aspect" id="{name.lower()}" data-aspect="{letter}">
<div class="ahead"><span class="aletter" aria-hidden="true">{letter}</span><h2>{name}</h2><span class="prog"><span data-prog="{letter}">{n} items</span><span class="pbar" aria-hidden="true"><i data-bar="{letter}"></i></span></span></div>
<p class="question">{inline(a['question'])}</p>"""]
    if a["links"]:
        parts.append(f'<p class="alinks">{inline(a["links"])}</p>')
    for g in [g for g in a["groups"] if g["items"]]:
        cls = "group top3" if g["top"] else "group"
        label = "If you do nothing else: top 3" if g["top"] else g["name"]
        star = icon('<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>') if g["top"] else ""
        parts.append(f'<div class="{cls}"><h3>{star}{inline(label)}</h3><ul class="items">')
        parts += [render_item(it) for it in g["items"]]
        parts.append("</ul></div>")
    if a["evidence"]:
        parts.append(f'<p class="evidence"><strong>Evidence to attach:</strong> {inline(a["evidence"])}</p>')
    parts.append("</section>")
    return "\n".join(parts)


def render_tail(name: str, lines: list[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    body = blocks(lines)
    # Decision checks become real, saved checkboxes.
    counter = [0]

    def box(m: re.Match) -> str:
        counter[0] += 1
        key = f"{slug}-{counter[0]}"
        return (f'<li class="dc"><label><input type="checkbox" class="cb" data-key="{key}"> '
                f"<span>{m.group(1)}</span></label></li>")

    body = re.sub(r"<li>\[ \] (.*?)</li>", box, body)
    return f'<section class="tail" id="{slug}"><h2>{inline(name)}</h2>\n{body}\n</section>'


def render(doc: dict) -> str:
    pre = [l for l in doc["preamble"]]
    intro_html = blocks(pre).replace("<p><strong>High-risk deployments:</strong>",
                                     '<p class="callout"><strong>High-risk deployments:</strong>', 1)
    howto_name, howto_lines = doc["howto"]
    toc = "".join(f'<a href="#{ASPECTS[a["letter"]].lower()}" class="chip-{a["letter"]}"><b>{a["letter"]}</b> {ASPECTS[a["letter"]]}'
                  f'<span class="tc" data-prog="{a["letter"]}-toc"></span></a>' for a in doc["aspects"])
    aspects = "\n".join(render_aspect(a) for a in doc["aspects"])
    tail_sections = [(n, l) for n, l in doc["tail"]]
    tail = "\n".join(render_tail(n, l) for n, l in tail_sections)
    total = doc["count"]
    return (TEMPLATE
            .replace("@@TITLE@@", html.escape(doc["title"]))
            .replace("@@TOTAL@@", str(total))
            .replace("@@INTRO@@", intro_html)
            .replace("@@HOWTO_NAME@@", inline(howto_name))
            .replace("@@HOWTO@@", blocks(howto_lines))
            .replace("@@TOC@@", toc)
            .replace("@@ASPECTS@@", aspects)
            .replace("@@TAIL@@", tail))


TEMPLATE = r"""<!DOCTYPE html>
<!-- Generated by tools/site/gen_checklist_page.py from CHECKLIST.md. Do not edit by hand. -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign-off checklist — BRACE Framework</title>
<meta name="description" content="The BRACE sign-off checklist for autonomous AI agents: @@TOTAL@@ checks across Build-time, Run-time, Agent, Configuration and Ecosystem, each with its priority gate, full requirement and fallbacks.">
<link rel="canonical" href="https://braceframework.org/checklist/">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="BRACE Framework">
<meta property="og:title" content="The BRACE sign-off checklist">
<meta property="og:description" content="@@TOTAL@@ checks across all five BRACE aspects. Tick them off, expand any item for the full requirement.">
<meta property="og:url" content="https://braceframework.org/checklist/">
<meta property="og:image" content="https://braceframework.org/og-checklist.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="BRACE sign-off checklist">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="The BRACE sign-off checklist">
<meta name="twitter:description" content="@@TOTAL@@ checks across all five BRACE aspects.">
<meta name="twitter:image" content="https://braceframework.org/og-checklist.png">
<style>
  :root{
    --ink:#1a1a1a; --muted:#555a63; --primary:#1a4d6e; --accent:#2e8bc0;
    --tint:#eef5fc; --tint2:#dde9f3; --rule:#c8d4df; --bg:#ffffff; --card:#ffffff; --head:#15384f;
    --blocker:#b23a2e; --blocker-bg:#fbecea; --required:#a2650a; --required-bg:#fdf3e1; --detection:#1f6a8a; --detection-bg:#e6f2f8;
    --good:#1f7a4d; --good-bg:#e9f5ee;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --ink:#e4e8ec; --muted:#9aa4ae; --primary:#7fb8de; --accent:#6cb6e6;
      --tint:#16222c; --tint2:#1c2b37; --rule:#2c3b47; --bg:#0f161c; --card:#131d25; --head:#cfe3f2;
      --blocker:#f08a7e; --blocker-bg:#3a1d1a; --required:#e7b25a; --required-bg:#352813; --detection:#7cc4e4; --detection-bg:#142c38;
      --good:#6fcf9b; --good-bg:#16301f;
    }
  }
  :root[data-theme="dark"]{
    --ink:#e4e8ec; --muted:#9aa4ae; --primary:#7fb8de; --accent:#6cb6e6;
    --tint:#16222c; --tint2:#1c2b37; --rule:#2c3b47; --bg:#0f161c; --card:#131d25; --head:#cfe3f2;
    --blocker:#f08a7e; --blocker-bg:#3a1d1a; --required:#e7b25a; --required-bg:#352813; --detection:#7cc4e4; --detection-bg:#142c38;
    --good:#6fcf9b; --good-bg:#16301f;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0; color:var(--ink); background:var(--bg); font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  a{color:var(--accent); text-decoration:none}
  a:hover{text-decoration:underline}
  code{background:var(--tint2); border-radius:4px; padding:1px 5px; font:13.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
  .wrap{max-width:800px; margin:0 auto; padding:0 24px}
  main p,.intro p{max-width:68ch}
  .crumb{background:#1a4d6e; color:#fff; font-size:13px; padding:10px 0}
  .crumb a{color:#cfe2f1}
  header.hero{background:#1a4d6e; color:#fff; padding:40px 0 34px}
  .eyebrow{letter-spacing:.18em; text-transform:uppercase; font-size:12px; opacity:.85; margin:0 0 10px}
  h1{font-size:40px; line-height:1.06; margin:0 0 12px; font-weight:800; letter-spacing:-.5px}
  .lede{font-size:18px; line-height:1.5; margin:0; max-width:40em; opacity:.96}
  .stats{display:flex; flex-wrap:wrap; gap:8px; margin-top:18px; font-size:13px}
  .stats span{background:rgba(255,255,255,.14); border-radius:999px; padding:4px 12px}
  .intro{padding-top:28px; padding-bottom:8px; font-size:16.5px}
  .intro p{margin:10px 0}
  .callout{background:var(--tint); border:1px solid var(--tint2); padding:14px 18px; border-radius:12px}
  details.more{border:1px solid var(--rule); border-radius:12px; margin:14px 0; background:var(--card)}
  details.more>summary{cursor:pointer; padding:10px 16px; font-weight:600; color:var(--primary)}
  details.more>div{padding:0 18px 12px; font-size:15px}
  /* aspect accents: text-safe colour (--a), soft fill (--at) */
  :root{--aB:#4338ca; --aR:#0f766e; --aA:#7e22ce; --aC:#a1530a; --aE:#15803d; --star:#a16207; --star-bg:#fef7e0; --star-rule:#f2d58a}
  @media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){--aB:#a5b4fc; --aR:#5eead4; --aA:#d8b4fe; --aC:#fbbf24; --aE:#86efac; --star:#fcd34d; --star-bg:#2b2410; --star-rule:#5c4a17} }
  :root[data-theme="dark"]{--aB:#a5b4fc; --aR:#5eead4; --aA:#d8b4fe; --aC:#fbbf24; --aE:#86efac; --star:#fcd34d; --star-bg:#2b2410; --star-rule:#5c4a17}
  [data-aspect="B"],.chip-B{--a:var(--aB)} [data-aspect="R"],.chip-R{--a:var(--aR)} [data-aspect="A"],.chip-A{--a:var(--aA)}
  [data-aspect="C"],.chip-C{--a:var(--aC)} [data-aspect="E"],.chip-E{--a:var(--aE)}
  [data-aspect],[class^="chip-"]{--at:color-mix(in srgb, var(--a) 11%, var(--card)); --ar:color-mix(in srgb, var(--a) 35%, var(--card))}
  .ic{flex:none; vertical-align:-3px}
  /* toolbar + sticky TOC */
  .bar{position:sticky; top:0; z-index:5; background:var(--bg); border-bottom:1px solid var(--rule); padding:8px 0; box-shadow:0 4px 14px -10px rgba(0,0,0,.25)}
  .bar .wrap{display:flex; flex-wrap:wrap; gap:8px 14px; align-items:center}
  .toc{display:flex; flex-wrap:wrap; gap:6px}
  .toc a{display:inline-flex; align-items:center; gap:6px; font-size:13px; padding:3px 10px 3px 3px; border-radius:999px; color:var(--ink); white-space:nowrap; background:var(--at, var(--tint)); border:1px solid var(--ar, var(--rule))}
  .toc a:not([class]){padding-left:10px}
  .toc a:hover{text-decoration:none; border-color:var(--a, var(--accent))}
  .toc b{display:inline-grid; place-items:center; width:20px; height:20px; border-radius:50%; background:var(--a); color:var(--card); font-size:11.5px}
  .tc{color:var(--muted); font-size:12px}
  .tools{display:none; gap:8px; align-items:center; margin-left:auto; font-size:13px}
  .js .tools{display:flex}
  .tools select,.tools button{font:inherit; font-size:13px; color:var(--ink); background:var(--card); border:1px solid var(--rule); border-radius:6px; padding:3px 8px; cursor:pointer}
  .overall{display:none; font-size:13px; font-weight:600; color:var(--good)}
  .js .overall{display:inline}
  /* aspects */
  section.aspect,section.tail{padding:30px 0 20px; border-bottom:1px solid var(--rule); scroll-margin-top:60px}
  .ahead{display:flex; align-items:center; gap:12px; flex-wrap:wrap}
  .aletter{display:inline-grid; place-items:center; width:38px; height:38px; border-radius:10px; background:var(--a); color:var(--card); font-weight:800; font-size:18px; box-shadow:0 2px 0 var(--ar)}
  h2{font-size:24px; color:var(--primary); margin:0; letter-spacing:-.3px}
  section.aspect h2{color:var(--ink)}
  section.tail h2{margin-bottom:8px}
  .prog{margin-left:auto; display:flex; align-items:center; gap:10px; font-size:13px; color:var(--muted)}
  .pbar{display:none; width:90px; height:8px; border-radius:999px; background:var(--at); border:1px solid var(--ar); overflow:hidden}
  .js .pbar{display:block}
  .pbar i{display:block; height:100%; width:0; background:var(--a); border-radius:999px; transition:width .25s}
  .question{font-size:16px; font-weight:600; color:var(--head); margin:12px 0 2px}
  .alinks{font-size:14px; margin:4px 0 0; color:var(--muted)}
  .group{margin-top:18px}
  .group h3{font-size:13px; letter-spacing:.02em; color:var(--muted); margin:0 0 8px; font-weight:700}
  .group.top3{background:var(--star-bg); border:1px solid var(--star-rule); border-radius:14px; padding:12px 12px 12px}
  .group.top3 h3{display:flex; align-items:center; gap:7px; color:var(--star); font-size:14.5px; margin:2px 4px 10px}
  .group.top3 h3 .ic{fill:currentColor}
  ul.items{list-style:none; margin:0; padding:0; border:1px solid var(--rule); border-radius:10px; overflow:hidden; background:var(--card)}
  li.item{display:flex; align-items:flex-start; gap:4px; border-top:1px solid var(--rule); padding:0 0 0 12px; box-shadow:inset 4px 0 0 var(--a); scroll-margin-top:70px}
  li.item:first-child{border-top:none}
  li.item:target{background:var(--at)}
  li.item.hidden{display:none}
  li.item details[open]{padding-bottom:2px}
  .cb{flex:none; width:19px; height:19px; margin:13px 6px 0 2px; accent-color:var(--a, var(--good)); cursor:pointer}
  li.item details{flex:1; min-width:0}
  li.item summary{display:flex; align-items:flex-start; gap:10px; padding:11px 14px 11px 4px; cursor:pointer; list-style:none}
  li.item summary::-webkit-details-marker{display:none}
  li.item summary::after{content:""; flex:none; width:7px; height:7px; border-right:2px solid var(--muted); border-bottom:2px solid var(--muted); transform:rotate(45deg); margin:6px 2px 0 4px; transition:transform .15s}
  li.item details[open] summary::after{transform:rotate(-135deg); margin-top:10px}
  li.item summary:hover .ttl{color:var(--a)}
  .ttl{flex:1; min-width:0; font-weight:600; line-height:1.4; overflow-wrap:anywhere}
  li.item.done .ttl{color:var(--muted); text-decoration:line-through; text-decoration-color:var(--rule)}
  .body{padding:0 18px 16px 4px; font-size:16px; line-height:1.65}
  .body p{margin:8px 0}
  .meta{margin:0 0 6px !important}
  a.self{display:inline-flex; flex-wrap:wrap; align-items:center; gap:2px 8px; font-size:12.5px; font-weight:700; color:var(--a); background:var(--at); border-radius:999px; padding:3px 11px}
  a.self:hover{text-decoration:none; box-shadow:inset 0 0 0 1px var(--a)}
  .sid{display:inline-flex; align-items:center; gap:3px; font:600 11.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:var(--muted)}
  .sid .ic{width:13px; height:13px}
  .refs{font-size:12.5px; color:var(--muted); margin-top:0 !important}
  .note{--n:var(--accent); border-radius:10px; padding:4px 14px 6px; margin:12px 0; background:color-mix(in srgb, var(--n) 9%, var(--card)); border:1px solid color-mix(in srgb, var(--n) 25%, var(--card))}
  .note .nl{display:flex; align-items:center; gap:7px; font-size:13px; font-weight:700; color:var(--n); margin-top:8px}
  .note p{margin:6px 0}
  .note.hard{--n:var(--required)}
  .note.fallback{--n:var(--detection)}
  .note.trade{--n:var(--good)}
  .evidence{font-size:14px; color:var(--muted); margin:14px 0 0; padding:10px 14px; border:1px dashed var(--ar); border-radius:10px}
  .tail{font-size:15px}
  .tail h4{font-size:15px; color:var(--head); margin:18px 0 6px}
  .tablewrap{overflow-x:auto}
  table{border-collapse:collapse; width:100%; font-size:14px; margin:8px 0}
  th,td{border:1px solid var(--rule); padding:7px 10px; text-align:left; vertical-align:top}
  th{background:var(--tint2)}
  li.dc{list-style:none; margin:6px 0 6px -1.2em}
  li.dc label{display:flex; gap:8px; cursor:pointer}
  li.dc .cb{margin-top:3px}
  footer{padding:30px 0; color:var(--muted); font-size:14px}
  @media (max-width:640px){
    h1{font-size:30px} .lede{font-size:16px}
    .wrap{padding:0 16px}
    .tools{margin-left:0; width:100%; flex-wrap:wrap}
    .tools label,.overall,.tools button{white-space:nowrap}
    .toc{width:100%; flex-wrap:nowrap; overflow-x:auto; padding-bottom:2px}
    .prog{margin-left:50px; width:100%}
    .group.top3{padding:10px 8px; margin-left:-4px; margin-right:-4px}
    li.item{padding-left:10px}
    li.item summary{padding-right:10px}
    .body{padding-right:12px}
  }
  @media print{
    .bar,.crumb,.cb-hide,footer .noprint{display:none !important}
    header.hero{background:none; color:#000; padding:0}
    body{font-size:11pt; background:#fff; color:#000}
    li.item{break-inside:avoid-page}
    li.item.hidden{display:flex}
    li.item summary::after{display:none}
    details>summary{list-style:none}
    a{color:#000}
  }
</style>
</head>
<body>
<div class="crumb"><div class="wrap"><a href="/">BRACE</a> <span aria-hidden="true">›</span> <span>Sign-off checklist</span></div></div>

<header class="hero">
  <div class="wrap">
    <p class="eyebrow">BRACE · Sign-off checklist</p>
    <h1>@@TITLE@@</h1>
    <p class="lede">@@TOTAL@@ checks in five groups. Each row is one check: tick it when the deployed setup meets it and you can link to proof. Open a row to read the full requirement.</p>
    <div class="stats"><span>Start with the highlighted top 3 in each group</span></div>
  </div>
</header>

<div class="wrap intro">
@@INTRO@@
<details class="more" id="priority-gates"><summary>@@HOWTO_NAME@@ (full instructions)</summary><div>
@@HOWTO@@
</div></details>
</div>

<nav class="bar" aria-label="Checklist sections and tools">
  <div class="wrap">
    <div class="toc">@@TOC@@<a href="#final-sign-off">Sign-off</a></div>
    <div class="tools">
      <span class="overall" id="overall" aria-live="polite"></span>
      <label>Show <select id="gatefilter" aria-label="Filter items">
        <option value="all">All items</option>
        <option value="todo">Unchecked only</option>
      </select></label>
      <button type="button" id="toggleall">Expand all</button>
    </div>
  </div>
</nav>

<main class="wrap">
@@ASPECTS@@
@@TAIL@@
</main>

<footer><div class="wrap">The BRACE Framework · <a href="/">braceframework.org</a> · CC BY 4.0. <span class="noprint">Your ticks are stored only in this browser.</span></div></footer>

<script>
(function(){
  var d=document; d.documentElement.className+=' js';
  var KEY='brace-checklist-v1', state={};
  try{ state=JSON.parse(localStorage.getItem(KEY)||'{}')||{}; }catch(e){ state={}; }
  function save(){ try{ localStorage.setItem(KEY, JSON.stringify(state)); }catch(e){} }
  var boxes=[].slice.call(d.querySelectorAll('input.cb'));
  function refresh(){
    var total=0, done=0;
    [].forEach.call(d.querySelectorAll('section.aspect'), function(sec){
      var items=sec.querySelectorAll('li.item'), n=items.length, c=0;
      [].forEach.call(items,function(li){ var on=li.querySelector('.cb').checked; li.classList.toggle('done',on); if(on)c++; });
      total+=n; done+=c;
      var L=sec.getAttribute('data-aspect');
      sec.querySelector('[data-prog="'+L+'"]').textContent=c+' of '+n+' checked';
      var bar=sec.querySelector('[data-bar="'+L+'"]'); if(bar) bar.style.width=(n?Math.round(100*c/n):0)+'%';
      var t=d.querySelector('[data-prog="'+L+'-toc"]'); if(t) t.textContent=c+'/'+n;
    });
    d.getElementById('overall').textContent=done+' of '+total+' checked';
  }
  boxes.forEach(function(b){
    b.checked=!!state[b.getAttribute('data-key')];
    b.addEventListener('change',function(){ var k=b.getAttribute('data-key'); if(b.checked) state[k]=1; else delete state[k]; save(); refresh(); applyFilter(); });
  });
  var sel=d.getElementById('gatefilter');
  function applyFilter(){
    var v=sel.value;
    [].forEach.call(d.querySelectorAll('li.item'),function(li){
      var show = v==='all' || !li.querySelector('.cb').checked;
      li.classList.toggle('hidden',!show);
    });
    [].forEach.call(d.querySelectorAll('.group'),function(g){
      g.style.display = g.querySelector('li.item:not(.hidden)') ? '' : 'none';
    });
  }
  sel.addEventListener('change',applyFilter);
  var tog=d.getElementById('toggleall');
  tog.addEventListener('click',function(){
    var open=tog.textContent==='Expand all';
    [].forEach.call(d.querySelectorAll('li.item:not(.hidden) details'),function(x){ x.open=open; });
    tog.textContent=open?'Collapse all':'Expand all';
  });
  var opened=[];
  window.addEventListener('beforeprint',function(){ opened=[]; [].forEach.call(d.querySelectorAll('details'),function(x){ if(!x.open){ opened.push(x); x.open=true; } }); });
  window.addEventListener('afterprint',function(){ opened.forEach(function(x){ x.open=false; }); });
  if(location.hash){ var t=d.getElementById(location.hash.slice(1)); if(t&&t.classList.contains('item')) t.querySelector('details').open=true; }
  refresh(); applyFilter();
})();
</script>
</body>
</html>
"""


REF_NOTE = "<strong>Obs-T1</strong> is identity fields"
OBS_NOTES = {f"<strong>Obs-T{n}</strong> is": f'<a href="/#obs-t{n}"><strong>Obs-T{n}</strong></a> is' for n in (1, 2, 3)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if checklist/index.html is out of date")
    args = ap.parse_args()
    try:
        doc = parse(SOURCE.read_text(encoding="utf-8"))
        page = render(doc)
        if REF_NOTE not in page:
            sys.exit("The control reference note in CHECKLIST.md changed; update REF_NOTE")
        for old, new in OBS_NOTES.items():
            page = page.replace(old, new, 1)
    except ChecklistError as e:
        print(f"gen_checklist_page: {e}", file=sys.stderr)
        return 2
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != page:
            print("checklist/index.html is out of date; run python tools/site/gen_checklist_page.py", file=sys.stderr)
            return 1
        print(f"checklist/index.html is up to date ({doc['count']} items)")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({doc['count']} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
