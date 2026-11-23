"""Regression checks for universal claims, admitted omissions and blinded discovery."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import challenge
import review_coverage as coverage
import validate_findings as validator


def row(subject='main', status='enforced', **extra):
    return dict(subject=subject, status=status, evidence='app.py:1', quote='limit = 10',
                note='The harness enforces this path before dispatching work.', **extra)


def positive(cid='B02.1'):
    return dict(id=cid, met='yes', coverage=[row()], deviations=[], attempts=[],
                evidence='app.py:1', quote='limit = 10', counter_search='Traced callers and found no bypass.',
                note='The harness enforces the required control here.')


def test_inventory_finds_helper_calls_without_executing_repo(tmp_path):
    (tmp_path/'app.py').write_text('raise RuntimeError("must never execute")\n# client.messages.create()\nclient.messages.create(model="helper")\naudit.record(kind="child_finished")\n')
    sites = coverage.inventory(tmp_path)['sites']
    assert {(s['kind'], s['evidence']) for s in sites} == {('model_call','app.py:3'),('audit_write','app.py:4')}


def test_positive_must_cover_all_candidates_and_rule_families(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    c=positive('R07.1')
    errors=coverage.ledger_problems(c,coverage.spec(c['id']),tmp_path,[{'id':'Ihelper','kind':'model_call'}])
    assert any('Ihelper' in e for e in errors)
    c=positive('E04.1'); c['coverage']=[row(subject) for subject in coverage.FIELDS]
    assert any('rule family' in e for e in coverage.ledger_problems(c,coverage.spec(c['id']),tmp_path))


def test_concrete_attempts_cannot_be_accepted_while_holds(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    c=positive('E05.2')
    c['attempts']=[dict(category=category,input='repeated lookalike mutation',trace='Normalization and comparison admit this candidate without a conflict flag.',
                        outcome='accepted',evidence='app.py:1',quote='limit = 10') for category in coverage.ATTEMPTS[c['id']]]
    assert any('accepted/unresolved' in e for e in coverage.ledger_problems(c,coverage.spec(c['id']),tmp_path))


def test_budget_counter_alone_is_not_enforcement_and_bound_can_be_proved(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    c=positive('B07.2');meta=coverage.spec(c['id']);meta['attempt_categories']=[]
    assert any('overshoot' in e for e in coverage.ledger_problems(c,meta,tmp_path))
    c['coverage'][0].update(phase='bounded_after',bound='At most two in flight calls each reserve ten tokens; cited configuration bounds both quantities.')
    assert not coverage.ledger_problems(c,meta,tmp_path)


def test_missing_coverage_forces_gap_even_with_yes_label(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    c=positive();c['coverage']=[row(status='missing')]
    meta={'requirement':'Enforce the required scoped credential boundary.', 'checks':[{'id':c['id'],**coverage.spec(c['id'])}]}
    doc={'findings':[{'item':'B02','rating':'likely_pass','checks':[c],'red_flags_found':[]}]}
    validator.fix(doc,{'B02':meta},tmp_path,False)
    assert c['met']=='no' and doc['findings'][0]['rating']=='gap'


def test_challenger_admission_cannot_uphold(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    c=positive();c.pop('met');c['result']='holds';c['deviations']=[row(status='missing')]
    doc={'review_protocol':'coverage-first-v1','findings':[{'item':'B02','rating':'likely_pass',
                                                         'checks':[{'id':'B02.1','met':'yes'}]}]}
    _,problems=challenge.apply(doc,{'B02':{'verdict':'upheld','checks':[c],'note':'Small residual gap remains.'}},tmp_path)
    assert not problems and doc['findings'][0]['rating']=='gap'
    assert doc['findings'][0]['challenge']['verdict']=='failed'


def test_discovery_sheet_hides_initial_claim_and_quotes(tmp_path):
    table={'B02':{'gate':'G1','title':'Credentials','requirement':'Enforce scoped credentials.',
                  'checks':[{'id':'B02.1','check':'Scoped credentials are enforced.'}]}}
    doc={'findings':[{'item':'B02','rating':'likely_pass','summary':'UNIQUE CLAIM',
                     'checks':[{'id':'B02.1','quote':'UNIQUE SUPPORT','note':'UNIQUE NOTE'}]}]}
    challenge.make(doc,table,tmp_path,tmp_path/'sheets')
    text=(tmp_path/'sheets/B02.md').read_text()
    assert all(word not in text for word in ['UNIQUE CLAIM','UNIQUE SUPPORT','UNIQUE NOTE','likely_pass'])
    assert 'UNIQUE CLAIM' in (tmp_path/'sheets/B02.claim.json').read_text()


def test_batch_validation_checks_only_requested_items_but_requires_answers(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    script=Path(__file__).parent/'validate_findings.py'
    findings=tmp_path/'brace-findings.json'
    subprocess.run([sys.executable,str(script.parent/'new_findings.py'),str(findings)],check=True,capture_output=True)
    r=subprocess.run([sys.executable,str(script),str(findings),'--batch','B02','--before-challenges'],capture_output=True,text=True)
    assert r.returncode==1 and 'B02:' in r.stdout and 'Missing findings' not in r.stdout


def test_malformed_ledger_returns_errors_instead_of_crashing(tmp_path):
    (tmp_path/'app.py').write_text('limit = 10\n')
    c=positive('E04.1');c['coverage']=[row(subject=['invalid'],rules=None)]
    c['deviations']=None;c['attempts']=[{'category':[],'outcome':'blocked'}]
    assert coverage.ledger_problems(c,coverage.spec(c['id']),tmp_path)
    assert coverage.failure_rows(c)==[]


def test_quote_cannot_be_null_or_escape_repo(tmp_path):
    repo=tmp_path/'repo';repo.mkdir();(tmp_path/'outside.py').write_text('limit = 10\n')
    assert not validator.quote_found(repo,'../outside.py:1','limit = 10')
    assert not validator.quote_found(repo,'../outside.py:1',None)
