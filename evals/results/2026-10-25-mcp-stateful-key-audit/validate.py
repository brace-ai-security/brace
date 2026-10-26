"""Reproduce static artifact checks. Never import or execute fixture modules."""
from pathlib import Path
import ast
import json
import sys
import tomllib

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(REPO / 'evals/mcp'))
import coverage_eval
import qualify

def read(path):
    return json.loads(path.read_text())

quote_count = 0
for batch in ['A', 'B', 'C']:
    packet = ROOT / 'audit-inputs' / batch
    original = ROOT / f'audit-{batch}.source-first.json'
    selected = ROOT / 'audit-A.source-first.exact-quotes.json' if batch == 'A' else original
    for path in [selected, ROOT / f'audit-{batch}.json', ROOT / f'audit-{batch}.recheck.json']:
        def walk(value):
            global quote_count
            if isinstance(value, dict):
                if isinstance(value.get('path'), str) and value['path'].startswith('source/') and 'quote' in value:
                    target = packet / value['path']
                    assert target.resolve().is_relative_to(packet.resolve())
                    assert value['quote'] and value['quote'] in target.read_text(), (path, value)
                    quote_count += 1
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(read(path))
    initial = read(ROOT / f'audit-{batch}.json')
    recheck = read(ROOT / f'audit-{batch}.recheck.json')
    verdict = recheck.get('overall_verdict', recheck.get('verdict'))
    assert verdict == 'accept'
    assert len(initial['cases']) == 4
    for case in initial['cases']:
        cid = case.get('case_id', case.get('case'))
        key = read(packet / 'keys' / f'{cid}.json')
        ids = {row['id'] for group in ['must_find', 'guards', 'coverage'] for row in key[group]}
        assert ids == set(case['confirmed_keyed_ids']) | set(case['challenged_ids'])

snapshot = ROOT / 'snapshot-v2/data'
suite = coverage_eval.validate(snapshot)
files = [path for path in (snapshot / 'fixtures').rglob('*') if path.is_file()]
for path in files:
    if path.suffix == '.py':
        ast.parse(path.read_text(), filename=str(path))
    elif path.suffix == '.json':
        json.loads(path.read_text())
    elif path.suffix == '.toml':
        tomllib.loads(path.read_text())
assert qualify.tree_hash(REPO / 'evals/mcp/stateful') == qualify.tree_hash(snapshot)
skill_hash = qualify.tree_hash(REPO / 'skills/brace-mcp-review')
assert skill_hash == 'ee2b246495ebe9f01565590eddde62c475b2eee2286754e2eb84b6a8cbe7d294'
assert qualify.tree_hash(snapshot / 'fixtures') == qualify.tree_hash(ROOT / 'snapshot/data/fixtures')
for slot in read(ROOT / 'audit-mapping.json'):
    for suffix, folder in [('.json', 'expected'), ('.witness.json', 'witnesses')]:
        packet = ROOT / 'recheck-inputs' / slot['batch'] / (slot['id'] + suffix)
        frozen = snapshot / folder / (slot['fixture'] + '.json')
        assert packet.read_bytes() == frozen.read_bytes()
validation = {'selected_audit_source_quotes_checked': quote_count,
              'fixture_files': len(files), 'all_keyed_ids_audited': True,
              'fixture_ast_json_toml': 'pass; no execution/import',
              'source_key_anchors': 'pass', 'working_data_matches_revised_freeze': True,
              'fixture_source_unchanged_between_freezes': True, 'skill_unchanged': True,
              'fixture_execution': False, 'target_reviewer_trials': 0,
              'source_first_quote_provenance': 'Pre-key findings retained. A compact excerpts expanded mechanically after key review; C two quote-format corrections/recovered original recorded separately.'}
(ROOT / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
print(json.dumps(validation, indent=2))
