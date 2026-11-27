"""Render a BRACE action plan as one self-contained web page.

Used by `action_plan.py --html`. The page walks through the plan: summary,
full map, risky connections, the action list, then one card per action with a
small diagram of just the parts involved, plain fix steps, test code and a
"done when" check. Diagrams use Mermaid, loaded from a pinned CDN version; if
it cannot load, the diagram source is still shown as text.

All finding text is untrusted (it can quote repository content), so every value
is HTML-escaped and Mermaid runs with securityLevel "strict".
"""
from __future__ import annotations

import html
import json

from brace_tools.topology import core as topology

# The single-file build, pinned by Subresource Integrity: the browser refuses any other bytes.
# (The ES-module build imports further chunks that SRI on the entry file would not cover.)
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"
MERMAID_SRI = "sha384-rbtjAdnIQE/aQJGEgXrVUlMibdfTSa4PQju4HDhN3sR2PmaKFzhEafuePsl9H/9I"

CSS = """
:root{--bg:#f7f7f5;--surface:#fff;--ink:#1d1d1b;--muted:#5f5f5a;--line:#e2e2dc;--accent:#2f5bd3;
--gap:#b42318;--gap-bg:#fde2e1;--need:#9a4a00;--need-bg:#fff1d6;--ok:#067647;--ok-bg:#e3f4e8;
--code-bg:#f0f0ec;--shadow:0 1px 2px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141413;--surface:#1e1e1c;--ink:#ecece8;
--muted:#a3a39c;--line:#33332f;--accent:#8aa8ff;--gap:#ff8a80;--gap-bg:#3a1d1b;--need:#ffc46b;--need-bg:#3a2c12;
--ok:#7fd3a0;--ok-bg:#16301f;--code-bg:#262623;--shadow:none}}
:root[data-theme=dark]{--bg:#141413;--surface:#1e1e1c;--ink:#ecece8;--muted:#a3a39c;--line:#33332f;--accent:#8aa8ff;
--gap:#ff8a80;--gap-bg:#3a1d1b;--need:#ffc46b;--need-bg:#3a2c12;--ok:#7fd3a0;--ok-bg:#16301f;--code-bg:#262623;--shadow:none}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 80px}
h1{font-size:1.9rem;line-height:1.2;margin:0 0 4px}
h2{font-size:1.35rem;margin:48px 0 8px}
h3{font-size:1.1rem;margin:0}
p{margin:8px 0}
.lede{color:var(--muted);margin-bottom:24px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:24px 0}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.tile b{display:block;font-size:1.8rem;line-height:1.1}
.tile span{color:var(--muted);font-size:.9rem}
.tile.gap b{color:var(--gap)}.tile.need b{color:var(--need)}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:16px;box-shadow:var(--shadow);overflow-x:auto}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:.9rem;color:var(--muted);margin:10px 0 0;padding:0;list-style:none}
.sw{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px;border:1px solid var(--line)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.conn{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--gap);border-radius:10px;padding:12px 14px}
.conn .path{font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.chip{font-size:.8rem;padding:2px 8px;border-radius:999px;background:var(--code-bg);color:var(--ink)}
.chip.risk{background:var(--gap-bg);color:var(--gap)}
table{width:100%;border-collapse:collapse;font-size:.95rem}
th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.85rem}
.badge{display:inline-block;font-size:.78rem;font-weight:600;padding:2px 8px;border-radius:6px;white-space:nowrap}
.badge.gap{background:var(--gap-bg);color:var(--gap)}.badge.needs_evidence{background:var(--need-bg);color:var(--need)}
.blank{color:var(--muted);letter-spacing:2px}
.action{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:20px;margin:16px 0;box-shadow:var(--shadow)}
.action header{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 12px;margin-bottom:8px}
.action .id{font-weight:700;color:var(--accent)}
.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin:12px 0;font-size:.92rem}
.meta div{background:var(--bg);border-radius:8px;padding:8px 10px}
.meta dt{color:var(--muted);font-size:.8rem}.meta dd{margin:0}
.problem{font-size:1.05rem}
ol.steps{padding-left:1.4em}ol.steps li{margin:6px 0}
.done{border-left:4px solid var(--ok);background:var(--ok-bg);padding:10px 14px;border-radius:8px;margin-top:12px}
.mini{margin:12px 0}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em}
code{background:var(--code-bg);padding:1px 5px;border-radius:4px}
pre{background:var(--code-bg);padding:12px;border-radius:8px;overflow-x:auto}
pre.mermaid{background:transparent;text-align:center}
.limits li{margin:4px 0;color:var(--muted)}
@media (max-width:640px){th:nth-child(3),td:nth-child(3){display:none}h1{font-size:1.5rem}}
"""


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def code_spans(text: str) -> str:
    """Escape, then turn `backtick` spans into <code>."""
    parts = esc(text).split("`")
    return "".join(f"<code>{p}</code>" if i % 2 else p for i, p in enumerate(parts))


def mini_focus(bom: dict, refs: list[str]) -> set[str]:
    """The parts named by an action, their containing servers, and the agent."""
    nodes = topology.all_nodes(bom)
    keep = {r for r in refs if r in nodes}
    for r in list(keep):
        if nodes[r].get("_parent"):
            keep.add(nodes[r]["_parent"])
    root = bom["metadata"]["component"]["bom-ref"]
    specific = [r for r in refs if r != root]  # the agent touches everything; don't expand from it
    for c in topology.connections(bom):
        if c["from"] in specific or c["to"] in specific:
            keep |= {c["from"], c["to"]}
    return keep


def render(data: dict, bom: dict) -> str:
    names = {c["ref"]: c["name"] for c in data["components"]}
    status, counts = {}, {}
    for a in data["actions"]:
        for c in a["components"]:
            counts[c] = (counts[c] + " · " if c in counts else "") + a["id"]
            if status.get(c) != "gap":
                status[c] = "gap" if a["rating"] == "gap" else "needs_evidence"
    s = data["summary"]
    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'>",
           f"<title>BRACE plan: {esc(data['agent'])}</title><style>{CSS}</style></head><body><main>",
           f"<h1>Security map and action plan: {esc(data['agent'])}</h1>",
           f"<p class=lede>Review of <code>{esc(data.get('repo') or '?')}</code>"
           f"{' at commit <code>' + esc(data['commit']) + '</code>' if data.get('commit') else ''}"
           f"{', ' + esc(data['reviewed_at']) if data.get('reviewed_at') else ''}. "
           "Each action has a lead, a place for who is doing it, and steps to follow.</p>",
           "<div class=tiles>",
           f"<div class='tile gap'><b>{s['gaps']}</b><span>things to fix</span></div>",
           f"<div class='tile gap'><b>{s['blocker_gaps']}</b><span>must fix before release</span></div>",
           f"<div class='tile need'><b>{s['needs_evidence']}</b><span>need proof they work</span></div>",
           f"<div class=tile><b>{s['risky_connections']}</b><span>risky connections</span></div>",
           f"<div class=tile><b>{s['components']}</b><span>parts on the map</span></div>",
           "</div>"]

    out += ["<h2>1. The map</h2>",
            "<p>What the agent connects to. Arrows point from the part that starts an action to the part it "
            "reaches. Codes in a box (like B06) are the actions below.</p>",
            "<div class=panel><pre class=mermaid>",
            esc(topology.mermaid(bom, status, counts, topology.focus_refs(bom, status))),
            "</pre><ul class=legend>",
            "<li><span class=sw style='background:var(--gap-bg);border-color:var(--gap)'></span>must be fixed</li>",
            "<li><span class=sw style='background:var(--need-bg);border-color:var(--need)'></span>needs proof</li>",
            "<li><span class=sw style='background:var(--gap)'></span>thick red arrow: risky connection</li>",
            "<li><span class=sw style='border-style:dashed'></span>dashed: network unknown</li>",
            "<li><span class=sw style='border-width:3px'></span>thick border: found by reading code</li>",
            f"</ul></div><p class=lede>Only parts with actions or risky connections are shown. "
            f"The full map has {s['components']} parts.</p>"]

    risky = sorted([c for c in data["connections"] if c["risks"]], key=lambda c: -len(c["risks"]))
    out += ["<h2>2. Connections that matter</h2>",
            "<p>These connections could cause harm if someone misused the agent. Check them first.</p><div class=cards>"]
    for c in risky:
        out.append("<div class=conn>"
                   f"<div class=path>{esc(names.get(c['from'], c['from']))} → {esc(names.get(c['to'], c['to']))}</div>"
                   + (f"<div>{esc(c['label'])}</div>" if c["label"] else "")
                   + "<div class=chips>" + "".join(f"<span class='chip risk'>{esc(t)}</span>" for t in c["risk_text"])
                   + "</div>"
                   + (f"<div>Actions: {', '.join(f'<a href=#{esc(i.lower())}>{esc(i)}</a>' for i in c['actions'])}</div>"
                      if c["actions"] else "")
                   + (f"<div><code>{esc(c['evidence'])}</code></div>" if c["evidence"] else "")
                   + "</div>")
    if not risky:
        out.append("<p>No connection has been marked as risky yet.</p>")
    out.append("</div>")

    out += ["<h2>3. Action list</h2>",
            "<p>The <b>Lead</b> is the role that usually owns the fix.</p>",
            "<div class=panel><table><thead><tr><th>#</th><th>What to fix</th><th>Where</th><th>Priority</th>"
            "<th>Lead</th></tr></thead><tbody>"]
    for a in data["actions"]:
        where = ", ".join(esc(names.get(c, c)) for c in a["components"]) or "not mapped"
        out.append(f"<tr><td><a href=#{esc(a['id'].lower())}>{esc(a['id'])}</a></td><td>{code_spans(a['problem'])}</td>"
                   f"<td>{where}</td><td><span class='badge {esc(a['rating'])}'>{esc(a['priority'])}</span></td>"
                   f"<td>{esc(a['lead'])}</td></tr>")
    if not data["actions"]:
        out.append("<tr><td colspan=5>Nothing to fix or prove was found.</td></tr>")
    out.append("</tbody></table></div>")

    out.append("<h2>4. How to fix each one</h2>")
    for a in data["actions"]:
        mini = topology.mermaid(bom, {c: status[c] for c in a["components"] if c in status},
                                {c: a["id"] for c in a["components"]}, mini_focus(bom, a["components"]))
        out += [f"<section class=action id={esc(a['id'].lower())}><header>",
                f"<span class=id>{esc(a['id'])}</span><h3>{esc(a['title'])}</h3>",
                f"<span class='badge {esc(a['rating'])}'>{esc(a['priority'])} ({esc(a['gate'])})</span></header>",
                f"<p class=problem>{code_spans(a['problem'])}</p>",
                "<dl class=meta>",
                f"<div><dt>Lead</dt><dd>{esc(a['lead'])}</dd></div>",
                f"<div><dt>Effort</dt><dd>{esc(a['effort'] or 'not stated')}</dd></div>",
                f"<div><dt>Where in the code</dt><dd>{', '.join(f'<code>{esc(e)}</code>' for e in a['evidence']) or 'not stated'}</dd></div>",
                "</dl>"]
        if a["components"]:
            out += ["<div class='panel mini'><pre class=mermaid>", esc(mini), "</pre></div>"]
        out.append("<p><b>Steps</b></p><ol class=steps>" + "".join(f"<li>{code_spans(x)}</li>" for x in a["steps"]) + "</ol>")
        if not a["steps_plain"]:
            out.append("<p class=lede>These steps came from the reviewer's notes and are not yet written in plain words.</p>")
        if a.get("test") and a["test"].get("code"):
            out.append(f"<p><b>Test to add</b> <code>{esc(a['test'].get('file', ''))}</code></p><pre>{esc(a['test']['code'])}</pre>")
            if a["test"].get("run"):
                out.append(f"<p>Run it with <code>{esc(a['test']['run'])}</code>.</p>")
        if a["done_when"]:
            out.append(f"<div class=done><b>You are done when:</b> {code_spans(a['done_when'])}</div>")
        if a["also_affects"]:
            out.append(f"<p class=lede>Also affects: {esc(', '.join(a['also_affects']))}</p>")
        out.append("</section>")

    out += ["<h2>5. What this page does not show</h2><ul class=limits>"]
    out += [f"<li>{esc(x)}</li>" for x in data["limits"]]
    out += [f"<li>Left off the map because its code changed: {esc(x)}</li>" for x in data["stale_map_entries"]]
    if data["notes"]:
        out.append(f"<li>{len(data['notes'])} input note(s) were reported when this page was made.</li>")
    out.append("</ul></main>")
    out.append(f"<script src={json.dumps(MERMAID)} integrity={json.dumps(MERMAID_SRI)} crossorigin=anonymous "
               "referrerpolicy=no-referrer></script><script>"
               "const dark=matchMedia('(prefers-color-scheme: dark)').matches;"
               "mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:dark?'dark':'default',"
               "flowchart:{htmlLabels:true}});"
               "mermaid.run({querySelector:'pre.mermaid'});"
               "</script></body></html>\n")
    return "\n".join(out)
