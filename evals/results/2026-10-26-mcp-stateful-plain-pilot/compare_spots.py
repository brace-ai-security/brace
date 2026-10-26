"""Validate independent spot grades and expose disagreements without auto-resolving them."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
GRADING = ROOT / 'source-grading'
sys.path.insert(0, str(GRADING / 'engine'))
import source_grade
import qualify

def read(path):
    return json.loads(path.read_text())

spot = GRADING / 'spot-audit'
selection = read(spot / 'selection.json')
corrections = read(GRADING / 'corrections.json')
spot_corrections = read(spot / 'corrections.json') if (spot / 'corrections.json').exists() else {}
rows = []
for slot in selection['reports']:
    sid = slot['spot_id']
    workspace = spot / 'inputs' / sid
    assert qualify.tree_hash(workspace) == slot['input_sha256']
    report = (workspace / 'reports' / f'{sid}.md').read_text()
    key = read(workspace / 'expected.json')
    original_path = corrections.get(slot['case_id'] + '/' + slot['report_id'], {}).get('path', f"grades/{slot['case_id']}/{slot['report_id']}.json")
    primary = read(GRADING / original_path)
    assert primary['report_id'] == slot['report_id']
    spot_path = spot_corrections.get(sid, {}).get('path', f'grades/{sid}.json')
    audit = read(spot / spot_path)
    assert audit['report_id'] == sid
    first, _ = source_grade.score(report, primary, key, workspace)
    second, _ = source_grade.score(report, audit, key, workspace)
    differences = [{'id': cid, 'primary': value, 'spot': second['case_results'][cid]} for cid, value in first['case_results'].items() if value != second['case_results'][cid]]
    flags = [{'id': flag, 'primary': value, 'spot': second['report_checks'][flag]} for flag, value in first['report_checks'].items() if value != second['report_checks'][flag]]
    errors = lambda grade: [claim for claim in grade['claims'] if claim['error_type'] is not None]
    rows.append(dict(slot, case_checks=len(first['case_results']), case_differences=differences, check_differences=flags,
                     primary_grade=original_path, spot_grade=spot_path, primary_errors=errors(primary), spot_errors=errors(audit)))
assert len(rows) == 4
result = {'method': 'Fresh independent source audits of four preselected reports. Differences are exposed for source adjudication, not automatically treated as grading errors; claim granularity can differ.',
          'reports': rows, 'case_checks': sum(row['case_checks'] for row in rows),
          'case_disagreements': sum(len(row['case_differences']) for row in rows),
          'report_check_disagreements': sum(len(row['check_differences']) for row in rows)}
(spot / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: value for key, value in result.items() if key != 'reports'}, indent=2))
