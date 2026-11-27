"""Hardening of the non-scanner tools: bounded, symlink-safe reads; URL and argument cleaning;
atomic writes; Markdown escaping."""
import json
import os

import pytest
from conftest import TOOL_DIR  # noqa: F401  (puts src/ on sys.path)

from brace_tools import io
from brace_tools.topology import core as topology

TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"


def build(repo):
    return topology.build(repo, repo / "brace-inventory.json", None, repo / "none.json", None, [])


def services(bom):
    return {s["name"]: s for s in bom.get("services", [])}


def test_endpoints_drop_credentials_query_and_secret_args(tmp_path):
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {
        "remote": {"type": "http", "url": f"https://user:{TOKEN}@mcp.example/x?key={TOKEN}#f"},
        "local": {"command": "node", "args": ["s.js", "--api-key", "hunter2-value", TOKEN]},
    }}))
    bom = build(tmp_path)
    text = json.dumps(bom)
    assert TOKEN not in text and "hunter2" not in text and "user:" not in text
    assert services(bom)["remote"]["endpoints"] == ["https://mcp.example/x"]


@pytest.mark.parametrize("doc", ["[]", '{"mcpServers": []}', '{"mcpServers": {"a": "x", "b": 3}}'])
def test_non_object_mcp_json_is_ignored_not_a_traceback(tmp_path, doc):
    (tmp_path / ".mcp.json").write_text(doc)
    if doc == "[]":
        with pytest.raises(io.ReadError, match="JSON object"):
            build(tmp_path)
    else:
        assert "a" not in services(build(tmp_path))


@pytest.mark.skipif(not hasattr(os, "symlink") or os.name == "nt", reason="needs symlinks")
def test_symlinked_repo_file_is_refused(tmp_path):
    secret = tmp_path / "outside.json"
    secret.write_text('{"mcpServers": {}}')
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".mcp.json").symlink_to(secret)
    with pytest.raises(io.ReadError, match="symlink"):
        build(repo)


def test_oversized_and_invalid_json(tmp_path):
    big = tmp_path / "big.json"
    big.write_text(" " * 2048)
    with pytest.raises(io.ReadError, match="larger"):
        io.read_json(big, limit=1024)
    (tmp_path / "deep.json").write_text("[" * 100_000)
    with pytest.raises(io.ReadError, match="not valid JSON"):
        io.read_json(tmp_path / "deep.json")


def test_write_atomic_replaces_and_leaves_no_temp(tmp_path):
    f = tmp_path / "o.json"
    io.write_atomic(f, "one")
    io.write_atomic(f, "two")
    assert f.read_text() == "two" and [p.name for p in tmp_path.iterdir()] == ["o.json"]


def test_cli_reports_unreadable_input_without_traceback(tmp_path, capsys):
    (tmp_path / "bad.json").write_text("{")
    assert topology.main(["validate", str(tmp_path / "bad.json")]) == 1
    err = capsys.readouterr().err
    assert "not valid JSON" in err and "Traceback" not in err


def test_plan_markdown_escapes_untrusted_text_but_keeps_code_spans():
    from brace_tools.plan.core import cell, code, fence, md_inline
    assert md_inline("see `neg:<tenant>` ok") == "see `neg:<tenant>` ok"
    assert md_inline("![x](https://t.example/p.png) <img src=x>\n# H") == \
        "!\\[x\\](https://t.example/p.png) \\<img src=x\\> # H"
    assert cell("a | b") == "a \\| b"
    assert code("a`b") == "`` a`b ``"
    assert fence("x ```` y") == "`````"


def test_plan_sarif_has_driver_version_and_srcroot():
    from brace_tools import __version__
    from brace_tools.plan.core import sarif
    action = {"id": "B01", "title": "T", "steps": [], "problem": "p", "lead": "l", "priority": "p", "done_when": "",
              "evidence": ["a b/c.py:3"], "rating": "gap", "gate": "Blocker", "components": [], "lead_role": "x"}
    run = sarif({"actions": [action]})["runs"][0]
    assert run["tool"]["driver"]["version"] == __version__
    loc = run["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]
    assert loc == {"uri": "a%20b/c.py", "uriBaseId": "%SRCROOT%"}


def test_imported_result_text_is_redacted_by_the_scanner_cleaner():
    from brace_tools.imports.results import clean
    assert TOKEN not in clean(f"probe leaked {TOKEN}\n‮", 200) and "\n" not in clean("a\nb")


@pytest.mark.skipif(not hasattr(os, "symlink") or os.name == "nt", reason="needs symlinks")
def test_record_yaml_symlink_is_refused(tmp_path):
    from brace_tools.record import core
    (tmp_path / "real.yaml").write_text("a: 1\n")
    (tmp_path / "link.yaml").symlink_to(tmp_path / "real.yaml")
    with pytest.raises(core.InputError, match="symlink"):
        core.load_yaml(tmp_path / "link.yaml")
