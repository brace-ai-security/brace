"""Describe frozen plain-pilot results; no model calls or fixture execution."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
summary = json.loads((ROOT / 'source-audited-summary.json').read_text())
suite = json.loads((ROOT / 'snapshot/coverage/suite.json').read_text())
rows = summary['runs']
assert summary['source_audit_complete'] and len(rows) == 36
assert all(row['arm'] == 'plain' and row['status'] == 'scored' for row in rows)
fixtures = {fixture['name']: fixture for fixture in suite['fixtures']}
errors = lambda row: len(row['score']['unsupported_gaps']) + len(row['score']['false_assurances'])
by_fixture = {}
for name, fixture in fixtures.items():
    group = sorted([row for row in rows if row['fixture'] == name], key=lambda row: row['run'])
    assert [row['run'] for row in group] == [1, 2, 3]
    key = json.loads((ROOT / 'snapshot/coverage/expected' / f'{name}.json').read_text())
    findings = key['must_find']
    assert len(findings) == int(fixture['variant'] == 'issue')
    by_fixture[name] = {
        'family': fixture['family'], 'variant': fixture['variant'],
        'required_findings_met': sum(row['score']['case_results'][finding['id']] for row in group for finding in findings),
        'required_findings_total': len(findings) * 3,
        'reports_with_incorrect_claims': sum(errors(row) > 0 for row in group),
        'incorrect_claims': sum(errors(row) for row in group),
        'selected_grade_files': [row['source_grade'] for row in group],
    }
issues = [value for value in by_fixture.values() if value['variant'] == 'issue']
met = sum(value['required_findings_met'] for value in issues)
total = sum(value['required_findings_total'] for value in issues)
assert len(issues) == 6 and total == 18
result = {
    'method': 'Descriptive difficulty-development pilot. Six distinct bugs repeated three times, not eighteen independent vulnerabilities. No skill arm or effect comparison.',
    'required_findings': {'met': met, 'total': total, 'fraction': met / total,
                          'distinct_bugs_found_at_least_once': sum(value['required_findings_met'] > 0 for value in issues),
                          'distinct_bugs_found_every_repetition': sum(value['required_findings_met'] == 3 for value in issues)},
    'pilot_aspiration': {'range': [0.4, 0.6], 'observed_in_range': 0.4 <= met / total <= 0.6,
                         'interpretation': 'An aspiration, not an acceptance/qualification threshold or a reason to filter/rewrite cases after scoring.'},
    'reports_with_incorrect_claims': sum(errors(row) > 0 for row in rows),
    'incorrect_claims': sum(errors(row) for row in rows),
    'by_fixture': by_fixture,
    'total_metrics': summary['totals']['plain'],
}
(ROOT / 'pilot-analysis.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: value for key, value in result.items() if key not in {'by_fixture', 'total_metrics'}}, indent=2))
