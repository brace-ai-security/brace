#!/usr/bin/env python3
"""BRACE component topology prototype (CycloneDX 1.7).

Builds a first-pass component topology for one agent repository from files that
already exist, writes it as a CycloneDX 1.7 BOM, validates it against the vendored
official schema, and renders it as a Mermaid flowchart.

    python tools/brace/topology.py build <repo> -o topology.cdx.json \
        [--inventory <repo>/brace-inventory.json] [--agent-config <repo>/config/agent.yaml]
    python tools/brace/topology.py validate topology.cdx.json
    python tools/brace/topology.py mermaid topology.cdx.json [-o topology.mmd]
    python tools/brace/topology.py report topology.cdx.json [--findings brace-findings.json] -o topology.html
    python tools/brace/topology.py add-node|add-edge|set-zone <repo> --evidence path:line --quote "..." ...
    python tools/brace/topology.py record topology.cdx.json [--record .brace/topology.cdx.json] [--apply]

Workflow: `build` seeds what files declare; the reviewer records code-traced nodes,
edges and trust zones with `add-node`/`add-edge`/`set-zone` into an overlay file
(each rejected unless the quote is on the cited line, and re-checked on every build);
`record` reports whether the recorded topology is missing or differs and proposes
creating or updating it. It writes only with `--apply`, which a skill passes only
after the user confirms.

Inputs: `.mcp.json` (MCP servers), the candidate inventory written by
`skills/brace-review/scripts/review_coverage.py inventory`, and optionally an agent
config with `agent.name`, `agent.model`, `agent.operational_owner`,
`tools.allowlist` and `connections` (the services and stores the agent is meant to
reach: `[{from, to, kind, name, label}]`). Nothing is executed or contacted. The result is a declared,
script-derived starting point: it is always marked incomplete, and trust zones,
boundary crossings and data flows stay unknown until a reviewer establishes them.

Status: prototype for brace-fjm.1. The `brace:` property names are provisional.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
CDX_DIR = HERE / "schemas" / "cyclonedx-1.7"
SPEC_VERSION = "1.7"
NS = uuid.UUID("6f1c3a52-6a39-4f0e-9a64-2b1f6e0f7a11")  # BRACE topology namespace
SECRET_FLAG = re.compile(r"(token|secret|password|passwd|api[-_]?key|credential)", re.I)
LIMITATIONS = (
    "Script-derived first pass from .mcp.json, the candidate inventory and agent config. "
    "Trust zones, boundary crossings, data flows and components reached only through "
    "code (databases, HTTP APIs, queues) are not established. No code was executed."
)


def prop(name: str, value) -> dict:
    return {"name": f"brace:{name}", "value": str(value)}


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        sys.exit("--agent-config needs PyYAML: pip install pyyaml")
    return yaml.safe_load(path.read_text()) or {}


def redact_args(args: list) -> list[str]:
    """Keep the argument shape but drop values that follow secret-looking flags."""
    out, hide_next = [], False
    for a in map(str, args):
        if hide_next:
            out.append("<redacted>")
            hide_next = False
        elif "=" in a and SECRET_FLAG.search(a.split("=", 1)[0]):
            out.append(a.split("=", 1)[0] + "=<redacted>")
        else:
            out.append(a)
            hide_next = a.startswith("-") and bool(SECRET_FLAG.search(a))
    return out


SERVICE_KINDS = {"mcp_server", "mcp_tool", "tool", "external_api", "gateway"}
COMPONENT_TYPES = {"data_store": "data", "audit_sink": "data", "secret": "data", "model": "machine-learning-model",
                   "agent": "application", "agent_unit": "application", "human_approval": "application"}
KINDS = sorted(SERVICE_KINDS | set(COMPONENT_TYPES))


def check_quote(repo: Path, evidence: str, quote: str) -> str | None:
    """Return None if `quote` is on the cited line, else why not."""
    path, _, line = evidence.rpartition(":")
    if not path or not line.isdigit():
        return f"evidence must be path:line, got {evidence!r}"
    f = (repo / path).resolve()
    if repo.resolve() not in f.parents or not f.is_file():
        return f"{path} not found in repository"
    lines = f.read_text(errors="replace").splitlines()
    n = int(line)
    if not 1 <= n <= len(lines):
        return f"{evidence} is past end of file"
    if " ".join(quote.split()) not in " ".join(lines[n - 1].split()):
        return f"quote not found at {evidence}"
    return None


def line_of(path: Path, needle: str) -> int:
    for i, text in enumerate(path.read_text().splitlines(), 1):
        if needle in text:
            return i
    return 1


def quote_prop(entry: dict) -> dict:
    """The verified code quote behind an overlay entry, kept so reports can show it."""
    return prop("quote", json.dumps([entry["evidence"], entry["quote"]]))


# --------------------------------------------------------------------------- build
def tool_entries(cfg: dict) -> list[tuple[str, dict]]:
    """Tools from `tools.allowlist: [name]` or `tools: {name: {kind, server, qualified}}`."""
    tools = cfg.get("tools")
    if isinstance(tools, dict) and isinstance(tools.get("allowlist"), list):
        return [(str(t), {}) for t in tools["allowlist"]]
    if isinstance(tools, dict):
        return [(str(k), v if isinstance(v, dict) else {}) for k, v in tools.items() if k != "allowlist"]
    if isinstance(tools, list):
        return [(str(t), {}) if not isinstance(t, dict) else (str(t.get("name")), t) for t in tools]
    return []


def build(repo: Path, inventory: Path | None, agent_config: Path | None,
          overlay: Path | None = None, tools_config: Path | None = None) -> dict:
    cfg = load_yaml(agent_config) if agent_config else {}
    agent_cfg = cfg.get("agent") or {}
    cfg_rel = agent_config.relative_to(repo).as_posix() if agent_config else None
    agent_name = agent_cfg.get("name") or repo.resolve().name

    agent = {"type": "application", "bom-ref": "agent", "name": agent_name,
             "properties": [prop("kind", "agent"), prop("source", "agent_config" if agent_cfg else "repository")]}
    if agent_cfg.get("operational_owner"):
        agent["properties"].append(prop("owner", agent_cfg["operational_owner"]))
    components: list[dict] = []
    services: list[dict] = []
    deps: dict[str, list[str]] = {"agent": []}

    def depend(src: str, dst: str) -> None:
        deps.setdefault(src, [])
        if dst not in deps[src]:
            deps[src].append(dst)

    model_ref = None
    model = agent_cfg.get("model") or cfg.get("model")
    if isinstance(model, dict):  # e.g. model: {provider: x, id: y}
        model = model.get("id") or model.get("name") or model.get("model")
    if isinstance(model, str) and model:
        model_ref = f"model:{model}"
        components.append({"type": "machine-learning-model", "bom-ref": model_ref, "name": model,
                           "properties": [prop("kind", "model"), prop("source", "agent_config"),
                                          prop("evidence", f"{cfg_rel}:{line_of(agent_config, 'model:')}")]})

    # Inventory: files with model calls become agent units; other sites attach as evidence.
    sites = json.loads(inventory.read_text()).get("sites", []) if inventory and inventory.exists() else []
    by_file: dict[str, list[dict]] = {}
    for s in sites:
        by_file.setdefault(s["evidence"].split(":")[0], []).append(s)
    owner_of: dict[str, str] = {}
    for f, fs in sorted(by_file.items()):
        calls = [s for s in fs if s["kind"] == "model_call"]
        if not calls:
            owner_of[f] = "agent"
            continue
        ref = f"unit:{f}"
        owner_of[f] = ref
        components.append({"type": "application", "bom-ref": ref, "name": f,
                           "properties": [prop("kind", "agent_unit"), prop("source", "inventory")]
                           + [prop("evidence", s["evidence"]) for s in calls]})
        depend("agent", ref)
        if model_ref:
            depend(ref, model_ref)
    for f, fs in sorted(by_file.items()):
        node = agent if owner_of[f] == "agent" else next(c for c in components if c["bom-ref"] == owner_of[f])
        for s in fs:
            if s["kind"] in ("handoff", "tool_registration"):
                node["properties"].append(prop(s["kind"], s["evidence"]))
    audit_files = sorted({f for f, fs in by_file.items() if any(s["kind"] == "audit_write" for s in fs)})
    if audit_files:
        components.append({"type": "data", "bom-ref": "data:audit-log", "name": "audit log",
                           "properties": [prop("kind", "audit_sink"), prop("source", "inventory")]})
        for f in audit_files:
            first = next(s for s in by_file[f] if s["kind"] == "audit_write")
            depend(owner_of[f], "data:audit-log")
            components[-1]["properties"].append(prop("evidence", first["evidence"]))

    # MCP servers from .mcp.json.
    mcp_path = repo / ".mcp.json"
    servers = json.loads(mcp_path.read_text()).get("mcpServers", {}) if mcp_path.exists() else {}
    by_server: dict[str, dict] = {}
    for name, entry in sorted(servers.items()):
        transport = entry.get("type") or ("stdio" if "command" in entry else "unknown")
        svc = {"bom-ref": f"mcp:{name}", "name": name,
               "properties": [prop("kind", "mcp_server"), prop("transport", transport), prop("source", "mcp_config"),
                              prop("trust_zone", "unknown"),
                              prop("evidence", f".mcp.json:{line_of(mcp_path, json.dumps(name) + ':')}")]}
        if entry.get("url"):
            svc["endpoints"] = [entry["url"]]
        headers = entry.get("headers") or {}
        if any(k.lower() in ("authorization", "x-api-key") for k in headers):
            svc["authenticated"] = True  # a credential is configured; its scope is not established
        if entry.get("command"):
            svc["properties"].append(prop("command", entry["command"]))
            if entry.get("args"):
                svc["properties"].append(prop("args", " ".join(redact_args(entry["args"]))))
        for key in sorted((entry.get("env") or {}) | headers):
            svc["properties"].append(prop("credential_key" if SECRET_FLAG.search(key) or key.lower() == "authorization"
                                          or "KEY" in key.upper() else "config_key", key))
        services.append(svc)
        by_server[name] = svc
        depend("agent", svc["bom-ref"])

    # Tools from the agent config allowlist: `server__tool` nests under that MCP server.
    entries = [(t, meta, agent_config) for t, meta in tool_entries(cfg)]
    if tools_config:
        entries += [(t, meta, tools_config) for t, meta in tool_entries(load_yaml(tools_config))]
    seen_tools = set()
    for tool, meta, src in entries:
        if tool in seen_tools or tool == "None":
            continue
        seen_tools.add(tool)
        server, _, short = tool.partition("__")
        if not short and meta.get("server") in by_server:
            server, short = meta["server"], str(meta.get("qualified", tool)).split("/")[-1]
        rel = src.relative_to(repo).as_posix()
        text = src.read_text()
        needle = f"- {tool}" if f"- {tool}" in text else f"{tool}:"
        ev = prop("evidence", f"{rel}:{line_of(src, needle)}")
        if short and server in by_server:
            by_server[server].setdefault("services", []).append(
                {"bom-ref": f"mcp:{server}/{short}", "name": short,
                 "properties": [prop("kind", "mcp_tool"), prop("source", "agent_config"), ev]})
        else:
            extra = [prop("via_server", meta["server"])] if meta.get("server") else []
            services.append({"bom-ref": f"tool:{tool}", "name": tool,
                             "properties": [prop("kind", "tool"), prop("source", "agent_config"), ev, *extra]})
            depend("agent", f"tool:{tool}")

    # Declared connections: `connections: [{from, to, kind, name, label}]` in the agent config
    # names the services and stores the agent is meant to reach (the intended egress).
    declared = {c["bom-ref"]: c for c in [agent, *components, *services]}
    for sv in services:
        declared.update({t["bom-ref"]: t for t in sv.get("services", [])})
    conns = cfg.get("connections") if isinstance(cfg.get("connections"), list) else []
    text = agent_config.read_text() if agent_config and conns else ""
    for c in conns:
        if not isinstance(c, dict) or not c.get("to") or c.get("from", "agent") not in declared:
            continue
        src, dst = c.get("from", "agent"), str(c["to"])
        ev = f"{cfg_rel}:{line_of(agent_config, f'to: {dst}') if f'to: {dst}' in text else 1}"
        if dst not in declared:
            kind = c.get("kind") if c.get("kind") in KINDS else "external_api"
            node = {"bom-ref": dst, "name": c.get("name") or dst.split(":", 1)[-1],
                    "properties": [prop("kind", kind), prop("source", "agent_config"), prop("evidence", ev)]}
            if kind in SERVICE_KINDS:
                node["properties"].append(prop("trust_zone", "unknown"))
                services.append(node)
            else:
                components.append({"type": COMPONENT_TYPES.get(kind, "application"), **node})
            declared[dst] = node
        declared[src]["properties"].append(prop("declared_edge", f"{dst}|{c.get('label', '')}|{ev}"))
        depend(src, dst)

    # Reviewer overlay: code-traced nodes, edges and trust zones, each re-verified now.
    stale: list[str] = []
    if overlay and overlay.exists():
        ov = json.loads(overlay.read_text())
        existing = {c["bom-ref"]: c for c in [agent, *components, *services]}
        for sv in services:
            existing.update({t["bom-ref"]: t for t in sv.get("services", [])})
        for n in ov.get("nodes", []):
            err = check_quote(repo, n["evidence"], n["quote"])
            if err:
                stale.append(f"node {n['ref']}: {err}")
                continue
            if n["ref"] in existing:  # already declared: keep one node, add the traced evidence
                existing[n["ref"]]["properties"] += [prop("traced_evidence", n["evidence"]), quote_prop(n)]
                continue
            node = {"bom-ref": n["ref"], "name": n.get("name") or n["ref"].split(":", 1)[-1],
                    "properties": [prop("kind", n["kind"]), prop("source", "traced"), prop("evidence", n["evidence"]),
                                   quote_prop(n)]}
            if n["kind"] in SERVICE_KINDS:
                node["properties"].append(prop("trust_zone", "unknown"))
                services.append(node)
            else:
                components.append({"type": COMPONENT_TYPES.get(n["kind"], "application"), **node})
        index = {c["bom-ref"]: c for c in [agent, *components, *services]}
        for s in services:
            for t in s.get("services", []):
                index[t["bom-ref"]] = t
        for z in ov.get("zones", []):
            err = check_quote(repo, z["evidence"], z["quote"])
            if err or z["ref"] not in index or z["ref"] not in {s["bom-ref"] for s in services}:
                stale.append(f"zone {z['ref']}: {err or 'not a service in this topology'}")
                continue
            svc = index[z["ref"]]
            svc["trustZone"] = z["zone"]
            svc["properties"] = [p for p in svc["properties"] if p["name"] != "brace:trust_zone"]
            svc["properties"] += [prop("zone_evidence", z["evidence"]), quote_prop(z)]
        for e in ov.get("edges", []):
            err = check_quote(repo, e["evidence"], e["quote"])
            if err or e["from"] not in index or e["to"] not in index:
                stale.append(f"edge {e['from']} -> {e['to']}: {err or 'unknown bom-ref'}")
                continue
            depend(e["from"], e["to"])
            index[e["from"]]["properties"].append(
                prop("edge", f"{e['to']}|{e.get('label', '')}|traced|{e['evidence']}|{','.join(e.get('risks', []))}"))
            index[e["from"]]["properties"].append(quote_prop(e))

    all_refs = [c["bom-ref"] for c in components] + [s["bom-ref"] for s in services]
    for s in services:
        all_refs += [n["bom-ref"] for n in s.get("services", [])]
    seed = json.dumps([agent_name, all_refs, deps], sort_keys=True)
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid5(NS, seed)}",
        "version": 1,
        "metadata": {
            "tools": {"components": [{"type": "application", "name": "brace topology.py", "version": "prototype"}]},
            "component": agent,
            "properties": [prop("limitations", LIMITATIONS)] + [prop("stale_overlay", x) for x in stale],
        },
        "components": components,
        "services": services,
        "dependencies": [{"ref": r, "dependsOn": d} for r, d in deps.items()]
        + [{"ref": r} for r in all_refs if r not in deps],
        "compositions": [{"aggregate": "incomplete", "assemblies": ["agent", *all_refs]}],
    }
    return bom


# ------------------------------------------------------------------------ validate
def validate(bom: dict) -> list[str]:
    errors: list[str] = []
    try:
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource
    except ImportError:
        return ["schema validation needs jsonschema: pip install jsonschema"]
    registry = Registry()
    for f in CDX_DIR.glob("*.schema.json"):
        res = Resource.from_contents(json.loads(f.read_text()))
        registry = registry.with_resource(f.name, res).with_resource(res.id() or f.name, res)
    schema = json.loads((CDX_DIR / "bom-1.7.schema.json").read_text())
    for e in sorted(Draft7Validator(schema, registry=registry).iter_errors(bom), key=lambda e: list(e.path)):
        errors.append(f"schema: /{'/'.join(map(str, e.path))}: {e.message[:200]}")

    # BRACE checks the schema cannot express.
    refs: list[str] = [bom.get("metadata", {}).get("component", {}).get("bom-ref", "")]
    refs += [c["bom-ref"] for c in bom.get("components", [])]

    def walk(svcs):
        for s in svcs:
            refs.append(s.get("bom-ref", ""))
            walk(s.get("services", []))
    walk(bom.get("services", []))
    seen = set()
    for r in refs:
        if not r:
            errors.append("brace: every node needs a bom-ref")
        elif r in seen:
            errors.append(f"brace: duplicate bom-ref {r}")
        seen.add(r)
    for d in bom.get("dependencies", []):
        for r in [d["ref"], *d.get("dependsOn", [])]:
            if r not in seen:
                errors.append(f"brace: dependency refers to unknown bom-ref {r}")
    return errors


# ------------------------------------------------------------------------- mermaid
SHAPES = {"agent": ('(["', '"])'), "agent_unit": ('(["', '"])'), "model": ('{{"', '"}}'),
          "audit_sink": ('[("', '")]'), "data_store": ('[("', '")]'), "mcp_server": ('[/"', '"/]'),
          "external_api": ('[/"', '"/]'), "gateway": ('[/"', '"/]'), "tool": ('["', '"]'),
          "mcp_tool": ('["', '"]')}

# Plain-language names for what makes a connection security-relevant.
RISKS = {
    "writes": "can change, send or delete things",
    "money": "can move money",
    "personal_data": "carries personal data",
    "untrusted_input": "brings in text an outsider could write",
    "code_execution": "can run commands or code",
    "credential": "uses a secret key or token",
    "crosses_boundary": "crosses into another system or network",
    "unknown_zone": "we don't yet know which network it is in",
}
SHORT_RISKS = {
    "writes": "changes things", "money": "money", "personal_data": "personal data",
    "untrusted_input": "outside text", "code_execution": "runs code", "credential": "secret key",
    "crosses_boundary": "leaves network", "unknown_zone": "network unknown",
}
OUTSIDE_KINDS = {"mcp_server", "external_api", "gateway"}


def node_props(node: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in node.get("properties", []):
        out.setdefault(p["name"].removeprefix("brace:"), []).append(p["value"])
    return out


def all_nodes(bom: dict) -> dict[str, dict]:
    out = {}

    def add(n, parent=None):
        out[n["bom-ref"]] = {**n, "_parent": parent}
        for t in n.get("services", []):
            add(t, n["bom-ref"])
    add(bom["metadata"]["component"])
    for n in [*bom.get("components", []), *bom.get("services", [])]:
        add(n)
    return out


def zone_of(node: dict, nodes: dict) -> str:
    if node.get("trustZone"):
        return node["trustZone"]
    if node.get("_parent"):
        return zone_of(nodes[node["_parent"]], nodes)
    return node_props(node).get("trust_zone", ["agent"])[0] if node_props(node).get("kind") != ["agent"] else "agent"


def connections(bom: dict) -> list[dict]:
    """Every edge, with the reasons it matters for security (stated or derived)."""
    nodes = all_nodes(bom)
    meta = {}
    for ref, n in nodes.items():
        for v in node_props(n).get("edge", []):
            parts = v.split("|")
            to, label, source, evidence = parts[:4]
            risks = [r for r in (parts[4].split(",") if len(parts) > 4 else []) if r]
            meta[(ref, to)] = {"label": label, "source": source, "evidence": evidence, "risks": risks}
    out = []
    for d in bom.get("dependencies", []):
        for to in d.get("dependsOn", []):
            m = meta.get((d["ref"], to), {"label": "", "source": "declared", "evidence": "", "risks": []})
            src, dst = nodes[d["ref"]], nodes[to]
            risks = list(m["risks"])
            dp = node_props(dst)
            if "credential_key" in dp or dst.get("authenticated"):
                risks.append("credential")
            if dp.get("kind", [""])[0] in OUTSIDE_KINDS:
                zs, zd = zone_of(src, nodes), zone_of(dst, nodes)
                if zd == "unknown":
                    risks.append("unknown_zone")
                elif zs != zd:
                    risks.append("crosses_boundary")
            if not m["evidence"]:
                m = {**m, "evidence": dp.get("evidence", [""])[0]}
            out.append({"from": d["ref"], "to": to, **m, "risks": list(dict.fromkeys(risks))})
    return out


def focus_refs(bom: dict, status: dict[str, str]) -> set[str]:
    """Parts worth showing in a focused map: anything with an action, both ends of every
    risky connection, the agent itself, and the servers that contain shown tools."""
    nodes = all_nodes(bom)
    keep = {bom["metadata"]["component"]["bom-ref"], *status}
    for c in connections(bom):
        if set(c["risks"]) - {"unknown_zone"}:
            keep |= {c["from"], c["to"]}
    for ref in list(keep):
        if ref in nodes and nodes[ref].get("_parent"):
            keep.add(nodes[ref]["_parent"])
    return keep & set(nodes)


def mermaid(bom: dict, status: dict[str, str] | None = None, counts: dict[str, int | str] | None = None,
            focus: set[str] | None = None) -> str:
    """Render the topology. `status` maps bom-ref -> gap|needs_evidence|ok to colour nodes;
    `counts` adds "N to fix" (int) or action IDs (str) to node labels; `focus` limits the map to those bom-refs.
    Risky connections are drawn thick and red."""
    status, counts = status or {}, counts or {}
    if focus is not None:
        keep = focus

        def trim(n):
            return {**n, "services": [t for t in n.get("services", []) if t["bom-ref"] in keep]}
        bom = {**bom,
               "components": [c for c in bom.get("components", []) if c["bom-ref"] in keep],
               "services": [trim(x) for x in bom.get("services", []) if x["bom-ref"] in keep],
               "dependencies": [{"ref": d["ref"], "dependsOn": [t for t in d.get("dependsOn", []) if t in keep]}
                                for d in bom.get("dependencies", []) if d["ref"] in keep]}
    ids: dict[str, str] = {}

    def nid(ref: str) -> str:
        return ids.setdefault(ref, f"n{len(ids)}")

    def node_line(node: dict, indent: str = "  ") -> str:
        p = node_props(node)
        kind = p.get("kind", ["tool"])[0]
        extra = [kind.replace("_", " ")]
        if "transport" in p:
            extra.append(p["transport"][0])
        if node.get("authenticated"):
            extra.append("login required")
        tag = counts.get(node["bom-ref"])
        if isinstance(tag, str) and tag.count(" · ") >= 4:  # keep boxes readable
            codes = tag.split(" · ")
            tag = " · ".join(codes[:4]) + f" +{len(codes) - 4} more"
        if tag:
            extra.append(f"<b>{tag if isinstance(tag, str) else f'{tag} to fix'}</b>")
        a, b = SHAPES.get(kind, ('["', '"]'))
        name = str(node["name"]).replace('"', "'")
        return f'{indent}{nid(node["bom-ref"])}{a}{name}<br/><small>{" · ".join(extra)}</small>{b}'

    lines = ["flowchart LR"]
    agent = bom["metadata"]["component"]
    lines.append(node_line(agent))
    for c in bom.get("components", []):
        lines.append(node_line(c))
    links = 0
    risky_links: list[int] = []
    local_tools = [s for s in bom.get("services", []) if node_props(s).get("kind") == ["tool"]]
    # Tools with their own findings or outgoing connections are drawn individually.
    conns = connections(bom)
    busy = {c["from"] for c in conns} | set(status)
    quiet = [s for s in local_tools if s["bom-ref"] not in busy]
    if quiet:
        lines.append(f'  subgraph local_tools["Other local tools ({len(quiet)})"]')
        lines += [node_line(s, "    ") for s in quiet]
        lines.append("  end")
    for s in local_tools:
        if s not in quiet:
            lines.append(node_line(s))
    for s in bom.get("services", []):
        if s in local_tools:
            continue
        zone = s.get("trustZone") or node_props(s).get("trust_zone", ["unknown"])[0]
        lines.append(f'  subgraph z_{nid(s["bom-ref"])}["network: {zone}"]')
        lines.append(node_line(s, "    "))
        for t in s.get("services", []):
            lines.append(node_line(t, "    "))
            lines.append(f'    {nid(s["bom-ref"])} --- {nid(t["bom-ref"])}')
            links += 1
        lines.append("  end")
    quiet_refs = {s["bom-ref"] for s in quiet}
    grouped = set()
    for c in conns:
        if c["to"] in quiet_refs:
            if c["from"] in grouped:
                continue
            grouped.add(c["from"])
            lines.append(f'  {nid(c["from"])} --> local_tools')
            links += 1
            continue
        label = c["label"] or ""
        words = [SHORT_RISKS.get(r, r) for r in c["risks"] if r not in label]
        if words:
            label = (label + " · " if label else "") + ", ".join(words)
        arrow = f' -->|"{label}"| ' if label else " --> "
        lines.append(f'  {nid(c["from"])}{arrow}{nid(c["to"])}')
        if set(c["risks"]) - {"unknown_zone"}:
            risky_links.append(links)
        links += 1
    lines.append("  classDef unknown stroke-dasharray: 5 5")
    lines.append("  classDef traced stroke-width: 3px")
    lines.append("  classDef gap fill:#fde2e1,stroke:#b42318,color:#000")
    lines.append("  classDef needs fill:#fff4d6,stroke:#b54708,color:#000")
    lines.append("  classDef ok fill:#e3f4e8,stroke:#067647,color:#000")
    nodes = [*bom.get("components", []), *bom.get("services", [])]
    unknown = [nid(s["bom-ref"]) for s in bom.get("services", []) if node_props(s).get("trust_zone") == ["unknown"]]
    if unknown:
        lines.append(f"  class {','.join(unknown)} unknown")
    traced = [nid(n["bom-ref"]) for n in nodes if node_props(n).get("source") == ["traced"]]
    if traced:
        lines.append(f"  class {','.join(traced)} traced")
    for st, cls in (("gap", "gap"), ("needs_evidence", "needs"), ("ok", "ok")):
        refs = [nid(r) for r, v in status.items() if v == st and r in ids]
        if refs:
            lines.append(f"  class {','.join(refs)} {cls}")
    if risky_links:
        lines.append(f"  linkStyle {','.join(map(str, risky_links))} stroke:#b42318,stroke-width:3px")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------- overlay
def overlay_add(repo: Path, overlay: Path, section: str, entry: dict) -> str | None:
    """Verify the entry's quote against the code, then add or replace it in the overlay."""
    err = check_quote(repo, entry["evidence"], entry["quote"])
    if err:
        return err
    data = json.loads(overlay.read_text()) if overlay.exists() else {}
    data.setdefault("nodes", []), data.setdefault("edges", []), data.setdefault("zones", [])
    key = ("from", "to") if section == "edges" else ("ref",)
    data[section] = [x for x in data[section] if tuple(x[k] for k in key) != tuple(entry[k] for k in key)]
    data[section].append(entry)
    overlay.write_text(json.dumps(data, indent=2) + "\n")
    return None


# -------------------------------------------------------------------------- record
def summary(bom: dict) -> tuple[dict, set]:
    def props(n):
        return {p["name"]: p["value"] for p in n.get("properties", [])}
    nodes = {}

    def add(n):
        p = props(n)
        nodes[n["bom-ref"]] = {"name": n.get("name"), "kind": p.get("brace:kind"),
                               "trustZone": n.get("trustZone", p.get("brace:trust_zone")),
                               "endpoints": n.get("endpoints"), "authenticated": n.get("authenticated")}
        for t in n.get("services", []):
            add(t)
    add(bom["metadata"]["component"])
    for n in [*bom.get("components", []), *bom.get("services", [])]:
        add(n)
    edges = {(d["ref"], t) for d in bom.get("dependencies", []) for t in d.get("dependsOn", [])}
    return nodes, edges


def compare(recorded: dict, fresh: dict) -> list[str]:
    (rn, re_), (fn, fe) = summary(recorded), summary(fresh)
    out = [f"+ node {r} ({fn[r]['kind']})" for r in sorted(fn.keys() - rn.keys())]
    out += [f"- node {r} ({rn[r]['kind']})" for r in sorted(rn.keys() - fn.keys())]
    for r in sorted(rn.keys() & fn.keys()):
        for k in rn[r]:
            if rn[r][k] != fn[r][k]:
                out.append(f"~ node {r}: {k} {rn[r][k]!r} -> {fn[r][k]!r}")
    out += [f"+ edge {a} -> {b}" for a, b in sorted(fe - re_)]
    out += [f"- edge {a} -> {b}" for a, b in sorted(re_ - fe)]
    return out


def stale_entries(bom: dict) -> list[str]:
    return [p["value"] for p in bom["metadata"].get("properties", []) if p["name"] == "brace:stale_overlay"]


# ---------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build a CycloneDX topology for a repository")
    b.add_argument("repo", type=Path)
    b.add_argument("-o", "--output", type=Path, required=True)
    b.add_argument("--inventory", type=Path, help="default: <repo>/brace-inventory.json")
    b.add_argument("--agent-config", type=Path, help="YAML with agent.* and tools.allowlist")
    b.add_argument("--tools-config", type=Path, help="YAML with a `tools:` list or map, if not in the agent config")
    b.add_argument("--overlay", type=Path, help="reviewer overlay; default: <repo>/brace-topology.overlay.json")
    v = sub.add_parser("validate", help="validate against CycloneDX 1.7 and BRACE ref rules")
    v.add_argument("bom", type=Path)
    m = sub.add_parser("mermaid", help="render a topology as a Mermaid flowchart")
    m.add_argument("bom", type=Path)
    m.add_argument("-o", "--output", type=Path)
    for name, hlp in (("add-node", "record a code-traced component"),
                      ("add-edge", "record a code-traced connection"),
                      ("set-zone", "record a service's trust zone")):
        o = sub.add_parser(name, help=hlp + " (quote must appear at path:line)")
        o.add_argument("repo", type=Path)
        o.add_argument("--overlay", type=Path, help="default: <repo>/brace-topology.overlay.json")
        o.add_argument("--evidence", required=True, help="path:line relative to repo")
        o.add_argument("--quote", required=True, help="exact code on that line")
        if name == "add-node":
            o.add_argument("--ref", required=True, help="bom-ref, e.g. data:invoices-db")
            o.add_argument("--kind", required=True, choices=KINDS)
            o.add_argument("--name")
        elif name == "add-edge":
            o.add_argument("--from", dest="src", required=True)
            o.add_argument("--to", required=True)
            o.add_argument("--label", default="", help="what the connection does, e.g. 'sends refunds'")
            o.add_argument("--risk", default="", help="comma list of: " + ", ".join(RISKS))
        else:
            o.add_argument("--ref", required=True)
            o.add_argument("--zone", required=True)
    w = sub.add_parser("report", help="write a self-contained web page: declared vs found-in-code map with findings")
    w.add_argument("bom", type=Path)
    w.add_argument("--findings", type=Path, help="brace-findings.json to show on the map")
    w.add_argument("-o", "--output", type=Path, required=True, help="the .html file to write")
    r = sub.add_parser("record", help="compare with the recorded topology; create/update only with --apply")
    r.add_argument("bom", type=Path, help="freshly built topology")
    r.add_argument("--record", type=Path, default=Path(".brace/topology.cdx.json"))
    r.add_argument("--apply", action="store_true", help="write the record; use only after the user confirms")
    a = ap.parse_args(argv)

    if a.cmd == "build":
        bom = build(a.repo, a.inventory or a.repo / "brace-inventory.json", a.agent_config,
                    a.overlay or a.repo / "brace-topology.overlay.json", a.tools_config)
        errors = validate(bom)
        a.output.write_text(json.dumps(bom, indent=2) + "\n")
        for e in errors:
            print(e, file=sys.stderr)
        for x in stale_entries(bom):
            print(f"stale overlay entry skipped: {x}", file=sys.stderr)
        print(f"wrote {a.output} ({'valid' if not errors else f'{len(errors)} errors'})")
        print("bom-refs: " + ", ".join(sorted(all_nodes(bom))))
        stale = stale_entries(bom)
        print(f"stale overlay entries: {len(stale)}" + ("" if stale else " (none)"))
        return 1 if errors else 0
    if a.cmd in ("add-node", "add-edge", "set-zone"):
        base = {"evidence": a.evidence, "quote": a.quote}
        if a.cmd == "add-node":
            section, entry = "nodes", {"ref": a.ref, "kind": a.kind, **({"name": a.name} if a.name else {}), **base}
        elif a.cmd == "add-edge":
            bad = [r for r in a.risk.split(",") if r and r not in RISKS]
            if bad:
                print(f"rejected: unknown risk {', '.join(bad)}; use {', '.join(RISKS)}")
                return 1
            section, entry = "edges", {"from": a.src, "to": a.to, "label": a.label,
                                       "risks": [r for r in a.risk.split(",") if r], **base}
        else:
            section, entry = "zones", {"ref": a.ref, "zone": a.zone, **base}
        err = overlay_add(a.repo, a.overlay or a.repo / "brace-topology.overlay.json", section, entry)
        print(f"rejected: {err}" if err else f"recorded {section[:-1]}")
        return 1 if err else 0
    bom = json.loads(a.bom.read_text())
    if a.cmd == "validate":
        errors = validate(bom)
        for e in errors:
            print(e)
        print("Valid" if not errors else f"{len(errors)} errors")
        return 1 if errors else 0
    if a.cmd == "report":
        import topology_report
        m = topology_report.write(a.bom, a.findings, a.output)
        s = m["summary"]
        print(f"wrote {a.output}: {s['parts']} parts, {s['connections']} connections, "
              f"{s['undeclared']} undeclared, {sum(s['findings'].values())} findings")
        return 0
    if a.cmd == "record":
        errors, stale = validate(bom), stale_entries(bom)
        exists = a.record.exists()
        diff = compare(json.loads(a.record.read_text()), bom) if exists else []
        if exists and not diff:
            print(f"{a.record} matches the current topology.")
            return 0
        if not a.apply:
            if exists:
                print(f"{a.record} differs from the current topology:")
                print("\n".join(f"  {d}" for d in diff))
                print("Proposed: update the record. Ask the user; re-run with --apply only if they confirm.")
            else:
                n, e = summary(bom)
                print(f"No topology record at {a.record}.")
                print(f"Proposed: create it ({len(n)} nodes, {len(e)} edges). "
                      "Ask the user; re-run with --apply only if they confirm.")
            for x in stale:
                print(f"  note: stale overlay entry not included: {x}")
            return 3
        if errors or stale:
            print("refusing to write: " + "; ".join(errors + [f"stale overlay entry: {x}" for x in stale]))
            return 1
        a.record.parent.mkdir(parents=True, exist_ok=True)
        a.record.write_text(json.dumps(bom, indent=2) + "\n")
        print(f"{'updated' if exists else 'created'} {a.record}")
        return 0
    text = mermaid(bom)
    if a.output:
        a.output.write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
