"""Output formats: text, JSON, SARIF, Markdown and GitHub step outputs."""
import json
import os
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from support import FLAG, cli_run, mcp, report, run, scan, write

from open_agent_security.catalog import RULES
from open_agent_security.engine import assign_ids
from open_agent_security.model import Finding, Report
from open_agent_security.report import BUILTIN, ReportOptions
from open_agent_security.report.markdown import Markdown

BAD = "bad\udcff.sh"  # a file name with the byte 0xFF, as os.walk returns it on Linux


def test_sarif_and_markdown(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    sf, md = tmp_path / "r.sarif", tmp_path / "s.md"
    run(tmp_path, sarif_path=str(sf), md_path=str(md))
    res = json.loads(sf.read_text())["runs"][0]["results"]
    assert res[0]["ruleId"] == "AP01" and res[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 1
    assert "permission checks turned off" in md.read_text()


def test_github_output(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    gh = tmp_path / "gh_out"
    run(tmp_path, github_output=str(gh))
    assert gh.read_text() == "findings=1\nincomplete=false\n"


def test_tilde_repo_path_is_kept_in_sarif(tmp_path):
    write(tmp_path, "~drafts/run.sh", "claude --dangerously-skip-permissions\n")
    sf = tmp_path / "r.sarif"
    run(tmp_path, sarif_path=str(sf))
    assert len(json.loads(sf.read_text())["runs"][0]["results"]) == 1


def test_markdown_summary_is_capped():
    findings = [Finding("AP01", "d/" + "x" * 280 + f"{i}.sh", i, "detail", severity="high") for i in range(6000)]
    rules = (replace(RULES[0], title="T" * 80, fix="F" * 300), *RULES[1:])  # the longest a row can be
    md = Markdown().render(Report(findings=findings, rules=rules, notes=["n" * 300] * 500), ReportOptions())
    assert len(md.encode()) < 900_000
    assert md.count("\n| high |") == 200 and "and 5800 more (see the SARIF or JSON output)" in md


def test_one_finding_is_singular(tmp_path):
    write(tmp_path, "run.sh", f"claude -p hi {FLAG}\n")
    out = scan(tmp_path, "--fail-on", "none")[1]
    assert "(1 finding)." in out and "(1 findings)" not in out


def render_all(report: Report) -> dict[str, str]:
    return {r.name: r.render(report, ReportOptions()) for r in BUILTIN}


def test_a_path_that_is_not_utf8_is_written_by_every_reporter():
    [f] = assign_ids([Finding("AP01", "d/" + BAD, 1, FLAG, severity="high")])
    out = render_all(Report(findings=[f], rules=RULES))
    for text in out.values():
        text.encode("utf-8")  # no lone surrogate reaches an output
    sarif = json.loads(out["sarif"])["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert sarif["artifactLocation"]["uri"] == "d/bad%FF.sh"
    assert json.loads(out["json"])["findings"][0]["file"] == "d/bad\\xff.sh"
    assert json.loads(out["gitlab-sast"])["vulnerabilities"][0]["location"]["file"] == "d/bad\\xff.sh"
    assert ET.fromstring(out["junit"].split("\n", 1)[1]).find(".//testcase").get("file") == "d/bad\\xff.sh"
    assert "d/bad.sh:1" in out["text"]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file names")
def test_a_real_file_name_that_is_not_utf8_is_scanned(tmp_path):
    try:
        fd = os.open(os.fsencode(str(tmp_path / BAD)), os.O_WRONLY | os.O_CREAT, 0o644)
    except OSError:
        pytest.skip("this file system refuses names that are not UTF-8")
    with os.fdopen(fd, "w") as fh:
        fh.write(f"claude {FLAG}\n")
    code, out, err = cli_run(tmp_path, "--fail-on", "none", "--sarif", str(tmp_path.parent / "o.sarif"))
    assert code == 0 and "bad" in out
    assert "bad%FF.sh" in (tmp_path.parent / "o.sarif").read_text(encoding="utf-8")


def test_machine_outputs_keep_the_exact_long_path(tmp_path):
    rel = "/".join(["x" * 100] * 4) + "/run\tme.sh"  # longer than a shown path, with a control character
    write(tmp_path, rel, f"claude {FLAG}\n")
    sf = tmp_path.parent / "o.sarif"
    code, out, _ = cli_run(tmp_path, "--fail-on", "none", "--sarif", str(sf))
    uri = json.loads(sf.read_text())["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]
    assert uri["uri"] == rel.replace("\t", "%09") and report(tmp_path)["findings"][0]["file"] == rel
    assert "…" in out and rel not in out  # people see the cut path


def test_skip_notes_carry_the_prefix_findings_carry(tmp_path):
    sub = tmp_path / "sub"
    write(sub, ".mcp.json", "{}")
    os.symlink("/etc/hosts", sub / "x.sh")
    code, out, _ = cli_run(sub, "--fail-on", "none", cwd=tmp_path)
    assert "sub/x.sh" in out


def test_findings_that_share_a_rule_and_line_have_distinct_names(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {f"s{i}": {"command": "npx", "args": [f"p{i}"]}
                                                             for i in range(3)}}))
    for name in ("junit", "gitlab-sast"):
        target = tmp_path.parent / name
        cli_run(tmp_path, "--fail-on", "none", "--output", f"{name}={target}")
        text = target.read_text()
        if name == "junit":
            names = [c.get("name") for c in ET.fromstring(text.split("\n", 1)[1]).iter("testcase")
                     if c.get("classname").endswith("AP04")]
        else:
            names = [(v["name"], json.dumps(v["location"])) for v in json.loads(text)["vulnerabilities"]]
        assert len(names) == 3 and len(set(names)) == 3, name
