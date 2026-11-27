"""CycloneDX 1.7 JSON: an inventory of the agent config files and MCP servers a scan saw.

The same CycloneDX version as topology.py, which builds the richer component map (tools,
data stores, trust zones, flows); this is the flat inventory a scan can state on its own.

- Each agent config file (and each CI workflow that runs an agent) is a component of type
  `file`; each MCP server is a service; a package or image a server fetches at start is a
  `library` or `container` component the service depends on.
- Properties use the `brace:` namespace (as topology.py does): `brace:client`,
  `brace:config_file`, `brace:line`, `brace:transport`, `brace:command`, `brace:runner`,
  `brace:url_host`, `brace:env_key` / `brace:header_key` (names only), `brace:pinned`.
- Findings stay out of the BOM. CycloneDX `vulnerabilities` describe known vulnerabilities
  in a component, not a configuration finding about how it is launched, so each node that a
  finding points at (same file and line, or a detail that names the server) carries `brace:finding` = "<rule> <id>" instead; the
  JSON or SARIF report holds the finding itself.

Every value comes from inventory.py, which keeps no env or header values and redacts
arguments; JSON encoding escapes the rest. The serial number is derived from the content, so
two scans of the same folder give the same BOM apart from the timestamp.
"""
from __future__ import annotations

import json
import re
import uuid
from urllib.parse import quote

from .. import __version__
from ..model import Report
from ..output import safe_path
from .common import ReportOptions

SPEC_VERSION = "1.7"
NS = uuid.UUID("0b6f1e5c-3f0a-4c1e-9a43-6c2f8d9e7b21")  # open-agent-security inventory namespace
NPM_NAME = re.compile(r"^(@[\w.\-~]{1,214}/)?[\w.\-~]{1,214}$")
VERSION = re.compile(r"^[\w.\-+]{1,100}$")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
ECOSYSTEMS = {"npm", "pypi"}


def prop(name: str, value) -> dict:
    return {"name": f"brace:{name}", "value": str(value)}


def split_spec(eco: str, spec: str) -> tuple[str, str]:
    """(name, exact version or '') of a registry package spec, '' name when it is not one."""
    if eco == "pypi":
        name, sep, ver = spec.partition("==") if "==" in spec else spec.rpartition("@") if "@" in spec else (spec, "", "")
        name = name.split("[")[0]
    elif eco == "npm":
        body = spec[1:] if spec.startswith("@") else spec
        name, sep, ver = body.rpartition("@") if "@" in body else (body, "", "")
        name = ("@" if spec.startswith("@") else "") + name
    else:
        return "", ""
    if not NPM_NAME.match(name or ""):
        return "", ""
    return name, ver if sep and VERSION.match(ver) else ""


def purl(eco: str, name: str, version: str) -> str:
    if eco == "npm" and name.startswith("@"):
        scope, _, base = name.partition("/")
        path = f"{quote(scope)}/{quote(base)}"
    else:
        path = quote(name.lower() if eco == "pypi" else name)
    return f"pkg:{eco}/{path}" + (f"@{quote(version)}" if version else "")


def build(report: Report) -> dict:
    by_place: dict[tuple, list[str]] = {}
    by_file: dict[str, list] = {}
    for f in report.findings:
        by_place.setdefault((safe_path(f.file), None), []).append(f"{f.rule} {f.id}")
        by_file.setdefault(safe_path(f.file), []).append(f)

    def server_findings(file: str, line: int, name: str) -> list[str]:
        """Findings on the server's line, or whose detail names the server (an env key's line)."""
        return [f"{f.rule} {f.id}" for f in by_file.get(file, [])
                if f.line == line or (name and f.detail.startswith(name + ": "))]
    components, services, deps = [], [], []
    for n, item in enumerate(report.inventory, 1):
        file = safe_path(item["file"])
        if item["kind"] != "mcp_server":
            ref = f"config-{n}"
            props = [prop("kind", item["kind"]), prop("client", item["client"]), prop("config_file", file),
                     prop("origin", item["origin"]), prop("mcp_servers", item["servers"])]
            props += [prop("finding", x) for x in by_place.get((file, None), [])]
            components.append({"type": "file", "bom-ref": ref, "name": file, "properties": props})
            continue
        ref = f"mcp-{n}"
        props = [prop("kind", "mcp_server"), prop("client", item["client"]), prop("config_file", file),
                 prop("line", item["line"]), prop("json_key", item["key"]), prop("origin", item["origin"]),
                 prop("transport", item["transport"])]
        props += [prop(k, item[k]) for k in ("command", "runner", "url_host") if item[k]]
        if item["args"]:
            props.append(prop("args", " ".join(item["args"])))
        props += [prop("env_key", k) for k in item["env_keys"]] + [prop("header_key", k) for k in item["header_keys"]]
        props += [prop("finding", x) for x in server_findings(file, item["line"], item["name"])]
        service = {"bom-ref": ref, "name": item["name"] or "(unnamed)", "properties": props}
        if item["url_host"]:
            service["endpoints"] = [f"{item['url_scheme']}://{item['url_host']}"]
        services.append(service)
        uses = []
        for i, pkg in enumerate(item["packages"], 1):
            name, version = split_spec(pkg["ecosystem"], pkg["spec"]) if pkg["ecosystem"] in ECOSYSTEMS else ("", "")
            comp = {"type": "library", "bom-ref": f"{ref}-pkg-{i}", "name": name or pkg["spec"],
                    "properties": [prop("ecosystem", pkg["ecosystem"] or "unknown"), prop("spec", pkg["spec"]),
                                   prop("pinned", str(pkg["pinned"]).lower())]}
            if name and version:
                comp["version"] = version
            if name:
                comp["purl"] = purl(pkg["ecosystem"], name, version if pkg["pinned"] else "")
            components.append(comp)
            uses.append(comp["bom-ref"])
        if item["image"]:
            name, at, digest = item["image"].partition("@")
            comp = {"type": "container", "bom-ref": f"{ref}-image", "name": name,
                    "properties": [prop("image", item["image"]), prop("pinned", str(item["image_pinned"]).lower())]}
            if at and item["image_pinned"]:
                comp["hashes"] = [{"alg": "SHA-256", "content": digest.split(":", 1)[1]}] \
                    if SHA256.fullmatch(digest) else []
                if not comp["hashes"]:
                    del comp["hashes"]
            components.append(comp)
            uses.append(comp["bom-ref"])
        deps.append({"ref": ref, "dependsOn": uses} if uses else {"ref": ref})
    refs = [c["bom-ref"] for c in components if c["type"] == "file"]
    deps = [{"ref": "scanned-folder", "dependsOn": refs + [s["bom-ref"] for s in services]}] \
        + [{"ref": r} for r in refs] + deps
    deps += [{"ref": c["bom-ref"]} for c in components if c["type"] != "file"]
    seed = json.dumps([components, services], sort_keys=True)
    meta_props = [prop("scan_verdict", report.verdict), prop("findings", len(report.findings))]
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid5(NS, seed)}",
        "version": 1,
        "metadata": {
            "tools": {"components": [{"type": "application", "name": "open-agent-security", "version": __version__}]},
            # The BOM describes the scanned folder; its name stays out (it may be a private path).
            "component": {"type": "application", "bom-ref": "scanned-folder", "name": "scanned folder"},
            "properties": meta_props,
        },
        "components": components,
        "services": services,
        "dependencies": deps,
        # A scan lists what it read; it does not claim the list is complete.
        "compositions": [{"aggregate": "incomplete" if report.verdict != "clean" else "unknown"}],
    }
    if report.started:
        bom["metadata"]["timestamp"] = report.started.strftime("%Y-%m-%dT%H:%M:%SZ")
    return bom


class CycloneDx:
    name = "cyclonedx"
    media = "json"

    def render(self, report: Report, opts: ReportOptions) -> str:
        return json.dumps(build(report), indent=2) + "\n"
