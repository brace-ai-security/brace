"""Shared helpers for the open-agent-security tests: build a folder, run the scanner, read its output.

Every scan here goes through the command line (cli.main) or the engine, never a compatibility
facade, so the tests exercise what users run.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / "tools" / "brace"

from open_agent_security import cli, registry  # noqa: E402
from open_agent_security.config import load  # noqa: E402
from open_agent_security.engine import run_scan  # noqa: E402
from open_agent_security.limits import MAX_SEGMENTS  # noqa: E402
from open_agent_security.registry import builtin  # noqa: E402

CONFIG = ".open-agent-security.toml"
FLAG = "--dangerously-skip-permissions"
TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"  # a GitHub token shape that must never be printed
TOKEN_MIXED = "ghp_" + "Ab1" * 12                         # the same, with mixed case and digits
AGENT = json.dumps({"mcpServers": {"t": {"command": "node", "args": ["t.js"]}}})  # agent config, no finding
UNPINNED = json.dumps({"mcpServers": {"s": {"command": "npx", "args": ["-y", "some-server"]}}})  # one AP04
EVIL = {"command": "npx", "args": ["-y", "evil-mcp"], "env": {"GH": TOKEN}}  # an AP04 and an AP05 server
PLAIN = "/".join(["*?*"] * (MAX_SEGMENTS - 1))  # with the last segment: 16, the most allowed
TUNED = "/".join(["*?*", "**"] * 5)  # live states in every folder of a 6-deep tree
needs_symlinks = pytest.mark.skipif(not hasattr(os, "symlink") or os.name == "nt", reason="needs symlinks")


def skip_unless_ci(reason: str) -> None:
    """Skip locally when a tool or the history is missing; in CI (CI=true) fail instead, since
    these tests must run there."""
    if os.environ.get("CI") == "true":
        pytest.fail(f"must run in CI: {reason}")
    pytest.skip(reason)


class EntryPoint:
    """A fake installed plugin: counts how often it is loaded."""

    def __init__(self, name, register):
        self.name, self.register, self.loads = name, register, 0

    def load(self):
        self.loads += 1
        return self.register


def write(root: Path, rel: str, text: str | bytes) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return p


def mcp(root: Path, *servers: dict, rel: str = ".mcp.json") -> None:
    """An MCP config with one server per argument, named s0, s1, ..."""
    write(root, rel, json.dumps({"mcpServers": {f"s{i}": s for i, s in enumerate(servers)}}, indent=2) + "\n")


def limits(root: Path, **values: int) -> list[str]:
    """`--config FILE` arguments for a config file outside `root` (so it is not scanned itself)
    that sets these limits, such as max_files=3 or max_file_bytes=10."""
    path = root.parent / f"{root.name}-limits.toml"
    path.write_text(toml({"limits": {k.replace("_", "-"): v for k, v in values.items()}}), encoding="utf-8")
    return ["--config", str(path)]


def toml_value(v) -> str:
    """One TOML value; tables are written inline, so any nesting fits on one line."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)  # a JSON string is a valid TOML basic string
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{json.dumps(str(k))} = {toml_value(x)}" for k, x in v.items()) + "}"
    raise TypeError(f"TOML has no {type(v).__name__}")


def toml(data: dict) -> str:
    """A TOML document with the top-level keys of `data`."""
    return "".join(f"{json.dumps(k)} = {toml_value(v)}\n" for k, v in data.items())


def config(root: Path, data) -> None:
    """The scanned folder's config file: `data` as written if it is text, else as TOML."""
    write(root, CONFIG, data if isinstance(data, str) else toml(data))


def cli_run(root: Path, *args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run the command line on `root` from `cwd` (default: root): (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    old = os.getcwd()
    os.chdir(cwd or root)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([str(root), *args])
    finally:
        os.chdir(old)
    return code, out.getvalue(), err.getvalue()


def scan(root: Path, *args: str) -> tuple[int, str]:
    """(exit code, stdout and stderr) of the command line run in `root`."""
    code, out, err = cli_run(root, *args)
    return code, out + err


def run(root: Path, cwd: Path | None = None, as_json: bool = False, fail_on: str = "none",
        sarif_path: str | None = None, md_path: str | None = None, github_output: str | None = None,
        args: list[str] = ()) -> tuple[int, str]:
    """(exit code, stdout) of the command line, with its options as keyword arguments."""
    args = ["--fail-on", fail_on, *args] + (["--json"] if as_json else [])
    for flag, value in (("--sarif", sarif_path), ("--markdown", md_path), ("--github-output", github_output)):
        if value:
            args += [flag, value]
    code, out, _ = cli_run(root, *args, cwd=cwd)
    return code, out


def report(root: Path, *args: str) -> dict:
    return json.loads(scan(root, "--json", "--fail-on", "none", *args)[1])


def found(root: Path, *args: str) -> list[tuple[str, str]]:
    return sorted((f["rule"], f["detail"]) for f in report(root, *args)["findings"])


def rules(root: Path) -> list[str]:
    return sorted(f["rule"] for f in report(root)["findings"])


def result(root: Path):
    """The engine's Report for a folder, as the command line builds it (paths not prefixed)."""
    registry = builtin()
    return run_scan(load(Path(root), registry.rules), registry)


def host_result(project: Path):
    """The engine's Report for a host scan (--host) of an empty `project` folder; set HOME first."""
    project.mkdir(parents=True, exist_ok=True)
    registry = builtin()
    return run_scan(replace(load(project, registry.rules), host=True), registry)


def six_servers(root: Path) -> None:
    mcp(root, *({"command": "npx", "args": [f"tool{i}-mcp"]} for i in range(6)))


def noise(suffix: str = "") -> list[str]:
    """150 lines of bypass flags (one finding each), and the repro's 120 flags on one line."""
    return [" ".join(["--dangerously-skip-permissions"] * 120) + suffix] + \
        [f"{i} --dangerously-skip-permissions{suffix}" for i in range(150)]


def all_outputs(root: Path) -> list[str]:
    prompt = root.parent / "out.prompt"
    code, text = scan(root, "--fail-on", "none", "--sarif", str(root.parent / "out.sarif"),
                      "--output", f"agent-prompt={prompt}")
    sarif = (root.parent / "out.sarif").read_text(encoding="utf-8")
    out = [text, json.dumps(report(root)["notes"]), sarif, prompt.read_text(encoding="utf-8")]
    prompt.unlink()
    return out


def fast(fn, limit: float = 3.0):
    """fn()'s result, asserting it used less than `limit` seconds of CPU time.

    CPU time (not wall-clock time) so a loaded machine cannot fail a linear-time check."""
    start = time.process_time()
    out = fn()
    assert time.process_time() - start < limit
    return out


@pytest.fixture
def plugins(monkeypatch):
    """Installed plugins, by name: add EntryPoint objects to the returned dict."""
    eps = {}
    monkeypatch.setattr(registry, "entry_points", lambda group: list(eps.values()) if group == registry.GROUP else [])
    monkeypatch.delenv(registry.PLUGIN_ENV, raising=False)
    return eps
