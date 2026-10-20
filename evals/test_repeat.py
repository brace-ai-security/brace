"""Checks for eval isolation and retaining failures; never calls a model."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import repeat


def test_failed_cli_is_preserved_and_workspace_is_isolated(tmp_path, monkeypatch):
    def failed_call(model, cwd, prompt, log, timeout):
        assert (cwd / "agent").is_dir()
        assert (cwd / "skill/SKILL.md").is_file()
        assert not (cwd / "expected").exists()
        assert not (cwd / "results").exists()
        assert sys.executable in prompt
        log.write_text("model exited without findings")
        raise RuntimeError("CLI failed")
    monkeypatch.setattr(repeat, "call", failed_call)
    result = repeat.run_one("sol", "clinic-agent", 1, tmp_path, 1)
    saved = json.loads((tmp_path / "clinic-agent.sol.run-1/run.json").read_text())
    assert saved == result
    assert result["status"] == "error" and result["error"] == "CLI failed"


def test_fresh_challenger_sees_only_code_and_its_sheet(tmp_path, monkeypatch):
    calls = []
    real_validate = repeat.validator.validate
    validation_calls = []
    def validate(*args, **kwargs):
        validation_calls.append(1)
        return [] if len(validation_calls) == 1 else real_validate(*args, **kwargs)
    monkeypatch.setattr(repeat.validator, "validate", validate)
    def fake_call(model, cwd, prompt, log, timeout):
        calls.append(cwd)
        log.write_text("fake model response")
        if (cwd / "validation-errors.json").exists():
            return  # leave invalid findings visible to the final validator
        elif (cwd / "skill").exists():
            (cwd / "agent/brace-findings.json").write_text(json.dumps({"findings": [
                {"item": "E07", "rating": "na_candidate", "checks": []}]}))
        else:
            assert set(p.name for p in cwd.iterdir()) == {"agent", "sheet.md"}
            assert not (cwd / "agent/brace-findings.json").exists()
            (cwd / "E07.verdict.json").write_text(json.dumps({"verdict": "unclear", "applicability": "unclear",
                                                          "checks": [], "note": "Could not establish absence"}))
    monkeypatch.setattr(repeat, "call", fake_call)
    result = repeat.run_one("luna", "clinic-agent", 1, tmp_path, 1)
    assert len(calls) == 3 and calls[0] != calls[1]
    assert result["status"] == "fail" and result["score_exit"] == 1
    assert result["validation_errors"] and result["gap_recall"] == 0
    assert result["ratings"]["E07"] == "needs_evidence"
    assert (tmp_path / "clinic-agent.luna.run-1/initial.json").exists()
    assert (tmp_path / "clinic-agent.luna.run-1/findings.json").exists()


def test_incomplete_review_is_scored_without_challenges(tmp_path, monkeypatch):
    calls = []
    def incomplete(model, cwd, prompt, log, timeout):
        calls.append(cwd)
        (cwd / "agent/brace-findings.json").write_text(json.dumps({"findings": []}))
    monkeypatch.setattr(repeat, "call", incomplete)
    result = repeat.run_one("luna", "clinic-agent", 1, tmp_path, 1)
    assert len(calls) == 1
    assert result["status"] == "fail" and result["gap_recall"] == 0
    assert result["initial_validation_errors"]


def test_normalize_only_evidence_paths():
    original = {"evidence": "agent/a.py:1, agent/b.py:2", "quote": "agent/a.py",
                "checks": [{"evidence": "agent/c.py:3", "quote": "agent/c.py"}]}
    normalized = repeat.normalize_verdict(original)
    assert normalized["evidence"] == "a.py:1, b.py:2"
    assert normalized["checks"][0]["evidence"] == "c.py:3"
    assert normalized["quote"] == "agent/a.py" and original["evidence"].startswith("agent/")


def test_nested_ledger_evidence_is_normalized_without_changing_inputs():
    verdict={'checks':[{'coverage':[{'evidence':'agent/app.py:3','quote':'agent/app.py'}],
                        'attempts':[{'evidence':'agent/app.py:4','input':'agent/app.py'}]}]}
    result=repeat.normalize_verdict(verdict)
    assert result['checks'][0]['coverage'][0]['evidence']=='app.py:3'
    assert result['checks'][0]['coverage'][0]['quote']=='agent/app.py'
    assert result['checks'][0]['attempts'][0]['input']=='agent/app.py'


def test_bounded_batch_starts_pristine_and_stops_on_validation_failure(tmp_path,monkeypatch):
    calls=[]
    def fake(model,cwd,prompt,log,timeout):
        calls.append(cwd)
        doc=json.loads((cwd/'agent/brace-findings.json').read_text())
        assert len(doc['findings'])==5 and [f['item'] for f in doc['findings']]==repeat.validator.IDS[:5]
        assert not (cwd/'expected').exists() and not (cwd/'results').exists()
        log.write_text('batch model failed coverage')
    monkeypatch.setattr(repeat,'call',fake)
    result=repeat.run_one('sonnet','ticket-agent',1,tmp_path,1,batch_size=5)
    assert len(calls)==1 and result['status']=='fail'
    assert 'Bounded batch failed' in result['error']
    assert (tmp_path/'ticket-agent.sonnet.run-1/batch-01.json').exists()


def test_summary_keeps_failed_runs_in_variance_and_requires_full_matrix():
    results = [{"model": "sol", "fixture": "clinic-agent", "run": i + 1,
                "runtime": [{"model": "gpt-6.1-sol"}],
                "status": "pass" if i == 0 else "fail", "gap_recall": recall,
                "false_passes": ["B07"] * i, "false_gaps": [],
                "ratings": {"B01": "gap" if i == 0 else "needs_evidence"}}
               for i, recall in enumerate((1.0, 0.9, 0.8))]
    summary = repeat.summarize(results, ["sol"], ["clinic-agent"], 3)
    assert not summary["qualified"]["sol"]
    data = summary["spread"]["clinic-agent.sol"]
    assert data["gap_recall"]["mean"] == 0.9
    assert abs(data["gap_recall"]["sample_stddev"] - 0.1) < 1e-9
    assert data["false_passes"]["mean"] == 1
    assert data["rating_disagreement"] == ["B01"]
    for r in results:
        r["status"] = "pass"
    assert repeat.summarize(results, ["sol"], ["clinic-agent"], 3)["qualified"]["sol"]
    assert not repeat.summarize(results[:2], ["sol"], ["clinic-agent"], 3)["qualified"]["sol"]
    results[2]["runtime"] = [{"model": "other-model"}]
    assert not repeat.summarize(results, ["sol"], ["clinic-agent"], 3)["qualified"]["sol"]
    for r in results:
        r["runtime"] = [{"model": "gpt-6-luna"}]
    assert not repeat.summarize(results, ["sol"], ["clinic-agent"], 3)["qualified"]["sol"]


def test_runtime_records_served_model_and_reasoning_setting(tmp_path):
    (tmp_path / "review.log").write_text("OpenAI Codex v0.160.0\nmodel: gpt-6.1-sol\nreasoning effort: none\n")
    (tmp_path / "A01.log").write_text(json.dumps({"type": "system", "subtype": "init",
                                               "model": "claude-sonnet-5-5", "claude_code_version": "2.1.287"}) + "\n")
    (tmp_path / "failed.log").write_text("Executable not found\n")
    sessions = repeat.runtime_metadata(tmp_path)
    assert len(sessions) == 2
    assert sessions[0]["model"] == "claude-sonnet-5-5"
    assert sessions[1]["model"] == "gpt-6.1-sol" and sessions[1]["reasoning_effort"] == "none"


def test_snapshot_hash_ignores_caches_but_detects_instruction_changes(tmp_path):
    (tmp_path/'SKILL.md').write_text('first version')
    before=repeat.tree_hash(tmp_path)
    cache=tmp_path/'__pycache__';cache.mkdir();(cache/'module.pyc').write_bytes(b'compiled noise')
    assert repeat.tree_hash(tmp_path)==before
    (tmp_path/'SKILL.md').write_text('changed review instructions')
    assert repeat.tree_hash(tmp_path)!=before


def test_positive_control_fixture_has_no_recall_denominator(tmp_path):
    p=tmp_path/'findings.json';p.write_text(json.dumps({'findings':[]}))
    result={};repeat.grade(p,'catalog-agent',tmp_path,result)
    assert result['gap_recall'] is None and result['keyed_gap_locations']==0
