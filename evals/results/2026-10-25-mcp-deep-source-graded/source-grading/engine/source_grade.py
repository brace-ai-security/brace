"""Validate source-audit claim decisions and project them to the existing scorer."""
from pathlib import Path
import qualify

VERDICT_FIELDS = set(qualify.JUDGE_SCHEMA['required']) - {'unsupported_gap_claims', 'false_assurance_claims'}
OUTCOMES = {'supported', 'qualified', 'unsupported', 'contradicted'}
ERRORS = {'unsupported_gap', 'false_assurance'}


def score(report, audit, key, workspace):
    if not isinstance(audit, dict) or set(audit) != {'report_id', 'case_verdict', 'claims'}:
        raise ValueError('Invalid source-audit envelope')
    if not isinstance(audit['report_id'], str) or not audit['report_id']:
        raise ValueError('Missing report identity')
    if not isinstance(audit['case_verdict'], dict):
        raise ValueError('Invalid case verdict')
    verdict = dict(audit['case_verdict'])
    if set(verdict) != VERDICT_FIELDS or not isinstance(audit['claims'], list) or not audit['claims']:
        raise ValueError('Invalid case verdict or claims')
    groups = {'unsupported_gap': [], 'false_assurance': []}
    seen = set()
    workspace = Path(workspace).resolve()
    for row in audit['claims']:
        if not isinstance(row, dict) or set(row) != {'id', 'report_quote', 'outcome', 'error_type', 'reason', 'evidence'}:
            raise ValueError('Invalid claim schema')
        if not isinstance(row['id'], str) or not row['id'] or row['id'] in seen:
            raise ValueError('Duplicate or missing claim id')
        seen.add(row['id'])
        if not isinstance(row['report_quote'], str) or not row['report_quote'] or row['report_quote'] not in report:
            raise ValueError('Claim quote is absent from report')
        if not isinstance(row['reason'], str) or not row['reason'].strip() or not isinstance(row['outcome'], str) or row['outcome'] not in OUTCOMES:
            raise ValueError('Invalid claim decision')
        wrong = row['outcome'] in {'unsupported', 'contradicted'}
        if (wrong and (not isinstance(row['error_type'], str) or row['error_type'] not in ERRORS)) or (not wrong and row['error_type'] is not None):
            raise ValueError('Claim outcome and error category disagree')
        if not isinstance(row['evidence'], list) or not row['evidence']:
            raise ValueError('Claim needs source evidence')
        for item in row['evidence']:
            if not isinstance(item, dict) or set(item) != {'path', 'quote'}:
                raise ValueError('Invalid source evidence')
            if not isinstance(item['path'], str) or not isinstance(item['quote'], str) or not item['quote']:
                raise ValueError('Invalid source evidence text')
            path = Path(item['path'])
            if path.is_absolute() or '..' in path.parts or path.parts[:1] not in {('repo',), ('research',), ('skill',)}:
                raise ValueError('Evidence path escapes authorized sources')
            if path.parts[:1] == ('skill',) and path.parts[:2] != ('skill', 'references'):
                raise ValueError('Grader may use skill references only')
            target = (workspace / path).resolve()
            if not target.is_relative_to(workspace) or not target.is_file() or item['quote'] not in target.read_text():
                raise ValueError('Source quote is absent or outside workspace')
        if wrong:
            groups[row['error_type']].append(f"{row['report_quote']} — {row['reason']}")
    verdict['unsupported_gap_claims'] = groups['unsupported_gap']
    verdict['false_assurance_claims'] = groups['false_assurance']
    return qualify.grade(report, verdict, key), verdict
