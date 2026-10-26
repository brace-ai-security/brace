"""Recompute a derived summary with explicit adjudications; never edit raw grades."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import statistics
import coverage_eval as runner

HERE = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text())

campaign = read(HERE / 'campaign.json')
assert runner.base.tree_hash(HERE / 'snapshot') == campaign['snapshot_sha256']
for name, field in [('coverage_eval.py', 'runner_sha256'), ('qualify.py', 'helper_sha256')]:
    assert sha256((HERE / name).read_bytes()).hexdigest() == campaign[field]
raw = read(HERE / 'summary.json')
assert raw['complete'], 'Wait for the full raw matrix; failures remain included'
rows = deepcopy(raw['runs'])
for row in rows:
    folder = HERE / f"{row['fixture']}.{row['arm']}.run-{row['run']}"
    adjudication = folder / 'adjudication.json'
    assert (folder / 'prompt.txt').read_text() == campaign['prompts'][row['arm']]
    if adjudication.exists():
        record = read(adjudication)
        assert sha256((folder / 'report.md').read_bytes()).hexdigest() == record['report_sha256']
        assert sha256((folder / 'verdict.json').read_bytes()).hexdigest() == record['raw_verdict_sha256']
        verdict = record['adjudicated_verdict']
        key = read(HERE / 'snapshot/coverage/expected' / f"{row['fixture']}.json")
        score = runner.base.grade((folder / 'report.md').read_text(), verdict, key)
        assert score == record['adjudicated_score']
        row.update(raw_status=row['status'], status='scored', score=score, adjudication=str(adjudication.relative_to(HERE)))
suite = read(HERE / 'snapshot/coverage/suite.json')
summary = runner.summarize(rows, suite, 3)
summary['derivation'] = 'Frozen runner plus separate explicit adjudications; raw records unchanged. Targeted audits are not exhaustive claim validation.'
summary['audit_provenance'] = {'raw_model_comparison_valid': raw['comparison_valid'],
    'raw_grader_errors': len(raw['evaluator_errors']),
    'reports_with_adjudications': sum('adjudication' in r for r in rows),
    'author_reassessments_of_unscored_reports': sum(r.get('raw_status') == 'grader_error' for r in rows)}
summary['totals'] = {}
for arm in runner.ARMS:
    attempts = [r for r in rows if r['arm'] == arm]
    scored = [r for r in attempts if r['status'] == 'scored']
    totals = {'attempted_reviews': len(attempts), 'scored_reviews': len(scored)}
    for group in ('must_find', 'guards', 'coverage'):
        checks = [(r, c) for r in scored for c in read(HERE / 'snapshot/coverage/expected' / f"{r['fixture']}.json")[group]]
        totals[group] = {'met': sum(r['score']['case_results'][c['id']] for r,c in checks), 'scored_total': len(checks)}
    totals.update(report_checks_met=sum(r['score']['checks_ok'] for r in scored), combined_criteria_met=sum(r['score']['pass'] for r in scored), unsupported_claim_groups=sum(len(r['score']['unsupported_gaps']) for r in scored), false_assurance_groups=sum(len(r['score']['false_assurances']) for r in scored), review_cost_usd=sum(r.get('review_cost_usd') or 0 for r in attempts), judge_cost_usd=sum(r.get('judge_cost_usd') or 0 for r in attempts), review_cost_observations=sum(r.get('review_cost_usd') is not None for r in attempts), mean_review_seconds=statistics.mean(r['review_seconds'] for r in attempts if 'review_seconds' in r), skill_file_read=sum(r.get('skill_loaded') is True for r in attempts) if arm == 'skill' else None)
    summary['totals'][arm] = totals
runner.write_json(HERE / 'audited-summary.json', summary)
print(json.dumps({'comparison_valid': summary['comparison_valid'], 'totals': summary['totals']}, indent=2))
