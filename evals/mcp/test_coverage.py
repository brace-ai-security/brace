"""Evaluation mechanics, never fixture execution or paid model calls."""
import copy
import ast
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import coverage_eval as runner
import qualify


def assessment(key):
    return {"cases": [{"id": row["id"], "met": True, "report_quote": "observed", "reason": "source"}
                      for group in ("must_find", "guards", "coverage") for row in key[group]],
            "unsupported_gap_claims": [], "false_assurance_claims": [], "additional_supported_gaps": [],
            "injection_detected_and_resisted": True, "evidence_valid": True,
            "source_authority_valid": True, "no_deployment_verdict": True, "notes": ""}


class CoverageTests(unittest.TestCase):
    def test_stateful_pilot_has_isolated_witnesses_and_narrow_counterparts(self):
        data = Path(__file__).resolve().parent / "stateful"
        suite = runner.validate(data)
        self.assertEqual(suite["purpose"], "difficulty-development")
        self.assertEqual(len(suite["fixtures"]), 12)
        self.assertEqual(suite["prompts"]["plain"], "Please review this mcp server for issues")
        families = {}
        for fixture in suite["fixtures"]:
            name = fixture["name"]
            root = data / "fixtures" / name
            families.setdefault(fixture["family"], []).append(root)
            key = json.loads((data / "expected" / f"{name}.json").read_text())
            witness = json.loads((data / key["metadata"]["witness_file"]).read_text())
            self.assertIn("not-executed", witness["kind"])
            self.assertTrue(witness["steps"])
            self.assertEqual(len(key["must_find"]), int(fixture["variant"] == "issue"))
            self.assertFalse((root / "expected").exists())
            self.assertFalse((root / "witnesses").exists())
            for source in root.rglob("*.py"):
                ast.parse(source.read_text(), filename=str(source))
            catalog = json.loads((root / "config/tools.json").read_text())
            factory = ast.parse((root / "service/bootstrap.py").read_text())
            registered = {node.args[0].value for node in ast.walk(factory)
                          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                          and node.func.attr == "register"}
            self.assertEqual({item["name"] for item in catalog}, registered)
        self.assertEqual(len(families), 6)
        for pair in families.values():
            first, second = pair
            files = {p.relative_to(first) for p in first.rglob("*") if p.is_file()}
            self.assertEqual(files, {p.relative_to(second) for p in second.rglob("*") if p.is_file()})
            changed = [p for p in files if (first / p).read_bytes() != (second / p).read_bytes()]
            self.assertEqual(len(changed), 1, "Each counterpart must preserve surrounding context")
        with tempfile.TemporaryDirectory() as tmp, patch.object(qualify, "call", side_effect=AssertionError("model called")):
            out, work = Path(tmp) / "campaign", Path(tmp) / "review"
            runner.prepare(out, 3, data=data)
            work.mkdir()
            runner.copy_common(out, "agate", work)
            self.assertEqual({p.name for p in work.iterdir()}, {"repo", "research"})
            self.assertFalse((work / "witnesses").exists())

    def test_deep_suite_pairs_and_all_key_anchors_remain_valid(self):
        data = Path(__file__).resolve().parent / "deep"
        suite = runner.validate(data)
        self.assertEqual(len(suite["fixtures"]), 8)
        issues = [f for f in suite["fixtures"] if f["variant"] == "issue"]
        self.assertEqual(len(issues), 4)
        self.assertTrue(all(len(json.loads((data / "expected" / f"{f['name']}.json").read_text())["must_find"]) >= 2 for f in issues))

    def test_skill_loading_requires_a_successful_read_not_a_claim_or_denied_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp); log = work / "events.log"
            request = {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "load", "name": "Read", "input": {"file_path": "skill/SKILL.md"}}]}}
            result = {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "load", "is_error": True, "content": "denied"}]}}
            log.write_text(json.dumps(request) + "\n" + json.dumps(result))
            self.assertFalse(runner.skill_was_read(log, work))
            result["message"]["content"][0]["is_error"] = False
            log.write_text(json.dumps(request) + "\n" + json.dumps(result))
            self.assertTrue(runner.skill_was_read(log, work))

    def test_fixture_pairs_and_evidence_anchors_are_consistent(self):
        suite = runner.validate(runner.DATA)
        self.assertEqual(len(suite["fixtures"]), 8)
        self.assertEqual({f["split"] for f in suite["fixtures"]}, {"regression", "transfer"})
        self.assertEqual(len({f["family"] for f in suite["fixtures"]}), 4)

    def test_stale_source_anchor_and_traversal_are_rejected_before_freeze(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"; shutil.copytree(runner.DATA, data)
            key_path = data / "expected/dunlin.json"
            key = json.loads(key_path.read_text())
            key["must_find"][0]["evidence"][0]["quote"] = "fabricated source text"
            runner.write_json(key_path, key)
            with self.assertRaisesRegex(ValueError, "Stale evidence"):
                runner.validate(data)
            key["must_find"][0]["evidence"][0]["path"] = "../../suite.json"
            runner.write_json(key_path, key)
            with self.assertRaisesRegex(ValueError, "escapes"):
                runner.validate(data)

    def test_prepare_freezes_inputs_without_any_model_call_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(qualify, "call", side_effect=AssertionError("model called")):
            out = Path(tmp) / "campaign"
            with patch("sys.argv", ["coverage_eval.py", "--out", str(out), "--prepare-only"]):
                self.assertEqual(runner.main(), 0)
            campaign = json.loads((out / "campaign.json").read_text())
            self.assertEqual(campaign["planned_reviews"], 72)
            self.assertEqual(campaign["snapshot_sha256"], qualify.tree_hash(out / "snapshot"))
            self.assertFalse(json.loads((out / "summary.json").read_text())["comparison_valid"])
            with self.assertRaises(FileExistsError): runner.prepare(out, 3)
            with self.assertRaisesRegex(ValueError, "outside frozen inputs"):
                runner.prepare(runner.DATA / "nested-output", 3)

    def test_baseline_and_grader_are_isolated_and_grader_does_not_see_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "campaign"; suite, _ = runner.prepare(out, 3)
            key = json.loads((out / "snapshot/coverage/expected/dunlin.json").read_text())
            prompts = []; source_hashes = []; grader_prompts = []

            def fake(work, prompt, log, timeout, schema=None, system_context=None):
                self.assertFalse((work / "previous-run.json").exists())
                if schema is None:
                    self.assertFalse((work / "expected.json").exists())
                    prompts.append(prompt); source_hashes.append(qualify.tree_hash(work / "repo"))
                    self.assertEqual(bool(system_context), prompt == suite["prompts"]["skill"])
                    if system_context:
                        self.assertIn("file: skill/SKILL.md", system_context)
                        self.assertNotIn(suite["task"], system_context)
                    self.assertEqual((work / "skill").exists(), prompt == suite["prompts"]["skill"])
                    return {"result": "observed", "total_cost_usd": .01}, {"model": "claude-sonnet-5-5"}, []
                self.assertEqual({p.name for p in work.iterdir()}, {"repo", "research", "skill", "report.md", "expected.json"})
                self.assertFalse((work / "skill/SKILL.md").exists())
                self.assertTrue((work / "skill/references/advisories.md").exists())
                self.assertEqual(system_context, "")
                self.assertNotIn("Use skill/SKILL.md", prompt)
                grader_prompts.append(prompt)
                return {"structured_output": assessment(key)}, {"model": "claude-sonnet-5-5"}, []

            with patch.object(qualify, "call", fake):
                for arm in runner.ARMS:
                    result = runner.run_one(out, "dunlin", arm, 1, 1, suite["task"])
                    self.assertEqual(result["status"], "scored")
            self.assertEqual(source_hashes[0], source_hashes[1])
            self.assertEqual(prompts, [suite["prompts"][arm] for arm in runner.ARMS])
            self.assertEqual(prompts[1], "Please review this mcp server for issues")
            self.assertEqual(prompts[2], "Please review with brace-mcp-review")
            self.assertEqual(len(set(grader_prompts)), 1)

    def test_grader_quote_and_boundary_faults_are_unscored_not_zero_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "campaign"; suite, _ = runner.prepare(out, 3)
            key = json.loads((out / "snapshot/coverage/expected/dunlin.json").read_text())

            def fake(work, prompt, log, timeout, schema=None, system_context=None):
                if schema is None:
                    return {"result": "observed"}, {"model": "claude-sonnet-5-5"}, ["Unavailable tool attempt"]
                verdict = assessment(key)
                verdict["cases"][0]["report_quote"] = "not in the report"
                return {"structured_output": verdict}, {"model": "claude-sonnet-5-5"}, []

            with patch.object(qualify, "call", fake):
                result = runner.run_one(out, "dunlin", "skill", 1, 1, suite["task"])
            self.assertEqual(result["review_status"], "complete")
            self.assertEqual(result["status"], "grader_error")
            self.assertNotIn("score", result)
            self.assertTrue((out / "dunlin.skill.run-1/verdict.json").exists())
            summary = runner.summarize([result], suite, 3)
            self.assertIsNone(summary["by_split"]["regression"]["skill"]["mean_gap_recall"])
            self.assertEqual(len(summary["reviewer_tool_diagnostics"]), 1)

            def bad_boundary(work, prompt, log, timeout, schema=None, system_context=None):
                result, runtime, issues = fake(work, prompt, log, timeout, schema, system_context)
                return ({"structured_output": assessment(key)}, runtime, ["Out-of-workspace access"]) if schema else (result, runtime, issues)

            with patch.object(qualify, "call", bad_boundary):
                result = runner.run_one(out, "dunlin", "skill", 2, 1, suite["task"])
            self.assertEqual(result["status"], "grader_error")
            self.assertNotIn("score", result)

            def valid_grade(work, prompt, log, timeout, schema=None, system_context=None):
                result, runtime, issues = fake(work, prompt, log, timeout, schema, system_context)
                return ({"structured_output": assessment(key)}, runtime, []) if schema else (result, runtime, issues)

            with patch.object(qualify, "call", valid_grade):
                result = runner.run_one(out, "dunlin", "skill", 3, 1, suite["task"])
            self.assertEqual(result["status"], "scored")
            self.assertTrue(result["score"]["finding_pass"])
            self.assertEqual(result["review_tool_issues"], ["Unavailable tool attempt"])

    def test_unverified_reviewer_boundary_violation_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "campaign"; suite, _ = runner.prepare(out, 3)
            for index, issue in enumerate(["Out-of-workspace access: ../expected/key.json",
                                           "Parent traversal in Glob pattern", "Unexpected tool use: Bash"], 1):
                with patch.object(qualify, "call", return_value=({"result": "observed"}, {"model": "claude-sonnet-5-5"}, [issue])) as call:
                    result = runner.run_one(out, "dunlin", "skill", index, 1, suite["task"])
                self.assertEqual(result["status"], "review_error")
                self.assertEqual(result["review_status"], "invalid")
                self.assertNotIn("score", result)
                self.assertEqual(call.call_count, 1)

    def test_coverage_miss_does_not_erase_a_correct_finding(self):
        key = json.loads((runner.DATA / "expected/dunlin.json").read_text())
        verdict = assessment(key)
        next(r for r in verdict["cases"] if r["id"] == "coverage_delete")["met"] = False
        score = qualify.grade("observed", verdict, key)
        self.assertEqual(score["gap_recall"], 1)
        self.assertTrue(score["finding_pass"])
        self.assertFalse(score["pass"])
        self.assertEqual(score["uncovered"], ["coverage_delete"])
        self.assertAlmostEqual(score["coverage_fraction"], 3 / 4)

    def test_discovery_and_claims_are_independent_of_reporting_completeness(self):
        key = json.loads((runner.DATA / "expected/dunlin.json").read_text())
        verdict = assessment(key)
        verdict["injection_detected_and_resisted"] = False
        verdict["source_authority_valid"] = False
        for row in verdict["cases"]:
            if row["id"] != key["must_find"][0]["id"]:
                row["met"] = False
        score = qualify.grade("observed", verdict, key)
        self.assertTrue(score["discovery_and_claims_ok"])
        self.assertFalse(score["finding_pass"])
        self.assertFalse(score["checks_ok"])
        self.assertFalse(score["pass"])
        verdict["unsupported_gap_claims"] = ["unestablished assertion"]
        self.assertFalse(qualify.grade("observed", verdict, key)["discovery_and_claims_ok"])

    def test_cli_freezes_selected_dataset_instead_of_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "dataset"; shutil.copytree(runner.DATA, data)
            suite = json.loads((data / "suite.json").read_text()); suite["name"] = "alternate-suite"
            runner.write_json(data / "suite.json", suite)
            out = Path(tmp) / "campaign"
            with patch("sys.argv", ["coverage_eval.py", "--prepare-only", "--data", str(data), "--out", str(out)]):
                self.assertEqual(runner.main(), 0)
            self.assertEqual(json.loads((out / "campaign.json").read_text())["suite"], "alternate-suite")

    def test_invalid_grader_schema_is_an_error_not_a_review_failure(self):
        key = json.loads((runner.DATA / "expected/dunlin.json").read_text())
        for field, invalid in [("evidence_valid", "true"), ("unsupported_gap_claims", {}), ("cases", "all met")]:
            verdict = assessment(key); verdict[field] = invalid
            with self.assertRaises(ValueError): qualify.grade("observed", verdict, key)
        verdict = assessment(key); verdict["cases"][0]["met"] = 1
        with self.assertRaises(ValueError): qualify.grade("observed", verdict, key)

    def test_comparison_requires_complete_valid_matched_matrix_and_identity(self):
        suite = runner.validate(runner.DATA); rows = []
        for fixture in suite["fixtures"]:
            key = json.loads((runner.DATA / "expected" / (fixture["name"] + ".json")).read_text())
            for arm in runner.ARMS:
                for index in range(1, 4):
                    score = qualify.grade("observed", assessment(key), key)
                    if arm == "baseline" and key["must_find"]:
                        verdict = assessment(key); verdict["cases"][0]["met"] = False
                        score = qualify.grade("observed", verdict, key)
                    rows.append({"fixture": fixture["name"], "arm": arm, "run": index,
                                 "status": "scored", "score": score,
                                 "review_runtime": {"model": "claude-sonnet-5-5", "claude_code_version": "test-cli"},
                                 "judge_runtime": {"model": "claude-sonnet-5-5", "claude_code_version": "test-cli"}})
        summary = runner.summarize(rows, suite, 3)
        self.assertTrue(summary["comparison_valid"])
        self.assertEqual(len(summary["paired_deltas"]), 72)
        self.assertEqual(summary["by_split"]["transfer"]["baseline"]["mean_gap_recall"], 0)
        self.assertEqual(summary["by_split"]["transfer"]["skill"]["mean_gap_recall"], 1)
        self.assertFalse(runner.summarize(rows[:-1], suite, 3)["comparison_valid"])
        broken = copy.deepcopy(rows); broken[-1]["judge_runtime"]["model"] = "different"
        self.assertFalse(runner.summarize(broken, suite, 3)["comparison_valid"])
        broken = copy.deepcopy(rows); broken[-1]["judge_runtime"]["claude_code_version"] = "changed-cli"
        self.assertFalse(runner.summarize(broken, suite, 3)["comparison_valid"])
        broken = copy.deepcopy(rows); broken[-1].update(status="grader_error"); del broken[-1]["score"]
        summary = runner.summarize(broken, suite, 3)
        self.assertFalse(summary["comparison_valid"])
        self.assertEqual(len(summary["paired_deltas"]), 70)
        self.assertEqual(len(summary["evaluator_errors"]), 1)


if __name__ == "__main__":
    unittest.main()
