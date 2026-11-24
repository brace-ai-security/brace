"""Render a BRACE topology as one self-contained, interactive web page.

    python tools/brace/topology.py report topology.cdx.json [--findings brace-findings.json] -o topology.html

The page shows what the agent connects to: its sub-agents, tools, MCP servers and
their tools, the APIs, data stores and models behind them, grouped by trust zone.
It compares what the settings *declare* with what a reviewer *found in code*:

- confirmed: declared and found in code (solid line);
- declared only: in the settings, but not found in code (dashed line);
- undeclared: found in code, but not in the settings (thick purple line, "!" mark).

BRACE findings sit on the parts and connections they name, as a badge whose shape
shows the gate (octagon Blocker, triangle Required, circle Detection). Clicking or
pressing Enter on a part opens a panel with evidence, findings and fix steps. Tables
below the map hold the same content for screen readers and print.

Everything is inline (no CDN, no network). All text from the topology and findings
is untrusted, because it can quote repository content: it is HTML-escaped when
written into the page, embedded as JSON with `<`, `>` and `&` escaped, and the
script only ever writes it with `textContent`.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import action_plan
import topology

GATES = ["Blocker", "Required", "Detection"]
COLUMNS = ["Agent and sub-agents", "Tools and MCP servers", "Services, data and models"]
COLUMN_OF = {"agent": 0, "agent_unit": 0, "tool": 1, "mcp_server": 1, "gateway": 1, "human_approval": 1,
             "external_api": 2, "data_store": 2, "audit_sink": 2, "secret": 2, "model": 2}
KIND_ORDER = ["agent", "agent_unit", "human_approval", "gateway", "mcp_server", "tool",
              "model", "data_store", "external_api", "secret", "audit_sink"]
KIND_LABEL = {"agent": "Agent", "agent_unit": "Agent loop", "tool": "Tool", "mcp_server": "MCP server",
              "mcp_tool": "MCP tool", "external_api": "API or service", "data_store": "Data store",
              "model": "Model", "gateway": "Gateway", "human_approval": "Human approval", "secret": "Secret",
              "audit_sink": "Audit log"}
KIND_TEXT = {
    "agent": "The agent being reviewed.",
    "agent_unit": "Code that calls the model. It runs as the agent itself or as a sub-agent it starts.",
    "tool": "A tool the model can choose to call.",
    "mcp_server": "An MCP server. It gives the agent extra tools over a connection.",
    "mcp_tool": "A tool offered by an MCP server.",
    "external_api": "A service outside this code that the agent sends requests to.",
    "data_store": "A database or store the agent reads or writes.",
    "model": "The AI model that decides what the agent does next.",
    "gateway": "A gateway that sits between the agent and a service.",
    "human_approval": "A step where a person approves an action.",
    "secret": "A secret, such as a key or token.",
    "audit_sink": "Where the agent writes its audit log.",
}
STATUS_TEXT = {"confirmed": "Declared and found in code",
               "declared": "Declared only: not found in code",
               "undeclared": "Undeclared: found in code, not in the settings"}
STATUS_SHORT = {"confirmed": "confirmed", "declared": "declared only", "undeclared": "undeclared"}
RATING_TEXT = {"gap": "Gap", "needs_evidence": "Needs proof"}
DECLARED_SOURCES = {"agent_config", "mcp_config", "repository", "inventory"}
DETECTED_SOURCES = {"traced", "inventory"}

# Layout (SVG user units).
NODE_W, NODE_H, COL_GAP, V_GAP = 232, 50, 136, 14
LEFT, TOP, RIGHT = 64, 44, 40
LANE_HEAD, LANE_FOOT, LANE_GAP = 34, 16, 10
CHILD_H, CHILD_GAP, SERVER_HEAD = 28, 6, 46


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def zone_name(z: str) -> str:
    return {"agent": "Agent's own systems", "unknown": "Unknown network"}.get(z, z[:1].upper() + z[1:])


def code_spans(text: str) -> str:
    """Escape, then turn `backtick` spans into <code>."""
    bits = esc(text).split("`")
    return "".join(f"<code>{b}</code>" if i % 2 else b for i, b in enumerate(bits))


def short(text: str, n: int = 25) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


# ------------------------------------------------------------------------- model
def build_model(bom: dict, findings: dict | None = None) -> dict:
    """Classify every part and connection, and attach findings. Pure data; no HTML."""
    nodes = topology.all_nodes(bom)
    root = bom["metadata"]["component"]["bom-ref"]
    quotes: dict[str, str] = {}
    for n in nodes.values():
        for v in topology.node_props(n).get("quote", []):
            try:
                at, q = json.loads(v)
                quotes.setdefault(at, q)
            except (ValueError, TypeError):
                pass

    parts: dict[str, dict] = {}
    for ref, n in nodes.items():
        p = topology.node_props(n)
        kind = p.get("kind", ["tool"])[0]
        source = p.get("source", ["unknown"])[0]
        ev = p.get("evidence", [])
        code_ev = list(p.get("traced_evidence", [])) + (ev if source in DETECTED_SOURCES else [])
        decl_ev = ev if source not in DETECTED_SOURCES else []
        parent = n.get("_parent")
        parts[ref] = {
            "id": "n" + str(len(parts)), "ref": ref, "name": n.get("name") or ref, "kind": kind,
            "kind_label": KIND_LABEL.get(kind, kind), "about": KIND_TEXT.get(kind, ""),
            "parent": parent, "zone": topology.zone_of(n, nodes),
            "declared": ref == root or source in DECLARED_SOURCES,
            "detected": ref == root or source in DETECTED_SOURCES or bool(p.get("traced_evidence")),
            "declared_in": decl_ev, "found_in": [{"at": e, "quote": quotes.get(e, "")} for e in code_ev],
            "endpoints": [str(x) for x in n.get("endpoints", [])], "transport": p.get("transport", [""])[0],
            "credential_keys": p.get("credential_key", []), "owner": p.get("owner", [""])[0],
            "zone_evidence": [{"at": e, "quote": quotes.get(e, "")} for e in p.get("zone_evidence", [])],
            "children": [], "findings": [], "badge": [], "note": "",
        }
    for ref, part in parts.items():
        if part["parent"]:
            parts[part["parent"]]["children"].append(ref)

    declared_edges: dict[tuple, str] = {}
    traced_edges: set[tuple] = set()
    for ref, n in nodes.items():
        p = topology.node_props(n)
        for v in p.get("declared_edge", []):
            to, _, at = v.split("|")[:3]
            declared_edges[(ref, to)] = at
        for v in p.get("edge", []):
            bits = v.split("|")
            if len(bits) > 2 and bits[2] == "traced":
                traced_edges.add((ref, bits[0]))
    for a, b in traced_edges:  # anything a traced connection touches exists in code
        for r in (a, b):
            if r in parts:
                parts[r]["detected"] = True

    # Settings-made edges (agent -> tool, agent -> MCP server) and declared connections.
    traced_only = {(d["ref"], t) for d in bom.get("dependencies", []) for t in d.get("dependsOn", [])
                   if (d["ref"], t) in traced_edges and (d["ref"], t) not in declared_edges}
    declared_into: dict[str, set] = {}
    for d in bom.get("dependencies", []):
        for t in d.get("dependsOn", []):
            if (d["ref"], t) not in traced_only:
                declared_into.setdefault(t, set()).add(d["ref"])
    agent_side = {r for r, p in parts.items() if p["kind"] in ("agent", "agent_unit")}

    def is_reply(a: str, b: str) -> bool:
        """A service answering the agent: the reverse of a declared call into that service."""
        callers = declared_into.get(parts[a]["parent"] or a, set())
        return b in callers or (b in agent_side and bool(callers & agent_side))

    edges = []
    for c in topology.connections(bom):
        key = (c["from"], c["to"])
        src, dst = parts[c["from"]], parts[c["to"]]
        traced = key in traced_edges
        reply = traced and key not in declared_edges and is_reply(c["from"], c["to"])
        if key in declared_edges or reply:
            declared = True
        else:  # edges made from settings (agent -> tool, agent -> MCP server) or the code scan
            declared = not traced
        detected = traced or (not traced and dst["detected"] and (src["detected"] or src["ref"] == root))
        if not traced and key not in declared_edges and "inventory" in (
                topology.node_props(nodes[c["from"]]).get("source", []) + topology.node_props(nodes[c["to"]]).get("source", [])):
            detected = True
        edges.append({
            "id": "e" + str(len(edges)), "from": c["from"], "to": c["to"], "label": c["label"],
            "risks": c["risks"], "risk_text": [topology.RISKS[r] for r in c["risks"] if r in topology.RISKS],
            "declared": declared, "detected": detected,
            "found_in": [{"at": c["evidence"], "quote": quotes.get(c["evidence"], "")}] if traced and c["evidence"] else [],
            "reply": reply,
            "declared_in": [declared_edges[key]] if key in declared_edges else
            (["reply on the declared connection " + parts[c["to"]]["name"] + " \u2192 " + parts[c["from"]]["name"]]
             if reply else []),
            "findings": [], "crosses": bool({"crosses_boundary", "unknown_zone"} & set(c["risks"])),
        })

    for e in edges:  # a connection seen in code shows both its ends exist in code
        if e["detected"]:
            parts[e["from"]]["detected"] = parts[e["to"]]["detected"] = True
    # MCP tools are exposed through their server: confirmed when the server connection is.
    for part in parts.values():
        if part["kind"] == "mcp_tool" and not part["detected"] and part["parent"] and parts[part["parent"]]["detected"]:
            part["detected"] = True
            part["note"] = "Reached through the MCP server connection, which was found in code."
    for part in parts.values():
        part["status"] = status_of(part["declared"], part["detected"])
    for e in edges:
        e["status"] = status_of(e["declared"], e["detected"])

    # Findings: on a connection when it names both ends, else on the parts it names.
    actions = action_plan.actions_from(findings, nodes)[0] if findings else []
    out_findings = []
    for i, a in enumerate(actions):
        comps = set(a["components"])
        hit_edges = [e for e in edges if e["from"] in comps and e["to"] in comps]
        covered = {r for e in hit_edges for r in (e["from"], e["to"])}
        targets = [e["id"] for e in hit_edges]
        for e in hit_edges:
            e["findings"].append(i)
        for r in a["components"]:
            parts[r]["findings"].append(i)
            if r not in covered:
                parts[r]["badge"].append(i)
                targets.append(parts[r]["id"])
        out_findings.append({
            "n": i, "item": a["id"], "title": a["title"], "gate": a["gate"], "rating": a["rating"],
            "rating_text": RATING_TEXT.get(a["rating"], a["rating"]), "priority": a["priority"],
            "problem": a["summary"], "steps": a["steps"], "done_when": a["done_when"], "effort": a["effort"],
            "lead": action_plan.ROLE_NAMES.get(a["lead_role"], a["lead_role"]),
            "evidence": a["evidence"], "where": [parts[r]["name"] for r in a["components"]], "targets": targets,
        })
    zones = sorted({p["zone"] for p in parts.values()}, key=lambda z: (z != "agent", z == "unknown", z))
    summary = {
        "parts": len(parts), "connections": len(edges),
        "undeclared": sum(p["status"] == "undeclared" for p in parts.values()) + sum(e["status"] == "undeclared" for e in edges),
        "declared_only": sum(p["status"] == "declared" for p in parts.values()) + sum(e["status"] == "declared" for e in edges),
        "crossings": sum(e["crosses"] for e in edges),
        "unknown_zone": sum(p["zone"] == "unknown" for p in parts.values() if not p["parent"]),
        "findings": {g: sum(f["gate"] == g for f in out_findings) for g in GATES},
    }
    limits = [p["value"] for p in bom["metadata"].get("properties", []) if p["name"] == "brace:limitations"]
    limits += [f"Left off the map because its code changed: {x}" for x in topology.stale_entries(bom)]
    return {"agent": bom["metadata"]["component"]["name"], "root": root,
            "owner": parts[root]["owner"], "parts": parts, "edges": edges, "findings": out_findings,
            "zones": zones, "summary": summary, "limits": limits,
            "repo": (findings or {}).get("repo"), "commit": (findings or {}).get("commit"),
            "reviewed_at": (findings or {}).get("reviewed_at")}


def status_of(declared: bool, detected: bool) -> str:
    return "confirmed" if declared and detected else "undeclared" if detected else "declared"


# ------------------------------------------------------------------------ layout
def layout(m: dict) -> dict:
    """Place parts in a grid: columns by role (left to right), lanes by trust zone."""
    parts, edges = m["parts"], m["edges"]
    top = [p for p in parts.values() if not p["parent"]]

    def height(p):
        return SERVER_HEAD + len(p["children"]) * (CHILD_H + CHILD_GAP) + 4 if p["children"] else NODE_H

    def owner(ref):
        return parts[ref]["parent"] or ref

    cells: dict[tuple, list] = {}
    for p in sorted(top, key=lambda p: (KIND_ORDER.index(p["kind"]) if p["kind"] in KIND_ORDER else 99, p["name"])):
        cells.setdefault((p["zone"], COLUMN_OF.get(p["kind"], 1)), []).append(p["ref"])
    nbrs: dict[str, list[str]] = {}
    for e in edges:
        a, b = owner(e["from"]), owner(e["to"])
        if a != b:
            nbrs.setdefault(a, []).append(b)
            nbrs.setdefault(b, []).append(a)
    pos: dict[str, tuple] = {}

    def place():
        y = TOP
        lanes = []
        for z in m["zones"]:
            lane_h = max([sum(height(parts[r]) for r in cells.get((z, c), [])) +
                          V_GAP * max(0, len(cells.get((z, c), [])) - 1) for c in range(3)] + [NODE_H])
            for c in range(3):
                yy = y + LANE_HEAD
                for r in cells.get((z, c), []):
                    pos[r] = (LEFT + c * (NODE_W + COL_GAP), yy, NODE_W, height(parts[r]))
                    yy += height(parts[r]) + V_GAP
            lanes.append({"zone": z, "y": y, "h": LANE_HEAD + lane_h + LANE_FOOT})
            y += LANE_HEAD + lane_h + LANE_FOOT + LANE_GAP
        return lanes, y

    lanes, _ = place()
    for _ in range(4):  # barycentre sweeps reduce crossings
        for key, refs in cells.items():
            def bary(r):
                ys = [pos[o][1] + pos[o][3] / 2 for o in nbrs.get(r, []) if o in pos]
                return sum(ys) / len(ys) if ys else pos[r][1]
            refs.sort(key=bary)
        lanes, bottom = place()
    for ref, p in parts.items():
        if p["parent"]:
            x, y, w, _ = pos[p["parent"]]
            i = parts[p["parent"]]["children"].index(ref)
            pos[ref] = (x + 10, y + SERVER_HEAD + i * (CHILD_H + CHILD_GAP), w - 20, CHILD_H)
    width = LEFT + 3 * NODE_W + 2 * COL_GAP + RIGHT
    return {"pos": pos, "lanes": lanes, "width": width, "height": bottom + 4}


def edge_path(e: dict, m: dict, pos: dict, lane_x: float | None = None) -> tuple[str, tuple, tuple]:
    parts = m["parts"]

    def col(ref):
        r = parts[ref]["parent"] or ref
        return COLUMN_OF.get(parts[r]["kind"], 1)

    sx, sy, sw, sh = pos[e["from"]]
    tx, ty, tw, th = pos[e["to"]]
    a, b = col(e["from"]), col(e["to"])
    if b > a:
        p0, p3 = (sx + sw, sy + sh / 2), (tx - 7, ty + th / 2)
        d = max(40, (p3[0] - p0[0]) / 2)
        p1, p2 = (p0[0] + d, p0[1]), (p3[0] - d, p3[1])
        if lane_x is not None and p3[0] - p0[0] < COL_GAP + 20:  # neighbouring columns: own vertical channel
            p1, p2 = (lane_x, p0[1]), (lane_x, p3[1])
    elif b < a:
        p0, p3 = (sx, sy + sh / 2), (tx + tw + 7, ty + th / 2)
        d = max(40, (p0[0] - p3[0]) / 2)
        p1, p2 = (p0[0] - d, p0[1]), (p3[0] + d, p3[1])
    else:  # same column: loop out on the left
        p0, p3 = (sx, sy + sh / 2), (tx - 7, ty + th / 2)
        bulge = min(LEFT - 8, 24 + abs(p3[1] - p0[1]) / 8)
        p1, p2 = (p0[0] - bulge, p0[1]), (p3[0] - bulge, p3[1])
    pts = (p0, p1, p2, p3)
    d = f"M{p0[0]:.1f},{p0[1]:.1f} C{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}"
    return d, pts, p3


def at(pts: tuple, t: float) -> tuple:
    u = 1 - t
    return tuple(u ** 3 * pts[0][i] + 3 * u * u * t * pts[1][i] + 3 * u * t * t * pts[2][i] + t ** 3 * pts[3][i]
                 for i in range(2))


def free_spot(pts: tuple, width: float, taken: list, boxes: list) -> tuple:
    """Pick the point on the curve, nearest the middle, where a marker of this width overlaps the
    fewest other markers and parts (ideally none)."""
    def overlap(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    best = None
    for k in range(17):
        t = 0.5 + (k + 1) // 2 * 0.05 * (1 if k % 2 else -1)
        x, y = at(pts, t)
        r = (x - 14, y - 14, x + width - 2, y + 14)
        cost = sum(overlap(r, o) for o in taken) * 3 + sum(overlap(r, o) for o in boxes)
        if best is None or cost < best[0]:
            best = (cost, x, y, r)
        if cost == 0:
            break
    taken.append(best[3])
    return best[1], best[2]


# ------------------------------------------------------------------------- icons
ICONS = {  # 20x20 glyphs, drawn with currentColor
    "agent": "<rect x='3' y='5' width='14' height='11' rx='3'/><circle cx='7.5' cy='10.5' r='1.3' class='f'/>"
             "<circle cx='12.5' cy='10.5' r='1.3' class='f'/><path d='M10 5V2.5'/>",
    "agent_unit": "<rect x='4' y='6' width='12' height='10' rx='3'/><path d='M7.5 11h5'/><path d='M10 6V3.5'/>",
    "tool": "<path d='M12.5 3.5a3.5 3.5 0 0 0-3.3 4.7L3.8 13.6a1.4 1.4 0 0 0 2 2l5.4-5.4a3.5 3.5 0 0 0 4.7-3.3l-2 2-2-.6-.6-2z'/>",
    "mcp_tool": "<path d='M12.5 3.5a3.5 3.5 0 0 0-3.3 4.7L3.8 13.6a1.4 1.4 0 0 0 2 2l5.4-5.4a3.5 3.5 0 0 0 4.7-3.3l-2 2-2-.6-.6-2z'/>",
    "mcp_server": "<path d='M7 3v4M13 3v4'/><rect x='4.5' y='7' width='11' height='5' rx='1.5'/><path d='M10 12v5'/>",
    "external_api": "<path d='M6 15.5h8.5a3.5 3.5 0 0 0 .3-7 5 5 0 0 0-9.6 1.2A3 3 0 0 0 6 15.5z'/>",
    "data_store": "<ellipse cx='10' cy='5' rx='6' ry='2.3'/><path d='M4 5v10c0 1.3 2.7 2.3 6 2.3s6-1 6-2.3V5'/>"
                  "<path d='M4 10c0 1.3 2.7 2.3 6 2.3s6-1 6-2.3'/>",
    "model": "<path d='M10 2.5l1.8 5.7 5.7 1.8-5.7 1.8L10 17.5l-1.8-5.7L2.5 10l5.7-1.8z'/>",
    "gateway": "<path d='M10 2.5l6 2.5v4.5c0 3.8-2.6 6.6-6 8-3.4-1.4-6-4.2-6-8V5z'/>",
    "human_approval": "<circle cx='10' cy='6.5' r='3'/><path d='M4 17c.6-3.4 3-5 6-5s5.4 1.6 6 5'/>",
    "secret": "<circle cx='6.5' cy='10' r='3'/><path d='M9.5 10H17M14 10v3M16.5 10v2'/>",
    "audit_sink": "<rect x='4' y='3' width='12' height='14' rx='1.5'/><path d='M7 7h6M7 10h6M7 13h4'/>",
}
GATE_SHAPE = {  # badge glyph centred on (0,0), radius ~5
    "Blocker": "<polygon points='-2.1,-5 2.1,-5 5,-2.1 5,2.1 2.1,5 -2.1,5 -5,2.1 -5,-2.1'/>",
    "Required": "<polygon points='0,-5.5 5.5,4.5 -5.5,4.5'/>",
    "Detection": "<circle r='5'/>",
}


def icon(kind: str, x: float, y: float) -> str:
    return f"<g class=ico transform='translate({x:.1f},{y:.1f})' aria-hidden=true>{ICONS.get(kind, ICONS['tool'])}</g>"


def worst_gate(idx: list[int], findings: list[dict]) -> str | None:
    gates = {findings[i]["gate"] for i in idx}
    return next((g for g in GATES if g in gates), None)


def badge(idx: list[int], findings: list[dict], cx: float, cy: float) -> str:
    """A pill: gate shape + count. The shape and the number carry the meaning, not just the colour."""
    if not idx:
        return ""
    g = worst_gate(idx, findings)
    w = 34 if len(idx) < 10 else 42
    return (f"<g class='badge g-{g.lower()}' transform='translate({cx - w / 2:.1f},{cy - 10:.1f})' aria-hidden=true>"
            f"<rect width='{w}' height='20' rx='10'/><g class=gs transform='translate(11,10)'>{GATE_SHAPE[g]}</g>"
            f"<text x='{w - 10}' y='14.5' text-anchor=end>{len(idx)}</text></g>")


def findings_phrase(idx: list[int], findings: list[dict]) -> str:
    if not idx:
        return "No findings."
    counts = [f"{sum(findings[i]['gate'] == g for i in idx)} {g}" for g in GATES
              if any(findings[i]["gate"] == g for i in idx)]
    return f"{len(idx)} finding{'s' if len(idx) != 1 else ''}: {', '.join(counts)}."


# ---------------------------------------------------------------------------- svg
def svg(m: dict) -> str:
    L = layout(m)
    pos, parts, findings = L["pos"], m["parts"], m["findings"]
    out = [f"<svg id=map xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {L['width']} {L['height']:.0f}' "
           f"width='{L['width']}' height='{L['height']:.0f}' role=group aria-labelledby='map-title map-desc'>",
           f"<title id=map-title>Connection map for {esc(m['agent'])}</title>",
           "<desc id=map-desc>Parts are grouped in rows by trust zone and in columns from the agent on the left "
           "to services on the right. Each part and connection can be focused and selected. The tables after the "
           "map list the same information.</desc>",
           "<defs><pattern id=hatch width='8' height='8' patternUnits=userSpaceOnUse patternTransform='rotate(45)'>"
           "<rect width='8' height='8' class='hatch-bg'/><line x1='0' y1='0' x2='0' y2='8' class='hatch-line'/></pattern>"]
    for s in ("confirmed", "declared", "undeclared"):
        out.append(f"<marker id=arrow-{s} viewBox='0 0 10 10' refX='1' refY='5' markerWidth='7' markerHeight='7' "
                   f"orient=auto-start-reverse><path d='M0,0 L10,5 L0,10 z' class='ah {s}'/></marker>")
    out.append("</defs>")
    for c, name in enumerate(COLUMNS):
        out.append(f"<text class=colhead x='{LEFT + c * (NODE_W + COL_GAP) + NODE_W / 2}' y='24' "
                   f"text-anchor=middle>{esc(name)}</text>")
    for lane in L["lanes"]:
        unknown = lane["zone"] == "unknown"
        out.append(f"<g class='lane{' unknown' if unknown else ''}'>"
                   f"<rect x='8' y='{lane['y']}' width='{L['width'] - 16}' height='{lane['h']}' rx='12'/>"
                   f"<text x='24' y='{lane['y'] + 22}'>{esc(zone_name(lane['zone']))}"
                   + ("<tspan class=lane-note> — zone not established; treat as untrusted</tspan>" if unknown else "")
                   + "</text></g>")

    # Edges first so parts sit on top of them.
    out.append("<g id=edges>")
    taken: list = [(pos[r][0] + pos[r][2] - 22 - 20, pos[r][1] - 12, pos[r][0] + pos[r][2] - 22 + 20, pos[r][1] + 12)
                   for r in parts if parts[r]["badge"]]
    boxes = [(x, y, x + w, y + h) for r, (x, y, w, h) in pos.items() if not parts[r]["parent"]]
    # Give each forward edge between neighbouring columns its own vertical channel, so long
    # drops do not stack on one line. Deeper drops take channels further left (fewer crossings).
    channel: dict[str, float] = {}
    gaps: dict[float, list] = {}
    for e in m["edges"]:
        sx, sy, sw, sh = pos[e["from"]]
        tx, ty, _, th = pos[e["to"]]
        if tx - (sx + sw) > 0 and tx - (sx + sw) < COL_GAP + 20 + 30:
            gaps.setdefault(round(sx + sw if not parts[e["from"]]["parent"] else sx + sw + 10), []).append(
                (-(ty + th / 2 - sy - sh / 2), e["id"]))
    for left, items in gaps.items():
        items.sort()
        n = len(items)
        for k, (_, eid) in enumerate(items):
            channel[eid] = left + COL_GAP * (0.22 + 0.6 * (k / (n - 1) if n > 1 else 0.5))
    for e in m["edges"]:
        d, pts, _ = edge_path(e, m, pos, channel.get(e["id"]))
        need = (24 if e["status"] == "undeclared" else 0) + (36 if e["findings"] else 0)
        mid = free_spot(pts, need, taken, boxes) if need else (0, 0)
        src, dst = parts[e["from"]]["name"], parts[e["to"]]["name"]
        label = (f"Connection from {src} to {dst}" + (f", {e['label']}" if e["label"] else "")
                 + f". {STATUS_TEXT[e['status']]}. " + findings_phrase(e["findings"], findings))
        extra = ""
        if e["status"] == "undeclared":
            extra += (f"<g class=undecl-mark transform='translate({mid[0]:.1f},{mid[1]:.1f})' aria-hidden=true>"
                      "<rect x='-8' y='-8' width='16' height='16' transform='rotate(45)'/>"
                      "<text y='4.5' text-anchor=middle>!</text></g>")
        extra += badge(e["findings"], findings, mid[0] + (24 if e["status"] == "undeclared" else 0) + 6, mid[1])
        out.append(f"<g class='edge {e['status']}' id={e['id']} data-id={e['id']} tabindex=0 role=button "
                   f"aria-label='{esc(label)}'><path class=hit d='{d}'/>"
                   f"<path class=line d='{d}' marker-end='url(#arrow-{e['status']})'/>{extra}</g>")
    out.append("</g><g id=nodes>")

    def node_svg(ref: str) -> str:
        p = parts[ref]
        x, y, w, h = pos[ref]
        label = (f"{p['kind_label']} {p['name']}, zone {zone_name(p['zone'])}. {STATUS_TEXT[p['status']]}. "
                 + findings_phrase(p["findings"], findings))
        cls = f"node k-{p['kind']} {p['status']}" + (" root" if ref == m["root"] else "") + (" child" if p["parent"] else "")
        if p["children"]:  # MCP server: a container with its tools inside
            body = (f"<rect class=box x='{x}' y='{y}' width='{w}' height='{h}' rx='10'/>"
                    f"{icon(p['kind'], x + 10, y + 13)}"
                    f"<text class=name x='{x + 38}' y='{y + 22}'>{esc(short(p['name'], 22))}</text>"
                    f"<text class=kind x='{x + 38}' y='{y + 37}'>{esc(p['kind_label'])}"
                    f"{' · ' + esc(STATUS_SHORT[p['status']]) if p['status'] != 'confirmed' else ''}</text>")
        elif p["parent"]:
            body = (f"<rect class=box x='{x}' y='{y}' width='{w}' height='{h}' rx='6'/>"
                    f"{icon(p['kind'], x + 6, y + 4)}"
                    f"<text class=name x='{x + 30}' y='{y + 18.5}'>{esc(short(p['name'], 22))}</text>")
        else:
            body = (f"<rect class=box x='{x}' y='{y}' width='{w}' height='{h}' rx='10'/>"
                    f"{icon(p['kind'], x + 12, y + 15)}"
                    f"<text class=name x='{x + 42}' y='{y + 22}'>{esc(short(p['name']))}</text>"
                    f"<text class=kind x='{x + 42}' y='{y + 38}'>{esc(p['kind_label'])}"
                    f"{' · ' + esc(STATUS_SHORT[p['status']]) if p['status'] != 'confirmed' else ''}</text>")
        if p["status"] == "undeclared":
            body += (f"<g class=undecl-mark transform='translate({x + 2},{y + 2})' aria-hidden=true>"
                     "<rect x='-8' y='-8' width='16' height='16' transform='rotate(45)'/>"
                     "<text y='4.5' text-anchor=middle>!</text></g>")
        body += badge(p["badge"], findings, x + w - 22, y)
        title = f"<title>{esc(p['name'])}</title>"
        return (f"<g class='{cls}' id={p['id']} data-id={p['id']} tabindex=0 role=button "
                f"aria-label='{esc(label)}'>{title}{body}</g>")

    order = sorted((r for r in parts if not parts[r]["parent"]), key=lambda r: (pos[r][0], pos[r][1]))
    for ref in order:
        if parts[ref]["children"]:
            out.append(f"<g class=group>{node_svg(ref)}" + "".join(node_svg(c) for c in parts[ref]["children"]) + "</g>")
        else:
            out.append(node_svg(ref))
    out.append("</g></svg>")
    return "".join(out)


# --------------------------------------------------------------------------- page
CSS = """
:root{--ink:#1a1a1a;--muted:#555a63;--primary:#1a4d6e;--accent:#2e8bc0;--tint:#eef5fc;--tint2:#dde9f3;
--rule:#c8d4df;--bg:#ffffff;--card:#ffffff;--head:#15384f;--edge:#5b6b78;--lane:#f6f9fc;--lane-unknown:#fbf7ef;
--undecl:#7e22ce;--undecl-bg:#f5ecfd;--blocker:#b42318;--required:#8f4700;--detection:#1d4ed8;--on-badge:#ffffff;
--focus:#2e8bc0;--hatch:#efe6d3}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ink:#e4e8ec;--muted:#9aa4ae;--primary:#7fb8de;
--accent:#6cb6e6;--tint:#16222c;--tint2:#1c2b37;--rule:#2c3b47;--bg:#0f161c;--card:#131d25;--head:#cfe3f2;
--edge:#8c9aa6;--lane:#121c24;--lane-unknown:#1d1a14;--undecl:#d8b4fe;--undecl-bg:#2a1838;--blocker:#c4302b;
--required:#9a5200;--detection:#2b5fd9;--focus:#6cb6e6;--hatch:#2a2418}}
:root[data-theme="dark"]{--ink:#e4e8ec;--muted:#9aa4ae;--primary:#7fb8de;--accent:#6cb6e6;--tint:#16222c;
--tint2:#1c2b37;--rule:#2c3b47;--bg:#0f161c;--card:#131d25;--head:#cfe3f2;--edge:#8c9aa6;--lane:#121c24;
--lane-unknown:#1d1a14;--undecl:#d8b4fe;--undecl-bg:#2a1838;--blocker:#c4302b;--required:#9a5200;--detection:#2b5fd9;
--focus:#6cb6e6;--hatch:#2a2418}
*{box-sizing:border-box}
body{margin:0;color:var(--ink);background:var(--bg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1400px;margin:0 auto;padding:28px 16px 80px}
h1{font-size:1.75rem;line-height:1.2;margin:0 0 6px;color:var(--head)}
h2{font-size:1.3rem;margin:40px 0 8px;color:var(--head)}
h3{font-size:1.05rem;margin:0 0 4px}
p{margin:6px 0}
.lede{color:var(--muted);max-width:70ch}
code{background:var(--tint2);border-radius:4px;padding:1px 5px;font:13.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;overflow-wrap:anywhere}
.skip{position:absolute;left:-9999px}.skip:focus{left:16px;top:8px;background:var(--card);padding:6px 10px;border:2px solid var(--focus);z-index:10}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:20px 0}
.tile{background:var(--card);border:1px solid var(--rule);border-radius:12px;padding:12px 14px}
.tile b{display:block;font-size:1.7rem;line-height:1.1}
.tile>span{color:var(--muted);font-size:.88rem}
.tile.undecl{border-color:var(--undecl);background:var(--undecl-bg)}.tile.undecl b{color:var(--undecl)}
.tile .gates{display:flex;flex-direction:column;gap:3px;font-size:.92rem;margin-top:2px}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:.8rem;font-weight:600;padding:1px 9px 1px 6px;border-radius:999px;white-space:nowrap;color:var(--on-badge)}
.chip svg{width:12px;height:12px;fill:currentColor}
.chip.blocker{background:var(--blocker)}.chip.required{background:var(--required)}.chip.detection{background:var(--detection)}
.st{display:inline-block;font-size:.8rem;font-weight:600;padding:1px 8px;border-radius:6px;border:1.5px solid var(--edge);color:var(--ink);white-space:nowrap}
.st.declared{border-style:dashed;color:var(--muted)}
.st.undeclared{border-color:var(--undecl);color:var(--undecl);background:var(--undecl-bg);border-width:2px}
.layout{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:16px;align-items:start}
.mapcard{background:var(--card);border:1px solid var(--rule);border-radius:14px;overflow:hidden}
.toolbar{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;padding:10px 14px;border-bottom:1px solid var(--rule);font-size:.9rem}
.toolbar label{display:inline-flex;align-items:center;gap:6px;cursor:pointer}
.toolbar fieldset{border:0;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px 14px}
.toolbar legend{float:left;font-weight:600;margin-right:6px;padding:0}
.toolbar details summary{cursor:pointer;font-weight:600}
.toolbar .types{display:flex;flex-wrap:wrap;gap:4px 12px;padding:6px 0 0}
.zoom{margin-left:auto;display:flex;gap:4px}
button{font:inherit;font-size:.88rem;color:var(--ink);background:var(--card);border:1px solid var(--rule);border-radius:6px;padding:3px 10px;cursor:pointer}
button:hover{border-color:var(--accent)}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.scroller{overflow:auto;max-height:78vh;-webkit-overflow-scrolling:touch}
#map{display:block;font-family:inherit}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;margin:0;padding:10px 14px;list-style:none;border-top:1px solid var(--rule);font-size:.85rem;color:var(--muted)}
.legend li{display:flex;align-items:center;gap:6px}
.legend svg{flex:none}
/* svg parts */
.colhead{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;fill:var(--muted)}
.lane rect{fill:var(--lane);stroke:var(--rule)}
.lane text{font-size:13px;font-weight:700;fill:var(--head)}
.lane.unknown rect{fill:url(#hatch);stroke:var(--required);stroke-dasharray:4 4}
.lane .lane-note{font-weight:400;fill:var(--muted)}
.hatch-bg{fill:var(--lane-unknown)}.hatch-line{stroke:var(--hatch);stroke-width:3}
.node .box{fill:var(--card);stroke:var(--edge);stroke-width:1.5}
.node.root .box{fill:var(--tint);stroke:var(--primary);stroke-width:2.5}
.node.declared .box{stroke-dasharray:6 4;fill:var(--bg)}
.node.declared .name,.node.declared .ico{opacity:.75}
.node.undeclared .box{stroke:var(--undecl);stroke-width:3;fill:var(--undecl-bg)}
.node.child .box{fill:var(--tint)}
.node .name{font-size:13.5px;font-weight:600;fill:var(--ink)}
.node .kind{font-size:11.5px;fill:var(--muted)}
.node.undeclared .kind{fill:var(--undecl);font-weight:600}
.ico{fill:none;stroke:var(--primary);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
.ico .f{fill:var(--primary);stroke:none}
.edge .line{fill:none;stroke:var(--edge);stroke-width:1.6}
.edge.declared .line{stroke-dasharray:7 6;opacity:.85}
.edge.undeclared .line{stroke:var(--undecl);stroke-width:3}
.edge .hit{fill:none;stroke:transparent;stroke-width:14;pointer-events:stroke}
.ah{fill:var(--edge)}.ah.undeclared{fill:var(--undecl)}
.undecl-mark rect{fill:var(--undecl);stroke:var(--card);stroke-width:2}
.undecl-mark text{fill:var(--bg);font-size:13px;font-weight:800}
.badge rect{stroke:var(--card);stroke-width:2}
.badge text{fill:var(--on-badge);font-size:12px;font-weight:700}
.badge .gs{fill:var(--on-badge)}
.g-blocker rect{fill:var(--blocker)}.g-required rect{fill:var(--required)}.g-detection rect{fill:var(--detection)}
.node,.edge{cursor:pointer;transition:opacity .15s}
.node:focus,.edge:focus{outline:none}
.node:focus-visible .box,.node.sel .box{stroke:var(--focus);stroke-width:3.5}
.edge:focus-visible .line,.edge.sel .line{stroke:var(--focus);stroke-width:3.5}
#map.hov .node:not(.hl),#map.hov .edge:not(.hl){opacity:.22}
.node.off,.edge.off{opacity:.08 !important;pointer-events:none}
/* panel */
#panel{position:sticky;top:12px;background:var(--card);border:1px solid var(--rule);border-radius:14px;padding:16px 18px;max-height:calc(100vh - 24px);overflow:auto}
#panel h2{margin:0 0 6px;font-size:1.15rem}
#panel .kindline{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:var(--muted);font-size:.9rem}
#panel dl{margin:10px 0;display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:.92rem}
#panel dt{color:var(--muted)}#panel dd{margin:0;overflow-wrap:anywhere}
#panel h3{margin:16px 0 6px;font-size:.95rem;color:var(--head)}
.ev{list-style:none;padding:0;margin:0}.ev li{margin:4px 0}
.ev q{display:block;quotes:none;font:12.5px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--tint);border-left:3px solid var(--rule);padding:4px 8px;margin-top:2px;white-space:pre-wrap;overflow-wrap:anywhere}
.fcard{border:1px solid var(--rule);border-left:5px solid var(--edge);border-radius:10px;padding:10px 12px;margin:8px 0}
.fcard.blocker{border-left-color:var(--blocker)}.fcard.required{border-left-color:var(--required)}.fcard.detection{border-left-color:var(--detection)}
.fcard .top{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.fcard .who{font-size:.88rem;color:var(--muted);margin-top:6px}
.fcard .who b{color:var(--ink);font-weight:600}
details summary{cursor:pointer}
.fcard details{margin-top:6px}.fcard ol{padding-left:1.3em;margin:6px 0}.fcard li{margin:3px 0}
.done{border-left:4px solid var(--detection);background:var(--tint);padding:6px 10px;border-radius:6px;font-size:.92rem}
.links{list-style:none;padding:0;margin:0}.links li{margin:2px 0}
.links button{text-align:left;width:100%;border-color:transparent;background:var(--tint)}
.why{margin:6px 0;padding-left:1.2em}
.callout{border:2px solid var(--undecl);background:var(--undecl-bg);color:var(--ink);border-radius:8px;padding:6px 10px;font-size:.92rem}
/* tables */
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--rule);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.92rem}
caption{text-align:left;padding:10px 12px 0;color:var(--muted);font-size:.88rem}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.84rem}
tbody tr:last-child td{border-bottom:0}
td ol{margin:4px 0;padding-left:1.2em}
.limits li{color:var(--muted);margin:4px 0}
@media (max-width:1000px){.layout{grid-template-columns:minmax(0,1fr)}#panel{position:static;max-height:none}}
@media (max-width:640px){h1{font-size:1.4rem}.scroller{max-height:70vh}.zoom{margin-left:0}}
@media print{
 body{background:#fff;color:#000;font-size:11pt}
 .toolbar,.zoom,#panel,.skip{display:none !important}
 .layout{display:block}.scroller{overflow:visible;max-height:none}
 #map{width:100% !important;height:auto !important}
 .mapcard,.tablewrap,.tile{border-color:#999}
 h2{break-after:avoid}tr,.fcard{break-inside:avoid}
 .node.off,.edge.off{opacity:1 !important}
}
@media (prefers-reduced-motion:reduce){.node,.edge{transition:none}}
"""

JS = r"""
(() => {
const D = JSON.parse(document.getElementById('topology-data').textContent);
const svg = document.getElementById('map'), panel = document.getElementById('panel');
const byId = {}; D.parts.forEach(p => byId[p.id] = p); D.edges.forEach(e => byId[e.id] = e);
const refId = {}; D.parts.forEach(p => refId[p.ref] = p.id);
const GATES = ['Blocker', 'Required', 'Detection'];
const SHAPES = {Blocker: 'M-2.1,-5H2.1L5,-2.1V2.1L2.1,5H-2.1L-5,2.1V-2.1Z', Required: 'M0,-5.5L5.5,4.5H-5.5Z',
                Detection: 'M0,-5A5,5 0 1 1 0,5A5,5 0 1 1 0,-5Z'};
const NS = 'http://www.w3.org/2000/svg';
let selected = null;

function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) { if (k === 'class') n.className = v; else n.setAttribute(k, v); }
  for (const k of kids) if (k != null) n.append(k.nodeType ? k : document.createTextNode(String(k)));
  return n;
}
function rich(text) {  // `code` spans become <code>; everything else stays plain text
  const span = el('span');
  String(text).split('`').forEach((bit, k) => span.append(k % 2 ? el('code', {}, bit) : document.createTextNode(bit)));
  return span;
}
function chip(gate) {
  const s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', '-6 -6 12 12'); s.setAttribute('aria-hidden', 'true');
  const p = document.createElementNS(NS, 'path'); p.setAttribute('d', SHAPES[gate]); s.append(p);
  return el('span', {class: 'chip ' + gate.toLowerCase()}, s, gate);
}
function status(s) { return el('span', {class: 'st ' + s}, D.status_text[s]); }
function name(ref) { return byId[refId[ref]] ? byId[refId[ref]].name : ref; }
function evList(title, items) {
  if (!items.length) return null;
  const ul = el('ul', {class: 'ev'});
  for (const it of items) {
    const li = el('li', {}, el('code', {}, typeof it === 'string' ? it : it.at));
    if (it.quote) li.append(el('q', {}, it.quote));
    ul.append(li);
  }
  return [el('h3', {}, title), ul];
}
function findingCard(i) {
  const f = D.findings[i];
  const card = el('div', {class: 'fcard ' + f.gate.toLowerCase()},
    el('div', {class: 'top'}, chip(f.gate), el('strong', {}, f.item + ' ' + f.title), el('span', {class: 'st'}, f.rating_text)),
    el('p', {}, rich(f.problem)),
    el('div', {class: 'who'}, 'Lead role: ', el('b', {}, f.lead || 'not set')));
  const steps = el('ol'); f.steps.forEach(s => steps.append(el('li', {}, rich(s))));
  const det = el('details', {}, el('summary', {}, 'How to fix (' + f.steps.length + ' steps' + (f.effort ? ', ' + f.effort + ' effort' : '') + ')'), steps);
  if (f.done_when) det.append(el('p', {class: 'done'}, el('b', {}, 'Done when: '), rich(f.done_when)));
  if (f.evidence.length) det.append(el('p', {}, 'Where in the code: ', ...f.evidence.flatMap((e, k) => [k ? ', ' : '', el('code', {}, e)])));
  card.append(det);
  return card;
}
function linkTo(id, text) {
  const b = el('button', {type: 'button'}, text);
  b.addEventListener('click', () => { select(id); document.getElementById(id).focus(); });
  return el('li', {}, b);
}
function show(id) {
  const x = byId[id]; panel.replaceChildren();
  const isEdge = id[0] === 'e';
  if (isEdge) {
    panel.append(el('h2', {}, name(x.from) + ' → ' + name(x.to)),
      el('div', {class: 'kindline'}, 'Connection', status(x.status)));
    if (x.label) panel.append(el('p', {}, 'What it does: ' + x.label + '.'));
    if (x.risk_text.length) {
      const ul = el('ul', {class: 'why'}); x.risk_text.forEach(r => ul.append(el('li', {}, r)));
      panel.append(el('h3', {}, 'Why it matters'), ul);
    }
  } else {
    panel.append(el('h2', {}, x.name), el('div', {class: 'kindline'}, x.kind_label, status(x.status)), el('p', {}, x.about));
    const dl = el('dl');
    const row = (k, v) => { if (v) dl.append(el('dt', {}, k), el('dd', {}, v)); };
    row('Trust zone', D.zone_names[x.zone]); row('Inside', x.parent ? name(x.parent) : '');
    row('Owner', x.owner); row('Transport', x.transport); row('Address', x.endpoints.join(', '));
    row('Secrets used', x.credential_keys.length ? x.credential_keys.join(', ') + ' (names only)' : '');
    panel.append(dl);
    if (x.note) panel.append(el('p', {class: 'lede'}, x.note));
    if (x.zone === 'unknown') panel.append(el('p', {class: 'lede'}, 'Nobody has shown which network this is in. Treat it as untrusted until someone does.'));
  }
  if (x.status === 'undeclared') panel.append(el('p', {class: 'callout'}, 'Found in code but not declared. Check it is meant to exist, then declare it or remove it.'));
  if (x.status === 'declared') panel.append(el('p', {class: 'lede'}, 'Declared in the settings, but the reviewer did not find code that uses it. If it is not needed, remove it.'));
  for (const part of [evList('Declared in', x.declared_in), evList('Found in code', x.found_in), evList('Trust zone shown by', x.zone_evidence || [])])
    if (part) panel.append(...part);
  panel.append(el('h3', {}, x.findings.length ? 'BRACE findings (' + x.findings.length + ')' : 'BRACE findings'));
  if (!x.findings.length) panel.append(el('p', {class: 'lede'}, 'None recorded here.'));
  x.findings.forEach(i => panel.append(findingCard(i)));
  const ul = el('ul', {class: 'links'});
  if (isEdge) { ul.append(linkTo(refId[x.from], 'From: ' + name(x.from)), linkTo(refId[x.to], 'To: ' + name(x.to))); }
  else D.edges.filter(e => e.from === x.ref || e.to === x.ref).forEach(e =>
    ul.append(linkTo(e.id, (e.from === x.ref ? '→ ' + name(e.to) : '← ' + name(e.from)) + (e.status === 'undeclared' ? ' (undeclared)' : ''))));
  if (x.children && x.children.length) x.children.forEach(c => ul.append(linkTo(refId[c], 'Tool: ' + name(c))));
  if (ul.children.length) panel.append(el('h3', {}, isEdge ? 'Ends' : 'Connections'), ul);
}
function neighbours(id) {
  const x = byId[id], set = new Set([id]);
  if (id[0] === 'e') { set.add(refId[x.from]); set.add(refId[x.to]); }
  else D.edges.forEach(e => { if (e.from === x.ref || e.to === x.ref) { set.add(e.id); set.add(refId[e.from]); set.add(refId[e.to]); } });
  if (x.parent) set.add(refId[x.parent]);
  (x.children || []).forEach(c => set.add(refId[c]));
  return set;
}
function highlight(id) {
  svg.querySelectorAll('.hl').forEach(n => n.classList.remove('hl'));
  if (!id) { svg.classList.remove('hov'); return; }
  neighbours(id).forEach(n => { const g = document.getElementById(n); if (g) g.classList.add('hl'); });
  svg.classList.add('hov');
}
function select(id) {
  svg.querySelectorAll('.sel').forEach(n => n.classList.remove('sel'));
  selected = id;
  if (id) { document.getElementById(id).classList.add('sel'); show(id); highlight(id); }
  else { panel.replaceChildren(...intro.map(n => n.cloneNode(true))); highlight(null); }
}
const intro = [...panel.childNodes].map(n => n.cloneNode(true));
svg.querySelectorAll('.node,.edge').forEach(g => {
  const id = g.dataset.id;
  g.addEventListener('click', ev => { ev.stopPropagation(); select(id); });
  g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(id); } });
  g.addEventListener('mouseenter', () => highlight(id));
  g.addEventListener('mouseleave', () => highlight(selected));
  g.addEventListener('focus', () => highlight(id));
  g.addEventListener('blur', () => highlight(selected));
});
document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && selected) { const s = selected; select(null); document.getElementById(s).focus(); } });

// Filters: everything stays in place; filtered-out parts fade so the layout never jumps.
const form = document.getElementById('filters');
function applyFilters() {
  const only = form.querySelector('[name=only]:checked').value;
  const kinds = new Set([...form.querySelectorAll('[name=kind]:checked')].map(i => i.value));
  const kindOk = p => kinds.has(p.kind) || (p.kind === 'mcp_tool' && kinds.has('mcp_server'));
  const match = x => only === 'all' || (only === 'findings' && x.findings.length) || (only === 'undeclared' && x.status === 'undeclared')
                     || (only === 'declared' && x.status === 'declared');
  const on = new Set();
  D.edges.forEach(e => { const a = byId[refId[e.from]], b = byId[refId[e.to]];
    if (kindOk(a) && kindOk(b) && match(e)) { on.add(e.id); on.add(a.id); on.add(b.id); } });
  D.parts.forEach(p => { if (kindOk(p) && match(p)) on.add(p.id); });
  D.parts.forEach(p => { if (p.parent && on.has(p.id)) on.add(refId[p.parent]); });
  if (only === 'all') D.parts.forEach(p => { if (kindOk(p)) on.add(p.id); });
  svg.querySelectorAll('.node,.edge').forEach(g => {
    const off = !on.has(g.dataset.id); g.classList.toggle('off', off);
    if (off) g.setAttribute('tabindex', '-1'); else g.setAttribute('tabindex', '0');
  });
  document.getElementById('filter-count').textContent = 'Showing ' + [...on].filter(i => i[0] === 'n').length + ' of ' + D.parts.length + ' parts';
}
form.addEventListener('change', applyFilters);

// Zoom keeps the drawing sharp (it is vector) and scrolls inside its box.
const W = +svg.getAttribute('width'), H = +svg.getAttribute('height'); let z = 1;
function zoom(f) { z = f === 0 ? Math.min(1, document.querySelector('.scroller').clientWidth / W) : Math.max(.4, Math.min(2.5, z * f));
  svg.setAttribute('width', Math.round(W * z)); svg.setAttribute('height', Math.round(H * z)); }
document.getElementById('zin').addEventListener('click', () => zoom(1.25));
document.getElementById('zout').addEventListener('click', () => zoom(0.8));
document.getElementById('zfit').addEventListener('click', () => zoom(0));
if (document.querySelector('.scroller').clientWidth < W) zoom(0);
addEventListener('beforeprint', () => document.querySelectorAll('details').forEach(d => d.open = true));
})();
"""


def legend_item(svg_body: str, text: str, w: int = 34) -> str:
    return (f"<li><svg width='{w}' height='20' viewBox='0 0 {w} 20' aria-hidden=true>{svg_body}</svg>{esc(text)}</li>")


def gate_chip(g: str) -> str:
    shape = GATE_SHAPE[g]
    return (f"<span class='chip {g.lower()}'><svg viewBox='-6 -6 12 12' aria-hidden=true>{shape}</svg>{esc(g)}</span>")


def render(m: dict) -> str:
    s = m["summary"]
    parts, edges, findings = m["parts"], m["edges"], m["findings"]
    data = {
        "parts": list(parts.values()), "edges": edges, "findings": findings,
        "status_text": STATUS_TEXT, "zone_names": {z: zone_name(z) for z in m["zones"]},
    }
    blob = json.dumps(data).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    kinds = sorted({p["kind"] for p in parts.values() if not p["parent"]},
                   key=lambda k: KIND_ORDER.index(k) if k in KIND_ORDER else 99)
    meta = []
    if m.get("repo"):
        meta.append(f"Review of <code>{esc(m['repo'])}</code>")
    if m.get("commit"):
        meta.append(f"commit <code>{esc(m['commit'])}</code>")
    if m.get("reviewed_at"):
        meta.append(esc(m["reviewed_at"]))
    if m.get("owner"):
        meta.append(f"owner {esc(m['owner'])}")
    ordered = sorted(findings, key=lambda f: (GATES.index(f["gate"]) if f["gate"] in GATES else 9, f["rating"] != "gap", f["item"]))

    out = ["<!doctype html><html lang=en><head><meta charset=utf-8>",
           "<meta name=viewport content='width=device-width,initial-scale=1'>",
           f"<title>Agent map: {esc(m['agent'])}</title><style>{CSS}</style></head><body>",
           "<a class=skip href=#tables>Skip the map and go to the tables</a><main>",
           f"<h1>What {esc(m['agent'])} connects to</h1>",
           f"<p class=lede>{' · '.join(meta) + '. ' if meta else ''}This map compares what the settings declare "
           "with what a reviewer found in the code. Start with the numbers, then select any part or line on the map "
           "to see the evidence, the BRACE findings and how to fix them.</p>",
           "<section aria-labelledby=ov><h2 id=ov style='margin-top:20px'>Overview</h2><div class=tiles>",
           f"<div class=tile><b>{s['parts']}</b><span>parts on the map</span></div>",
           f"<div class=tile><b>{s['connections']}</b><span>connections</span></div>",
           f"<div class='tile undecl'><b>{s['undeclared']}</b><span>undeclared: in code, not in settings</span></div>",
           f"<div class=tile><b>{s['declared_only']}</b><span>declared only: not found in code</span></div>",
           f"<div class=tile><b>{s['crossings']}</b><span>connections that cross a trust boundary or reach an unknown zone</span></div>",
           "<div class=tile><span>open BRACE findings</span><div class=gates>"
           + "".join(f"<div>{gate_chip(g)} <b style='display:inline;font-size:1.1rem'>{s['findings'][g]}</b></div>" for g in GATES)
           + "</div></div>",
           "</div></section>"]

    filt = ["<form id=filters class=toolbar onsubmit='return false'>",
            "<fieldset><legend>Show</legend>"]
    for val, text, checked in (("all", "Everything", True), ("findings", "Only with findings", False),
                               ("undeclared", "Only undeclared", False), ("declared", "Only declared, unused", False)):
        filt.append(f"<label><input type=radio name=only value={val}{' checked' if checked else ''}>{esc(text)}</label>")
    filt.append("</fieldset><details><summary>Types</summary><div class=types>")
    for k in kinds:
        filt.append(f"<label><input type=checkbox name=kind value={esc(k)} checked>{esc(KIND_LABEL.get(k, k))}</label>")
    filt.append("</div></details><span id=filter-count class=lede aria-live=polite></span>"
                "<div class=zoom role=group aria-label=Zoom><button type=button id=zout aria-label='Zoom out'>−</button>"
                "<button type=button id=zfit>Fit</button><button type=button id=zin aria-label='Zoom in'>+</button></div></form>")

    def legend() -> str:
        li = [
            legend_item("<path d='M2 10H32' stroke='var(--edge)' stroke-width='1.6'/>", "Declared and found in code"),
            legend_item("<path d='M2 10H32' stroke='var(--edge)' stroke-width='1.6' stroke-dasharray='7 6'/>",
                        "Declared only: not found in code"),
            legend_item("<path d='M2 10H32' stroke='var(--undecl)' stroke-width='3'/><g transform='translate(17,10)'>"
                        "<rect x='-6' y='-6' width='12' height='12' transform='rotate(45)' fill='var(--undecl)'/>"
                        "<text y='4' text-anchor=middle font-size='11' font-weight='800' fill='var(--bg)'>!</text></g>",
                        "Undeclared: found in code, not in settings"),
            legend_item("<rect x='2' y='3' width='30' height='14' rx='3' fill='url(#hatch)' stroke='var(--required)' "
                        "stroke-dasharray='3 3'/>", "Unknown trust zone"),
        ]
        for g in GATES:
            li.append(legend_item(f"<g class='badge g-{g.lower()}'><rect x='1' y='1' width='32' height='18' rx='9'/>"
                                  f"<g class=gs transform='translate(11,10)'>{GATE_SHAPE[g]}</g>"
                                  "<text x='26' y='14.5' text-anchor=end>n</text></g>", f"{g} findings (count)"))
        for k in kinds + (["mcp_tool"] if any(p["kind"] == "mcp_tool" for p in parts.values()) else []):
            li.append(legend_item(f"<g class=ico transform='translate(7,0)'>{ICONS.get(k, ICONS['tool'])}</g>",
                                  KIND_LABEL.get(k, k), 34))
        return "<ul class=legend aria-label='Map key'>" + "".join(li) + "</ul>"

    intro = ("<h2>How to read the map</h2><p>The agent is on the left. Lines run to the tools it can call and the "
             "services, data and models those reach. Rows are trust zones.</p>"
             "<p>Select a part or a line (click it, or press Tab and then Enter) to see what it is, where it is in "
             "the code, its BRACE findings and how to fix them. Press Escape to come back here.</p>"
             "<h3>Fix first</h3><ol style='padding-left:1.2em;margin:4px 0'>"
             + "".join(f"<li>{gate_chip(f['gate'])} <b>{esc(f['item'])}</b> {esc(f['title'])}: "
                       f"{esc(', '.join(f['where']) or 'not mapped')}</li>" for f in ordered[:5])
             + "</ol>" if findings else
             "<h2>How to read the map</h2><p>Select a part or a line to see its evidence. No findings were given.</p>")

    out += ["<h2 id=map-h>The map</h2>",
            "<div class=layout><div class=mapcard>", "".join(filt),
            "<div class=scroller>", svg(m), "</div>", legend(), "</div>",
            f"<aside id=panel aria-live=polite aria-label='Details'>{intro}</aside></div>"]

    # ---- text equivalent
    out.append("<h2 id=tables tabindex=-1>BRACE findings</h2>")
    out.append("<div class=tablewrap><table><caption>Most urgent first. Open “How to fix” for the steps.</caption>"
               "<thead><tr><th>Item</th><th>Gate</th><th>What is wrong</th><th>Where</th><th>Lead role</th></tr></thead><tbody>")
    for f in ordered:
        steps = "".join(f"<li>{code_spans(x)}</li>" for x in f["steps"])
        out.append(
            f"<tr><td><b>{esc(f['item'])}</b><br>{esc(f['title'])}</td><td>{gate_chip(f['gate'])}<br>"
            f"<span class=lede>{esc(f['rating_text'])}</span></td><td>{code_spans(f['problem'])}"
            f"<details><summary>How to fix</summary><ol>{steps}</ol>"
            + (f"<p class=done><b>Done when:</b> {code_spans(f['done_when'])}</p>" if f["done_when"] else "")
            + (f"<p>Where in the code: {', '.join(f'<code>{esc(e)}</code>' for e in f['evidence'])}</p>" if f["evidence"] else "")
            + f"</details></td><td>{esc(', '.join(f['where']) or 'not mapped')}</td><td>{esc(f['lead'])}</td></tr>")
    if not findings:
        out.append("<tr><td colspan=5>No findings were given for this map.</td></tr>")
    out.append("</tbody></table></div>")

    out.append("<h2>Every part</h2><div class=tablewrap><table><caption>Grouped by trust zone.</caption><thead><tr>"
               "<th>Part</th><th>Type</th><th>Trust zone</th><th>Status</th><th>Evidence</th><th>Findings</th>"
               "</tr></thead><tbody>")
    for z in m["zones"]:
        for p in sorted((p for p in parts.values() if p["zone"] == z),
                        key=lambda p: (KIND_ORDER.index(p["kind"]) if p["kind"] in KIND_ORDER else 50, p["name"])):
            ev = [f"declared <code>{esc(x)}</code>" for x in p["declared_in"]]
            ev += [f"code <code>{esc(x['at'])}</code>" for x in p["found_in"]]
            fl = ", ".join(esc(findings[i]["item"]) for i in p["findings"]) or "none"
            inside = f" <span class=lede>(in {esc(parts[p['parent']]['name'])})</span>" if p["parent"] else ""
            out.append(f"<tr><td>{esc(p['name'])}{inside}</td><td>{esc(p['kind_label'])}</td><td>{esc(zone_name(z))}</td>"
                       f"<td><span class='st {p['status']}'>{esc(STATUS_SHORT[p['status']])}</span></td>"
                       f"<td>{'<br>'.join(ev) or '<span class=lede>none</span>'}</td><td>{fl}</td></tr>")
    out.append("</tbody></table></div>")

    out.append("<h2>Every connection</h2><div class=tablewrap><table><caption>Undeclared connections first."
               "</caption><thead><tr><th>From</th><th>To</th><th>What it does</th><th>Status</th><th>Why it matters</th>"
               "<th>Evidence</th><th>Findings</th></tr></thead><tbody>")
    rank = {"undeclared": 0, "declared": 1, "confirmed": 2}
    for e in sorted(edges, key=lambda e: (rank[e["status"]], -len(e["findings"]), -len(e["risks"]))):
        ev = [f"declared <code>{esc(x)}</code>" for x in e["declared_in"]]
        ev += [f"code <code>{esc(x['at'])}</code>" + (f"<br><code>{esc(x['quote'])}</code>" if x["quote"] else "")
               for x in e["found_in"]]
        out.append(f"<tr><td>{esc(parts[e['from']]['name'])}</td><td>{esc(parts[e['to']]['name'])}</td>"
                   f"<td>{esc(e['label']) or '<span class=lede>not stated</span>'}</td>"
                   f"<td><span class='st {e['status']}'>{esc(STATUS_SHORT[e['status']])}</span></td>"
                   f"<td>{esc('; '.join(e['risk_text'])) or '<span class=lede>none stated</span>'}</td>"
                   f"<td>{'<br>'.join(ev) or '<span class=lede>none</span>'}</td>"
                   f"<td>{', '.join(esc(findings[i]['item']) for i in e['findings']) or 'none'}</td></tr>")
    out.append("</tbody></table></div>")

    out.append("<h2>What this page does not show</h2><ul class=limits>"
               "<li>It is built from reading code and settings. It does not prove the agent is safe when it runs.</li>"
               "<li>“Undeclared” means the settings do not list it. Code the reviewer did not trace is not on the map.</li>"
               + "".join(f"<li>{esc(x)}</li>" for x in m["limits"]) + "</ul>")
    out.append(f"</main><script type=application/json id=topology-data>{blob}</script><script>{JS}</script></body></html>\n")
    return "".join(out)


def write(bom_path: Path, findings_path: Path | None, out: Path) -> dict:
    bom = json.loads(bom_path.read_text())
    findings = json.loads(findings_path.read_text()) if findings_path else None
    m = build_model(bom, findings)
    out.write_text(render(m))
    return m
