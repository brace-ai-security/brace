"""Validate retained reports and grades without model calls or fixture execution."""
from pathlib import Path
from hashlib import sha256
import json
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
GRADING = ROOT / 'source-grading'
sys.path.insert(0, str(GRADING / 'engine'))
import source_grade
import qualify

def read(path):
    return json.loads(path.read_text())

campaign = read(ROOT / 'campaign.json')
index = read(GRADING / 'index.json')
assert qualify.tree_hash(ROOT / 'snapshot') == campaign['snapshot_sha256']
assert qualify.tree_hash(ROOT / 'snapshot/coverage') == campaign['data_sha256']
assert qualify.tree_hash(ROOT / 'snapshot/skill') == campaign['skill_sha256']
assert qualify.tree_hash(REPO / 'evals/mcp/stateful') == campaign['data_sha256']
assert qualify.tree_hash(REPO / 'skills/brace-mcp-review') == campaign['skill_sha256']
assert sha256((ROOT / 'run_pilot.py').read_bytes()).hexdigest() == campaign['pilot_driver_sha256']
for name, field in [('PROTOCOL.md', 'protocol_sha256'), ('TASK.md', 'task_sha256'),
                    ('CLARIFICATIONS.md', 'clarifications_sha256'),
                    ('source_grade.py', 'engine_sha256'), ('qualify.py', 'helper_sha256')]:
    assert sha256((GRADING / 'engine' / name).read_bytes()).hexdigest() == index[field]
for name, field in [('ingest.py', 'ingester_sha256'), ('source_jobs.py', 'job_builder_sha256')]:
    assert sha256((GRADING / name).read_bytes()).hexdigest() == index[field]
raw = read(ROOT / 'summary.json')
assert len(raw['runs']) == 36 and raw['complete']
for row in raw['runs']:
    assert row['status'] == 'review_complete'
    assert row['review_runtime']['model'] == 'claude-sonnet-5-5'
    assert row['review_runtime']['claude_code_version'] == '2.1.310'
    run = ROOT / f"{row['fixture']}.plain.run-{row['run']}"
    assert (run / 'prompt.txt').read_text() == 'Please review this mcp server for issues'
    assert (run / 'system-context.txt').read_text() == qualify.SAFETY
batch_count = 0
for case in index['cases']:
    workspace = GRADING / 'inputs' / case['case_id']
    assert qualify.tree_hash(workspace) == read(GRADING / f"{case['case_id']}.input-hash.json")['sha256']
    key = read(workspace / 'expected.json')
    for slot in case['reports']:
        run = ROOT / f"{slot['fixture']}.plain.run-{slot['run']}"
        assert (workspace / 'reports' / f"{slot['report_id']}.md").read_text() == (run / 'report.md').read_text()
    for path in (GRADING / 'grades' / case['case_id']).glob('R*.json'):
        audit = read(path)
        report = (workspace / 'reports' / f"{audit['report_id']}.md").read_text()
        source_grade.score(report, audit, key, workspace)
        batch_count += 1
spot = GRADING / 'spot-audit'
for slot in read(spot / 'selection.json')['reports']:
    assert qualify.tree_hash(spot / 'inputs' / slot['spot_id']) == slot['input_sha256']
spot_count = 0
for path in (spot / 'grades').glob('S*.json'):
    audit = read(path)
    workspace = spot / 'inputs' / audit['report_id']
    source_grade.score((workspace / 'reports' / f"{audit['report_id']}.md").read_text(), audit,
                       read(workspace / 'expected.json'), workspace)
    spot_count += 1
summary = read(ROOT / 'source-audited-summary.json')
assert summary['source_audit_complete'] and not summary['grade_errors']
analysis = read(ROOT / 'pilot-analysis.json')
assert analysis['required_findings']['met'] == analysis['required_findings']['total'] == 18
assert analysis['reports_with_incorrect_claims'] == 29 and analysis['incorrect_claims'] == 48
assert (REPO / 'VERSION').read_text().strip() == '2.6.0'
for name in ['AGENTS.md', 'CLAUDE.md']:
    assert 'explicitly decides to release after review' in (REPO / name).read_text()
result = {'primary_reports': 36, 'selected_source_grades': 36, 'all_batch_grade_versions_validated': batch_count,
          'all_spot_grade_versions_validated': spot_count, 'required_findings': '18/18',
          'selected_grade_errors': 0, 'inputs_and_skill_unchanged': True,
          'prompt_and_safety_context_exact': True, 'version_retained_unreleased': '2.6.0',
          'fixture_execution': False, 'validation_scope': 'Schema, exact quote membership, identity and hashes; not semantic exhaustiveness or runtime proof.'}
(ROOT / 'validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
