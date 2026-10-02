"""Self-test for challenge.py apply. Run: pytest skills/brace-review/scripts/test_challenge.py"""
import sys
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
