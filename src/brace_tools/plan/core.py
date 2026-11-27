#!/usr/bin/env python3
"""BRACE security map and action plan.

Joins a review's findings (`brace-findings.json`) with the component topology
(`topology.cdx.json`) and writes a report people can act on:

1. a map of the agent's connections, coloured by what needs fixing;
2. the connections that matter for security, in plain words;
3. an action list with a lead role for each item;
4. step-by-step fix guidance, with a check that each step is plain enough for a
   grade 12 reader.

    python tools/brace/action_plan.py brace-findings.json topology.cdx.json \
        -o brace-action-plan.md [--csv brace-actions.csv] [--strict]

Findings may carry these optional fields (written by the reviewer):

    "components": ["mcp:accounting", "tool:issue_refund"],   # bom-refs in the topology
    "fix": {"problem": "What is wrong, in plain words (used instead of summary).",
            "test": {"file": "tests/test_refund.py", "code": "...", "run": "python -m pytest tests/test_refund.py"},
            "steps": ["Open src/tools/payments.py.", "..."],
            "done_when": "A refund above the approved amount is refused.",
            "effort": "small | medium | large"},

Outputs: Markdown (-o), CSV (--csv), JSON for CI (--json, schema
`schemas/action-plan.schema.json`), SARIF 2.1.0 for code scanning (--sarif) and a
web page with diagrams (--html).

Exit codes: 0 written; 1 problems found with --strict (unknown component refs,
gaps or needs_evidence without fix steps, steps above grade 12, or missing files
and lines); 2 bad input; 3 an action matched --fail-on.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from brace_tools import __version__, data, io
from open_agent_security.output import path_uri
from brace_tools.topology import core as topology

ITEMS = {i["id"]: i for i in json.loads(data.path("brace_items.json").read_text(encoding="utf-8"))}
ROLE_NAMES = {
    "agent_team": "Agent team", "operations": "Operations", "security": "Security",
    "infrastructure": "Infrastructure", "governance": "Governance", "business_owner": "Business owner",
    "data_privacy": "Data and privacy", "model_team": "Model team", "vendors": "Vendors",
    "independent_audit": "Independent audit",
}
PRIORITY = {
    ("gap", "Blocker"): (1, "Must fix before release"),
    ("gap", "Required"): (2, "Fix before release, or get a written risk approval"),
    ("gap", "Detection"): (3, "Fix soon; track until done"),
    ("needs_evidence", "Blocker"): (4, "Show proof it works before release"),
    ("needs_evidence", "Required"): (5, "Show proof it works, or get a written risk approval"),
    ("needs_evidence", "Detection"): (6, "Show proof it works"),
}
MAX_GRADE = 12.0
MAX_WORDS = 30


# ---------------------------------------------------------------- readability
def _syllables(word: str) -> int:
    w = word.lower()
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def grade(text: str) -> float:
    """Flesch-Kincaid grade. Code, paths and names in backticks count as one short word."""
    plain = re.sub(r"`[^`]*`", "code", text)
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*|\S*[./_:()]\S*", plain)]
    words = ["code" if re.search(r"[./_:()]", w) else w for w in words]
    if not words:
        return 0.0
    sentences = max(1, len(re.findall(r"[.!?](\s|$)", plain)))
    syl = sum(_syllables(w) for w in words)
    return round(0.39 * len(words) / sentences + 11.8 * syl / len(words) - 15.59, 1)


def plain_problems(text: str) -> list[str]:
    out = []
    n = len(re.sub(r"`[^`]*`", "code", text).split())
    if n > MAX_WORDS:
        out.append(f"{n} words; split it into shorter sentences or steps (max {MAX_WORDS})")
    g = grade(text)
    if g > MAX_GRADE:
        out.append(f"reading grade {g}; use shorter words and sentences (max {MAX_GRADE:g})")
    return out


FILE_REF = re.compile(r"`([\w.-]+(?:/[\w.-]+)+|[\w-]+\.(?:py|ts|js|go|yaml|yml|json|sql|toml|md|tf))`")
LINE_REF = re.compile(r"\blines? (\d+)(?: (?:to|-|and) (\d+))?")


def reference_problems(text: str, repo: Path) -> list[str]:
    """Files named in backticks must exist; line numbers after them must be inside the file."""
    out = []
    files = FILE_REF.findall(text)
    for f in files:
        path = (repo / f).resolve()
        if repo.resolve() not in path.parents or not path.is_file():
            if not re.search(r"\b(create|new file|add (?:a|the) file|make (?:a|the) file)\b", text, re.I):
                out.append(f"`{f}` is not a file in the repository (say \"create\" if the step makes it)")
            continue
        try:
            n = len(io.read_text(path).splitlines())
        except io.ReadError as exc:
            out.append(str(exc))
            continue
        for a, b in LINE_REF.findall(text) if len(files) == 1 else []:
            for x in (a, b):
                if x and not 1 <= int(x) <= n:
                    out.append(f"line {x} is past the end of `{f}` ({n} lines)")
    return out


# ---------------------------------------------------------------------- build
def load(path: Path) -> dict:
    try:
        return io.read_json_object(path, follow=True)
    except io.ReadError as e:
        sys.exit(str(e))


def actions_from(findings: dict, nodes: dict, repo: Path | None = None) -> tuple[list[dict], list[str]]:
    actions, problems = [], []
    for f in findings.get("findings", []):
        rating = f.get("rating")
        if rating not in ("gap", "needs_evidence"):
            continue
        item = ITEMS.get(f["item"], {})
        gate = f.get("gate") or item.get("gate", "Detection")
        rank, priority = PRIORITY[(rating, gate)]
        comps = list(f.get("components") or [])
        for c in f.get("checks") or []:  # failing coverage rows can name the part too
            for row in [*(c.get("coverage") or []), *(c.get("deviations") or [])]:
                if isinstance(row, dict) and row.get("component") and row.get("status") in ("missing", "unclear") \
                        and row["component"] not in comps:
                    comps.append(row["component"])
        for c in comps:
            if c not in nodes:
                problems.append(f"{f['item']}: component {c!r} is not in the topology")
        fix = f.get("fix") or {}
        steps = [s for s in fix.get("steps", []) if str(s).strip()]
        if not steps:
            problems.append(f"{f['item']}: no plain fix steps (fix.steps); showing next_step instead")
        for i, s in enumerate(steps, 1):
            for p in plain_problems(s) + (reference_problems(s, repo) if repo else []):
                problems.append(f"{f['item']} step {i}: {p}")
        plain = fix.get("problem") or ""
        if plain:
            for p in plain_problems(plain):
                problems.append(f"{f['item']} fix.problem: {p}")
        elif plain_problems(f.get("summary", "")):
            problems.append(f"{f['item']}: summary is hard to read ({'; '.join(plain_problems(f.get('summary', '')))}); "
                            "add fix.problem in plain words")
        if fix.get("done_when"):
            for p in plain_problems(fix["done_when"]):
                problems.append(f"{f['item']} done_when: {p}")
        evidence = [f"{e['file']}:{e['line']}" for e in f.get("evidence", []) if e.get("file")]
        actions.append({
            "id": f["item"], "title": f.get("title") or item.get("title", ""), "gate": gate, "rating": rating,
            "rank": rank, "priority": priority, "summary": plain or f.get("summary", ""),
            "components": [c for c in comps if c in nodes], "lead_role": f.get("lead_role") or item.get("lead_role", ""),
            "steps": steps or [f.get("next_step", "Ask the Security lead.")],
            "plain": bool(steps), "done_when": fix.get("done_when", ""), "effort": fix.get("effort", ""),
            "test": fix.get("test") if isinstance(fix.get("test"), dict) else None,
            "evidence": evidence, "violates": f.get("violates", []), "also_affects": f.get("also_affects", []),
            "aivss": f.get("aivss") if isinstance(f.get("aivss"), dict) else None,
        })
    actions.sort(key=lambda a: (a["rank"], a["id"]))
    return actions, problems


def node_status(actions: list[dict], nodes: dict) -> tuple[dict, dict]:
    status, counts = {}, {}
    for a in actions:
        for c in a["components"]:
            counts[c] = (counts[c] + " · " if c in counts else "") + a["id"]
            if status.get(c) != "gap":
                status[c] = "gap" if a["rating"] == "gap" else "needs_evidence"
    return status, counts


def name(nodes: dict, ref: str) -> str:
    n = nodes.get(ref)
    return n["name"] if n else ref


MD_ACTIVE = re.compile(r"([\\<>\[\]])")  # backslash, HTML and autolinks, links and images
BACKTICKS = re.compile(r"`+")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")  # a code span: its content is not Markdown


def md_inline(text) -> str:
    """Untrusted text (findings come from a review of someone else's code) as one line of
    Markdown that cannot start a heading, open a link or image, or carry HTML. Backticks stay,
    so code spans in findings still render."""
    parts = CODE_SPAN.split(" ".join(str(text).split()))
    # split() with two groups yields text, ticks, code, text, ...: escape only the text parts
    return "".join(MD_ACTIVE.sub(r"\\\1", x) if i % 3 == 0 else (x + parts[i + 1] + x if i % 3 == 1 else "")
                   for i, x in enumerate(parts))


def cell(text: str) -> str:
    return md_inline(text).replace("|", "\\|")


def code(text) -> str:
    """An inline code span that holds any text, backticks included."""
    t = " ".join(str(text).split())
    ticks = "`" * (max((len(m) for m in BACKTICKS.findall(t)), default=0) + 1)
    pad = " " if t.startswith("`") or t.endswith("`") or ticks != "`" else ""
    return f"{ticks}{pad}{t}{pad}{ticks}"


def fence(text: str) -> str:
    """A code fence longer than any backtick run in the text, so the text cannot close it."""
    return "`" * max(3, max((len(m) for m in BACKTICKS.findall(text)), default=0) + 1)


def report(findings: dict, bom: dict, actions: list[dict], problems: list[str]) -> str:
    nodes = topology.all_nodes(bom)
    status, counts = node_status(actions, nodes)
    conns = topology.connections(bom)
    by_comp: dict[str, list[str]] = {}
    for a in actions:
        for c in a["components"]:
            by_comp.setdefault(c, []).append(a["id"])
    agent = bom["metadata"]["component"]["name"]
    gaps = sum(a["rating"] == "gap" for a in actions)
    needs = len(actions) - gaps
    stale = topology.stale_entries(bom)
    unknown_zone = [r for r, n in nodes.items() if topology.node_props(n).get("trust_zone") == ["unknown"]]
    L = [f"# Security map and action plan: {md_inline(agent)}", ""]
    L += [f"Review of {code(findings.get('repo', '?'))} at commit {code(findings.get('commit') or 'unknown')}, "
          f"{md_inline(findings.get('reviewed_at', 'date unknown'))}.", "",
          f"**{gaps} things to fix** and **{needs} things that need proof** were found. "
          "Each one below has a person to lead it, a place to write who is doing it, and steps to follow.", ""]

    L += ["## 1. Map", "",
          "This map shows what the agent connects to. Arrows point from the part that starts an action "
          "to the part it reaches.", "",
          "- **Red box:** something here must be fixed. The codes in the box (like B06) are the actions in section 3.",
          "- **Yellow box:** something here needs proof that it is safe.",
          "- **Thick red arrow:** a connection that can cause harm if misused. Section 2 says why.",
          "- **Dashed box:** we don't yet know which network it runs in.",
          "- **Thick border:** found by reading the code, not just the settings files.", "",
          "```mermaid", topology.mermaid(bom, status, counts, topology.focus_refs(bom, status)).rstrip(), "```", "",
          f"This map shows only the parts with actions or risky connections. The full map has "
          f"{len(nodes)} parts; draw it with `topology.py mermaid`.", ""]

    L += ["## 2. Connections that matter", "",
          "These connections could cause harm if someone misused the agent. Check them first.", "",
          "| From | To | Why it matters | Open actions | Evidence |", "|---|---|---|---|---|"]
    risky = [c for c in conns if c["risks"]]
    for c in sorted(risky, key=lambda c: -len(c["risks"])):
        why = "; ".join(topology.RISKS[r] for r in c["risks"] if r in topology.RISKS)
        both = set(by_comp.get(c["from"], [])) & set(by_comp.get(c["to"], []))
        acts = sorted(both or by_comp.get(c["to"], []))
        L.append(f"| {cell(name(nodes, c['from']))} | {cell(name(nodes, c['to']))} | {cell(why)} | "
                 f"{', '.join(acts) or '-'} | {cell(c['evidence']) or '-'} |")
    if not risky:
        L.append("| - | - | No connection has been marked as risky yet. | - | - |")
    L.append("")

    L += ["## 3. Action list", "",
          "The **Lead** is the role that usually owns the fix (see ROLES.md).", "",
          "| # | What to fix | Where | Priority | Lead |", "|---|---|---|---|---|"]
    for a in actions:
        where = ", ".join(name(nodes, c) for c in a["components"]) or "not mapped"
        L.append(f"| [{a['id']}](#{a['id'].lower()}) | {cell(a['summary'] or a['title'])} | {cell(where)} | "
                 f"{a['priority']} ({a['gate']}) | {ROLE_NAMES.get(a['lead_role'], a['lead_role'])} |")
    if not actions:
        L.append("| - | Nothing to fix or prove was found. | - | - | - |")
    L.append("")

    L += ["## 4. How to fix each one", ""]
    for a in actions:
        L += [f"### {a['id']}", "", f"**{a['title']}** · {a['priority']} ({a['gate']})", "",
              f"**The problem:** {md_inline(a['summary'])}", "",
              f"**Where:** {md_inline(', '.join(name(nodes, c) for c in a['components']) or 'not mapped to a component')}"
              + (f" — {', '.join(code(e) for e in a['evidence'])}" if a["evidence"] else ""), "",
              f"**Lead:** {ROLE_NAMES.get(a['lead_role'], a['lead_role'])}" + (f" · **Effort:** {a['effort']}" if a["effort"] else ""), "",
              "**Steps:**", ""]
        L += [f"{i}. {md_inline(s)}" for i, s in enumerate(a["steps"], 1)]
        if a["test"] and a["test"].get("code"):
            lang = re.sub(r"\W", "", Path(str(a["test"].get("file", ""))).suffix)
            body = str(a["test"]["code"]).rstrip()
            L += ["", f"**Test to add** ({code(a['test'].get('file', 'test file'))}):", "", fence(body) + lang,
                  body, fence(body)]
            if a["test"].get("run"):
                L += ["", f"Run it with {code(a['test']['run'])}."]
        if not a["plain"]:
            L += ["", "_These steps came from the reviewer's notes and are not yet written in plain words._"]
        if a["done_when"]:
            L += ["", f"**You are done when:** {md_inline(a['done_when'])}"]
        if a["also_affects"]:
            L += ["", f"**Also fixes or affects:** {md_inline(', '.join(map(str, a['also_affects'])))}"]
        L.append("")

    L += ["## 5. What this report does not show", "",
          "- It comes from reading code and settings. It does not prove the agent is safe when it runs.",
          "- The map may be missing parts. Parts reached only through code are included only if the "
          "reviewer traced them."]
    if unknown_zone:
        L.append(f"- We don't know which network these run in: {md_inline(', '.join(name(nodes, r) for r in unknown_zone))}.")
    for s in stale:
        L.append(f"- Left off the map because its code evidence changed: {md_inline(s)}.")
    unmapped = [a["id"] for a in actions if not a["components"]]
    if unmapped:
        L.append(f"- Not linked to a part of the map yet: {', '.join(unmapped)}.")
    if problems:
        L.append(f"- The report generator noted {len(problems)} issue(s) with this report's input; "
                 "rerun with --strict to list them.")
    return "\n".join(L) + "\n"


def write_csv(path: Path, actions: list[dict], nodes: dict) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "title", "priority", "gate", "rating", "components", "lead",
                    "problem", "steps", "done_when", "evidence"])
        for a in actions:
            w.writerow([a["id"], a["title"], a["priority"], a["gate"], a["rating"],
                        "; ".join(name(nodes, c) for c in a["components"]),
                        ROLE_NAMES.get(a["lead_role"], a["lead_role"]), a["summary"],
                        " ".join(f"{i}. {s}" for i, s in enumerate(a["steps"], 1)), a["done_when"],
                        "; ".join(a["evidence"])])


SCHEMA_ID = "brace-action-plan/1"
FAIL_ON = {
    "none": lambda a: False,
    "blocker": lambda a: a["rating"] == "gap" and a["gate"] == "Blocker",
    "gap": lambda a: a["rating"] == "gap",
    "any": lambda a: True,
}


def plan_data(findings: dict, bom: dict, actions: list[dict], problems: list[str]) -> dict:
    """The one structured view every output is built from (JSON, SARIF, HTML)."""
    nodes = topology.all_nodes(bom)
    by_comp: dict[str, list[str]] = {}
    for a in actions:
        for c in a["components"]:
            by_comp.setdefault(c, []).append(a["id"])
    comps = []
    for ref, n in nodes.items():
        p = topology.node_props(n)
        comps.append({"ref": ref, "name": n.get("name", ref), "kind": p.get("kind", ["unknown"])[0],
                      "trust_zone": n.get("trustZone") or p.get("trust_zone", [None])[0],
                      "source": p.get("source", ["unknown"])[0], "evidence": p.get("evidence", []),
                      "actions": sorted(by_comp.get(ref, []))})
    conns = []
    for c in topology.connections(bom):
        both = set(by_comp.get(c["from"], [])) & set(by_comp.get(c["to"], []))
        conns.append({"from": c["from"], "to": c["to"], "label": c["label"], "risks": c["risks"],
                      "risk_text": [topology.RISKS[r] for r in c["risks"] if r in topology.RISKS],
                      "evidence": c["evidence"] or None, "source": c["source"],
                      "actions": sorted(both or by_comp.get(c["to"], []))})
    out_actions = []
    for a in actions:
        out_actions.append({
            "id": a["id"], "title": a["title"], "gate": a["gate"], "rating": a["rating"],
            "priority": a["priority"], "priority_rank": a["rank"], "lead_role": a["lead_role"],
            "lead": ROLE_NAMES.get(a["lead_role"], a["lead_role"]),
            "components": a["components"], "problem": a["summary"], "steps": a["steps"],
            "steps_plain": a["plain"], "done_when": a["done_when"] or None, "effort": a["effort"] or None,
            "test": a["test"], "evidence": a["evidence"], "also_affects": a["also_affects"]})
    gaps = [a for a in actions if a["rating"] == "gap"]
    return {
        "schema": SCHEMA_ID,
        "agent": bom["metadata"]["component"]["name"],
        "repo": findings.get("repo"), "commit": findings.get("commit"), "reviewed_at": findings.get("reviewed_at"),
        "summary": {"actions": len(actions), "gaps": len(gaps), "needs_evidence": len(actions) - len(gaps),
                    "blocker_gaps": sum(a["gate"] == "Blocker" for a in gaps),
                    "risky_connections": sum(bool(c["risks"]) for c in conns),
                    "components": len(comps), "input_notes": len(problems),
                    "stale_map_entries": len(topology.stale_entries(bom))},
        "components": comps, "connections": conns, "actions": out_actions,
        "notes": problems, "stale_map_entries": topology.stale_entries(bom),
        "limits": ["Built from reading code and settings; it does not prove the agent is safe when it runs.",
                   "The map may be missing parts reached only through code that the reviewer did not trace."],
    }


MAX_SARIF_RESULTS = 5000  # code scanning rejects far larger runs; a plan has one result per action


def sarif(data: dict) -> dict:
    """SARIF 2.1.0 for code-scanning tools: one rule per BRACE item, one result per action."""
    level = {("gap", "Blocker"): "error", ("gap", "Required"): "error", ("gap", "Detection"): "warning"}
    rules, results = {}, []
    for a in data["actions"]:
        rules.setdefault(a["id"], {
            "id": a["id"], "name": re.sub(r"\W+", "", a["title"].title()) or a["id"],
            "shortDescription": {"text": f"BRACE {a['id']}: {a['title']}"},
            "properties": {"gate": a["gate"], "tags": ["security", "brace", a["gate"]]}})
        steps = "\n".join(f"{i}. {s}" for i, s in enumerate(a["steps"], 1))
        text = f"{a['problem']}\n\nLead: {a['lead']}. {a['priority']}.\n\nHow to fix:\n{steps}"
        if a["done_when"]:
            text += f"\n\nDone when: {a['done_when']}"
        locations = []
        for ev in a["evidence"]:
            path, _, line = ev.rpartition(":")
            if path and line.isdigit():
                locations.append({"physicalLocation": {"artifactLocation": {"uri": path_uri(path), "uriBaseId": "%SRCROOT%"},
                                                       "region": {"startLine": int(line)}}})
        result = {"ruleId": a["id"], "level": level.get((a["rating"], a["gate"]), "note"),
                  "message": {"text": text},
                  "partialFingerprints": {"braceItem/v1": f"{a['id']}:{','.join(sorted(a['components']))}"},
                  "properties": {"rating": a["rating"], "gate": a["gate"], "lead_role": a["lead_role"],
                                 "components": a["components"]}}
        if locations:
            result["locations"] = locations[:10]
        results.append(result)
    results = results[:MAX_SARIF_RESULTS]
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "BRACE", "version": __version__, "informationUri": "https://braceframework.org",
                                          "rules": list(rules.values())}},
                      "results": results}]}


def main(argv: list[str] | None = None, prog: str | None = None) -> int:
    ap = argparse.ArgumentParser(prog=prog, description=__doc__.split("\n\n")[0])
    ap.add_argument("findings", type=Path)
    ap.add_argument("topology", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--csv", type=Path, help="also write the action list as CSV for a tracker")
    ap.add_argument("--repo", type=Path, help="reviewed repository; check files and line numbers named in steps")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any input problem is found")
    ap.add_argument("--json", type=Path, help=f"structured plan for CI ({SCHEMA_ID}; schemas/action-plan.schema.json)")
    ap.add_argument("--sarif", type=Path, help="SARIF 2.1.0 for code scanning")
    ap.add_argument("--html", type=Path, help="a web page that walks through the plan with diagrams")
    ap.add_argument("--fail-on", choices=list(FAIL_ON), default="none",
                    help="exit 3 if any action matches: blocker = a Blocker gap, gap = any gap, any = any action")
    ap.add_argument("--github-output", type=Path, metavar="FILE",
                    help="append actions=, gaps=, blocker_gaps=, notes= and failing= (counts) to this file ($GITHUB_OUTPUT)")
    a = ap.parse_args(argv)
    findings, bom = load(a.findings), load(a.topology)
    errors = topology.validate(bom)
    if errors:
        print("topology is not valid:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 2
    nodes = topology.all_nodes(bom)
    actions, problems = actions_from(findings, nodes, a.repo)
    io.write_atomic(a.output, report(findings, bom, actions, problems))
    if a.csv:
        write_csv(a.csv, actions, nodes)
    data = plan_data(findings, bom, actions, problems)
    if a.json:
        io.write_atomic(a.json, json.dumps(data, indent=2) + "\n")
    if a.sarif:
        io.write_atomic(a.sarif, json.dumps(sarif(data), indent=2) + "\n")
    if a.html:
        from brace_tools.plan import html as report_html
        io.write_atomic(a.html, report_html.render(data, bom))
    for p in problems:
        print(f"note: {p}", file=sys.stderr)
    print(f"wrote {a.output} ({len(actions)} actions, {len(problems)} input notes)")
    hits = [x["id"] for x in data["actions"] if FAIL_ON[a.fail_on](x)]
    if a.github_output:
        with a.github_output.open("a", encoding="utf-8") as out:  # counts only: nothing from the inputs
            sm = data["summary"]
            out.write(f"actions={int(sm['actions'])}\ngaps={int(sm['gaps'])}\nblocker_gaps={int(sm['blocker_gaps'])}\n"
                      f"notes={len(problems)}\nfailing={len(hits)}\n")
    if a.strict and problems:
        return 1
    if hits:
        print(f"fail-on {a.fail_on}: {', '.join(hits)}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
