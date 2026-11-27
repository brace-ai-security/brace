"""The rule catalog, its documentation, the registry and plugins."""
import json

import pytest
from support import (
    ROOT,
    TOOL_DIR,
    EntryPoint,
    cli_run,
    config,
    plugins,  # noqa: F401  (a fixture)
)

from open_agent_security import registry
from open_agent_security.catalog import RULES, RuleMeta
from open_agent_security.model import Finding

ACME = RuleMeta("ACME01", "Acme agent left in debug mode", "medium", "Debug mode logs prompts.", "Turn it off.",
                url="https://example.org/acme01")


class DebugCheck:
    name = "acme-debug"
    emits = ("ACME01",)
    scope = "file"

    def run(self, doc, ctx):
        if "ACME_DEBUG=1" in doc.source.text:
            yield Finding("ACME01", doc.source.display, 1, "ACME_DEBUG=1")


class CrashingCheck:
    name = "crash"
    emits = ("ACME01",)
    scope = "file"

    def run(self, doc, ctx):
        raise RuntimeError("boom")
        yield


class LyingCheck:
    name = "liar"
    emits = ("ACME01",)
    scope = "file"

    def run(self, doc, ctx):
        yield Finding("AP01", doc.source.display, 1, "not mine")


def register_acme(reg):
    reg.add_rule(ACME)
    reg.add_check(DebugCheck())


def test_rules_match_anti_patterns_doc():
    doc = (TOOL_DIR.parent.parent / "ANTI-PATTERNS.md").read_text(encoding="utf-8")
    for rule in RULES:
        rid = rule.id
        assert f"### {rid}: {rule.title}\n" in doc, rid
        assert f"(#{rule.anchor})" in doc, rid
        row = doc.split(f"| {rid} |", 1)[1].split("\n", 1)[0]
        assert f"| {rule.severity.capitalize()} |" in row, rid


def test_every_rule_has_a_heading_in_anti_patterns():
    doc = (ROOT / "ANTI-PATTERNS.md").read_text(encoding="utf-8")
    for m in RULES:
        assert f"### {m.id}: {m.title}\n" in doc, m.id


def test_scan_md_table_matches_the_catalog():
    doc = (TOOL_DIR / "SCAN.md").read_text(encoding="utf-8")
    for m in RULES:
        row = doc.split(f"| {m.id} | ", 1)[1].split("\n", 1)[0]
        severity, title = row.split(" | ", 1)
        assert severity == m.severity and title.replace("`", "").startswith(m.title), m.id


def test_checklist_items_exist():
    items = {i["id"] for i in json.loads((TOOL_DIR / "brace_items.json").read_text(encoding="utf-8"))}
    for m in RULES:
        assert m.checklist and set(m.checklist) <= items, m.id


def test_every_rule_is_emitted_by_a_registered_check():
    reg = registry.builtin()
    emitted = {r for c in reg.checks for r in c.emits}
    assert emitted == set(reg.rules) == {m.id for m in RULES}


def test_plugins_are_found_but_not_loaded_unless_named(tmp_path, plugins):
    plugins["acme"] = EntryPoint("acme", register_acme)
    (tmp_path / "run.sh").write_text("ACME_DEBUG=1\n")
    assert cli_run(tmp_path, "--fail-on", "low")[0] == 0 and plugins["acme"].loads == 0
    code, out, _ = cli_run(tmp_path, "--fail-on", "low", "--plugin", "acme")
    assert code == 1 and "[ACME01]" in out and "https://example.org/acme01" in out and plugins["acme"].loads == 1


def test_plugin_from_environment(tmp_path, plugins, monkeypatch):
    plugins["acme"] = EntryPoint("acme", register_acme)
    (tmp_path / "run.sh").write_text("ACME_DEBUG=1\n")
    monkeypatch.setenv(registry.PLUGIN_ENV, "acme")
    assert "[ACME01]" in cli_run(tmp_path, "--fail-on", "none")[1]


def test_plugin_rules_are_configurable(tmp_path, plugins):
    plugins["acme"] = EntryPoint("acme", register_acme)
    (tmp_path / "run.sh").write_text("ACME_DEBUG=1\n")
    config(tmp_path, {"rules": {"ACME01": "off"}})
    assert cli_run(tmp_path, "--plugin", "acme", "--fail-on", "low")[0] == 0
    assert cli_run(tmp_path, "--fail-on", "low")[0] == 2  # unknown rule without the plugin


@pytest.mark.parametrize("register", [
    lambda reg: reg.add_rule(RuleMeta("AP99", "Spoof", "high", "w", "f")),       # reserved ID
    lambda reg: reg.add_rule(RULES[0]),                                          # duplicate
    lambda reg: reg.add_rule(RuleMeta("acme", "Bad id", "high", "w", "f")),
    lambda reg: reg.add_check(DebugCheck()),                                     # emits an unknown rule
    lambda reg: 1 / 0,
])
def test_bad_plugins_are_exit_2(tmp_path, plugins, register):
    plugins["bad"] = EntryPoint("bad", register)
    code, out, err = cli_run(tmp_path, "--plugin", "bad")
    assert code == 2 and out == "" and "plugin 'bad'" in err


def test_unknown_plugin_is_exit_2(tmp_path, plugins):
    code, _, err = cli_run(tmp_path, "--plugin", "nope")
    assert code == 2 and "no installed plugin named 'nope'" in err


@pytest.mark.parametrize("check", [CrashingCheck, LyingCheck])
def test_a_failing_plugin_check_makes_the_scan_incomplete(tmp_path, plugins, check):
    def register(reg):
        reg.add_rule(ACME)
        reg.add_check(check())
    plugins["p"] = EntryPoint("p", register)
    (tmp_path / "run.sh").write_text("echo\n")
    code, out, _ = cli_run(tmp_path, "--plugin", "p")
    assert code == 1 and "could not scan run.sh" in out and "No known-dangerous" not in out


def test_list_rules(tmp_path, plugins):
    plugins["acme"] = EntryPoint("acme", register_acme)
    config(tmp_path, {"rules": {"AP10": "off", "AP07": "high"}})
    code, out, _ = cli_run(tmp_path, "--list-rules", "--plugin", "acme")
    lines = out.splitlines()
    assert code == 0 and len(lines) == 15
    assert lines[0] == f"AP01   high      {RULES[0].title}"
    assert "AP07   high " in out and "AP10   off " in out and lines[-1].startswith("ACME01 medium")
    data = json.loads(cli_run(tmp_path, "--list-rules", "--json")[1])["rules"]
    assert [r["id"] for r in data] == [m.id for m in RULES]
    assert data[9]["enabled"] is False and data[6]["severity"] == "high"
    assert data[0]["help_uri"].endswith("#ap01-agent-runs-with-all-permission-checks-turned-off")


def test_project_checks_declare_their_facts():
    from open_agent_security.model import Project
    from open_agent_security.registry import builtin
    assert not hasattr(Project, "documents")
    assert all(callable(getattr(c, "facts", None)) for c in builtin().checks if c.scope == "project")


def test_every_config_format_is_listed_in_scan_md():
    doc = (TOOL_DIR / "SCAN-DETAILS.md").read_text(encoding="utf-8")
    for name in (".codex/config.toml", "opencode.json", "context_servers", "mcp.servers", "cline_mcp_settings.json",
                 ".gemini/settings.json"):
        assert name in doc, name
