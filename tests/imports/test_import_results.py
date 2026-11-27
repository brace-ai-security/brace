import json
import shutil
from pathlib import Path

import pytest
import yaml

from conftest import TOOL_DIR, brace

from brace_tools.imports import results as ri

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "results"


@pytest.fixture
def rec(tmp_path):
    """A fresh .brace/ made from the real templates (with comments)."""
    assert brace.main(["init", "--dir", str(tmp_path)]) == 0
    return tmp_path


def load(root):
    return yaml.safe_load((root / ".brace" / "record.yaml").read_text())["items"]


def run(root, tool, name, *extra):
    src = FIX / name
    dst = root / "results" / name
    dst.parent.mkdir(exist_ok=True)
    shutil.copy(src, dst)
    return brace.main(["import-results", tool, str(dst), "--dir", str(root), *extra])


@pytest.mark.parametrize("tool,name,passed,failed,other,version,date,cat", [
    ("garak", "garak.report.jsonl", 315, 13, 1, "0.13.2", "2026-11-18", "prompt_injection"),
    ("promptfoo", "promptfoo.results.json", 3, 1, 1, "0.121.4", "2026-11-19", "excessive_agency"),
    ("pyrit", "pyrit.attack_results.json", 1, 1, 1, "unknown", "2026-11-20", "prompt_injection"),
    ("pyrit", "pyrit.scores.jsonl", 1, 1, 1, "unknown", "2026-11-20", "pii_leakage"),
    ("inspect", "inspect.log.json", 3, 1, 0, "0.3.142", "2026-11-21", "prompt_injection"),
])
def test_parsers(tool, name, passed, failed, other, version, date, cat):
    s, digest = ri.summarize(tool, FIX / name)
    assert (s.passed, s.failed, s.other) == (passed, failed, other)
    assert s.version == version and s.run_date == date
    assert cat in s.categories
    assert len(digest) == 64


def test_inspect_invert():
    s, _ = ri.summarize("inspect", FIX / "inspect.log.json", invert=True)
    assert (s.passed, s.failed) == (1, 3)


@pytest.mark.parametrize("name,cat", [
    ("promptinject.HijackHateHumans", "prompt_injection"),
    ("latentinjection.LatentJailbreak", "prompt_injection"),
    ("dan.Dan_11_0", "jailbreak"),
    ("web_injection.MarkdownImageExfil", "data_exfiltration"),
    ("data-exfil", "data_exfiltration"),
    ("excessive-agency", "excessive_agency"),
    ("shell-injection", "tool_misuse"),
    ("pii:direct", "pii_leakage"),
    ("indirect-prompt-injection", "prompt_injection"),
    ("CrescendoAttack", "jailbreak"),
    ("bola", "access_control"),
    ("agentic:memory-poisoning", "memory_poisoning"),
    ("harmful:hate", "harmful_content"),
    ("something-new", "other"),
])
def test_categorize(name, cat):
    assert ri.categorize(name) == cat


def test_suggestions_are_real_items():
    known = {i["id"] for i in json.loads((TOOL_DIR.parent.parent / "src/brace_tools/data/brace_items.json").read_text())}
    for items in ri.CATEGORY_ITEMS.values():
        assert set(items) <= known


def test_no_item_writes_nothing(rec, capsys):
    before = (rec / ".brace" / "record.yaml").read_text()
    assert run(rec, "garak", "garak.report.jsonl") == 0
    assert (rec / ".brace" / "record.yaml").read_text() == before
    assert "Suggested items: R02" in capsys.readouterr().out


def test_failing_run_marks_not_reviewed_as_gap_and_keeps_comments(rec):
    assert run(rec, "garak", "garak.report.jsonl", "--item", "R02,B05") == 1
    text = (rec / ".brace" / "record.yaml").read_text()
    assert "# BRACE evidence record" in text and "# B05 · Blocker" in text
    items = load(rec)
    for item in ("R02", "B05"):
        assert items[item]["outcome"] == "gap"
        ev = items[item]["evidence"][-1]
        assert ev["link"] == "results/garak.report.jsonl"
        assert str(ev["date"]) == "2026-11-18"
        assert "garak 0.13.2" in ev["note"] and "13 failed" in ev["note"] and "sha256:" in ev["note"]
    assert items["R01"]["outcome"] == "not_reviewed"


def test_clean_run_never_sets_pass(rec):
    clean = rec / "clean.jsonl"
    clean.write_text("\n".join(json.dumps(r) for r in [
        {"entry_type": "init", "garak_version": "0.13.2", "start_time": "2026-11-18T10:00:00"},
        {"entry_type": "eval", "probe": "promptinject.HijackKillHumans", "detector": "d", "passed": 10, "fails": 0,
         "total_evaluated": 10},
    ]))
    code = brace.main(["import-results", "garak", str(rec / "clean.jsonl"), "--dir", str(rec), "--item", "R02"])
    assert code == 0
    item = load(rec)["R02"]
    assert item["outcome"] == "not_reviewed"
    assert "10 passed, 0 failed" in item["evidence"][0]["note"]


def test_existing_pass_is_not_changed_but_warned(rec, capsys):
    path = rec / ".brace" / "record.yaml"
    path.write_text(path.read_text().replace("  R02:\n    outcome: not_reviewed", "  R02:\n    outcome: pass", 1))
    assert run(rec, "promptfoo", "promptfoo.results.json", "--item", "R02") == 1
    assert load(rec)["R02"]["outcome"] == "pass"
    assert "R02 is marked pass" in capsys.readouterr().err


def test_same_file_twice_is_skipped(rec):
    run(rec, "inspect", "inspect.log.json", "--item", "R02")
    run(rec, "inspect", "inspect.log.json", "--item", "R02")
    assert len(load(rec)["R02"]["evidence"]) == 1


def test_appends_to_existing_block_list(rec):
    p = rec / ".brace" / "record.yaml"
    data = yaml.safe_load(p.read_text())
    data["items"]["R03"]["evidence"] = [{"link": "https://ci.example/1", "date": "2026-10-01"}]
    p.write_text(yaml.safe_dump(data, sort_keys=False))  # "- link" at the same indent as the key
    run(rec, "pyrit", "pyrit.scores.jsonl", "--item", "R03")
    ev = load(rec)["R03"]["evidence"]
    assert [e["link"] for e in ev] == ["https://ci.example/1", "results/pyrit.scores.jsonl"]


def test_record_still_checks(rec):
    run(rec, "garak", "garak.report.jsonl", "--item", "R02", "--link", "https://ci.example/artifacts/42")
    assert load(rec)["R02"]["evidence"][0]["link"] == "https://ci.example/artifacts/42"
    assert brace.main(["check", "--dir", str(rec), "--approvals", "off"]) == 1  # not_reviewed items remain


def test_dry_run(rec):
    before = (rec / ".brace" / "record.yaml").read_text()
    run(rec, "garak", "garak.report.jsonl", "--item", "R02", "--dry-run")
    assert (rec / ".brace" / "record.yaml").read_text() == before


def test_unknown_item_rejected(rec):
    assert run(rec, "garak", "garak.report.jsonl", "--item", "Z99") == 2


# ---- untrusted input -------------------------------------------------------

def test_size_limit(tmp_path):
    f = tmp_path / "big.json"
    f.write_text(" " * 2048)
    with pytest.raises(ri.ImportProblem, match="over the 1,024-byte limit"):
        ri.summarize("promptfoo", f, max_bytes=1024)


def test_zip_rejected(tmp_path):
    f = tmp_path / "log.eval"
    f.write_bytes(b"PK\x03\x04rest")
    with pytest.raises(ri.ImportProblem, match="inspect log convert"):
        ri.summarize("inspect", f)


def test_deep_nesting_rejected(tmp_path):
    f = tmp_path / "deep.json"
    f.write_text("[" * 200000 + "]" * 200000)
    with pytest.raises(ri.ImportProblem):
        ri.summarize("pyrit", f)


def test_wrong_tool_message(tmp_path):
    with pytest.raises(ri.ImportProblem, match="one JSON object per line"):
        ri.summarize("garak", FIX / "inspect.log.json")
    with pytest.raises(ri.ImportProblem, match="promptfoo"):
        ri.summarize("promptfoo", FIX / "inspect.log.json")


def test_hostile_strings_are_cleaned(rec, tmp_path):
    evil = 'promptinject.X\n\x1b[31m"; rm -rf / ‮' + "A" * 500
    f = rec / "evil.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in [
        {"entry_type": "init", "garak_version": "1.0\n  outcome: pass", "start_time": "2026-11-18"},
        {"entry_type": "eval", "probe": evil, "detector": "d", "passed": 1, "fails": 1, "total_evaluated": 2},
    ]))
    assert brace.main(["import-results", "garak", str(f), "--dir", str(rec), "--item", "R02"]) == 1
    item = load(rec)["R02"]
    assert item["outcome"] == "gap"
    note = item["evidence"][0]["note"]
    assert "\n" not in note and "\x1b" not in note and "‮" not in note
    assert set(item) == {"outcome", "lead", "shares", "evidence"}
