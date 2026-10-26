import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import coverage_eval as runner
import qualify
import source_grade
from grading import source_jobs
from test_coverage import assessment


class SourceGradeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        (self.work / 'repo').mkdir()
        (self.work / 'repo/code.py').write_text('if not token: raise ValueError()')
        self.key = {'must_find': [], 'guards': [], 'coverage': [], 'forbidden_output': []}
        verdict = assessment(self.key)
        del verdict['unsupported_gap_claims']; del verdict['false_assurance_claims']
        self.report = 'Empty tokens are sent. The host is unknown.'
        self.audit = {'report_id': 'R01', 'case_verdict': verdict, 'claims': [
            {'id': 'C1', 'report_quote': 'Empty tokens are sent.', 'outcome': 'contradicted',
             'error_type': 'unsupported_gap', 'reason': 'The startup guard rejects empty values.',
             'evidence': [{'path': 'repo/code.py', 'quote': 'if not token: raise ValueError()'}]}]}

    def test_errors_are_projected_only_from_substantive_decisions(self):
        score, verdict = source_grade.score(self.report, self.audit, self.key, self.work)
        self.assertFalse(score['discovery_and_claims_ok'])
        self.assertEqual(len(verdict['unsupported_gap_claims']), 1)
        qualified = copy.deepcopy(self.audit)
        qualified['claims'][0].update(report_quote='The host is unknown.', outcome='qualified', error_type=None)
        score, verdict = source_grade.score(self.report, qualified, self.key, self.work)
        self.assertTrue(score['discovery_and_claims_ok'])
        self.assertEqual(verdict['unsupported_gap_claims'], [])

    def test_qualified_or_supported_claim_cannot_be_counted_as_error(self):
        for outcome in ['supported', 'qualified']:
            bad = copy.deepcopy(self.audit); bad['claims'][0]['outcome'] = outcome
            with self.assertRaisesRegex(ValueError, 'disagree'):
                source_grade.score(self.report, bad, self.key, self.work)
        bad = copy.deepcopy(self.audit); bad['claims'][0]['error_type'] = None
        with self.assertRaisesRegex(ValueError, 'disagree'):
            source_grade.score(self.report, bad, self.key, self.work)

    def test_claim_and_source_quotes_must_exist_in_authorized_inputs(self):
        for field, value in [('report_quote', 'invented text')]:
            bad = copy.deepcopy(self.audit); bad['claims'][0][field] = value
            with self.assertRaises(ValueError): source_grade.score(self.report, bad, self.key, self.work)
        for path, quote in [('repo/code.py', 'invented code'), ('../secret', 'x'), ('/tmp/secret', 'x'), ('skill/SKILL.md', 'x')]:
            bad = copy.deepcopy(self.audit); bad['claims'][0]['evidence'] = [{'path': path, 'quote': quote}]
            with self.assertRaises(ValueError): source_grade.score(self.report, bad, self.key, self.work)

    def test_case_quotes_still_use_strict_shared_scorer(self):
        key = {'must_find': [{'id': 'G1'}], 'guards': [], 'coverage': []}
        bad = copy.deepcopy(self.audit)
        bad['case_verdict']['cases'] = [{'id': 'G1', 'met': True, 'report_quote': 'invented', 'reason': 'bad'}]
        with self.assertRaisesRegex(ValueError, 'absent'):
            source_grade.score(self.report, bad, key, self.work)

    def test_review_only_never_calls_the_cli_grader(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'campaign'; suite, _ = runner.prepare(out, 3)
            with patch.object(qualify, 'call', return_value=({'result': 'source report'}, {'model': 'claude-sonnet-5-5'}, [])) as call:
                row = runner.run_one(out, 'dunlin', 'plain', 1, 1, suite['task'], grade=False)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(row['status'], 'review_complete')
            self.assertNotIn('score', row)
            self.assertFalse((out / 'dunlin.plain.run-1/judge.log').exists())

    def test_opaque_batch_waits_for_nine_reports_and_preserves_input_hash(self):
        out=self.work/'campaign';runner.prepare(out,3)
        protocol=Path(__file__).parent/'grading/PROTOCOL.md'
        index=source_jobs.prepare(out,protocol,Path(source_grade.__file__))
        self.assertIn('task_sha256',index)
        case=index['cases'][0]
        self.assertFalse(source_jobs.ready_batch(out,case['case_id']))
        for slot in case['reports']:
            dest=out/f"{slot['fixture']}.{slot['arm']}.run-{slot['run']}";dest.mkdir()
            (dest/'report.md').write_text('Opaque source report.')
            runner.write_json(dest/'run.json',{'status':'review_complete'})
        self.assertTrue(source_jobs.ready_batch(out,case['case_id']))
        workspace=out/'source-grading/inputs'/case['case_id']
        jobs=(workspace/'jobs.json').read_text()
        self.assertNotIn('baseline',jobs);self.assertNotIn('skill.run',jobs)
        before=qualify.tree_hash(workspace)
        (out/'source-grading/grades'/case['case_id']/'R01.json').write_text('{}')
        self.assertEqual(before,qualify.tree_hash(workspace))
        self.assertFalse(source_jobs.ready_batch(out,case['case_id']))
