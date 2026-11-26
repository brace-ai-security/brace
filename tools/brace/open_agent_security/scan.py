"""`open-agent-security`: a fast, local check for known-dangerous agent setups.

Reads the files in a repository (and, with --host, the MCP settings on this machine) and
reports anti-patterns from ANTI-PATTERNS.md in plain language. It starts no server, runs
no model and contacts no network. File contents are untrusted data: they are matched
against fixed patterns, never executed, and every reported snippet is cut and stripped
of control characters. Secret values are never printed.

A clean scan means none of these patterns was found. It is not a security review and
not BRACE compliance; use the checklist for that.
"""
from __future__ import annotations

import json
import os
import platform
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import host_scan

MAX_FILE_BYTES = 1024 * 1024
MAX_FILES = 20000
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".tox",
             ".mypy_cache", ".pytest_cache", "vendor", "target", ".next", "site-packages"}
TEXT_EXT = {".json", ".jsonc", ".yaml", ".yml", ".toml", ".py", ".ts", ".tsx", ".js", ".mjs", ".cjs",
            ".sh", ".bash", ".zsh", ".md", ".env", ".ini", ".cfg", ".go", ".rs", ".rb", ".java", ".kt"}
TEXT_NAMES = {"Dockerfile", "Containerfile", "Makefile", "justfile", ".mcp.json"}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
DOCS = "https://braceframework.org/anti-patterns/"


def anchor(rule: str) -> str:
    """Heading anchor of the rule in ANTI-PATTERNS.md ('### AP01: Title')."""
    text = f"{rule}: {RULES[rule][1]}".lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")

# id -> (severity, title, why it is dangerous, what to do, checklist items)
RULES: dict[str, tuple[str, str, str, str, list[str]]] = {
    "AP01": ("high", "Agent runs with all permission checks turned off",
             "Every tool call, including shell commands and file deletes, runs without approval. One prompt "
             "injection in a file, issue or web page the agent reads can run any command as you.",
             "Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway "
             "sandbox with no secrets and no network beyond what the task needs.",
             ["B05", "B01", "B08"]),
    "AP02": ("critical", "Unattended agent in CI with permission checks turned off",
             "A CI agent with no approvals and the job's token can be steered by anyone who can write an issue, "
             "PR, commit message or file it reads, and then push code, read secrets or publish packages.",
             "Keep approvals on, give the job read-only permissions, and run untrusted-input jobs without "
             "repository secrets.",
             ["B05", "B02", "B03", "B09"]),
    "AP03": ("critical", "Agent workflow triggered by pull_request_target",
             "pull_request_target runs with the base repository's secrets and write token on events from "
             "forks. An agent that reads the fork's PR text or code can be told to leak or misuse them.",
             "Use pull_request for agent jobs, or split the job so the agent never sees secrets or a "
             "write token while it reads outside content.",
             ["B02", "B05", "R02"]),
    "AP04": ("high", "MCP server installed from an unpinned package",
             "npx/uvx/bunx fetch the newest version at every start. A hijacked or malicious update "
             "becomes code running with your agent's access, with no review.",
             "Pin an exact version (for example pkg@1.4.2), or install it once from a reviewed lockfile.",
             ["E02", "E03", "C05"]),
    "AP05": ("high", "Secret written directly in agent configuration",
             "Config files get committed, copied and read by the agent itself. A literal token is "
             "long-lived, shared and easy to leak through the agent's output.",
             "Load the secret from the environment or a secret manager, use a short-lived scoped "
             "token, and rotate the exposed one.",
             ["B03", "R03"]),
    "AP06": ("high", "Agent allowed to run any shell command",
             "An allow-rule like Bash(*) or a bare Bash lets the agent run any command without asking. "
             "That includes curl to send your files out, rm -rf and git push --force.",
             "Allow only the specific commands the task needs, such as Bash(npm test), and keep deny "
             "rules for network and destructive commands.",
             ["B01", "B05"]),
    "AP07": ("medium", "Remote MCP server reached over plain HTTP",
             "Tool calls, results and credentials cross the network unencrypted and can be read or "
             "changed in transit, including the tool descriptions the model trusts.",
             "Use https, and authenticate the server.",
             ["E05", "E06"]),
    "AP08": ("high", "Agent tool container can take over the host",
             "--privileged, a mounted Docker socket, host networking or a mounted root filesystem "
             "remove the container boundary. A compromised tool then controls the machine.",
             "Drop these flags. Mount only the folders the tool needs, read-only where possible.",
             ["B08", "B11", "B09"]),
    "AP09": ("high", "Lethal combination: untrusted input, private data and a way out",
             "The same agent can read content an attacker controls, reach private data and send data "
             "or act outside. Prompt injection then becomes data theft; no system prompt reliably stops it.",
             "Split the capabilities across agents, remove one leg, or require a person to approve "
             "every outbound or consequential action.",
             ["B05", "B01", "R02"]),
    "AP10": ("low", "Agent image not pinned to a digest",
             "A mutable tag such as :latest can change under you, so what you tested is not what runs.",
             "Pin the base image by digest (image@sha256:...) and update it on purpose.",
             ["B10", "C01"]),
}

SKIP_PERMS = re.compile(r"--dangerously-skip-permissions|--dangerously-bypass-approvals-and-sandbox|"
                        r"--yolo\b|[\"']?(permission_?mode|permissionMode|defaultMode)[\"']?\s*[:=]\s*[\"']bypassPermissions|"
                        r"sandbox_mode\s*=\s*[\"']danger-full-access|approval_policy\s*=\s*[\"']never", re.I)
AGENT_ACTION = re.compile(r"anthropics/claude-code(-base)?-action|openai/codex-action|google-github-actions/run-gemini-cli|"
                          r"\b(claude|codex|gemini|aider|opencode)\b\s+(-p|--print|exec|run)\b", re.I)
DOCKER_ESCAPE = re.compile(r"--privileged|/var/run/docker\.sock|--network[= ]host|--net[= ]host|--pid[= ]host|-v\s+/:/")
FROM_LINE = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)", re.I | re.M)
LITERAL_SECRET = re.compile(r"^(sk-(ant-)?[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
                            r"xox[abp]-[A-Za-z0-9\-]{10,}|AKIA[0-9A-Z]{16}|glpat-[A-Za-z0-9_\-]{16,}|AIza[0-9A-Za-z_\-]{30,})")
BEARER = re.compile(r"^Bearer\s+[A-Za-z0-9._\-]{20,}$")

# Heuristic capability classes for the lethal-combination check (AP09), matched on the
# server name, package and URL. Shown as "likely", never as proven.
UNTRUSTED = re.compile(r"fetch|browser|puppeteer|playwright|web|search|brave|tavily|exa|firecrawl|scrap|crawl|"
                       r"gmail|email|mail|slack|discord|github|gitlab|jira|linear|notion|rss|youtube|reddit|twitter", re.I)
PRIVATE = re.compile(r"filesystem|\bfs\b|postgres|mysql|sqlite|mongo|redis|database|\bdb\b|supabase|drive|gdrive|"
                     r"gmail|email|mail|notion|github|gitlab|jira|linear|slack|secret|vault|1password|bitwarden|aws|gcp|azure|stripe", re.I)
SENDS = re.compile(r"fetch|browser|puppeteer|playwright|http|slack|discord|gmail|email|mail|github|gitlab|jira|linear|"
                   r"notion|twitter|webhook|stripe|aws|shell|exec|terminal|desktop-commander", re.I)


@dataclass
class Finding:
    rule: str
    file: str
    line: int
    detail: str
    severity: str = ""
    title: str = ""
    why: str = ""
    fix: str = ""
    items: list[str] = field(default_factory=list)

    def __post_init__(self):
        sev, title, why, fix, items = RULES[self.rule]
        self.severity, self.title, self.why, self.fix, self.items = sev, title, why, fix, list(items)
        self.detail = clean(self.detail)


def clean(s: str, n: int = 160) -> str:
    s = "".join(ch for ch in str(s) if ch.isprintable())
    return s if len(s) <= n else s[: n - 1] + "…"


def iter_files(root: Path):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not (d.startswith(".") and d not in
                                                                             {".github", ".claude", ".cursor", ".vscode", ".codex", ".devin", ".gemini"})]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in TEXT_EXT or name in TEXT_NAMES or name.startswith("Dockerfile"):
                if p.is_symlink():
                    continue
                count += 1
                if count > MAX_FILES:
                    return
                yield p


def read(p: Path) -> str | None:
    try:
        if p.stat().st_size > MAX_FILE_BYTES:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def line_no(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def is_doc(rel: str) -> bool:
    return rel.lower().endswith(".md")


def scan_text(rel: str, text: str) -> list[Finding]:
    out: list[Finding] = []
    workflow = rel.replace("\\", "/").startswith(".github/workflows/") and rel.endswith((".yml", ".yaml"))
    if not is_doc(rel):
        for m in SKIP_PERMS.finditer(text):
            if workflow or re.search(r"\b(ci|pipeline|jenkins|gitlab-ci|buildkite)\b", rel, re.I):
                out.append(Finding("AP02", rel, line_no(text, m.start()), m.group(0)))
            else:
                out.append(Finding("AP01", rel, line_no(text, m.start()), m.group(0)))
    if workflow and re.search(r"^\s*pull_request_target\s*:|on:\s*\[?[^\n]*pull_request_target", text, re.M) \
            and AGENT_ACTION.search(text):
        m = re.search(r"pull_request_target", text)
        out.append(Finding("AP03", rel, line_no(text, m.start()), "pull_request_target + agent step"))
    name = Path(rel).name
    if name.startswith(("Dockerfile", "Containerfile")):
        stages = {a.lower() for a in re.findall(r"^\s*FROM\s+.*?\s+AS\s+(\S+)", text, re.I | re.M)}
        for m in FROM_LINE.finditer(text):
            img = m.group(1)
            if img.lower() in stages:
                continue
            if "@sha256:" not in img and img.lower() != "scratch" and not img.startswith("$"):
                out.append(Finding("AP10", rel, line_no(text, m.start()), f"FROM {img}"))
    if Path(rel).suffix.lower() in (".json", ".jsonc") or name == ".mcp.json":
        out += scan_json(rel, text)
    return out


def _servers(data) -> list[tuple[str, dict, str]]:
    found = []
    if isinstance(data, dict):
        for key in ("mcpServers", "servers", "mcp_servers"):
            val = data.get(key)
            if isinstance(val, dict):
                found += [(n, e, key) for n, e in val.items() if isinstance(e, dict)]
        projects = data.get("projects")
        if isinstance(projects, dict):
            for p in projects.values():
                if isinstance(p, dict) and isinstance(p.get("mcpServers"), dict):
                    found += [(n, e, "projects.mcpServers") for n, e in p["mcpServers"].items() if isinstance(e, dict)]
    return found


def scan_json(rel: str, text: str) -> list[Finding]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    out: list[Finding] = []

    def at(needle: str) -> int:
        i = text.find(needle)
        return line_no(text, i) if i >= 0 else 1

    servers = _servers(data)
    for name, entry, _ in servers:
        out += server_findings(rel, name, entry, at)
    if len(servers) > 1:
        out += combo_findings(rel, [(n, e) for n, e, _ in servers], at)
    perms = data.get("permissions") if isinstance(data, dict) else None
    if isinstance(perms, dict):
        for rule in perms.get("allow") or []:
            if isinstance(rule, str) and rule.strip() in ("Bash", "Bash(*)", "Bash(:*)", "*", "Bash(**)"):
                out.append(Finding("AP06", rel, at(f'"{rule}"'), f'allow "{rule}"'))
        if perms.get("defaultMode") == "bypassPermissions" and not SKIP_PERMS.search(text):
            out.append(Finding("AP01", rel, at("defaultMode"), "defaultMode bypassPermissions"))
    return out


def server_findings(rel: str, name: str, entry: dict, at) -> list[Finding]:
    out: list[Finding] = []
    cmd = Path(str(entry.get("command") or "")).name
    args = [str(a) for a in entry.get("args") or [] if isinstance(a, (str, int, float))]
    if cmd in ("npx", "uvx", "bunx", "pnpx") or (cmd in ("pnpm", "yarn") and args[:1] == ["dlx"]):
        pkg = next((a for a in args if not a.startswith("-") and a not in ("dlx", "--from")), "")
        bare = pkg.split("/")[-1] if pkg else ""
        unpinned = pkg and ("@" not in bare or bare.endswith("@latest")) and "==" not in pkg
        if unpinned and not pkg.startswith((".", "/")):
            out.append(Finding("AP04", rel, at(f'"{name}"'), f"{name}: {cmd} {clean(pkg, 80)}"))
    if cmd in ("docker", "podman") and DOCKER_ESCAPE.search(" ".join(args)):
        out.append(Finding("AP08", rel, at(f'"{name}"'), f"{name}: {DOCKER_ESCAPE.search(' '.join(args)).group(0)}"))
    for section in ("env", "headers"):
        vals = entry.get(section)
        if isinstance(vals, dict):
            for k, v in vals.items():
                v = str(v)
                if LITERAL_SECRET.search(v) or BEARER.search(v):
                    out.append(Finding("AP05", rel, at(f'"{k}"'), f"{name}: {section}.{k} = <redacted>"))
    for a in args:
        if LITERAL_SECRET.search(a.split("=", 1)[-1]):
            out.append(Finding("AP05", rel, at(f'"{name}"'), f"{name}: argument <redacted>"))
    url = str(entry.get("url") or "")
    if url.startswith("http://"):
        host = re.sub(r"^http://([^/:@]+@)?", "", url).split("/")[0].split(":")[0]
        if host not in ("localhost", "127.0.0.1", "::1", "0.0.0.0") and not host.endswith(".local"):
            out.append(Finding("AP07", rel, at(f'"{name}"'), f"{name}: http://{host}"))
    return out


def classify(name: str, entry: dict) -> set[str]:
    blob = " ".join([name, str(entry.get("command") or ""), " ".join(map(str, entry.get("args") or [])),
                     str(entry.get("url") or "")])
    legs = set()
    if UNTRUSTED.search(blob):
        legs.add("untrusted input")
    if PRIVATE.search(blob):
        legs.add("private data")
    if SENDS.search(blob):
        legs.add("a way out")
    return legs


def combo_findings(where: str, servers: list[tuple[str, dict]], at) -> list[Finding]:
    legs: dict[str, list[str]] = {}
    for name, entry in servers:
        for leg in classify(name, entry):
            legs.setdefault(leg, []).append(name)
    need = ["untrusted input", "private data", "a way out"]
    if not all(legs.get(l) for l in need):
        return []
    detail = "; ".join(f"{l}: {', '.join(sorted(set(legs[l]))[:4])}" for l in need)
    return [Finding("AP09", where, at(f'"{servers[0][0]}"'), f"likely, from server names — {detail}")]


def load_ignores(root: Path) -> list[str]:
    """Glob patterns from .open-agent-security-ignore, one per line; # starts a comment."""
    f = root / ".open-agent-security-ignore"
    text = read(f) if f.is_file() else None
    return [ln.split("#", 1)[0].strip() for ln in (text or "").splitlines() if ln.split("#", 1)[0].strip()]


def ignored(rel: str, patterns: list[str]) -> bool:
    from fnmatch import fnmatch
    for pat in patterns:
        pat = pat.lstrip("/")
        if pat.endswith("/"):
            if rel.startswith(pat) or ("/" + pat) in ("/" + rel):
                return True
        elif fnmatch(rel, pat) or fnmatch(Path(rel).name, pat) or rel.startswith(pat.rstrip("*") + "/") and pat.endswith("/**"):
            return True
    return False


IGNORE_MARK = "open-agent-security: ignore"


def scan_repo(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    patterns = load_ignores(root)
    for p in iter_files(root):
        rel = p.relative_to(root).as_posix()
        if ignored(rel, patterns):
            continue
        text = read(p)
        if text is None:
            continue
        lines = text.splitlines()
        for f in scan_text(rel, text):
            if 0 < f.line <= len(lines) and IGNORE_MARK in lines[f.line - 1]:
                continue
            findings.append(f)
    return findings


def scan_host(project: Path | None, home: Path | None = None) -> tuple[list[Finding], list[str]]:
    """MCP servers configured on this machine. Paths are shown with ~ for the home folder."""
    home = home or Path.home()
    sources = host_scan.host_sources(home, platform.system(), None)
    findings: list[Finding] = []
    notes: list[str] = []
    by_client: dict[str, list[tuple[str, dict]]] = {}
    for src in sources:
        path = Path(src["path"])
        if not path.is_file():
            continue
        data, err = host_scan.load_json(path)
        if err:
            notes.append(err)
            continue
        shown = "~/" + path.relative_to(home).as_posix() if path.is_relative_to(home) else str(path)
        raw = path.read_text(encoding="utf-8", errors="replace")

        def at(needle: str, raw=raw) -> int:
            i = raw.find(needle)
            return line_no(raw, i) if i >= 0 else 1
        for key in src["keys"]:
            if key == "projects.*.mcpServers":
                entries = list(host_scan.project_servers(data, project))
            else:
                entries = list(host_scan.servers_in(data, key))
            for _, name, entry in entries:
                if isinstance(entry, dict):
                    findings += server_findings(shown, str(name), entry, at)
                    by_client.setdefault(shown, []).append((str(name), entry))
        perms = data.get("permissions") if isinstance(data, dict) else None
        if isinstance(perms, dict) and perms.get("defaultMode") == "bypassPermissions":
            findings.append(Finding("AP01", shown, at("defaultMode"), "defaultMode bypassPermissions"))
    for where, servers in by_client.items():
        findings += combo_findings(where, servers, lambda _n: 1)
    for settings in (home / ".claude" / "settings.json",):
        if settings.is_file():
            text = read(settings) or ""
            findings += scan_json("~/.claude/settings.json", text)
    return findings, notes


def dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    for f in findings:
        k = (f.rule, f.file, f.line, f.detail)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return sorted(out, key=lambda f: (SEVERITY_ORDER[f.severity], f.rule, f.file, f.line))


def render(findings: list[Finding], notes: list[str], color: bool, max_places: int = 8) -> str:
    c = {"critical": "\033[1;31m", "high": "\033[31m", "medium": "\033[33m", "low": "\033[36m",
         "dim": "\033[2m", "bold": "\033[1m", "end": "\033[0m"} if color else {}
    g = lambda k: c.get(k, "")
    lines = []
    if not findings:
        lines.append(f"{g('bold')}No known-dangerous agent setups found.{g('end')}")
        lines.append(f"{g('dim')}This checks {len(RULES)} anti-patterns only. It is not a security review; see "
                     f"https://braceframework.org/checklist for the full sign-off.{g('end')}")
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.rule, []).append(f)
    for rule, fs in groups.items():
        f = fs[0]
        lines.append(f"{g(f.severity)}✗ {f.severity.upper():8}{g('end')} {g('bold')}{f.title}{g('end')}  "
                     f"{g('dim')}[{rule}] ×{len(fs)}{g('end')}")
        for x in fs[:max_places]:
            lines.append(f"    {x.file}:{x.line}  {g('dim')}{x.detail}{g('end')}")
        if len(fs) > max_places:
            lines.append(f"    {g('dim')}… and {len(fs) - max_places} more (use --json for all){g('end')}")
        lines.append(f"    Why:  {f.why}")
        lines.append(f"    Fix:  {f.fix}")
        lines.append(f"    {g('dim')}BRACE checklist {', '.join(f.items)} · {DOCS}#{anchor(rule)}{g('end')}")
        lines.append("")
    if findings:
        counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_ORDER}
        lines.append(", ".join(f"{n} {s}" for s, n in counts.items() if n) + f"  ({len(findings)} findings). "
                     f"Silence a reviewed line with an '{IGNORE_MARK}' comment or a .open-agent-security-ignore entry.")
    for n in notes:
        lines.append(f"{g('dim')}note: {clean(n)}{g('end')}")
    return "\n".join(lines)


def sarif(findings: list[Finding]) -> dict:
    level = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{"tool": {"driver": {"name": "open-agent-security", "informationUri": DOCS, "rules": [
                {"id": rid, "name": rid, "shortDescription": {"text": r[1]}, "fullDescription": {"text": r[2]},
                 "help": {"text": f"{r[3]} BRACE checklist: {', '.join(r[4])}."}, "helpUri": f"{DOCS}#{anchor(rid)}",
                 "properties": {"security-severity": {"critical": "9.5", "high": "8.0", "medium": "5.5", "low": "3.0"}[r[0]],
                                "tags": ["security", "ai-agent"]}} for rid, r in RULES.items()]}},
                "results": [{"ruleId": f.rule, "level": level[f.severity],
                             "message": {"text": f"{f.title}: {f.detail}. {f.fix}"},
                             "locations": [{"physicalLocation": {"artifactLocation": {"uri": f.file},
                                                                 "region": {"startLine": max(1, f.line)}}}]}
                            for f in findings if not f.file.startswith(("~", "/"))]}]}


def markdown(findings: list[Finding]) -> str:
    if not findings:
        return (f"### BRACE agent security scan: no known-dangerous setups found\n\n"
                f"Checked {len(RULES)} anti-patterns. This is not a full review; see the "
                f"[BRACE checklist](https://braceframework.org/checklist).\n")
    rows = ["### BRACE agent security scan", "", "| Severity | Problem | Where | Fix |", "|---|---|---|---|"]
    esc = lambda t: str(t).replace("|", "\\|").replace("\n", " ")
    for f in findings:
        rows.append(f"| {f.severity} | [{esc(f.title)}]({DOCS}#{anchor(f.rule)}) | `{esc(f.file)}:{f.line}` | {esc(f.fix)} |")
    return "\n".join(rows) + "\n"


def run(path: str, host: bool, as_json: bool, fail_on: str, out=sys.stdout,
        sarif_path: str | None = None, md_path: str | None = None) -> int:
    root = Path(path).resolve()
    if not root.is_dir():
        print(f"open-agent-security: not a folder: {path}", file=sys.stderr)
        return 2
    findings = scan_repo(root)
    notes: list[str] = []
    if host:
        hf, notes = scan_host(root)
        findings += hf
    findings = dedupe(findings)
    if as_json:
        json.dump({"scanner": "open-agent-security", "rules": len(RULES), "findings": [asdict(f) for f in findings],
                   "notes": notes}, out, indent=2)
        out.write("\n")
    else:
        out.write(render(findings, notes, color=out.isatty() and not os.environ.get("NO_COLOR")) + "\n")
    if sarif_path:
        Path(sarif_path).write_text(json.dumps(sarif(findings), indent=2), encoding="utf-8")
    if md_path:
        with open(md_path, "a", encoding="utf-8") as fh:
            fh.write(markdown(findings))
    limit = {"none": -1, "critical": 0, "high": 1, "medium": 2, "low": 3}[fail_on]
    return 1 if any(SEVERITY_ORDER[f.severity] <= limit for f in findings) else 0


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="open-agent-security", description="Find known-dangerous AI agent setups. Local, read-only.")
    p.add_argument("path", nargs="?", default=".", help="folder to scan (default: .)")
    p.add_argument("--host", action="store_true", help="also read MCP and agent settings on this machine")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--fail-on", choices=["critical", "high", "medium", "low", "none"], default="high",
                   help="exit 1 when a finding is this severe or worse (default: high)")
    p.add_argument("--sarif", metavar="FILE", help="also write SARIF (GitHub code scanning) to FILE")
    p.add_argument("--markdown", metavar="FILE", help="also append a Markdown summary to FILE")
    a = p.parse_args(argv)
    return run(a.path, a.host, a.json, a.fail_on, sarif_path=a.sarif, md_path=a.markdown)

