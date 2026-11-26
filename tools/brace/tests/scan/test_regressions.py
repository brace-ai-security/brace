"""A guard against detection regressions: inputs the original single-module scanner (3.1.0's
open_agent_security/scan.py) detected must still be detected.

Each case is a small folder. EXPECTED holds the rule IDs the original reported for it,
recorded by running that scanner on the case (test_expected_matches_the_original re-checks
the record against `git show` when the repository is available). The current scanner must
report at least those rule IDs. Cases are true positives only: inputs the original flagged
wrongly (a bare --yolo, a flag in a comment) are deliberately not here.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from support import ROOT, TOKEN, fast, found, result, write

AGENT = json.dumps({"mcpServers": {"t": {"command": "node", "args": ["t.js"]}}})  # agent evidence for AP10
SECRET_ANT = "sk-ant-api03-" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8Qr9St0"
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
SLACK = "xoxb-" + "1234567890-abcdefghij"
GITLAB = "glpat-" + "Ab1Cd2Ef3Gh4Ij5Kl6Mn"
GOOGLE = "AIza" + "Sy" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q"


def server(name="s", **entry) -> str:
    return json.dumps({"mcpServers": {name: entry}}, indent=2)


def wf(steps: str, on: str = "on: pull_request_target\n") -> str:
    return on + "jobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n" + steps


FLAG = "--dangerously-skip-permissions"

# name -> {path: text}
CASES: dict[str, dict[str, str]] = {
    # --- bypass flags (AP01 local, AP02 in CI) ---
    "sh-claude": {"run.sh": f'claude {FLAG} -p "x"\n'},
    "sh-codex": {"run.sh": "codex exec --dangerously-bypass-approvals-and-sandbox 'fix'\n"},
    "sh-gemini-yolo": {"run.sh": "gemini --yolo -p 'x'\n"},
    "makefile": {"Makefile": f"fix:\n\tclaude {FLAG} -p 'fix'\n"},
    "py-list": {"agent.py": f'import subprocess\nsubprocess.run(["claude", "{FLAG}", "-p", "x"])\n'},
    "py-string": {"agent.py": f'import os\nos.system("claude {FLAG} -p x")\n'},
    "py-sdk-mode": {"agent.py": 'opts = ClaudeAgentOptions(permission_mode="bypassPermissions")\n'},
    "js-spawn": {"agent.js": f'spawn("claude", ["{FLAG}", "-p", "x"]);\n'},
    "ts-sdk-mode": {"agent.ts": 'const o = { permissionMode: "bypassPermissions" };\n'},
    "toml-codex-sandbox": {".codex/config.toml": 'sandbox_mode = "danger-full-access"\n'},
    "yaml-mode": {"agent.yml": 'permission_mode: "bypassPermissions"\n'},
    "settings-default-mode": {".claude/settings.json": json.dumps({"permissions": {"defaultMode": "bypassPermissions"}})},
    "package-json-script": {"package.json": json.dumps({"scripts": {"fix": f"claude {FLAG} -p fix"}})},
    "package-json-prompt": {"package.json": json.dumps(
        {"scripts": {"fix": f'npx @anthropic-ai/claude-code {FLAG} "fix the tests"'}})},
    # H3: `/*` inside a string must not hide the rest of the file.
    "h3-ts-glob": {"agent.ts": f'const files = glob("src/*.ts");\nspawn("claude", ["{FLAG}"]);\n'},
    "h3-js-route": {"agent.js": f'const routes = ["/api/*"];\nspawn("claude", ["{FLAG}"]);\n'},
    "h3-go-accept": {"main.go": f'h := map[string]string{{"Accept": "*/*"}}\nexec.Command("claude", "{FLAG}")\n'},
    "h3-rs": {"main.rs": f'let p = "/tmp/*";\nCommand::new("claude").arg("{FLAG}");\n'},
    "h3-java": {"Main.java": f'String g = "a/*";\nnew ProcessBuilder("claude", "{FLAG}");\n'},
    "h3-kt": {"Main.kt": f'val g = "a/*"\nProcessBuilder("claude", "{FLAG}")\n'},
    "h3-jsonc": {"cfg.jsonc": '{"glob": "src/*.ts",\n "args": ["' + FLAG + '"]}\n'},
    # M3: a `*` line in code is not a comment; a triple-quoted argument is not a docstring.
    "m3-star-unpack": {"agent.py": f'subprocess.run([\n    *base, "{FLAG}"\n])\n'},
    "m3-triple-arg": {"agent.py": f'subprocess.run(\n    """\n    claude -p "x" {FLAG}\n    """, shell=True)\n'},
    # CI
    "wf-run": {".github/workflows/a.yml": wf(f'      - run: claude -p "x" {FLAG}\n', "on: push\n")},
    "wf-run-block": {".github/workflows/a.yml": wf(f"      - run: |\n          claude -p x {FLAG}\n", "on: push\n")},
    "gitlab-ci": {".gitlab-ci.yml": f"job:\n  script:\n    - claude -p x {FLAG}\n"},
    # M1: a quoted prompt after the flag is not prose.
    "m1-npx-claude": {".github/workflows/a.yml": wf(
        f'      - run: npx @anthropic-ai/claude-code {FLAG} "fix the tests"\n', "on: push\n")},
    "m1-npx-gemini": {".github/workflows/a.yml": wf(
        '      - run: npx @google/gemini-cli --yolo "explain the code"\n', "on: push\n")},
    # --- AP03 ---
    "ap03-claude-action": {".github/workflows/a.yml": wf("      - uses: anthropics/claude-code-action@v1\n")},
    "ap03-base-action": {".github/workflows/a.yml": wf("      - uses: anthropics/claude-code-base-action@v1\n")},
    "ap03-codex-action": {".github/workflows/a.yml": wf("      - uses: openai/codex-action@v1\n",
                                                        "on: [pull_request_target]\n")},
    "ap03-gemini-action": {".github/workflows/a.yml": wf("      - uses: google-github-actions/run-gemini-cli@v0\n")},
    "ap03-run": {".github/workflows/a.yml": wf("      - run: claude -p 'review'\n")},
    "ap03-run-block": {".github/workflows/a.yml": wf("      - run: |\n          codex exec 'review'\n")},
    "ap03-on-map": {".github/workflows/a.yml": wf("      - run: claude -p 'review'\n",
                                                  "on:\n  pull_request_target:\n    types: [opened]\n")},
    # M2: an agent CLI behind a prefix.
    "m2-timeout": {".github/workflows/a.yml": wf("      - run: timeout 300 claude -p 'review'\n")},
    "m2-env-prefix": {".github/workflows/a.yml": wf("      - run: |\n          ANTHROPIC_API_KEY=$KEY claude -p 'review'\n")},
    "m2-if-not": {".github/workflows/a.yml": wf("      - run: |\n          if ! claude -p 'review'; then exit 1; fi\n")},
    # --- AP04 ---
    "ap04-npx": {".mcp.json": server(command="npx", args=["-y", "some-server"])},
    "ap04-npx-scoped": {".mcp.json": server(command="npx", args=["-y", "@modelcontextprotocol/server-github"])},
    "ap04-npx-latest": {".mcp.json": server(command="npx", args=["-y", "some-server@latest"])},
    "ap04-uvx": {".mcp.json": server(command="uvx", args=["mcp-server-fetch"])},
    "ap04-uvx-from": {".mcp.json": server(command="uvx", args=["--from", "some-pkg", "tool"])},
    "ap04-bunx": {".mcp.json": server(command="bunx", args=["some-server"])},
    "ap04-pnpx": {".mcp.json": server(command="pnpx", args=["some-server"])},
    "ap04-pnpm-dlx": {".mcp.json": server(command="pnpm", args=["dlx", "some-server"])},
    "ap04-yarn-dlx": {".mcp.json": server(command="yarn", args=["dlx", "some-server"])},
    "ap04-abs-npx": {".mcp.json": server(command="/usr/local/bin/npx", args=["some-server"])},
    "ap04-vscode-servers": {".vscode/mcp.json": json.dumps({"servers": {"s": {"command": "npx", "args": ["a-mcp"]}}})},
    "ap04-mcp-servers-key": {"mcp.json": json.dumps({"mcp_servers": {"s": {"command": "uvx", "args": ["a-mcp"]}}})},
    "ap04-claude-projects": {".claude.json": json.dumps(
        {"projects": {"/p": {"mcpServers": {"s": {"command": "npx", "args": ["a-mcp"]}}}}})},
    "ap04-three-servers": {".mcp.json": json.dumps({"mcpServers": {
        "a": {"command": "npx", "args": ["a-mcp"]}, "b": {"command": "npx", "args": ["b-mcp"]},
        "c": {"command": "uvx", "args": ["c-mcp"]}}})},
    # --- AP05 ---
    "ap05-env-ghp": {".mcp.json": server(command="node", args=["s.js"], env={"GITHUB_TOKEN": TOKEN})},
    "ap05-env-ant": {".mcp.json": server(command="node", args=["s.js"], env={"ANTHROPIC_API_KEY": SECRET_ANT})},
    "ap05-env-aws": {".mcp.json": server(command="node", args=["s.js"], env={"AWS_ACCESS_KEY_ID": AWS})},
    "ap05-env-slack": {".mcp.json": server(command="node", args=["s.js"], env={"SLACK_BOT_TOKEN": SLACK})},
    "ap05-env-gitlab": {".mcp.json": server(command="node", args=["s.js"], env={"GITLAB_TOKEN": GITLAB})},
    "ap05-env-google": {".mcp.json": server(command="node", args=["s.js"], env={"GOOGLE_API_KEY": GOOGLE})},
    "ap05-header-bearer": {".mcp.json": server(url="https://mcp.example.com/mcp",
                                               headers={"Authorization": "Bearer " + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8"})},
    "ap05-arg-positional": {".mcp.json": server(command="node", args=["s.js", TOKEN])},
    "ap05-arg-assign": {".mcp.json": server(command="node", args=["s.js", "--api-key=" + SECRET_ANT])},
    "ap05-arg-env-assign": {".mcp.json": server(command="docker", args=["run", "-e", "GITHUB_TOKEN=" + TOKEN, "img"])},
    # --- AP07 ---
    "ap07-url": {".mcp.json": server(url="http://mcp.example.com/mcp")},
    "ap07-url-userinfo": {".mcp.json": server(url="http://user@mcp.example.com:8080/mcp")},
    # --- AP08 ---
    "ap08-privileged": {".mcp.json": server(command="docker", args=["run", "--privileged", "img"])},
    "ap08-socket": {".mcp.json": server(command="docker",
                                        args=["run", "-v", "/var/run/docker.sock:/var/run/docker.sock", "img"])},
    "ap08-network-host": {".mcp.json": server(command="docker", args=["run", "--network", "host", "img"])},
    "ap08-network-host-eq": {".mcp.json": server(command="docker", args=["run", "--network=host", "img"])},
    "ap08-net-host": {".mcp.json": server(command="docker", args=["run", "--net=host", "img"])},
    "ap08-pid-host": {".mcp.json": server(command="podman", args=["run", "--pid", "host", "img"])},
    "ap08-root-mount": {".mcp.json": server(command="docker", args=["run", "-v", "/:/host", "img"])},
    # --- AP09 ---
    "ap09-three-legs": {".mcp.json": json.dumps({"mcpServers": {
        "fetch": {"command": "node", "args": ["f.js"]}, "postgres": {"command": "node", "args": ["p.js"]},
        "slack": {"command": "node", "args": ["s.js"]}}})},
    # --- AP10 (in a folder where an agent runs) ---
    "ap10-tag": {"Dockerfile": "FROM python:3.12\n", ".mcp.json": AGENT},
    "ap10-latest": {"Dockerfile": "FROM node:latest\nRUN npm i\n", ".mcp.json": AGENT},
    "ap10-platform": {"Dockerfile": "FROM --platform=linux/amd64 node:20\n", ".mcp.json": AGENT},
    "ap10-multistage": {"Dockerfile": "FROM node:20 AS build\nRUN x\nFROM build\n", ".mcp.json": AGENT},
    "ap10-suffix": {"Dockerfile.agent": "FROM ubuntu:24.04\n", ".mcp.json": AGENT},
    "ap10-registry": {"Dockerfile": "FROM ghcr.io/acme/agent:1.2\n", ".mcp.json": AGENT},
}

# Rule IDs the original scanner reported for each case (recorded by running it on each case;
# test_expected_matches_the_original re-checks the record).
EXPECTED: dict[str, list[str]] = {
    **dict.fromkeys((
        "sh-claude", "sh-codex", "sh-gemini-yolo", "makefile", "py-list", "py-string", "py-sdk-mode",
        "js-spawn", "ts-sdk-mode", "toml-codex-sandbox", "yaml-mode", "settings-default-mode",
        "package-json-script", "package-json-prompt", "h3-ts-glob", "h3-js-route", "h3-go-accept", "h3-rs",
        "h3-java", "h3-kt", "h3-jsonc", "m3-star-unpack", "m3-triple-arg"
    ), ["AP01"]),
    **dict.fromkeys((
        "wf-run", "wf-run-block", "gitlab-ci", "m1-npx-claude", "m1-npx-gemini"
    ), ["AP02"]),
    **dict.fromkeys((
        "ap03-claude-action", "ap03-base-action", "ap03-codex-action", "ap03-gemini-action", "ap03-run",
        "ap03-run-block", "ap03-on-map", "m2-timeout", "m2-env-prefix", "m2-if-not"
    ), ["AP03"]),
    **dict.fromkeys((
        "ap04-npx", "ap04-npx-scoped", "ap04-npx-latest", "ap04-uvx", "ap04-uvx-from", "ap04-bunx",
        "ap04-pnpx", "ap04-pnpm-dlx", "ap04-yarn-dlx", "ap04-abs-npx", "ap04-vscode-servers",
        "ap04-mcp-servers-key", "ap04-claude-projects", "ap04-three-servers"
    ), ["AP04"]),
    **dict.fromkeys((
        "ap05-env-ghp", "ap05-env-ant", "ap05-env-aws", "ap05-env-slack", "ap05-env-gitlab",
        "ap05-env-google", "ap05-header-bearer", "ap05-arg-positional", "ap05-arg-assign",
        "ap05-arg-env-assign"
    ), ["AP05"]),
    **dict.fromkeys((
        "ap07-url", "ap07-url-userinfo"
    ), ["AP07"]),
    **dict.fromkeys((
        "ap08-privileged", "ap08-socket", "ap08-network-host", "ap08-network-host-eq", "ap08-net-host",
        "ap08-pid-host", "ap08-root-mount"
    ), ["AP08"]),
    **dict.fromkeys((
        "ap09-three-legs",
    ), ["AP09"]),
    **dict.fromkeys((
        "ap10-tag", "ap10-latest", "ap10-platform", "ap10-multistage", "ap10-suffix", "ap10-registry"
    ), ["AP10"]),
}


def scan_ids(root: Path) -> set[str]:
    return {f.rule for f in result(root).findings}


@pytest.mark.parametrize("name", sorted(CASES))
def test_detects_what_the_original_detected(tmp_path, name):
    for rel, text in CASES[name].items():
        write(tmp_path, rel, text)
    assert EXPECTED[name], f"{name}: the original detected nothing, so this case guards nothing"
    missing = set(EXPECTED[name]) - scan_ids(tmp_path)
    assert not missing, f"{name}: no longer reports {sorted(missing)}"


def original_scanner(tmp: Path):
    """The 3.1.0 scanner, from git, as an importable package; None without git or the commit."""
    pkg = tmp / "orig" / "open_agent_security"
    pkg.mkdir(parents=True)
    for name in ("__init__.py", "host_scan.py", "scan.py"):
        try:
            shown = subprocess.run(["git", "show", f"53eed02:tools/brace/open_agent_security/{name}"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        if shown.returncode:
            return None
        (pkg / name).write_text(shown.stdout, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("orig_oas", pkg / "__init__.py", submodule_search_locations=[str(pkg)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orig_oas"] = mod
    spec.loader.exec_module(mod)
    return importlib.import_module("orig_oas.scan")


def original_ids(scanner, tmp: Path, files: dict[str, str]) -> list[str]:
    root = tmp / "case"
    for rel, text in files.items():
        write(root, rel, text)
    try:
        return sorted({f.rule for f in scanner.scan_repo(root)})
    finally:
        shutil.rmtree(root)


def test_expected_matches_the_original(tmp_path):
    scanner = original_scanner(tmp_path)
    if scanner is None:
        pytest.skip("git or the 3.1.0 commit is not available")
    try:
        assert {name: original_ids(scanner, tmp_path, files) for name, files in CASES.items()} == EXPECTED
    finally:
        for key in [k for k in sys.modules if k == "orig_oas" or k.startswith("orig_oas.")]:
            del sys.modules[key]


# --- Round 8 review: critical and high findings, and every way a bypass was hidden ----------
# These go beyond the original scanner (it missed most of them), so they are checked against
# their own expected rule IDs rather than against EXPECTED.
REPORT_HEAD = '<?xml\n{}\n# ?><testsuites name="open-agent-security">\n'
BEARER = "Bearer " + "Ab1Cd2Ef3Gh4Ij5Kl6Mn7Op8"
REVIEW_CASES: dict[str, tuple[dict[str, str], list[str]]] = {
    # 1 (critical): a script or Dockerfile shaped like the scanner's JUnit report was skipped.
    "r8-own-report-sh": ({"run.sh": REPORT_HEAD.format(f'claude {FLAG} -p "do it"')}, ["AP01"]),
    "r8-own-report-bat": ({"run.bat": REPORT_HEAD.format(f'claude {FLAG} -p "do it"')}, ["AP01"]),
    "r8-own-report-dockerfile": ({"Dockerfile": REPORT_HEAD.format(f"RUN claude {FLAG}")}, ["AP01"]),
    "r8-own-report-workflow": ({".github/workflows/w.yml": REPORT_HEAD.format(f"# x\njobs:\n  a:\n    steps:\n"
                                                                              f"      - run: claude -p x {FLAG}")},
                               ["AP02"]),
    # 4: a JS regex literal opened a phantom block comment; unclosed comments hid the rest.
    "r8-js-regex-literal": ({"a.js": f'u = url.replace(/\\/*$/, "");\nspawn("claude", ["{FLAG}"]);\n'}, ["AP01"]),
    "r8-unclosed-block-comment": ({"a.go": f'/* never closed\nexec.Command("claude", "{FLAG}")\n'}, ["AP01"]),
    "r8-unclosed-docstring": ({"a.py": f'"""never closed\nos.system("claude {FLAG} -p x")\n'}, ["AP01"]),
    # 5: names that pass the flag were read as deny-lists.
    "r8-unsafe-args": ({"a.py": f'UNSAFE_ARGS = ["{FLAG}"]\nsubprocess.run(["claude", *UNSAFE_ARGS])\n'}, ["AP01"]),
    "r8-dangerous-flags": ({"a.ts": f'const dangerousFlags = ["{FLAG}"];\nspawn("claude", dangerousFlags);\n'},
                           ["AP01"]),
    "r8-yaml-danger-args": ({"agent.yml": f"danger_args:\n  - {FLAG}\n"}, ["AP01"]),
    # Skip-path audit: a loop list, a command built from $VAR, a continued gated flag.
    "r8-for-loop": ({"a.py": f'for f in ["{FLAG}"]:\n    args.append(f)\n'}, ["AP01"]),
    "r8-expansion-prose": ({"run.sh": f'sh -c "$AGENT {FLAG} on the repo"\n'}, ["AP01"]),
    "r8-continued-yolo": ({"run.sh": "gemini -p 'fix' \\\n  --yolo\n"}, ["AP01"]),
    # 7: Codex and Gemini full-access spellings that were missed.
    "r8-codex-action-sandbox": ({".github/workflows/w.yml": "jobs:\n  a:\n    steps:\n      - uses: openai/codex-action@v1\n"
                                 "        with:\n          sandbox: danger-full-access\n"}, ["AP02"]),
    "r8-codex-sdk-sandbox-mode": ({"a.ts": 'codex.startThread({ sandboxMode: "danger-full-access" });\n'}, ["AP01"]),
    "r8-gemini-short-yolo": ({"run.sh": "gemini -y -p 'fix the tests'\n"}, ["AP01"]),
    # 6: a Bearer credential inside a longer value was redacted but not reported.
    "r8-bearer-in-headers": ({".mcp.json": json.dumps({"mcpServers": {"notion": {
        "command": "node", "args": ["s.js"], "env": {"OPENAPI_MCP_HEADERS": json.dumps({"Authorization": BEARER})}}}})},
        ["AP05"]),
    # 13: a truncated wsl command raised and lost every server in the file.
    "r8-truncated-wsl": ({".mcp.json": json.dumps({"mcpServers": {
        "w": {"command": "wsl", "args": ["-d"]}, "s": {"command": "npx", "args": ["-y", "evil-mcp"]}}})}, ["AP04"]),
}


@pytest.mark.parametrize("name", sorted(REVIEW_CASES))
def test_round8_review_cases_are_detected(tmp_path, name):
    files, expected = REVIEW_CASES[name]
    for rel, text in files.items():
        write(tmp_path, rel, text)
    missing = set(expected) - scan_ids(tmp_path)
    assert not missing, f"{name}: does not report {sorted(missing)}"


@pytest.mark.parametrize("rel,text", [
    # 2 (high): `-{1,2}[\w=-]{1,30}` matched `--a` two ways, 8**6 paths per attempt (lines are
    # cut to 2,000 characters, so the input is many lines; 40 KB took 93 s).
    (".github/workflows/w.yml", "on: push\njobs:\n  a:\n    steps:\n"
     + ("      - run: x;" + "env --a --b --c " * 120 + "zz\n") * 60),
    # 3 (high): each triple quote rescanned its line: 400 KB took 29 s.
    ("a.py", f'run("claude {FLAG}")\n' + '"' * 400_000 + "\n"),
])
def test_round8_slow_inputs_are_fast(tmp_path, rel, text):
    write(tmp_path, rel, text)
    fast(lambda: found(tmp_path))
