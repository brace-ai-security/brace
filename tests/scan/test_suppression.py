"""Every suppression is reported: ignore entries, inline marks and rules turned off."""
import json

import pytest
from support import (AGENT, EVIL, TOKEN, UNPINNED, all_outputs, cli_run, config, found, noise, report, result, scan,
                     six_servers, write)

from open_agent_security import engine
from open_agent_security.ignore import IGNORE_FILE
from open_agent_security.report import sarif as sarif_module


@pytest.mark.parametrize("hide", ["mark", "ignore-file", "rule-off"])
def test_suppressed_findings_do_not_use_up_the_cap(tmp_path, hide):
    note = noise(" open-agent-security: ignore" if hide == "mark" else "")
    write(tmp_path, ".mcp.json", json.dumps({"_note": note, "mcpServers": {"evil": EVIL}}, indent=2) + "\n")
    if hide == "ignore-file":
        write(tmp_path, IGNORE_FILE, "AP01 .mcp.json\n")
    if hide == "rule-off":
        config(tmp_path, {"rules": {"AP01": "off"}})
    rules = {r for r, _ in found(tmp_path)}
    assert {"AP04", "AP05"} <= rules and "AP01" not in rules
    assert scan(tmp_path)[0] == 1


def test_ignore_file_star_is_reported(tmp_path):
    root = tmp_path / "r"
    six_servers(root)
    write(root, IGNORE_FILE, "*\n")
    for out in all_outputs(root):
        assert f"{IGNORE_FILE}: 1 entry" in out and "1 file not scanned because of ignore entries" in out


def test_rule_scoped_ignore_entry_is_reported_in_text(tmp_path):
    root = tmp_path / "r"
    six_servers(root)
    write(root, IGNORE_FILE, "AP04 .mcp.json\n")
    for out in all_outputs(root):
        assert "6 findings suppressed" in out


def test_config_path_ignores_count_skipped_files(tmp_path):
    six_servers(tmp_path)
    write(tmp_path, ".github/workflows/a.yml", "on: push\njobs: {a: {steps: [{run: claude -p x --dangerously-skip-permissions}]}}\n")
    write(tmp_path, ".github/workflows/b.yml", "on: push\n")
    config(tmp_path, {"ignore": [{"path": ".github/"}, {"path": ".mcp.json"}]})
    notes = report(tmp_path)["notes"]
    assert any("0 findings suppressed; 1 file and 1 folder not scanned because of ignore entries" in n for n in notes)


def test_inline_marks_are_reported(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions  # open-agent-security: ignore\n")
    notes = report(tmp_path)["notes"]
    assert any("inline ignore marks: 1 finding; 1 finding suppressed" in n for n in notes)


# Suppressed findings are listed in SARIF and JSON, with how each was suppressed.

RUN_SH = "claude --dangerously-skip-permissions\n"


def sarif_of(root, *args):
    code, _, _ = cli_run(root, "--fail-on", "none", "--sarif", str(root.parent / "out.sarif"), *args)
    return json.loads((root.parent / "out.sarif").read_text(encoding="utf-8"))["runs"][0]


@pytest.mark.parametrize("how, kind, justification, where", [
    ("mark", "inSource", "inline 'open-agent-security: ignore' mark on line 1", ("run.sh", 1)),
    ("ignore-file-rule", "external", f"{IGNORE_FILE} entry 'AP01 run.sh'", (IGNORE_FILE, 2)),
    ("config-reason", "external", "reviewed: test fixture", None),
    ("config", "external", "config ignore entry 'run.sh' in .open-agent-security.toml", None),
    ("rule-off", "external", "rule AP01 turned off in .open-agent-security.toml", None),
])
def test_each_suppression_is_a_sarif_and_json_suppressed_result(tmp_path, how, kind, justification, where):
    root = tmp_path / "r"
    write(root, "run.sh", RUN_SH.replace("\n", "  # open-agent-security: ignore\n") if how == "mark" else RUN_SH)
    if how == "ignore-file-rule":
        write(root, IGNORE_FILE, "# reviewed\nAP01 run.sh\n")
    if how == "config-reason":
        config(root, {"ignore": [{"path": "run.sh", "rules": ["AP01"], "reason": "reviewed: test fixture"}]})
    if how == "config":
        config(root, {"ignore": [{"path": "run.sh", "rules": ["AP01"]}]})
    if how == "rule-off":
        config(root, {"rules": {"AP01": "off"}})
    run = sarif_of(root, "--sarif-suppressed")
    [res] = [r for r in run["results"] if r["ruleId"] == "AP01"]
    [sup] = res["suppressions"]
    assert (sup["kind"], sup["status"], sup["justification"]) == (kind, "accepted", justification)
    loc = sup.get("location", {}).get("physicalLocation")
    assert ((loc["artifactLocation"]["uri"], loc["region"]["startLine"]) if loc else None) == where
    assert res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "run.sh"
    assert "AP01" in {r["id"] for r in run["tool"]["driver"]["rules"]}
    data = report(root)
    assert data["findings"] == [] and data["suppressed"] == 1
    [listed] = data["suppressed_findings"]
    assert listed["rule"] == "AP01" and listed["id"] == res["partialFingerprints"]["openAgentSecurity/v1"]
    assert listed["suppression"]["kind"] == kind and listed["suppression"]["justification"] == justification
    assert (listed["suppression"]["file"], listed["suppression"]["line"]) == (where or (None, None))


def test_rule_off_lists_findings_of_a_check_with_no_other_rule(tmp_path):
    """AP10's check emits nothing else: it still runs, so its findings are listed as suppressed."""
    write(tmp_path, ".mcp.json", UNPINNED)
    write(tmp_path, "Dockerfile", "FROM ubuntu:latest\n")
    config(tmp_path, {"rules": {"AP10": "off"}})
    data = report(tmp_path)
    assert [f["rule"] for f in data["findings"]] == ["AP04"]
    assert [(f["rule"], f["severity"], f["suppression"]["justification"]) for f in data["suppressed_findings"]] == \
        [("AP10", "low", "rule AP10 turned off in .open-agent-security.toml")]


def test_suppressed_findings_leave_verdict_exit_code_and_headline_alone(tmp_path):
    clean, marked = tmp_path / "clean", tmp_path / "marked"
    write(clean, ".mcp.json", AGENT)
    write(marked, ".mcp.json", AGENT)
    write(marked, "run.sh", RUN_SH.replace("\n", "  # open-agent-security: ignore\n"))
    code, text = scan(marked, "--fail-on", "low")
    assert code == scan(clean, "--fail-on", "low")[0] == 0
    assert text.splitlines()[:2] == scan(clean, "--fail-on", "low")[1].splitlines()[:2]
    assert result(marked).verdict == "clean" and result(marked).findings == []
    gitlab, junit = tmp_path / "g.json", tmp_path / "j.xml"
    cli_run(marked, "--fail-on", "none", "--output", f"gitlab-sast={gitlab}", "--output", f"junit={junit}")
    assert json.loads(gitlab.read_text())["vulnerabilities"] == [] and "<failure" not in junit.read_text()


def test_an_ignored_path_is_not_read_so_lists_nothing(tmp_path):
    """An entry for every rule skips the file unread: nothing was found, so nothing is listed."""
    write(tmp_path, "run.sh", RUN_SH)
    write(tmp_path, IGNORE_FILE, "run.sh\n")
    data = report(tmp_path)
    assert data["suppressed_findings"] == [] and data["suppressed"] == 0
    assert any("1 file not scanned because of ignore entries" in n for n in data["notes"])


def test_secrets_in_suppressed_findings_and_justifications_are_redacted(tmp_path):
    root = tmp_path / "r"
    write(root, ".mcp.json", json.dumps({"mcpServers": {"evil": EVIL}}, indent=2) + "\n")
    write(root, IGNORE_FILE, f"AP05 .mcp.json # {TOKEN}\n")
    config(root, {"ignore": [{"path": ".mcp.json", "rules": ["AP04"], "reason": f"token {TOKEN} is a fixture"}]})
    sarif, md, gitlab, junit = (tmp_path / n for n in ("o.sarif", "o.md", "o.json", "o.xml"))
    code, out, err = cli_run(root, "--fail-on", "none", "--sarif", str(sarif), "--sarif-suppressed", "--markdown", str(md),
                             "--output", f"gitlab-sast={gitlab}", "--output", f"junit={junit}")
    data = report(root)
    assert len(data["suppressed_findings"]) == 2
    assert any("<redacted>" in f["detail"] for f in data["suppressed_findings"])
    assert "<redacted>" in sarif.read_text()
    assert any(f["suppression"]["justification"] == "token <redacted> is a fixture" for f in data["suppressed_findings"])
    for text in (out, err, json.dumps(data), *(p.read_text() for p in (sarif, md, gitlab, junit))):
        assert TOKEN not in text and TOKEN[:12] not in text


def test_suppressed_ids_equal_unsuppressed_ids(tmp_path):
    """Removing a suppression must not make a "new" alert: same fingerprint either way."""
    plain, hidden = tmp_path / "plain", tmp_path / "hidden"
    for root in (plain, hidden):
        six_servers(root)
        write(root, "run.sh", RUN_SH * 2)
    write(hidden, IGNORE_FILE, "AP04 .mcp.json\n")
    write(hidden, "run.sh", RUN_SH + RUN_SH.replace("\n", "  # open-agent-security: ignore\n"))
    ids = {f["id"]: f for f in report(plain)["findings"]}
    data = report(hidden)
    assert len(data["suppressed_findings"]) == 7 and len(data["findings"]) == 1
    assert {f["id"] for f in data["findings"] + data["suppressed_findings"]} == set(ids)
    sarif = {r["partialFingerprints"]["openAgentSecurity/v1"] for r in sarif_of(hidden, "--sarif-suppressed")["results"]}
    assert sarif == set(ids)


def test_suppressed_findings_are_capped_and_counted(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "MAX_SUPPRESSED", 5)
    write(tmp_path, "run.sh", "".join(f"claude {i} --dangerously-skip-permissions\n" for i in range(9)))
    config(tmp_path, {"rules": {"AP01": "off"}})
    data = report(tmp_path)
    assert len(data["suppressed_findings"]) == 5 and data["suppressed"] == 9
    assert any("more than 5 findings suppressed; only the first 5 are listed in SARIF and JSON" in n
               for n in data["notes"])
    assert data["incomplete"] is False


def test_sarif_cap_lists_reported_results_before_suppressed_ones(tmp_path, monkeypatch):
    monkeypatch.setattr(sarif_module, "MAX_RESULTS", 3)
    write(tmp_path, "run.sh", "".join(f"claude {i} --dangerously-skip-permissions\n" for i in range(4)))
    write(tmp_path, "b.sh", "".join(f"claude {i} --dangerously-skip-permissions  # open-agent-security: ignore\n"
                                    for i in range(4)))
    run = sarif_of(tmp_path, "--sarif-suppressed")
    assert [("suppressions" in r) for r in run["results"]] == [False, False, False]
    capped = [n for n in run["invocations"][0]["toolExecutionNotifications"] if n["descriptor"]["id"] == "results-capped"]
    assert capped and capped[0]["message"]["text"] == (
        "SARIF lists at most 3 results: 1 reported result(s) are not listed; the JSON output lists every reported "
        "finding; 4 suppressed result(s) are not listed; the JSON output lists at most 5000 suppressed findings")


def test_sarif_cap_note_counts_only_suppressed_results_when_reported_ones_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(sarif_module, "MAX_RESULTS", 3)
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    write(tmp_path, "b.sh", "".join(f"claude {i} --dangerously-skip-permissions  # open-agent-security: ignore\n"
                                    for i in range(4)))
    run = sarif_of(tmp_path, "--sarif-suppressed")
    assert [("suppressions" in r) for r in run["results"]] == [False, True, True]
    [note] = [n for n in run["invocations"][0]["toolExecutionNotifications"] if n["descriptor"]["id"] == "results-capped"]
    assert note["message"]["text"] == ("SARIF lists at most 3 results: 2 suppressed result(s) are not listed; "
                                       "the JSON output lists at most 5000 suppressed findings")
    assert "reported" not in note["message"]["text"]


def notes_of(run, kind):
    return [n["message"]["text"] for n in run["invocations"][0]["toolExecutionNotifications"]
            if n["descriptor"]["id"] == kind]


def two_hidden_one_shown(root):
    write(root, "run.sh", "claude --dangerously-skip-permissions\n"
                          "claude -p x --dangerously-skip-permissions  # open-agent-security: ignore\n")
    write(root, IGNORE_FILE, "AP10 Dockerfile\n")
    write(root, ".mcp.json", json.dumps({"mcpServers": {"t": {"command": "npx", "args": ["tool-mcp@1.0.0"]}}}))
    write(root, "Dockerfile", "FROM ubuntu:latest\n")


def test_sarif_leaves_suppressed_results_out_by_default_with_a_note(tmp_path):
    root = tmp_path / "r"
    two_hidden_one_shown(root)
    run = sarif_of(root)
    data = report(root)
    hidden = len(data["suppressed_findings"])
    assert hidden >= 2 and not any("suppressions" in r for r in run["results"])
    assert [r["partialFingerprints"]["openAgentSecurity/v1"] for r in run["results"]] == \
        [f["id"] for f in data["findings"]]
    assert notes_of(run, "suppressed-results") == [
        f"{hidden} suppressed findings are not listed; see the JSON output or use --sarif-suppressed"]
    assert run["invocations"][0]["properties"]["suppressed"] == data["suppressed"]


@pytest.mark.parametrize("how", ["flag", "config", "config-and-flag"])
def test_sarif_suppressed_lists_them_with_suppressions(tmp_path, how):
    root = tmp_path / "r"
    two_hidden_one_shown(root)
    default = sarif_of(root)
    if how != "flag":
        config(root, {"sarif-suppressed": True})
    run = sarif_of(root, *(["--sarif-suppressed"] if how != "config" else []))
    data = report(root)
    shown = [r for r in run["results"] if "suppressions" not in r]
    hidden = [r for r in run["results"] if "suppressions" in r]
    assert [r["partialFingerprints"]["openAgentSecurity/v1"] for r in hidden] == \
        [f["id"] for f in data["suppressed_findings"]]
    assert all(r["suppressions"][0]["status"] == "accepted" for r in hidden)
    # Reported results and their fingerprints do not change with the option.
    assert shown == default["results"]
    assert notes_of(run, "suppressed-results") == []
    assert run["invocations"][0]["properties"]["suppressed"] == default["invocations"][0]["properties"]["suppressed"]


def test_command_line_overrides_the_sarif_suppressed_config_key(tmp_path):
    root = tmp_path / "r"
    two_hidden_one_shown(root)
    config(root, {"sarif-suppressed": True})
    assert any("suppressions" in r for r in sarif_of(root)["results"])
    run = sarif_of(root, "--no-sarif-suppressed")
    assert not any("suppressions" in r for r in run["results"]) and notes_of(run, "suppressed-results")


def test_json_lists_suppressed_findings_whatever_the_sarif_option(tmp_path):
    root = tmp_path / "r"
    two_hidden_one_shown(root)
    without = report(root)
    config(root, {"sarif-suppressed": True})
    with_key = report(root)
    for key in ("findings", "suppressed_findings", "suppressed"):
        assert with_key[key] == without[key]
    assert len(without["suppressed_findings"]) >= 2
