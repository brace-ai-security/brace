"""The config file: keys, validation, precedence and limits."""
import json

import pytest
from support import CONFIG, FLAG, TOOL_DIR, TUNED, cli_run, config, report, scan, six_servers, toml, write

from open_agent_security import registry
from open_agent_security.catalog import RULES
from open_agent_security.ignore import IGNORE_FILE

AGENT_AP04 = json.dumps({"mcpServers": {"t": {"command": "npx", "args": ["tool-mcp"]}}})  # AP04, high


class FakeEntryPoint:
    def __init__(self, name, loaded):
        self.name, self.loaded = name, loaded

    def load(self):
        self.loaded.append(self.name)
        return lambda reg: None


SHAPES = [[], {}, [{}], 1, "x", True, 1.5, [[]], {"a": []}]  # TOML has no null


def test_no_config_file_changes_nothing(tmp_path):
    write(tmp_path, ".mcp.json", AGENT_AP04)
    code, out, _ = cli_run(tmp_path, "--json")
    report = json.loads(out)
    assert code == 1 and report["config"] is None and report["suppressed"] == 0


def test_rule_off_and_severity_override_are_visible(tmp_path):
    write(tmp_path, ".mcp.json", AGENT_AP04)
    write(tmp_path, "run.sh", "gemini --yolo\n")
    config(tmp_path, '# comments are fine\nversion = 1\n\n[rules]\nAP01 = "off"\nAP04 = "low"\n')
    code, out, _ = cli_run(tmp_path, "--fail-on", "high")
    assert code == 0
    assert "AP01" not in out and "LOW      MCP server installed" in out
    assert f"note: config {CONFIG}: 1 rule off, 1 severity override; 1 finding suppressed" in out
    report = json.loads(cli_run(tmp_path, "--json")[1])
    assert report["suppressed"] == 1 and report["config"] == CONFIG and report["rules"] == 13


def test_config_ignore_entries_are_counted_and_combined_with_the_ignore_file(tmp_path):
    write(tmp_path, "a/.mcp.json", AGENT_AP04)
    write(tmp_path, "b/.mcp.json", AGENT_AP04)
    write(tmp_path, IGNORE_FILE, "AP04 b/.mcp.json\n")
    config(tmp_path, {"ignore": [{"path": "a/", "rules": ["AP04"], "reason": "reviewed"}]})
    code, out, _ = cli_run(tmp_path)
    assert code == 0 and (f"config {CONFIG}: 1 ignore entry; {IGNORE_FILE}: 1 entry; 2 findings suppressed; "
                          "0 files not scanned because of ignore entries") in out


def test_cli_fail_on_overrides_config(tmp_path):
    write(tmp_path, ".mcp.json", AGENT_AP04)
    config(tmp_path, {"fail-on": "none"})
    assert cli_run(tmp_path)[0] == 0
    assert cli_run(tmp_path, "--fail-on", "high")[0] == 1


def test_no_config_and_explicit_config(tmp_path):
    write(tmp_path, ".mcp.json", AGENT_AP04)
    config(tmp_path, {"rules": {"AP04": "off"}})
    assert cli_run(tmp_path)[0] == 0
    assert cli_run(tmp_path, "--no-config")[0] == 1
    other = write(tmp_path / "elsewhere", "c.toml", toml({"fail-on": "none"}))
    assert cli_run(tmp_path, "--config", str(other))[0] == 0
    assert cli_run(tmp_path, "--config", str(tmp_path / "missing.toml"))[0] == 2


@pytest.mark.parametrize("text", [
    "not = = toml",
    "[]",
    toml({"failon": "high"}),                      # unknown key
    toml({"version": 2}),
    toml({"fail-on": "severe"}),
    toml({"rules": {"AP99": "off"}}),              # unknown rule
    toml({"rules": {"AP01": "loud"}}),
    toml({"ignore": [{"path": "x", "why": "typo"}]}),
    toml({"ignore": [{"path": "x", "rules": ["AP99"]}]}),
    toml({"limits": {"max-files": 0}}),
    toml({"limits": {"max-files": True}}),
    toml({"limits": {"timeout": 5}}),
])
def test_malformed_config_is_exit_2(tmp_path, text):
    write(tmp_path, ".mcp.json", AGENT_AP04)
    config(tmp_path, text)
    code, out, err = cli_run(tmp_path)
    assert code == 2 and out == "" and "open-agent-security:" in err


def test_symlinked_config_in_the_folder_is_refused(tmp_path):
    secret = write(tmp_path, "outside/c.toml", toml({"rules": {"AP04": "off"}}))
    repo = tmp_path / "repo"
    write(repo, ".mcp.json", AGENT_AP04)
    (repo / CONFIG).symlink_to(secret)
    assert cli_run(repo)[0] == 2


@pytest.mark.parametrize("pattern", ["../outside.tpl", "/etc/passwd", "a/../../b", "~/x", "C:/x", "a\\b", "./x", ""])
@pytest.mark.parametrize("key", ["include", "agent-config"])
def test_globs_cannot_escape_the_folder(tmp_path, key, pattern):
    config(tmp_path, {key: [pattern]})
    assert cli_run(tmp_path)[0] == 2


def test_include_and_agent_config_globs(tmp_path):
    write(tmp_path, "deploy/run.sht", "gemini -y\n")  # -y is not a bypass marker, so the walk reads no .sht
    write(tmp_path, "config/mcp.prod.cfgjson", '{"servers": {')
    assert cli_run(tmp_path, "--fail-on", "low")[0] == 0  # neither file is read by default
    config(tmp_path, {"include": ["deploy/*.sht"], "agent-config": ["config/mcp.*.cfgjson"]})
    code, out, _ = cli_run(tmp_path, "--fail-on", "none", "--json")
    report = json.loads(out)
    assert [f["rule"] for f in report["findings"]] == ["AP01"]
    assert report["incomplete"] and any("config/mcp.prod.cfgjson" in n for n in report["notes"])
    write(tmp_path, "config/mcp.prod.cfgjson", json.dumps({"servers": {"s": {"command": "npx", "args": ["x"]}}}))
    assert "AP04" in cli_run(tmp_path)[1]


def test_custom_tokens_are_structured_and_redacted(tmp_path):
    token = "acme_" + "Q7w9E2r4T6y8U1i3O5p7A9s2"
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"t": {"command": "node", "env": {"ACME": token}}}}))
    write(tmp_path, "run.sh", f"gemini --yolo {token}\n")
    assert "AP05" not in cli_run(tmp_path)[1]
    config(tmp_path, {"tokens": [{"name": "acme", "prefix": "acme_", "charset": "alnum", "min": 20, "max": 64}]})
    code, out, _ = cli_run(tmp_path, "--json")
    assert "AP05" in out and token not in out


@pytest.mark.parametrize("token", [
    {"name": "re", "prefix": "(a+)+", "charset": "alnum", "min": 20, "max": 64},   # a regex, not a prefix
    {"name": "x", "prefix": "acme_", "charset": "[a-z]*", "min": 20, "max": 64},   # charset is a name
    {"name": "x", "prefix": "acme_", "charset": "alnum", "min": 1, "max": 64},
    {"name": "x", "prefix": "acme_", "charset": "alnum", "min": 20, "max": 100000},
    {"name": "x", "prefix": "acme_", "charset": "alnum", "min": 20, "max": 64, "regex": ".*"},
])
def test_custom_tokens_reject_anything_but_the_fixed_shape(tmp_path, token):
    config(tmp_path, {"tokens": [token]})
    assert cli_run(tmp_path)[0] == 2


def test_limits_lower_freely_and_are_capped(tmp_path):
    for i in range(3):
        write(tmp_path, f"f{i}.sh", "echo\n")
    config(tmp_path, {"limits": {"max-files": 2}})
    code, out, _ = cli_run(tmp_path)
    assert code == 1 and "stopped after 2 files" in out
    config(tmp_path, {"limits": {"max-files": 10 ** 9, "max-file-bytes": 10 ** 12}})
    code, out, _ = cli_run(tmp_path)
    assert code == 0 and "max-files capped at 1000000" in out and "max-file-bytes capped at 16777216" in out


def test_repo_config_cannot_enable_plugins(tmp_path, monkeypatch):
    loaded = []
    monkeypatch.setattr(registry, "entry_points", lambda group: [FakeEntryPoint("evil", loaded)])
    config(tmp_path, {"plugins": ["evil"]})
    code, out, _ = cli_run(tmp_path)
    assert code == 0 and loaded == [] and "'plugins' is ignored" in out


def test_fail_on_from_config_is_visible(tmp_path):
    six_servers(tmp_path)
    config(tmp_path, {"fail-on": "none"})
    code, out = scan(tmp_path)
    assert code == 0 and f"config {CONFIG}: fail-on none" in out
    assert "fail-on none" not in scan(tmp_path, "--fail-on", "high")[1]


@pytest.mark.parametrize("data", [
    {"rules": {"AP04": v}} for v in SHAPES] + [
    {"ignore": [{"path": "x", "rules": [v]}]} for v in SHAPES] + [
    {"ignore": [{"path": v}]} for v in SHAPES] + [
    {"tokens": [{"name": "t", "prefix": "tk_", "charset": v, "min": 8, "max": 9}]} for v in SHAPES] + [
    {"fail-on": v} for v in SHAPES] + [{"limits": {"max-files": v}} for v in SHAPES] + [
    {k: v} for k in ("rules", "ignore", "include", "agent-config", "tokens", "limits", "version") for v in SHAPES])
def test_config_shapes_exit_2_or_0(tmp_path, data):
    config(tmp_path, data)
    code, out = scan(tmp_path, "--fail-on", "none")
    assert code in (0, 2), out
    if code == 2:
        assert "internal error" not in out and CONFIG in out


def test_small_file_limit_is_shown_in_bytes(tmp_path):
    six_servers(tmp_path)
    config(tmp_path, {"limits": {"max-file-bytes": 40}})
    notes = report(tmp_path)["notes"]
    assert any("over 40 bytes" in n for n in notes)
    assert any("limits.max-file-bytes lowered to 40 bytes" in n for n in notes)


def test_config_globs_over_the_budget_are_refused(tmp_path):
    config(tmp_path, {"include": [f"{TUNED}/*{i}z" for i in range(50)]})
    code, out = scan(tmp_path)
    assert code == 2 and "segments after `**`" in out


def test_config_ignore_expansion_is_capped(tmp_path):
    every = [r.id for r in RULES]
    config(tmp_path, {"ignore": [{"path": f"d{i}/", "rules": every} for i in range(200)]})
    code, out = scan(tmp_path)
    assert code == 2 and "path-and-rule pairs" in out


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_config_version_must_be_the_integer_1(tmp_path, version):
    config(tmp_path, {"version": version})
    assert scan(tmp_path)[0] == 2


def test_config_ignore_accepts_an_anchored_path(tmp_path):
    config(tmp_path, {"ignore": [{"path": "/build/out.sh"}]})
    write(tmp_path, "build/out.sh", f"claude -p hi {FLAG}\n")
    write(tmp_path, "sub/build/out.sh", f"claude -p hi {FLAG}\n")
    assert [f["file"] for f in report(tmp_path)["findings"]] == ["sub/build/out.sh"]


@pytest.mark.parametrize("path", ["../x.sh", "//etc/x", "/../x", "~/x"])
def test_config_ignore_still_rejects_paths_outside_the_folder(tmp_path, path):
    config(tmp_path, {"ignore": [{"path": path}]})
    assert scan(tmp_path)[0] == 2


def test_the_documented_example_is_a_valid_config(tmp_path):
    text = (TOOL_DIR / "SCAN.md").read_text(encoding="utf-8").split("```toml\n", 1)[1].split("```", 1)[0]
    config(tmp_path, text)
    code, out = scan(tmp_path, "--fail-on", "none")
    assert code == 0 and f"config {CONFIG}: 1 rule off, 1 severity override, 2 ignore entries" in out


@pytest.mark.parametrize("text", ["include = " + "[" * 5000 + "]" * 5000 + "\n", "a = " + "{b = " * 3000 + "\n"])
def test_deeply_nested_toml_is_a_config_error(tmp_path, text):
    config(tmp_path, text)
    code, out = scan(tmp_path)
    assert code == 2 and "not valid TOML" in out


def test_a_deeply_nested_codex_config_makes_the_scan_incomplete(tmp_path):
    write(tmp_path, ".codex/config.toml", "a = " + "[" * 5000 + "]" * 5000 + "\n")
    r = report(tmp_path)
    assert r["incomplete"] is True and any("could not parse" in n for n in r["notes"])


@pytest.mark.parametrize("pattern", ["config/agent.yaml", "deploy/*.yml", "tools/mcp.toml"])
def test_an_agent_config_glob_naming_yaml_or_toml_is_refused(tmp_path, pattern):
    """Finding 17: agent config is read as JSON, so such a glob would silently do nothing."""
    config(tmp_path, {"agent-config": [pattern]})
    code, out, err = cli_run(tmp_path)
    assert code == 2 and "names a YAML or TOML file" in err


def test_an_agent_config_glob_for_codex_toml_is_allowed(tmp_path):
    config(tmp_path, {"agent-config": ["sub/.codex/config.toml"]})
    assert cli_run(tmp_path)[0] == 0


@pytest.mark.parametrize("value", ["yes", 1, [], {}])
def test_sarif_suppressed_must_be_a_boolean(tmp_path, value):
    write(tmp_path, ".mcp.json", AGENT_AP04)
    config(tmp_path, {"sarif-suppressed": value})
    code, _, err = cli_run(tmp_path)
    assert code == 2 and "sarif-suppressed must be true or false" in err
