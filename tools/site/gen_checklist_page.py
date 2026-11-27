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
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "CHECKLIST.md"
RECIPES = ROOT / "CHECKLIST-VERIFICATION.md"
ROLES = ROOT / "ROLES.md"
OUTPUT = ROOT / "checklist" / "index.html"

# Filled by parse(): the real item IDs, so only those become links.
ITEM_IDS: set[str] = set()

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
    while target.startswith("../"):
        target = target[3:]
    m = re.match(r"(CHECKLIST|CHECKLIST-VERIFICATION|SELF-ASSESSMENT|otel-conventions|VENDOR-MATRIX|SOURCE-REVIEW"
                 r"|mappings/nist-ai-rmf|mappings/iso-iec-42001|mappings/mitre-atlas|mappings/owasp-agentic-top-10|mappings/owasp-mcp-top-10)\.md(?:#(.*))?$", target)
    if m:
        page = {"CHECKLIST": "/checklist/", "CHECKLIST-VERIFICATION": "/verification/",
                "SELF-ASSESSMENT": "/self-assessment/", "otel-conventions": "/otel-conventions/",
                "VENDOR-MATRIX": "/vendor-matrix/", "SOURCE-REVIEW": "/source-review/",
                "mappings/nist-ai-rmf": "/mappings/nist-ai-rmf/", "mappings/iso-iec-42001": "/mappings/iso-iec-42001/",
                "mappings/mitre-atlas": "/mappings/mitre-atlas/",
                "mappings/owasp-agentic-top-10": "/mappings/owasp-agentic-top-10/",
                "mappings/owasp-mcp-top-10": "/mappings/owasp-mcp-top-10/"}[m.group(1)]
        frag = m.group(2) or ""
        if m.group(1) == "CHECKLIST":
            # Aspect anchors on the checklist page are "build-time", not "b--build-time".
            frag = re.sub(r"^[brace]--", "", frag)
            if frag.startswith("priority-gates"):
                frag = "priority-gates"
        return page + (f"#{frag}" if frag else "")
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

def rule_name(iid: str) -> str:
    """'R11' -> 'Run-time rule 11'."""
    return f"{ASPECTS[iid[0]]} rule {int(iid[1:])}"


def link_ids(s: str) -> str:
    """Turn bare item codes such as E09 into links reading 'Ecosystem rule 9'."""
    def sub(m: re.Match) -> str:
        iid = m.group(1)
        if iid not in ITEM_IDS:
            return iid
        return f'<a class="iref" href="/checklist/#{iid}" title="{iid}">{rule_name(iid)}</a>'
    return re.sub(r"(?<![\w#/-])([BRACE]\d\d)(?![\w-])", sub, s)


def inline(text: str) -> str:
    out = []
    pos = 0
    token = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)")
    for m in token.finditer(text):
        out.append(link_ids(emphasis(html.escape(text[pos:m.start()], quote=False))))
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
    out.append(link_ids(emphasis(html.escape(text[pos:], quote=False))))
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

def gh_slug(heading: str) -> str:
    """GitHub-style heading anchor: 'B — Build-time' -> 'b--build-time'."""
    s = re.sub(r"[*`]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", heading).lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


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
        if s.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append('<pre class="code"><code>' + html.escape("\n".join(code)) + "</code></pre>")
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
            out.append(f'<h4 id="{gh_slug(unbold(m.group(2)))}">{inline(unbold(m.group(2)))}</h4>')
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
        while i < len(lines) and lines[i].strip() and not re.match(r"^(\||#|- |\d+\. |```)", lines[i].strip()):
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
    fenced = False
    for line in lines[1:]:
        if line.strip().startswith("```"):
            fenced = not fenced
        if line.startswith("## ") and not fenced:
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
    ITEM_IDS.clear()
    ITEM_IDS.update(ids)
    return doc


def load_recipes(ids: list[str]) -> dict[str, tuple[str, str]]:
    """Item -> (test and expected result, evidence to keep) from CHECKLIST-VERIFICATION.md."""
    recipes: dict[str, tuple[str, str]] = {}
    for line in RECIPES.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([BRACE]\d\d) \|(.*)\|\s*$", line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) != 2 or not all(cells):
            raise ChecklistError(f"recipe row for {m.group(1)} must have a test and an evidence cell")
        if m.group(1) in recipes:
            raise ChecklistError(f"two recipes for {m.group(1)}")
        recipes[m.group(1)] = (cells[0], cells[1])
    missing = [i for i in ids if i not in recipes]
    if missing:
        raise ChecklistError(f"no verification recipe in CHECKLIST-VERIFICATION.md for: {', '.join(missing)}")
    return recipes


def load_roles(ids: list[str]) -> dict[str, tuple[str, list[str]]]:
    """Item -> (Lead, [Shares]) from the item tables in ROLES.md."""
    roles: dict[str, tuple[str, list[str]]] = {}
    for line in ROLES.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([BRACE]\d\d) \| (?:Blocker|Required|Detection) \|[^|]*\| \*\*([^*|]+)\*\* \|([^|]*)\|\s*$", line)
        if m:
            shares = [x.strip() for x in m.group(3).split(",") if x.strip() and x.strip() not in ("—", "-")]
            roles[m.group(1)] = (m.group(2).strip(), shares)
    missing = [i for i in ids if i not in roles]
    if missing:
        raise ChecklistError(f"no Lead role in ROLES.md for: {', '.join(missing)}")
    return roles


def guide_anchors() -> dict[str, str]:
    """Item -> guide URL, where the aspect guide has an id on that item's rule entry."""
    found = {}
    for letter, name in ASPECTS.items():
        page = ROOT / "guides" / name.lower() / "index.html"
        if page.exists():
            for iid in re.findall(r'<li class="r-[BRACE]" id="([BRACE]\d\d)"', page.read_text(encoding="utf-8")):
                found[iid] = f"/guides/{name.lower()}/#{iid}"
    return found


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


HOW_ICON = icon('<path d="M9 11l3 3 8-8"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9"/>')
BOOK_ICON = icon('<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5M8 7h7"/>')
USER_ICON = icon('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>')


def render_item(it: dict, extras: dict) -> str:
    iid = it["id"]
    title = plain(it["title"])
    notes = ""
    for label, txt in it["notes"]:
        cls, paths = NOTE_STYLE.get(label, NOTE_STYLE["Tradeoffs you can accept"])
        notes += f'<div class="note {cls}"><div class="nl">{icon(paths)}{html.escape(label)}</div>{paras(txt)}</div>'
    extra = "".join(f"<p>{inline(x)}</p>" for x in it["extra"])
    lead, shares = extras["roles"][iid]
    with_ = f' <span class="with">(with {html.escape(", ".join(shares))})</span>' if shares else ""
    test, evidence = extras["recipes"][iid]
    guide = extras["guides"].get(iid)
    learn = (f'<p class="learn"><a href="{guide}">{BOOK_ICON}Learn why in the {ASPECTS[iid[0]]} guide</a></p>'
             if guide else "")
    top = ' data-top="1"' if it["top"] else ""
    return f"""<li class="item" id="{iid}" data-gate="{it['gate']}"{top}>
<button type="button" class="st" data-key="{iid}" aria-haspopup="menu" aria-expanded="false" aria-label="Status of “{title}”: Not started"></button>
<details>
<summary><span class="ttl">{inline(it['title'])}</span></summary>
<div class="body">
<p class="meta"><a class="self" href="#{iid}" title="{iid}: link to this check">{rule_name(iid)} · {inline(it['title'])}<span class="sid">{LINK_ICON}{iid}</span></a></p>
<p class="refs">Controls and requirements: {ref_links(it['refs'])}</p>
<p class="owner">{USER_ICON}Usually led by: <strong>{html.escape(lead)}</strong>{with_}</p>
<p class="req">{inline(it['body'])}</p>{extra}{notes}
<div class="how"><div class="nl">{HOW_ICON}How to check it</div>
<h4 class="hl">Test and expected result</h4><p>{inline(test)}</p>
<h4 class="hl">Evidence to keep</h4><p>{inline(evidence)}</p></div>
{learn}<div class="mine"><label for="note-{iid}">Your note <span>(evidence link or comment, saved in this browser)</span></label><textarea id="note-{iid}" data-note="{iid}" rows="2"></textarea></div>
</div>
</details>
</li>"""


def render_aspect(a: dict, extras: dict) -> str:
    letter = a["letter"]
    name = ASPECTS[letter]
    n = sum(len(g["items"]) for g in a["groups"])
    parts = [f"""<section class="aspect" id="{name.lower()}" data-aspect="{letter}">
<div class="ahead"><span class="aletter" aria-hidden="true">{letter}</span><h2>{name}</h2><span class="prog"><span data-prog="{letter}">{n} checks</span><span class="pbar" aria-hidden="true"><i data-bar="{letter}"></i></span></span></div>
<p class="question">{inline(a['question'])}</p>"""]
    if a["links"]:
        parts.append(f'<p class="alinks">{inline(a["links"])}</p>')
    for g in [g for g in a["groups"] if g["items"]]:
        cls = "group top3" if g["top"] else "group"
        label = "If you do nothing else: top 3" if g["top"] else g["name"]
        star = icon('<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>') if g["top"] else ""
        parts.append(f'<div class="{cls}"><h3>{star}{inline(label)}</h3><ul class="items">')
        parts += [render_item(it, extras) for it in g["items"]]
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
    ids = [it["id"] for a in doc["aspects"] for g in a["groups"] for it in g["items"]]
    extras = {"recipes": load_recipes(ids), "roles": load_roles(ids), "guides": guide_anchors()}
    # The opening notes (high-risk note, when to run it, two kinds of trouble) live in the
    # "How to use" panel, ahead of its numbered steps.
    intro_html = blocks(doc["preamble"]).replace("<p><strong>High-risk deployments:</strong>",
                                                 '<p class="callout"><strong>High-risk deployments:</strong>', 1)
    howto_name, howto_lines = doc["howto"]
    toc = "".join(f'<a href="#{ASPECTS[a["letter"]].lower()}" class="chip-{a["letter"]}"><b>{a["letter"]}</b> {ASPECTS[a["letter"]]}'
                  f'<span class="tc" data-prog="{a["letter"]}-toc"></span></a>' for a in doc["aspects"])
    aspects = "\n".join(render_aspect(a, extras) for a in doc["aspects"])
    tail = "\n".join(render_tail(n, l) for n, l in doc["tail"])
    items_js = ",".join(
        '"%s":[%s,%s,%s]' % (it["id"], json.dumps(plain(it["title"])), json.dumps(extras["roles"][it["id"]][0]),
                             json.dumps(", ".join(extras["roles"][it["id"]][1])))
        for a in doc["aspects"] for g in a["groups"] for it in g["items"])
    return (TEMPLATE
            .replace("@@TITLE@@", html.escape(doc["title"]))
            .replace("@@TOTAL@@", str(doc["count"]))
            .replace("@@INTRO@@", intro_html)
            .replace("@@HOWTO_NAME@@", inline(howto_name))
            .replace("@@HOWTO@@", blocks(howto_lines))
            .replace("@@TOC@@", toc)
            .replace("@@ASPECTS@@", aspects)
            .replace("@@TAIL@@", tail)
            .replace("@@ITEMS_JS@@", "{" + items_js.replace("</", "<\\/") + "}"))


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
  .start{display:inline-block; margin-top:18px; background:#fff; color:#1a4d6e; font-weight:700; font-size:15px; border-radius:999px; padding:8px 18px}
  .start:hover{text-decoration:none; background:#eef5fc}
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
  /* status control */
  .st{display:none; flex:none; width:24px; height:24px; margin:10px 4px 0 0; padding:0; border-radius:50%; border:2px solid var(--rule); background:var(--card); color:var(--card); cursor:pointer; place-items:center}
  .js .st{display:grid}
  .st:hover{border-color:var(--a)}
  .st:focus-visible,.stmenu button:focus-visible,.tools :focus-visible{outline:2px solid var(--accent); outline-offset:2px}
  .st svg{width:14px; height:14px}
  li.s-done .st{background:var(--good); border-color:var(--good)}
  li.s-notyet .st{border-color:var(--required); color:var(--required)}
  li.s-na .st{background:var(--muted); border-color:var(--muted)}
  li.s-done .ttl,li.s-na .ttl{color:var(--muted)}
  li.s-done .ttl{text-decoration:line-through; text-decoration-color:var(--rule)}
  .stmenu{position:absolute; z-index:20; background:var(--card); border:1px solid var(--rule); border-radius:10px; padding:5px; box-shadow:0 10px 28px -10px rgba(0,0,0,.35); min-width:170px}
  .stmenu[hidden]{display:none}
  .stmenu button{display:flex; width:100%; align-items:center; gap:9px; font:inherit; font-size:14px; color:var(--ink); background:none; border:0; border-radius:7px; padding:6px 10px; cursor:pointer; text-align:left}
  .stmenu button:hover,.stmenu button:focus{background:var(--tint)}
  .stmenu button[aria-checked="true"]{font-weight:700}
  .stmenu i{display:inline-grid; place-items:center; width:18px; height:18px; border-radius:50%; border:2px solid var(--rule); color:var(--card)}
  .stmenu i svg{width:11px; height:11px}
  .stmenu .m-done i{background:var(--good); border-color:var(--good)}
  .stmenu .m-notyet i{border-color:var(--required); color:var(--required)}
  .stmenu .m-na i{background:var(--muted); border-color:var(--muted)}
  /* per-item panels */
  .owner{display:flex; align-items:center; gap:6px; flex-wrap:wrap; font-size:13.5px; color:var(--muted); margin:2px 0 8px !important}
  .owner strong{color:var(--ink); font-weight:600}
  .how{border-radius:10px; padding:4px 14px 8px; margin:14px 0; background:var(--tint); border:1px solid var(--tint2)}
  .how .nl{display:flex; align-items:center; gap:7px; font-size:13px; font-weight:700; color:var(--primary); margin-top:8px}
  .how h4.hl{font-size:12.5px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); margin:10px 0 0}
  .how p{margin:3px 0 6px; font-size:15.5px}
  .learn{margin:10px 0 !important; font-size:15px}
  .learn a{display:inline-flex; align-items:center; gap:6px; font-weight:600}
  a.iref{white-space:nowrap; font-weight:600}
  .mine{display:none; margin:14px 0 4px}
  .js .mine{display:block}
  .mine label{display:block; font-size:13px; font-weight:700; color:var(--ink); margin-bottom:4px}
  .mine label span{font-weight:400; color:var(--muted)}
  .mine textarea{display:block; width:100%; font:inherit; font-size:15px; color:var(--ink); background:var(--card); border:1px solid var(--rule); border-radius:8px; padding:7px 10px; resize:vertical; min-height:42px}
  .mine textarea:focus{outline:2px solid var(--accent); outline-offset:0; border-color:transparent}
  /* review */
  .rvb{flex:none; align-self:center; font-size:11.5px; font-weight:700; border-radius:999px; padding:1px 9px; white-space:nowrap}
  .rv-gap{color:var(--blocker); background:var(--blocker-bg)}
  .rv-needs_evidence{color:var(--required); background:var(--required-bg)}
  .rv-likely_pass{color:var(--good); background:var(--good-bg)}
  .rv-na_candidate{color:var(--muted); background:var(--tint2)}
  .review{border-radius:10px; padding:4px 14px 8px; margin:14px 0; border:1px solid var(--rule); border-left:4px solid var(--muted); background:var(--card); color:var(--ink)}
  .review.rv-gap{border-left-color:var(--blocker)} .review.rv-needs_evidence{border-left-color:var(--required)} .review.rv-likely_pass{border-left-color:var(--good)}
  .review .nl{font-size:13px; font-weight:700; margin-top:8px}
  .review p{margin:5px 0}
  .review ol{margin:6px 0; padding-left:1.4em; font-size:15px}
  .revbar{display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:18px 0 0; padding:10px 14px; border-radius:10px; background:var(--tint); border:1px solid var(--tint2); font-size:14px}
  .revbar[hidden],.nomatch[hidden]{display:none}
  .revbar span{flex:1; min-width:12em}
  .revbar button,.moremenu button{font:inherit; font-size:13px; color:var(--ink); background:var(--card); border:1px solid var(--rule); border-radius:6px; padding:4px 10px; cursor:pointer}
  .nomatch{margin:24px 0; color:var(--muted)}
  section.aspect.empty{display:none}
  /* toolbar extras */
  .tools{width:100%; flex-wrap:wrap}
  .tools input[type=search]{font:inherit; font-size:14px; color:var(--ink); background:var(--card); border:1px solid var(--rule); border-radius:6px; padding:4px 10px; flex:1 1 160px; min-width:0}
  .tools label.show{display:inline-flex; align-items:center; gap:5px; color:var(--muted)}
  .morew{position:relative}
  .moremenu{position:absolute; right:0; top:calc(100% + 6px); z-index:20; width:230px; background:var(--card); border:1px solid var(--rule); border-radius:10px; padding:8px; box-shadow:0 10px 28px -10px rgba(0,0,0,.35); display:flex; flex-direction:column; gap:2px}
  .moremenu[hidden]{display:none}
  .moremenu button{text-align:left; border:0; padding:7px 10px; font-size:14px; background:none}
  .moremenu button[hidden]{display:none}
  .moremenu button:hover{background:var(--tint)}
  .mnote{margin:4px 10px 2px; font-size:12px; color:var(--muted); line-height:1.4}
  .overall{margin-left:auto; white-space:nowrap}
  .flash{font-size:13px; color:var(--good); width:100%; text-align:right}
  .flash:empty{display:none}
  section.aspect,section.tail{scroll-margin-top:110px}
  li.item{scroll-margin-top:120px}
  @media (max-width:640px){
    .tools input[type=search]{flex-basis:100%}
    .bar{position:static}
    .tools label.show .lbl{position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0)}
    .rvb{font-size:11px; padding:1px 7px}
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
    .bar,.crumb,.cb-hide,footer .noprint,.st,.mine,.revbar button,.start,.stmenu{display:none !important}
    details::details-content{content-visibility:visible; display:block}
    .how,.note,.review{break-inside:avoid}
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
    <p class="lede">Welcome. These @@TOTAL@@ checks help your team see how well an AI agent is protected, one plain question at a time.</p>
    <a class="start" href="#build-time">Start here: the top 3 in each area <span aria-hidden="true">→</span></a>
  </div>
</header>

<div class="wrap intro">
<details class="more" id="priority-gates"><summary>@@HOWTO_NAME@@</summary><div>
@@INTRO@@
@@HOWTO@@
</div></details>
</div>

<nav class="bar" aria-label="Checklist sections and tools">
  <div class="wrap">
    <div class="toc">@@TOC@@<a href="#final-sign-off">Sign-off</a></div>
    <div class="tools">
      <input type="search" id="q" placeholder="Search checks" aria-label="Search checks by title, requirement or rule name" autocomplete="off">
      <label class="show"><span class="lbl">Show</span> <select id="gatefilter">
        <option value="all">All checks</option>
        <option value="top">Top 3 only</option>
        <option value="todo">Not done yet</option>
      </select></label>
      <button type="button" id="toggleall">Expand all</button>
      <div class="morew">
        <button type="button" id="morebtn" aria-expanded="false" aria-controls="moremenu">More <span aria-hidden="true">▾</span></button>
        <div class="moremenu" id="moremenu" hidden>
          <button type="button" id="copymd">Copy as Markdown</button>
          <button type="button" id="dlcsv">Download CSV</button>
          <button type="button" id="loadrev">Load a review file…</button>
          <button type="button" id="clearrev2" hidden>Clear review</button>
          <input type="file" id="revfile" accept=".json,application/json" hidden>
          <p class="mnote">Review files are read in this browser. Nothing is uploaded.</p>
        </div>
      </div>
      <span class="overall" id="overall"></span>
      <span class="flash" id="flash" role="status" aria-live="polite"></span>
    </div>
  </div>
</nav>

<main class="wrap">
<div class="revbar" id="revbar" hidden><span id="revtext"></span><button type="button" id="clearrev">Clear review</button></div>
<p class="nomatch" id="nomatch" hidden>No checks match. Try other words, or show all checks.</p>
@@ASPECTS@@
@@TAIL@@
</main>

<footer><div class="wrap">The BRACE Framework · <a href="/">braceframework.org</a> · Content CC BY 4.0 · Code Apache-2.0. <span class="noprint">Your statuses and notes are stored only in this browser.</span></div></footer>

<script>
(function(){
  var d=document; d.documentElement.className+=' js';
  var ITEMS=@@ITEMS_JS@@;
  var AREA={B:'Build-time',R:'Run-time',A:'Agent',C:'Configuration',E:'Ecosystem'};
  var LABEL={todo:'Not started',done:'Done',notyet:'Not yet',na:"Doesn't apply"};
  var ORDER=['todo','done','notyet','na'];
  var ICON={todo:'',
    done:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    notyet:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" aria-hidden="true"><path d="M12 6v6l4 2.5"/></svg>',
    na:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" aria-hidden="true"><path d="M6 12h12"/></svg>'};
  var RV={gap:'Gap',needs_evidence:'Needs evidence',likely_pass:'Likely pass',na_candidate:'N/A candidate'};
  function load(k){ try{ return JSON.parse(localStorage.getItem(k)||'null'); }catch(e){ return null; } }
  function store(k,v){ try{ if(v===null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); }catch(e){} }
  function each(sel,fn,root){ [].forEach.call((root||d).querySelectorAll(sel),fn); }

  // Ticks for the sign-off decision boxes stay in the original key.
  var KEY='brace-checklist-v1', ticks=load(KEY)||{};
  // Item status: {ID:{s:'done'|'notyet'|'na', n:'note', src:'review'}}. Old ticks migrate to Done.
  var SKEY='brace-status-v1', state=load(SKEY);
  if(!state || typeof state!=='object'){ state={}; Object.keys(ticks).forEach(function(k){ if(ITEMS[k]&&ticks[k]) state[k]={s:'done'}; }); store(SKEY,state); }
  function rec(id){ var r=state[id]; return (r&&typeof r==='object')?r:{}; }
  function status(id){ var s=rec(id).s; return LABEL[s]?s:'todo'; }
  function setRec(id,r){ if(!r.s||r.s==='todo') delete r.s; if(!r.n) delete r.n; if(!r.s) delete r.src; if(Object.keys(r).length) state[id]=r; else delete state[id]; store(SKEY,state); }
  function complete(s){ return s==='done'||s==='na'; }

  each('input.cb',function(b){
    b.checked=!!ticks[b.getAttribute('data-key')];
    b.addEventListener('change',function(){ var k=b.getAttribute('data-key'); if(b.checked) ticks[k]=1; else delete ticks[k]; store(KEY,ticks); });
  });

  function paint(li){
    var id=li.id, s=status(id), b=li.querySelector('.st');
    ORDER.forEach(function(x){ li.classList.toggle('s-'+x, x===s && x!=='todo'); });
    b.innerHTML=ICON[s];
    b.setAttribute('aria-label','Status of “'+ITEMS[id][0]+'”: '+LABEL[s]+'. Change status');
    b.title=LABEL[s];
  }
  function refresh(){
    var total=0, done=0;
    each('section.aspect',function(sec){
      var items=sec.querySelectorAll('li.item'), n=items.length, c=0;
      [].forEach.call(items,function(li){ paint(li); if(complete(status(li.id))) c++; });
      total+=n; done+=c;
      var L=sec.getAttribute('data-aspect');
      sec.querySelector('[data-prog="'+L+'"]').textContent=c+' of '+n+' complete';
      var bar=sec.querySelector('[data-bar="'+L+'"]'); if(bar) bar.style.width=(n?Math.round(100*c/n):0)+'%';
      var t=d.querySelector('[data-prog="'+L+'-toc"]'); if(t) t.textContent=c+'/'+n;
    });
    d.getElementById('overall').textContent=done+' of '+total+' complete';
  }

  // ---- status menu (one shared menu, opened beside the clicked button)
  var menu=d.createElement('div'); menu.className='stmenu'; menu.setAttribute('role','menu'); menu.hidden=true;
  ORDER.forEach(function(s){
    var b=d.createElement('button'); b.type='button'; b.className='m-'+s; b.setAttribute('role','menuitemradio'); b.setAttribute('data-s',s);
    var i=d.createElement('i'); i.innerHTML=ICON[s]; b.appendChild(i); b.appendChild(d.createTextNode(LABEL[s])); menu.appendChild(b);
  });
  d.body.appendChild(menu);
  var menuFor=null;
  function closeMenu(focus){ if(!menuFor) return; menu.hidden=true; menuFor.setAttribute('aria-expanded','false'); if(focus) menuFor.focus(); menuFor=null; }
  function openMenu(btn){
    closeMenu(); menuFor=btn; var id=btn.getAttribute('data-key'), s=status(id);
    menu.setAttribute('aria-label','Status of '+id);
    each('button',function(x){ x.setAttribute('aria-checked', x.getAttribute('data-s')===s?'true':'false'); },menu);
    menu.hidden=false; btn.setAttribute('aria-expanded','true');
    var r=btn.getBoundingClientRect();
    var left=Math.min(r.left+window.scrollX, window.scrollX+d.documentElement.clientWidth-menu.offsetWidth-8);
    menu.style.left=Math.max(8,left)+'px'; menu.style.top=(r.bottom+window.scrollY+4)+'px';
    (menu.querySelector('[aria-checked="true"]')||menu.firstChild).focus();
  }
  menu.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b||!menuFor) return;
    var id=menuFor.getAttribute('data-key'), r=rec(id); r.s=b.getAttribute('data-s'); delete r.src; setRec(id,r);
    closeMenu(true); refresh(); applyFilter();
  });
  menu.addEventListener('keydown',function(e){
    var bs=[].slice.call(menu.querySelectorAll('button')), i=bs.indexOf(d.activeElement);
    if(e.key==='ArrowDown'){ e.preventDefault(); bs[(i+1)%bs.length].focus(); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); bs[(i-1+bs.length)%bs.length].focus(); }
    else if(e.key==='Home'){ e.preventDefault(); bs[0].focus(); }
    else if(e.key==='End'){ e.preventDefault(); bs[bs.length-1].focus(); }
    else if(e.key==='Escape'||e.key==='Tab'){ e.preventDefault(); closeMenu(true); }
  });
  each('button.st',function(b){
    b.addEventListener('click',function(e){ e.stopPropagation(); if(menuFor===b) closeMenu(true); else openMenu(b); });
    b.addEventListener('keydown',function(e){ if(e.key==='ArrowDown'){ e.preventDefault(); openMenu(b); } });
  });
  d.addEventListener('click',function(e){
    if(menuFor && !menu.contains(e.target)) closeMenu(false);
    if(!more.hidden && !e.target.closest('.morew')) setMore(false);
  });
  window.addEventListener('resize',function(){ closeMenu(false); });

  // ---- notes
  each('textarea[data-note]',function(t){
    var id=t.getAttribute('data-note'); t.value=rec(id).n||'';
    t.addEventListener('input',function(){ var r=rec(id); r.n=t.value; setRec(id,r); });
  });

  // ---- search + filter
  var sel=d.getElementById('gatefilter'), q=d.getElementById('q');
  var hay={};
  each('li.item',function(li){
    hay[li.id]=(li.id+' '+li.querySelector('.ttl').textContent+' '+li.querySelector('.meta').textContent+' '+li.querySelector('.req').textContent).toLowerCase();
  });
  function applyFilter(){
    var v=sel.value, words=q.value.toLowerCase().split(/\s+/).filter(Boolean), any=false;
    each('li.item',function(li){
      var show = v==='all' || (v==='top' && li.hasAttribute('data-top')) || (v==='todo' && !complete(status(li.id)));
      if(show && words.length) show=words.every(function(w){ return hay[li.id].indexOf(w)>=0; });
      li.classList.toggle('hidden',!show); if(show) any=true;
    });
    each('.group',function(g){ g.style.display = g.querySelector('li.item:not(.hidden)') ? '' : 'none'; });
    var narrowed = v!=='all' || words.length>0;
    each('section.aspect',function(s){ s.classList.toggle('empty', narrowed && !s.querySelector('li.item:not(.hidden)')); });
    d.getElementById('nomatch').hidden=any;
  }
  sel.addEventListener('change',applyFilter);
  q.addEventListener('input',applyFilter);

  var tog=d.getElementById('toggleall');
  tog.addEventListener('click',function(){
    var open=tog.textContent==='Expand all';
    each('li.item:not(.hidden) details',function(x){ x.open=open; });
    tog.textContent=open?'Collapse all':'Expand all';
  });

  // ---- More menu (disclosure)
  var more=d.getElementById('moremenu'), moreBtn=d.getElementById('morebtn');
  function setMore(open){ more.hidden=!open; moreBtn.setAttribute('aria-expanded',open?'true':'false'); }
  moreBtn.addEventListener('click',function(){ setMore(more.hidden); if(!more.hidden) more.querySelector('button').focus(); });
  more.addEventListener('keydown',function(e){ if(e.key==='Escape'){ setMore(false); moreBtn.focus(); } });
  var flashT;
  function flash(msg){ var f=d.getElementById('flash'); f.textContent=msg; clearTimeout(flashT); flashT=setTimeout(function(){ f.textContent=''; },5000); }

  // ---- export
  function rows(){
    return Object.keys(ITEMS).map(function(id){
      var it=ITEMS[id];
      return [id, AREA[id[0]]+' rule '+parseInt(id.slice(1),10), it[0], AREA[id[0]], LABEL[status(id)], rec(id).n||'', it[1]+(it[2]?' (with '+it[2]+')':'')];
    });
  }
  var HEAD=['ID','Rule','Title','Area','Status','Note','Owner'];
  d.getElementById('copymd').addEventListener('click',function(){
    function cell(x){ return String(x).replace(/\\/g,'\\\\').replace(/\|/g,'\\|').replace(/\r?\n/g,'<br>'); }
    var md='| '+HEAD.join(' | ')+' |\n|'+HEAD.map(function(){return '---';}).join('|')+'|\n'+rows().map(function(r){ return '| '+r.map(cell).join(' | ')+' |'; }).join('\n')+'\n';
    function done(){ flash('Copied 53 checks as Markdown.'); setMore(false); }
    function fallback(){ var t=d.createElement('textarea'); t.value=md; t.style.position='fixed'; t.style.opacity='0'; d.body.appendChild(t); t.select(); try{ d.execCommand('copy'); done(); }catch(e){ flash('Copy failed in this browser.'); } d.body.removeChild(t); }
    if(navigator.clipboard&&navigator.clipboard.writeText) navigator.clipboard.writeText(md).then(done,fallback); else fallback();
  });
  d.getElementById('dlcsv').addEventListener('click',function(){
    function cell(x){ x=String(x); if(/^[=+\-@\t\r]/.test(x)) x="'"+x; return '"'+x.replace(/"/g,'""')+'"'; }
    var csv=[HEAD].concat(rows()).map(function(r){ return r.map(cell).join(','); }).join('\r\n')+'\r\n';
    var a=d.createElement('a'); a.href=URL.createObjectURL(new Blob(['﻿'+csv],{type:'text/csv;charset=utf-8'}));
    a.download='brace-checklist-status.csv'; d.body.appendChild(a); a.click(); d.body.removeChild(a);
    setTimeout(function(){ URL.revokeObjectURL(a.href); },1000);
    flash('Downloaded brace-checklist-status.csv.'); setMore(false);
  });

  // ---- review file (read locally; every value from it is shown with textContent only)
  var RKEY='brace-review-v1';
  function str(x,max){ return typeof x==='string' ? x.slice(0,max||2000) : ''; }
  function sanitize(data){
    if(!data||typeof data!=='object'||!Array.isArray(data.findings)) throw new Error('This file has no "findings" list.');
    var out={meta:{repo:str(data.repo,200), at:str(data.reviewed_at,40)}, f:{}}, n=0;
    data.findings.forEach(function(f){
      if(!f||typeof f!=='object'||!ITEMS[f.item]||!RV[f.rating]) return;
      var fix=(f.fix&&typeof f.fix==='object')?f.fix:{};
      out.f[f.item]={r:f.rating, s:str(f.summary), n:str(f.next_step),
        steps:Array.isArray(fix.steps)?fix.steps.filter(function(x){return typeof x==='string';}).slice(0,30).map(function(x){return x.slice(0,1000);}):[],
        dw:str(fix.done_when)};
      n++;
    });
    if(!n) throw new Error('No findings in this file match checklist items.');
    return out;
  }
  function clearReviewUI(){
    each('.rvb, .review',function(x){ x.parentNode.removeChild(x); });
    d.getElementById('revbar').hidden=true; d.getElementById('clearrev2').hidden=true;
  }
  function showReview(rv){
    clearReviewUI(); if(!rv) return;
    var ids=Object.keys(rv.f);
    ids.forEach(function(id){
      var f=rv.f[id], li=d.getElementById(id); if(!li) return;
      var badge=d.createElement('span'); badge.className='rvb rv-'+f.r; badge.textContent=RV[f.r];
      li.querySelector('summary').appendChild(badge);
      var p=d.createElement('div'); p.className='review rv-'+f.r;
      function add(tag,cls,text){ var e=d.createElement(tag); if(cls) e.className=cls; if(text) e.textContent=text; p.appendChild(e); return e; }
      add('div','nl','From your review: '+RV[f.r]);
      if(f.s) add('p','',f.s);
      // `code` spans become <code>; every piece is still inserted as text, never as HTML.
      function rich(el,text){ String(text).split('`').forEach(function(part,i){ if(!part) return; if(i%2){ var c=d.createElement('code'); c.textContent=part; el.appendChild(c); } else el.appendChild(d.createTextNode(part)); }); }
      if(f.n){ var np=add('p',''); var b=d.createElement('strong'); b.textContent='Next step: '; np.appendChild(b); rich(np,f.n); }
      if(f.steps.length){ var ol=add('ol',''); f.steps.forEach(function(s){ var x=d.createElement('li'); rich(x,s); ol.appendChild(x); }); }
      if(f.dw){ var dp=add('p',''); var b2=d.createElement('strong'); b2.textContent='Done when: '; dp.appendChild(b2); rich(dp,f.dw); }
      var body=li.querySelector('.body'); body.insertBefore(p, body.querySelector('.how'));
    });
    var gaps=ids.filter(function(id){ return rv.f[id].r==='gap'; }).length;
    d.getElementById('revtext').textContent='Review loaded'+(rv.meta.repo?' for '+rv.meta.repo:'')+(rv.meta.at?' ('+rv.meta.at.slice(0,10)+')':'')+': '+ids.length+' findings, '+gaps+' gaps. Look for the badges below.';
    d.getElementById('revbar').hidden=false; d.getElementById('clearrev2').hidden=false;
  }
  var review=load(RKEY); try{ showReview(review); }catch(e){ review=null; store(RKEY,null); }
  var fileIn=d.getElementById('revfile');
  d.getElementById('loadrev').addEventListener('click',function(){ fileIn.click(); });
  fileIn.addEventListener('change',function(){
    var file=fileIn.files&&fileIn.files[0]; fileIn.value=''; if(!file) return;
    if(file.size>5*1024*1024){ flash('That file is too large to be a review file.'); return; }
    var fr=new FileReader();
    fr.onload=function(){
      try{
        review=sanitize(JSON.parse(fr.result));
        Object.keys(review.f).forEach(function(id){
          var r=rec(id), f=review.f[id];
          if(!r.s && (f.r==='gap'||f.r==='needs_evidence')){ r.s='notyet'; r.src='review'; setRec(id,r); }
        });
        store(RKEY,review); showReview(review); refresh(); applyFilter(); setMore(false);
        flash('Review loaded. Nothing was uploaded.');
      }catch(e){ flash('Could not read that review file: '+(e&&e.message?e.message:'not valid JSON')); }
    };
    fr.onerror=function(){ flash('Could not read that file.'); };
    fr.readAsText(file);
  });
  function clearReview(){
    Object.keys(state).forEach(function(id){ var r=rec(id); if(r.src==='review'){ delete r.s; setRec(id,r); } });
    review=null; store(RKEY,null); clearReviewUI(); refresh(); applyFilter(); setMore(false); flash('Review cleared.');
  }
  d.getElementById('clearrev').addEventListener('click',clearReview);
  d.getElementById('clearrev2').addEventListener('click',clearReview);

  // ---- open the target of a link such as /checklist/#E09
  function openTarget(){
    if(!location.hash) return;
    var t; try{ t=d.getElementById(decodeURIComponent(location.hash.slice(1))); }catch(e){ return; }
    if(!t) return;
    if(t.classList.contains('item') && t.classList.contains('hidden')){ sel.value='all'; q.value=''; applyFilter(); }
    if(t.classList.contains('item')) t.querySelector('details').open=true;
    for(var p=t; p; p=p.parentElement){ if(p.tagName==='DETAILS') p.open=true; }
    t.scrollIntoView();
  }
  window.addEventListener('hashchange',openTarget);

  var opened=[];
  window.addEventListener('beforeprint',function(){ opened=[]; each('details',function(x){ if(!x.open){ opened.push(x); x.open=true; } }); });
  window.addEventListener('afterprint',function(){ opened.forEach(function(x){ x.open=false; }); });
  refresh(); applyFilter(); openTarget();
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
