"""Self-test for challenge.py apply. Run: pytest skills/brace-review/scripts/test_challenge.py"""
import sys
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import challenge  # noqa: E402


def _doc():
    return {"findings": [{"item": "B02", "rating": "likely_pass",
                          "checks": [{"id": "B02.1", "met": "yes"}]}]}


def _verdict(violates):
    return {"B02": {"verdict": "failed", "violates": violates, "note": "token reused",
                    "checks": [{"id": "B02.1", "result": "fails", "evidence": "app.py:2",
                                "quote": "token = REQUEST_TOKEN", "note": "reuses the caller's token"}]}}


def _apply(tmp_path, violates, existing=None):
    (tmp_path / "app.py").write_text("import os\ntoken = REQUEST_TOKEN\n")
    doc = _doc()
    if existing is not None:
        doc["findings"][0]["violates"] = existing
    changes, problems = challenge.apply(doc, _verdict(violates), tmp_path)
    assert not problems
    return doc["findings"][0]


def test_string_violates_stays_one_phrase(tmp_path):
    f = _apply(tmp_path, "a request for one task")
    assert f["rating"] == "gap"
    assert f["violates"] == ["a request for one task"]


def test_list_violates_merges_with_existing_string(tmp_path):
    f = _apply(tmp_path, ["a request for one task"], existing="scoped to one tenant")
    assert f["violates"] == ["scoped to one tenant", "a request for one task"]


def test_answer_rejects_paraphrased_violates(tmp_path):
    import json
    import subprocess
    doc = {"findings": [{"item": "B05", "rating": "needs_evidence", "summary": "TODO", "checks": []}]}
    f = tmp_path / "brace-findings.json"
    f.write_text(json.dumps(doc))
    base = [sys.executable, str(HERE / "answer.py"), str(f), "item", "B05", "--rating", "gap",
            "--summary", "Purchases skip the approval gate entirely", "--next", "gate browser clicks"]
    bad = subprocess.run(base + ["--violates", "Block them by default; every consequential action gated"],
                         capture_output=True, text=True)
    assert bad.returncode != 0 and "The requirement is:" in bad.stderr
    good = subprocess.run(base + ["--violates", "Block them by default in the execution path"],
                          capture_output=True, text=True)
    assert good.returncode == 0, good.stderr
    assert json.loads(f.read_text())["findings"][0]["violates"] == ["Block them by default in the execution path"]


def test_quote_pieces_from_two_files(tmp_path):
    from validate_findings import quote_found
    (tmp_path / "a.py").write_text("x = 1\nif not op.startswith(READ_PREFIXES):\n    deny()\n")
    (tmp_path / "b.yaml").write_text("read_prefixes:\n  - invoice.\n")
    ev = "a.py:2, b.yaml:2"
    assert quote_found(tmp_path, ev, "if not op.startswith(READ_PREFIXES):\n  - invoice.")
    assert quote_found(tmp_path, ev, "if not op.startswith(READ_PREFIXES): ... read_prefixes:")
    assert not quote_found(tmp_path, ev, "if not op.startswith(READ_PREFIXES):\nallow_everything()")


def test_make_challenges_na_only_for_g1_g2_without_hunt(tmp_path):
    table = {item: {"gate": gate, "title": "Peers", "requirement": "Verify peers",
                    "na_when": "No peer messages", "checks": [{"id": item + ".1"}]}
             for item, gate in (("E07", "G2"), ("B02", "G1"), ("C01", "G3"))}
    doc = {"findings": [{"item": item, "rating": "na_candidate", "checks": [],
                         "summary": "There are no peer messages here"} for item in table]}
    challenge.make(doc, table, tmp_path, tmp_path / "sheets")
    verdicts = json.loads((tmp_path / "sheets/verdicts.json").read_text())
    assert set(verdicts) == {"E07", "B02"}
    sheet = (tmp_path / "sheets/E07.md").read_text()
    assert "No peer messages" in sheet and "indirect paths" in sheet
    assert verdicts["E07"]["applicability"] == "TODO"


def test_na_present_failed_control_becomes_gap(tmp_path):
    (tmp_path / "app.py").write_text("import os\ntoken = REQUEST_TOKEN\n")
    doc = _doc()
    doc["findings"][0]["rating"] = "na_candidate"
    verdict = _verdict("a request for one task")
    verdict["B02"]["applicability"] = "present"
    changes, problems = challenge.apply(doc, verdict, tmp_path)
    assert changes and not problems
    assert doc["findings"][0]["rating"] == "gap"


def test_na_absence_requires_quote_and_search(tmp_path):
    (tmp_path / "app.py").write_text("tools = []\n")
    doc = _doc()
    doc["findings"][0]["rating"] = "na_candidate"
    v = {"verdict": "upheld", "applicability": "absent", "checks": [],
         "note": "Searched the harness and all tool registrations; no external tools exist"}
    _, problems = challenge.apply(doc, {"B02": v}, tmp_path)
    assert problems and "challenge" not in doc["findings"][0]
    v.update(evidence="app.py:1", quote="tools = []")
    _, problems = challenge.apply(doc, {"B02": v}, tmp_path)
    assert not problems
    f = doc["findings"][0]
    assert f["rating"] == "na_candidate" and f["challenge"]["applicability"] == "absent"


def test_na_uncertain_or_present_without_failure_needs_evidence(tmp_path):
    for applicability in ("unclear", "present"):
        doc = _doc()
        doc["findings"][0].update(rating="na_candidate", checks=[])
        _, problems = challenge.apply(doc, {"B02": {"verdict": "unclear", "applicability": applicability,
                                                   "checks": [], "note": "Exposure could not be ruled out"}}, tmp_path)
        assert not problems and doc["findings"][0]["rating"] == "needs_evidence"


def test_validator_rejects_unchallenged_na(tmp_path):
    from validate_findings import check_item
    meta = {"gate": "G2", "checks": [], "na_when": "No peer messages"}
    f = {"rating": "na_candidate", "checks": [], "red_flags_found": []}
    assert any("fresh challenge" in e for e in check_item("E07", f, meta, tmp_path))
