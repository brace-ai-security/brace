"""Import MCP scanner output as host evidence for topology.py (`--import-scan FILE`).

Reads Snyk Agent Scan (`--json`, v0.5 path-keyed or v0.6 `scan_path_responses`) and Cisco
mcp-scanner (`--format raw`) JSON. It sits beside results_import.py, outside the
open-agent-security wheel: the scanner never ingests other tools' findings (that would blur
its rule IDs, suppression accounting and incomplete verdict); merging belongs here, in the
map. Files are named explicitly on the command line, read as untrusted input with the host
reader's limits, and every string is cut and redacted like a host record.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from open_agent_security.host_scan import MAX_SERVERS, cut, load_json, server_record  # noqa: E402

MAX_BYTES = 5 * 1024 * 1024


def import_scan(path: Path) -> tuple[list[dict], list[str]]:
    """Import Snyk Agent Scan (`--json`, v0.5 path-keyed or v0.6 `scan_path_responses`)
    or Cisco mcp-scanner (`--format raw`) output. Returns (records, notes); each record is
    a server with `issues` [{tool, code, severity, message}]."""
    data, err = load_json(path, MAX_BYTES)
    if err:
        return [], [err]
    notes: list[str] = []
    if isinstance(data, dict) and "scan_results" in data and "server_url" in data:
        return _cisco([data], path, notes), notes
    if isinstance(data, list) and data and all(isinstance(x, dict) and "scan_results" in x for x in data):
        return _cisco(data, path, notes), notes
    if isinstance(data, dict) and isinstance(data.get("scan_path_responses"), list):
        return _snyk_v06(data["scan_path_responses"], path, notes), notes
    if isinstance(data, dict) and data and all(isinstance(v, dict) and "servers" in v for v in data.values()):
        return _snyk_v05(data, path, notes), notes
    return [], [f"{path.name}: not a recognised Snyk Agent Scan or Cisco mcp-scanner JSON file"]


def _scanner_record(name, client, file, key, server: dict | None, scanner: str) -> dict:
    rec = server_record(name, server or {}, client, file, key)
    rec["scanner"] = scanner
    rec["issues"] = []
    return rec


def _list(x, what: str, path: Path, notes: list[str]) -> list:
    """`x` if it is a list (None counts as empty); otherwise a note and an empty list."""
    if x is None or isinstance(x, list):
        return x or []
    notes.append(f"{path.name}: {cut(what)} is not a list; skipped")
    return []


def _dict(x, what: str, path: Path, notes: list[str]) -> dict:
    if x is None or isinstance(x, dict):
        return x or {}
    notes.append(f"{path.name}: {cut(what)} is not an object; skipped")
    return {}


def _snyk_v05(data: dict, path: Path, notes: list[str]) -> list[dict]:
    out = []
    for scan_path, res in list(data.items())[:MAX_SERVERS]:
        servers = _list(res.get("servers"), f"{scan_path} servers", path, notes)
        recs = []
        for i, s in enumerate(servers[:MAX_SERVERS]):
            if not isinstance(s, dict):
                continue
            rec = _scanner_record(s.get("name") or f"server-{i}", cut(res.get("client") or "unknown client"),
                                  str(path), f"{cut(scan_path)}#servers[{i}]", s.get("server"), "Snyk Agent Scan")
            tools = _list(s["signature"].get("tools"), "signature.tools", path, notes) \
                if isinstance(s.get("signature"), dict) else []
            rec["tools"] = [cut(t.get("name")) for t in tools[:200] if isinstance(t, dict)]
            recs.append(rec)
            out.append(rec)
        for issue in _list(res.get("issues"), f"{scan_path} issues", path, notes)[:2000]:
            if not isinstance(issue, dict):
                continue
            ref = issue.get("reference") or [None, None]
            si = ref[0] if isinstance(ref, list) and ref and isinstance(ref[0], int) else None
            if si is None or not 0 <= si < len(recs):
                continue
            ti = ref[1] if len(ref) > 1 and isinstance(ref[1], int) else None
            tools = recs[si].get("tools", [])
            recs[si]["issues"].append({"tool": tools[ti] if ti is not None and 0 <= ti < len(tools) else "",
                                       "code": cut(issue.get("code")), "severity": "",
                                       "message": cut(issue.get("message"))})
    return out


def _snyk_v06(responses: list, path: Path, notes: list[str]) -> list[dict]:
    out = []
    for resp in responses[:MAX_SERVERS]:
        if not isinstance(resp, dict):
            continue
        for i, s in enumerate(_list(resp.get("server_risks"), "server_risks", path, notes)[:MAX_SERVERS]):
            if not isinstance(s, dict):
                continue
            rec = _scanner_record(s.get("name") or f"server-{i}", cut(resp.get("client") or "unknown client"),
                                  str(path), f"{cut(resp.get('path'))}#server_risks[{i}]", None, "Snyk Agent Scan")
            ents = [e for e in _list(s.get("entities"), "entities", path, notes) if isinstance(e, dict)]
            rec["tools"] = [cut(e.get("name")) for e in ents if e.get("type") == "tool"][:200]
            for risk, v in list(_dict(s.get("risk_indexes"), "risk_indexes", path, notes).items())[:200]:
                v = v if isinstance(v, dict) else {}
                hit = [ents[k].get("name") for k in _list(v.get("affected_tools"), "affected_tools", path, notes)
                       if isinstance(k, int) and 0 <= k < len(ents)]
                rec["issues"].append({"tool": cut(", ".join(map(str, hit))), "code": cut(risk),
                                      "severity": f"score {cut(v.get('score'))}", "message": cut(v.get("evidence"))})
            out.append(rec)
    return out


def _cisco(results: list, path: Path, notes: list[str]) -> list[dict]:
    out = []
    for k, r in enumerate(results[:MAX_SERVERS]):
        url = r.get("server_url") or ""
        items = [x for x in _list(r.get("scan_results"), "scan_results", path, notes) if isinstance(x, dict)][:2000]
        name = next((x.get("server_name") for x in items if x.get("server_name")), None) or urlsplit(str(url)).hostname \
            or str(url) or f"server-{k}"
        server = {"url": url} if str(url).startswith(("http://", "https://")) else {"command": url}
        rec = _scanner_record(name, "Cisco mcp-scanner target", str(path), f"[{k}].server_url", server,
                              "Cisco mcp-scanner")
        rec["tools"] = [cut(x.get("tool_name")) for x in items if x.get("tool_name")][:200]
        for x in items:
            for analyzer, f in _dict(x.get("findings"), "findings", path, notes).items():
                if not isinstance(f, dict) or not f.get("total_findings"):
                    continue
                rec["issues"].append({"tool": cut(x.get("tool_name") or x.get("prompt_name") or x.get("resource_name")),
                                      "code": cut(", ".join(map(str, f.get("threat_names") or [])) or analyzer),
                                      "severity": cut(f.get("severity")),
                                      "message": cut(f.get("threat_summary"))})
        out.append(rec)
    return out
