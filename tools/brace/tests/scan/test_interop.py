"""Interoperability: the JSON, SARIF and GitLab goldens against their schemas, JUnit structure,
fingerprints, taxonomy references, and choosing reporters with --output.

The SARIF 2.1.0 schema (OASIS, errata 01) and the GitLab SAST report schema 15.2.5 are kept in
tests/fixtures/schemas, copied from github.com/oasis-tcs/sarif-spec and
gitlab.com/gitlab-org/security-products/security-report-schemas, so these tests run offline.
"""
import json
import re
import xml.etree.ElementTree as ET

import pytest
from support import FLAG, ROOT, TOOL_DIR, EntryPoint, cli_run, mcp, report, write
from support import plugins  # noqa: F401  (a fixture)

from open_agent_security.catalog import RULES, TAXA, TAXONOMIES

jsonschema = pytest.importorskip("jsonschema")
GOLDEN = TOOL_DIR / "tests" / "fixtures" / "oas_golden"
SCHEMAS = TOOL_DIR / "tests" / "fixtures" / "schemas"
REPORT_SCHEMA = TOOL_DIR / "open_agent_security" / "report" / "schema" / "report-1.schema.json"


def validator(path, cls):
    schema = json.loads(path.read_text(encoding="utf-8"))
    cls.check_schema(schema)
    return cls(schema)


@pytest.mark.parametrize("golden", sorted(p for p in GOLDEN.glob("*.json") if not p.name.endswith(".gitlab.json")),
                         ids=lambda p: p.name)
def test_json_goldens_match_the_report_schema(golden):
    data = json.loads(golden.read_text(encoding="utf-8").split("\n", 1)[1])  # after the "exit N" line
    validator(REPORT_SCHEMA, jsonschema.Draft202012Validator).validate(data)
    assert data["schema"] == json.loads(REPORT_SCHEMA.read_text())["$id"]


@pytest.mark.parametrize("golden", sorted(GOLDEN.glob("*.sarif")), ids=lambda p: p.name)
def test_sarif_goldens_match_the_sarif_schema(golden):
    data = json.loads(golden.read_text(encoding="utf-8"))
    validator(SCHEMAS / "sarif-schema-2.1.0.json", jsonschema.Draft4Validator).validate(data)
    run = data["runs"][0]
    assert all(r["partialFingerprints"]["openAgentSecurity/v1"] for r in run["results"])
    assert all(r["locations"][0]["physicalLocation"]["artifactLocation"]["uriBaseId"] == "%SRCROOT%"
               for r in run["results"])
    assert {"incomplete", "suppressed"} <= set(run["invocations"][0]["properties"])


@pytest.mark.parametrize("golden", sorted(GOLDEN.glob("*.gitlab.json")), ids=lambda p: p.name)
def test_gitlab_goldens_match_the_gitlab_schema(golden):
    data = json.loads(golden.read_text(encoding="utf-8").replace('"TIME"', '"2026-01-01T00:00:00"'))
    validator(SCHEMAS / "gitlab-sast-report-format-15.2.5.json", jsonschema.Draft7Validator).validate(data)


@pytest.mark.parametrize("golden", sorted(GOLDEN.glob("*.junit.xml")), ids=lambda p: p.name)
def test_junit_goldens_are_well_formed(golden):
    root = ET.fromstring(golden.read_text(encoding="utf-8").split("\n", 1)[1])
    suite = root.find("testsuite")
    cases = suite.findall("testcase")
    assert root.tag == "testsuites" and int(suite.get("tests")) == len(cases)
    assert int(suite.get("failures")) == sum(c.find("failure") is not None for c in cases)
    assert int(suite.get("errors")) == sum(c.find("error") is not None for c in cases)


def test_the_corpus_reports_carry_the_same_findings():
    findings = json.loads((GOLDEN / "corpus.json").read_text().split("\n", 1)[1])["findings"]
    sarif = json.loads((GOLDEN / "corpus.sarif").read_text())["runs"][0]["results"]
    gitlab = json.loads((GOLDEN / "corpus.gitlab.json").read_text())["vulnerabilities"]
    ids = [f["id"] for f in findings if not f["host"]]
    assert [r["partialFingerprints"]["openAgentSecurity/v1"] for r in sarif if "suppressions" not in r] == ids
    assert [v["id"].replace("-", "") for v in gitlab] == ids
    assert len(set(ids)) == len(ids)
    hidden = json.loads((GOLDEN / "corpus.json").read_text().split("\n", 1)[1])["suppressed_findings"]
    # SARIF leaves suppressed findings out by default (--sarif-suppressed lists them); JSON keeps them.
    assert not any("suppressions" in r for r in sarif) and len(hidden) == 2


def test_fingerprints_do_not_change_when_lines_move(tmp_path):
    write(tmp_path, "run.sh", f"claude -p a {FLAG}\nclaude -p b {FLAG}\n")
    before = [f["id"] for f in report(tmp_path)["findings"]]
    write(tmp_path, "run.sh", f"# a comment\n\nclaude -p a {FLAG}\nclaude -p b {FLAG}\n")
    after = report(tmp_path)["findings"]
    assert [f["id"] for f in after] == before and [f["line"] for f in after] == [3, 4]
    assert len(set(before)) == 2  # the same detail twice: told apart by occurrence


def test_fingerprints_never_hash_a_raw_secret(tmp_path):
    import hashlib
    token = "ghp_" + "Zx9" * 12
    mcp(tmp_path, {"command": "node", "env": {"GH": token}})
    f = report(tmp_path)["findings"][0]
    raw = hashlib.sha256("\0".join((f["rule"], f["file"], f"s0: env.GH = {token}", "0")).encode()).hexdigest()[:32]
    assert f["id"] != raw and token not in json.dumps(f)


def mapping_rows(name: str, pattern: str) -> dict[str, tuple[str, str, list[str]]]:
    """ID -> (name, coverage, BRACE items in order) for each row of a mapping table."""
    out = {}
    for line in (ROOT / "mappings" / name).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.match(rf"\[?({pattern})", cells[0]) if len(cells) >= 4 else None
        if m:
            out[m.group(1)] = (cells[1], cells[2], re.findall(r"\b[A-Z]\d\d\b", cells[-2]))
    return out


def test_taxonomy_refs_agree_with_the_mappings():
    """A risk or technique relates to a rule when its first-listed BRACE item is one of the
    rule's checklist items: Direct or Partial for OWASP, Direct for ATLAS (see catalog.py)."""
    tables = {"owasp-asi": (mapping_rows("owasp-agentic-top-10.md", r"ASI\d\d"), {"Direct", "Partial"}),
              "owasp-mcp": (mapping_rows("owasp-mcp-top-10.md", r"MCP\d\d"), {"Direct", "Partial"}),
              "atlas": (mapping_rows("mitre-atlas.md", r"AML\.T\d{4}(?:\.\d{3})?"), {"Direct"})}
    for rule in RULES:
        for prefix, (rows, coverage) in tables.items():
            want = {f"{prefix}:{k}" for k, (_, cov, items) in rows.items()
                    if items and items[0] in rule.checklist and cov in coverage}
            assert {r for r in rule.refs if r.startswith(prefix + ":")} == want, (rule.id, prefix)
        for ref in rule.refs:
            prefix, _, entry = ref.partition(":")
            assert prefix in TAXONOMIES and ref in TAXA, ref
            if prefix in tables:
                assert TAXA[ref] == tables[prefix][0][entry][0], ref
    cwe = {r.id: sorted(x for x in r.refs if x.startswith("cwe:")) for r in RULES}
    assert cwe == {"AP01": [], "AP02": [], "AP03": [], "AP04": ["cwe:829"], "AP05": ["cwe:798"], "AP06": [],
                   "AP07": ["cwe:319"], "AP08": ["cwe:250"], "AP09": [], "AP10": ["cwe:829"],
                   "AP20": [], "AP21": [], "AP22": [], "AP23": ["cwe:494"]}


def test_taxonomy_editions_match_the_mappings():
    assert "data release [v2026.10]" in (ROOT / "mappings" / "mitre-atlas.md").read_text()
    assert TAXONOMIES["atlas"].version == "2026.10"
    assert "2025 edition" in (ROOT / "mappings" / "owasp-mcp-top-10.md").read_text()
    assert TAXONOMIES["owasp-mcp"].version == "2025"
    assert "for 2026" in (ROOT / "mappings" / "owasp-agentic-top-10.md").read_text()
    assert TAXONOMIES["owasp-asi"].version == "2026"


def test_output_writes_any_reporter_and_dash_is_stdout(tmp_path):
    write(tmp_path, "run.sh", f"claude -p a {FLAG}\n")
    junit, gl = tmp_path.parent / f"{tmp_path.name}.xml", tmp_path.parent / f"{tmp_path.name}.gl.json"
    code, out, err = cli_run(tmp_path, "--fail-on", "none", "--output", f"junit={junit}", "--output", f"gitlab-sast={gl}",
                             "--output", "sarif=-")
    assert code == 0 and err == "" and json.loads(out)["version"] == "2.1.0"
    assert "<failure" in junit.read_text() and json.loads(gl.read_text())["vulnerabilities"]


@pytest.mark.parametrize("args", [["--output", "nope=x"], ["--output", "json=-", "--output", "sarif=-"],
                                  ["--json", "--output", "sarif=-"]])
def test_bad_outputs_are_exit_2(tmp_path, args):
    code, out, err = cli_run(tmp_path, *args)
    assert code == 2 and out == "" and "open-agent-security:" in err


def test_output_needs_name_and_file(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        cli_run(tmp_path, "--output", "sarif")
    assert e.value.code == 2


def test_markdown_appends_and_sarif_replaces(tmp_path):
    md, sarif = tmp_path.parent / f"{tmp_path.name}.md", tmp_path.parent / f"{tmp_path.name}.sarif"
    md.write_text("before\n")
    sarif.write_text("old")
    cli_run(tmp_path, "--output", f"markdown={md}", "--output", f"sarif={sarif}")
    assert md.read_text().startswith("before\n### open-agent-security") and sarif.read_text().startswith("{")


class Csv:
    name = "csv"  # declares no media: the command line defuses it as text

    def render(self, report, opts):
        return "".join(f"{f.rule},{f.file},{f.line}\n" for f in report.findings) + "::warning::x\n"


def test_a_plugin_reporter_is_selectable_and_defused(tmp_path, plugins, monkeypatch):  # noqa: F811
    plugins["csv"] = EntryPoint("csv", lambda reg: reg.add_reporter(Csv()))
    write(tmp_path, "run.sh", f"claude -p a {FLAG}\n")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    code, out, _ = cli_run(tmp_path, "--plugin", "csv", "--fail-on", "none", "--output", "csv=-")
    assert code == 0 and out.startswith("AP01,run.sh,1\n") and "\n::warning" not in out


def test_round9_gitlab_findings_sharing_a_line_have_distinct_identifiers(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions --permission-mode bypassPermissions -p x\n")
    gl = tmp_path.parent / "gl.json"
    cli_run(tmp_path, "--fail-on", "none", "--output", f"gitlab-sast={gl}")
    vulns = json.loads(gl.read_text())["vulnerabilities"]
    assert len(vulns) == 2 and len({v["location"]["start_line"] for v in vulns}) == 1
    assert all(v["identifiers"][0]["value"] == "AP01" for v in vulns)
    assert len({json.dumps(v["identifiers"]) for v in vulns}) == 2
    validator(SCHEMAS / "gitlab-sast-report-format-15.2.5.json", jsonschema.Draft7Validator).validate(
        json.loads(gl.read_text()))


def test_suppressed_results_match_the_sarif_and_report_schemas(tmp_path):
    """Every kind of suppression, including rules turned off and config reasons, validates."""
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions  # open-agent-security: ignore\n")
    write(tmp_path, "Dockerfile", "FROM ubuntu:latest\n")
    mcp(tmp_path, {"command": "npx", "args": ["tool-mcp"], "env": {"K": "v"}})
    write(tmp_path, ".open-agent-security-ignore", "AP05 .mcp.json\n")
    write(tmp_path, ".open-agent-security.toml",
          'rules = {AP10 = "off"}\n[[ignore]]\npath = ".mcp.json"\nrules = ["AP04"]\nreason = "pinned upstream"\n')
    sarif = tmp_path.parent / f"{tmp_path.name}.sarif"
    cli_run(tmp_path, "--fail-on", "none", "--sarif", str(sarif))
    validator(SCHEMAS / "sarif-schema-2.1.0.json", jsonschema.Draft4Validator).validate(
        json.loads(sarif.read_text(encoding="utf-8")))
    cli_run(tmp_path, "--fail-on", "none", "--sarif", str(sarif), "--sarif-suppressed")
    data = json.loads(sarif.read_text(encoding="utf-8"))
    validator(SCHEMAS / "sarif-schema-2.1.0.json", jsonschema.Draft4Validator).validate(data)
    kinds = sorted(r["suppressions"][0]["kind"] for r in data["runs"][0]["results"] if "suppressions" in r)
    assert kinds[0] == "external" and "inSource" in kinds and len(kinds) >= 3
    out = report(tmp_path)
    validator(REPORT_SCHEMA, jsonschema.Draft202012Validator).validate(out)
    assert len(out["suppressed_findings"]) == len(kinds)
