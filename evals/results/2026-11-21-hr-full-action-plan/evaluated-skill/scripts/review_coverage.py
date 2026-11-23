#!/usr/bin/env python3
"""Static candidate inventory and evidence ledger. Never executes repository code.

python review_coverage.py inventory REPO
python review_coverage.py ledger FINDINGS.json CHECK --rows rows.json --attempts attempts.json

Inventory matches are candidates, not findings or proof of completeness. Review
aliases, wrappers, computed calls and unsupported languages manually as well.
"""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

from prescan import walk, MAX_FILE_BYTES, COMMENT_LINE

FIELDS = ['server_instructions', 'tool_names', 'tool_titles', 'tool_descriptions',
          'input_schemas', 'output_schemas', 'annotations', 'prompt_templates', 'resource_templates']
RULES = ['hidden_instructions', 'cross_tool_references', 'control_characters',
         'role_overrides', 'encoded_payloads', 'data_sending_targets', 'length_limits']
KINDS = {
    'model_call': re.compile(r'(?:messages|responses|completions)\.(?:create|stream)|(?:generateText|generateObject|invoke_model)\s*\('),
    'handoff': re.compile(r'(?:spawn|handoff|delegate|run_subagent|extract_document|subagent_started|subagent_finished)\b', re.I),
    'tool_call': re.compile(r'(?:\.invoke\s*\(|execute_tool\s*\(|dispatch_tool\s*\()'),
    'tool_registration': re.compile(r'(?:registerMcp|register_tool|registerTool|add_tool|\.add)\s*\('),
    'audit_write': re.compile(r'(?:audit\.record|recordAudit|audit\.emit|audit\.write)\s*\('),
}
TARGETS = {'B07.2': ['model_call', 'tool_call'], 'B07.4': ['model_call', 'tool_call'],
           'R07.1': ['model_call', 'audit_write'], 'R07.4': ['handoff', 'audit_write']}
ATTEMPTS = {'B07.2': ['unmetered_call', 'limit_boundary'],
            'B07.4': ['multiple_runs', 'spend_before_check'],
            'E04.1': ['field_differential'], 'E04.2': ['encoded_payload', 'multiline_override'],
            'E05.2': ['repeated_confusables', 'multiple_edits', 'normalization_boundary']}
ADMISSION = re.compile(r'\b(?:minor gaps?|residual gap|uncounted|not counted|not budgeted|'
                       r'quotas? (?:are )?charged after|can slip through)\b', re.I)


def inventory(repo):
    sites, skipped = [], []
    for full, rel in walk(Path(repo).resolve()):
        if full.suffix not in ('.py', '.ts', '.tsx', '.js', '.go', '.rs') or full.name.startswith('brace-'):
            continue
        if any(part in ('test', 'tests') for part in Path(rel).parts) or re.search(r'(?:^test_|\.(?:test|spec)\.)', full.name):
            continue
        if full.stat().st_size > MAX_FILE_BYTES:
            skipped.append(rel)
            continue
        source = full.read_text(errors='replace')
        lines = source.splitlines()
        if full.suffix == '.py':
            try:
                nodes = [(n.lineno, ast.unparse(n.func) + '(') for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]
            except SyntaxError:
                skipped.append(rel)
                nodes = []
        else:
            nodes = [(i + 1, line) for i, line in enumerate(lines) if not COMMENT_LINE.match(line)]
        seen = set()
        for line, call in nodes:
            for kind, pattern in KINDS.items():
                if not pattern.search(call) or (line, kind) in seen:
                    continue
                seen.add((line, kind))
                site_id = 'I' + hashlib.sha256(f'{rel}:{line}:{kind}'.encode()).hexdigest()[:10]
                sites.append({'id': site_id, 'kind': kind, 'evidence': f'{rel}:{line}', 'quote': lines[line-1].strip()})
    return {'sites': sorted(sites, key=lambda s: (s['evidence'], s['kind'])), 'skipped': skipped,
            'limitations': 'Candidate inventory only: manually trace aliases, wrappers, computed calls and unsupported languages. Tests excluded; no code executed.'}


def spec(cid):
    result = {'coverage_required': True}
    if cid in TARGETS:
        result['inventory_kinds'] = TARGETS[cid]
    if cid == 'E04.1':
        result.update(fields=FIELDS, rules=RULES)
    if cid in ATTEMPTS:
        result['attempt_categories'] = ATTEMPTS[cid]
    return result


def ledger_problems(c, meta, repo, sites=()):
    """Validate a positive claim, including candidate coverage and bypass attempts."""
    from validate_findings import quote_found, norm
    errors = []
    rows = c.get('coverage')
    if not isinstance(rows, list) or not rows:
        return ['needs coverage rows with subject, status, evidence, quote and note']
    subjects = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append('coverage rows must be objects')
            continue
        subject = row.get('subject')
        if not isinstance(subject, str) or not subject or subject in subjects:
            errors.append('coverage subjects must be nonempty and unique')
        if isinstance(subject, str):
            subjects.add(subject)
        if row.get('status') not in ('enforced', 'not_applicable'):
            errors.append(f'coverage {subject} is missing or unresolved')
        if len(norm(row.get('note', '')).split()) < 6 or not quote_found(repo, row.get('evidence'), row.get('quote')):
            errors.append(f'coverage {subject} needs quoted code and a six-word explanation')
        if c.get('id') in ('B07.2', 'B07.4') and row.get('status') == 'enforced' and row.get('phase') not in ('before', 'reserved_before', 'bounded_after'):
            errors.append(f'coverage {subject} needs enforcement/reservation or a proved finite overshoot bound, not a counter alone')
        if row.get('phase') == 'bounded_after' and len(norm(row.get('bound', '')).split()) < 6:
            errors.append(f'coverage {subject} needs a finite overshoot formula and the code/config that bounds concurrency and per-call spend')
        if (meta.get('fields') and row.get('status') == 'enforced'
                and (not isinstance(row.get('rules'), list) or not all(isinstance(r,str) for r in row['rules'])
                     or not set(meta['rules']).issubset(row['rules']))):
            errors.append(f'coverage {subject} does not account for every scanner rule family')
    required = set(meta.get('fields', [])) | {s['id'] for s in sites if s['kind'] in meta.get('inventory_kinds', [])}
    if required - subjects:
        errors.append('coverage omits subjects: ' + ', '.join(sorted(required - subjects)))
    deviations = c.get('deviations')
    if not isinstance(deviations, list):
        errors.append('needs explicit deviations list (empty only if none)')
    elif deviations:
        errors.append('acknowledged required-control deviations prevent holds/yes')
    if ADMISSION.search(str(c.get('note', ''))):
        errors.append('note admits an unmet control; record it as a deviation and answer no or unknown')
    attempts = c.get('attempts', [])
    if not isinstance(attempts, list):
        return errors + ['attempts must be a list']
    categories = set()
    for attempt in attempts:
        if not isinstance(attempt, dict):
            errors.append('attempts must be objects')
            continue
        if isinstance(attempt.get('category'), str):
            categories.add(attempt['category'])
        if (attempt.get('outcome') not in ('blocked', 'not_applicable') or not attempt.get('input')
                or len(norm(attempt.get('trace', '')).split()) < 8
                or not quote_found(repo, attempt.get('evidence'), attempt.get('quote'))):
            errors.append('attempt needs concrete input, quoted code and traced blocked/exempt outcome; accepted/unresolved cannot hold')
    if set(meta.get('attempt_categories', [])) - categories:
        errors.append('needs falsification attempts: ' + ', '.join(sorted(set(meta['attempt_categories']) - categories)))
    return errors


def failure_rows(c):
    """Return admitted failures and uncertainty, without interpreting free prose."""
    lists = {k: c.get(k) if isinstance(c.get(k),list) else [] for k in ('coverage','deviations','attempts')}
    rows = [r for r in lists['coverage'] if isinstance(r, dict) and r.get('status') in ('missing', 'unclear')]
    rows += [r for r in lists['deviations'] if isinstance(r, dict)]
    rows += [r for r in lists['attempts'] if isinstance(r, dict) and r.get('outcome') in ('accepted', 'unclear')]
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    scan = sub.add_parser('inventory'); scan.add_argument('repo')
    policy = sub.add_parser('policy'); policy.add_argument('check'); policy.add_argument('--repo')
    record = sub.add_parser('ledger'); record.add_argument('findings'); record.add_argument('check')
    record.add_argument('--rows', required=True); record.add_argument('--attempts'); record.add_argument('--deviations')
    args = ap.parse_args()
    if args.command == 'policy':
        table = json.loads((Path(__file__).parent.parent/'references/checks.json').read_text())
        meta = next(c for c in table[args.check.split('.')[0]]['checks'] if c['id'] == args.check)
        result = dict(meta)
        if args.repo:
            result['candidate_sites'] = [s for s in inventory(args.repo)['sites'] if s['kind'] in meta.get('inventory_kinds', [])]
        print(json.dumps(result, indent=2))
        return
    if args.command == 'inventory':
        out = Path(args.repo) / 'brace-inventory.json'
        out.write_text(json.dumps(inventory(args.repo), indent=2) + '\n')
        print(f'Wrote {out}; candidate matches need manual scope review.')
        return
    path = Path(args.findings); doc = json.loads(path.read_text())
    c = next(c for f in doc['findings'] for c in f['checks'] if c['id'] == args.check)
    for option, field in ((args.rows, 'coverage'), (args.attempts, 'attempts'), (args.deviations, 'deviations')):
        if option:
            value = json.loads(Path(option).read_text())
            if not isinstance(value, list):
                ap.error(f'{field} file must contain a list')
            c[field] = value
    path.write_text(json.dumps(doc, indent=2) + '\n')
    print(f'Saved ledger for {args.check}; run the validator before retaining yes.')


if __name__ == '__main__':
    main()
