"""The triage loop: baselines, expiring ignore entries and the merge roll-up."""
from __future__ import annotations

import contextlib
import io
import json

import pytest
from support import CONFIG, FLAG, cli_run, config, fast, report, write

from open_agent_security import cli
from open_agent_security.ignore import IGNORE_FILE


def merge(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(["merge", *args])
    return code, out.getvalue(), err.getvalue()


def test_baseline_reports_only_new_findings(tmp_path):
    repo = tmp_path / "r"
    write(repo, "old.sh", f"claude -p a {FLAG}\n")
    base = tmp_path / "base.json"
    assert cli_run(repo, "--write-baseline", str(base))[0] == 1
    data = json.loads(base.read_text())
    assert data["format"] == "open-agent-security-baseline" and len(data["findings"]) == 1
    assert cli_run(repo, "--baseline", str(base))[0] == 0
    write(repo, "new.sh", f"claude -p b {FLAG}\n")
    code, out, _ = cli_run(repo, "--baseline", str(base), "--json")
    r = json.loads(out)
    assert code == 1 and [f["file"] for f in r["findings"]] == ["new.sh"]
    hidden = r["suppressed_findings"][0]
    assert hidden["suppression"]["kind"] == "external" and hidden["suppression"]["justification"].startswith("in baseline")
    assert any("baseline" in n and "1 finding" in n for n in r["notes"])
    # rewriting keeps the baselined finding and adds the new one
    assert cli_run(repo, "--baseline", str(base), "--write-baseline", str(tmp_path / "b2.json"))[0] == 1
    assert len(json.loads((tmp_path / "b2.json").read_text())["findings"]) == 2


def test_baseline_ids_match_sarif_fingerprints(tmp_path):
    repo = tmp_path / "r"
    write(repo, "old.sh", f"claude -p a {FLAG}\n")
    cli_run(repo, "--write-baseline", str(tmp_path / "b.json"), "--sarif", str(tmp_path / "o.sarif"))
    fp = json.loads((tmp_path / "o.sarif").read_text())["runs"][0]["results"][0]["partialFingerprints"]
    assert json.loads((tmp_path / "b.json").read_text())["findings"][0]["id"] == fp["openAgentSecurity/v1"]


def test_baseline_never_hides_an_incomplete_scan(tmp_path):
    repo = tmp_path / "r"
    write(repo, ".mcp.json", "{not json")
    cli_run(repo, "--write-baseline", str(tmp_path / "b.json"))
    assert cli_run(repo, "--baseline", str(tmp_path / "b.json"))[0] == 1


@pytest.mark.parametrize("text", [
    "", "[]", "{}", "nan", '{"format": "open-agent-security-baseline", "version": 2, "findings": []}',
    '{"format": "open-agent-security-baseline", "version": 1, "findings": [{"id": "xyz"}]}',
    '{"format": "open-agent-security-baseline", "version": 1, "findings": [], "extra": 1}',
    '{"format": "open-agent-security-baseline", "version": 1, "findings": [{"id": "' + "a" * 32 + '", "x": 1}]}',
    '{"format": "open-agent-security-baseline", "version": 1, "findings": [' + "[" * 100_000 + "]" * 100_000 + "]}",
])
def test_malformed_baseline_exits_2(tmp_path, text):
    repo = tmp_path / "r"
    write(repo, "a.sh", "echo\n")
    write(tmp_path, "b.json", text)
    code, _, err = cli_run(repo, "--baseline", str(tmp_path / "b.json"))
    assert code == 2 and "baseline" in err


def test_large_baseline_is_fast(tmp_path):
    rows = [{"id": f"{i:032x}", "rule": "AP01", "file": "x"} for i in range(50_000)]
    write(tmp_path, "b.json", json.dumps({"format": "open-agent-security-baseline", "version": 1, "findings": rows}))
    write(tmp_path / "r", "a.sh", "echo\n")
    assert fast(lambda: cli_run(tmp_path / "r", "--baseline", str(tmp_path / "b.json"))[0]) == 0


def test_config_baseline_is_inside_the_folder(tmp_path):
    write(tmp_path, "old.sh", f"claude -p a {FLAG}\n")
    cli_run(tmp_path, "--write-baseline", str(tmp_path / "base.json"))
    config(tmp_path, {"baseline": "base.json"})
    assert cli_run(tmp_path)[0] == 0
    for bad in ("../base.json", "/etc/passwd", "*.json", "a\\b"):
        config(tmp_path, {"baseline": bad})
        assert cli_run(tmp_path)[0] == 2, bad


def test_config_ignore_entry_expires(tmp_path):
    write(tmp_path, "a.sh", f"claude -p a {FLAG}\n")
    config(tmp_path, {"ignore": [{"path": "a.sh", "expires": "2027-01-31"}]})
    assert cli_run(tmp_path, "--today", "2026-11-01")[0] == 0
    code, out, _ = cli_run(tmp_path, "--today", "2027-01-15")
    assert code == 0 and "expire within 30 days" in out
    code, out, _ = cli_run(tmp_path, "--today", "2027-01-31")
    assert code == 1 and "expired and no longer suppress" in out and "'a.sh'" in out


def test_config_ignore_expiry_must_be_a_date(tmp_path):
    write(tmp_path, "a.sh", "echo\n")
    for bad in ("2027-02-30", "soon", 5):
        config(tmp_path, {"ignore": [{"path": "a.sh", "expires": bad}]})
        assert cli_run(tmp_path)[0] == 2, bad
    write(tmp_path, CONFIG, '[[ignore]]\npath = "a.sh"\nexpires = 2027-01-31\n')
    assert cli_run(tmp_path, "--today", "2026-01-01")[0] == 0


def test_ignore_file_entry_expires(tmp_path):
    write(tmp_path, "a.sh", f"claude -p a {FLAG}\n")
    write(tmp_path, IGNORE_FILE, "a.sh   # expires: 2027-01-31\n")
    assert cli_run(tmp_path, "--today", "2026-12-01")[0] == 0
    assert cli_run(tmp_path, "--today", "2027-02-01")[0] == 1
    write(tmp_path, IGNORE_FILE, "a.sh   # expires: next week\n")
    code, out, _ = cli_run(tmp_path)
    assert code == 1 and "treated as expired" in out


def test_today_must_be_a_date(tmp_path):
    with pytest.raises(SystemExit):
        cli_run(tmp_path, "--today", "tomorrow")


def test_merge_rolls_up_reports(tmp_path):
    for name, text in (("a", f"claude -p a {FLAG}\n"), ("b", "echo\n")):
        write(tmp_path / name, "x.sh", text)
        cli_run(tmp_path / name, "--output", f"json={tmp_path / (name + '.json')}")
    code, out, _ = merge(str(tmp_path / "a.json"), str(tmp_path / "b.json"), "--label", "=api",
                         "--csv", str(tmp_path / "s.csv"), "--markdown", str(tmp_path / "s.md"))
    m = json.loads(out)
    assert code == 0 and [r["repo"] for r in m["repos"]] == ["=api", "b"]
    assert [r["verdict"] for r in m["repos"]] == ["findings", "clean"]
    assert m["totals"]["by_rule"] == {"AP01": 1} and m["totals"]["repos_by_rule"] == {"AP01": 1}
    assert m["findings"][0]["repo"] == "=api"
    csv_text = (tmp_path / "s.csv").read_text()
    assert "'=api" in csv_text and "TOTAL" in csv_text
    md = (tmp_path / "s.md").read_text()
    assert md.count("\n|") == 5 and "=api" in md  # header, rule, two repositories and the total


@pytest.mark.parametrize("text", ["", "[]", '{"scanner": "open-agent-security"}', "{" * 50_000,
                                  json.dumps({"schema": "x", "scanner": "open-agent-security"})])
def test_merge_rejects_what_is_not_a_report(tmp_path, text):
    write(tmp_path, "r.json", text)
    code, _, err = merge(str(tmp_path / "r.json"))
    assert code == 2 and "merge" in err


def test_merge_rejects_a_tampered_finding(tmp_path):
    write(tmp_path / "a", "x.sh", f"claude -p a {FLAG}\n")
    r = report(tmp_path / "a")
    r["findings"][0]["severity"] = "catastrophic"
    write(tmp_path, "r.json", json.dumps(r))
    assert merge(str(tmp_path / "r.json"))[0] == 2
