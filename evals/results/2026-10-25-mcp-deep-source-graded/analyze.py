"""Separate factual error reports and synthetic canaries from legacy composites."""
from itertools import combinations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
summary = json.loads((ROOT / 'source-audited-summary.json').read_text())
rows = summary['runs']
assert summary['source_audit_complete'] and len(rows) == 72
assert all(row['status'] == 'scored' for row in rows)
arms = ['baseline', 'plain', 'skill']

def errors(row):
    return len(row['score']['unsupported_gaps']) + len(row['score']['false_assurances'])

def metrics(group):
    return {
        'reports': len(group),
        'reports_with_incorrect_claims': sum(errors(row) > 0 for row in group),
        'incorrect_claims': sum(errors(row) for row in group),
        'synthetic_canary_disclosures': sum(row['score']['secret_leak'] for row in group),
        'all_required_findings_and_no_incorrect_claims': sum(not row['score']['missed'] and errors(row) == 0 for row in group),
        'misses': [{'fixture': row['fixture'], 'run': row['run'], 'ids': row['score']['missed']} for row in group if row['score']['missed']],
    }

output = {'method': 'Derived from selected source grades. Claim errors and synthetic canary echoing are separate. Legacy discovery_and_claims_ok also requires no canary disclosure; the explicit finding/claim count here does not.',
          'by_arm': {arm: metrics([row for row in rows if row['arm'] == arm]) for arm in arms},
          'per_fixture': {}, 'paired': {}}
for fixture in sorted({row['fixture'] for row in rows}):
    output['per_fixture'][fixture] = {arm: metrics([row for row in rows if row['fixture'] == fixture and row['arm'] == arm]) for arm in arms}
lookup = {(row['fixture'], row['arm'], row['run']): row for row in rows}
for first, second in combinations(arms, 2):
    pairs = [(lookup[(fixture, first, run)], lookup[(fixture, second, run)]) for fixture in output['per_fixture'] for run in range(1, 4)]
    assert len(pairs) == 24
    output['paired'][f'{second}-minus-{first}'] = {
        'pairs': len(pairs),
        'fewer_incorrect_claims': sum(errors(b) < errors(a) for a, b in pairs),
        'equal_incorrect_claims': sum(errors(b) == errors(a) for a, b in pairs),
        'more_incorrect_claims': sum(errors(b) > errors(a) for a, b in pairs),
        'more_coverage': sum(len(b['score']['uncovered']) < len(a['score']['uncovered']) for a, b in pairs),
        'equal_coverage': sum(len(b['score']['uncovered']) == len(a['score']['uncovered']) for a, b in pairs),
        'less_coverage': sum(len(b['score']['uncovered']) > len(a['score']['uncovered']) for a, b in pairs),
    }
for counts in output['paired'].values():
    assert sum(counts[name] for name in ['fewer_incorrect_claims', 'equal_incorrect_claims', 'more_incorrect_claims']) == 24
    assert sum(counts[name] for name in ['more_coverage', 'equal_coverage', 'less_coverage']) == 24
(ROOT / 'analysis.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output['by_arm'], indent=2))
