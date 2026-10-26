"""Rebuild a derived summary; preserve every original attempt and raw grade."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import statistics
import coverage_eval as runner

HERE = Path(__file__).resolve().parent
RECOVERY = HERE.parent / '2026-10-24-mcp-coverage-launch-recovery'

def read(path):
    return json.loads(path.read_text())

def identity(row):
    return row['fixture'], row['arm'], row['run']

original = read(HERE / 'summary.json')
recovery = read(RECOVERY / 'recovery.json')
assert original['complete'] and recovery['complete']
for folder in (HERE, RECOVERY):
    campaign = read(folder / 'campaign.json')
    assert runner.base.tree_hash(folder / 'snapshot') == campaign['snapshot_sha256']
    for filename, field in [('coverage_eval.py', 'runner_sha256'), ('qualify.py', 'helper_sha256')]:
        assert sha256((folder / filename).read_bytes()).hexdigest() == campaign[field]
assert read(HERE / 'campaign.json')['snapshot_sha256'] == read(RECOVERY / 'campaign.json')['snapshot_sha256']
rows = {identity(row): deepcopy(row) for row in original['runs']}
assert len(rows) == 48 and len(recovery['runs']) == recovery['selection_count'] == 21
replaced = set()
for row in recovery['runs']:
    key = identity(row)
    assert key not in replaced
    replaced.add(key)
    old = rows[key]
    folder = HERE / f'{key[0]}.{key[1]}.run-{key[2]}'
    assert old['status'] == 'review_error' and old['error'].startswith(('[Errno 2]', '[Errno 8]'))
    assert 'review_runtime' not in old and not (folder / 'report.md').exists()
    assert not (folder / 'review.log').exists() or (folder / 'review.log').stat().st_size == 0
    rows[key] = deepcopy(row)
    rows[key]['derived_provenance'] = str((RECOVERY / folder.name / 'run.json').relative_to(HERE.parent))
    rows[key]['original_status'] = old['status']
for key, row in rows.items():
    folder = (RECOVERY if key in replaced else HERE) / f'{key[0]}.{key[1]}.run-{key[2]}'
    path = folder / 'adjudication.json'
    if path.exists():
        adjudication = read(path)
        assert sha256((folder / 'report.md').read_bytes()).hexdigest() == adjudication['report_sha256']
        assert sha256((folder / 'verdict.json').read_bytes()).hexdigest() == adjudication['raw_verdict_sha256']
        score = runner.base.grade((folder / 'report.md').read_text(), adjudication['adjudicated_verdict'], read(HERE / 'snapshot/coverage/expected' / f'{key[0]}.json'))
        assert score == adjudication['adjudicated_score']
        row.update(raw_status=row['status'], status='scored', score=score, adjudication=str(path.relative_to(HERE.parent)))
suite = read(HERE / 'snapshot/coverage/suite.json')
summary = runner.summarize(list(rows.values()), suite, 3)
assert summary['complete'] and summary['comparison_valid']
summary['derivation'] = {'original': 'summary.json', 'launch_recovery': '../2026-10-24-mcp-coverage-launch-recovery/recovery.json', 'replaced_unstarted_attempts': 21, 'raw_files_preserved': True, 'audit_limit': 'Targeted manual adjudications are not an exhaustive or unbiased false-positive audit.'}
summary['totals'] = {}
for arm in runner.ARMS:
    arm_rows = [r for r in rows.values() if r['arm'] == arm]
    totals = {'reviews': len(arm_rows)}
    for group in ('must_find', 'guards', 'coverage'):
        checks = [(r, c) for r in arm_rows for c in read(HERE / 'snapshot/coverage/expected' / f"{r['fixture']}.json")[group]]
        totals[group] = {'met': sum(r['score']['case_results'][c['id']] for r,c in checks), 'total': len(checks)}
    totals.update(report_checks_met=sum(r['score']['checks_ok'] for r in arm_rows), combined_criteria_met=sum(r['score']['pass'] for r in arm_rows), unsupported_claim_groups=sum(len(r['score']['unsupported_gaps']) for r in arm_rows), false_assurance_groups=sum(len(r['score']['false_assurances']) for r in arm_rows), review_cost_usd=sum(r['review_cost_usd'] for r in arm_rows), judge_cost_usd=sum(r.get('judge_cost_usd',0) for r in arm_rows), mean_review_seconds=statistics.mean(r['review_seconds'] for r in arm_rows), median_review_seconds=statistics.median(r['review_seconds'] for r in arm_rows))
    summary['totals'][arm] = totals
runner.write_json(HERE / 'combined-audited-summary.json', summary)
print(json.dumps(summary['totals'], indent=2))
