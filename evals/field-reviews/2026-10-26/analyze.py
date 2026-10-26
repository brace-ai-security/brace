"""Validate static claim/advice audits and summarize without recall/pass claims."""
from pathlib import Path
from hashlib import sha256
import json,sys

OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT/'audit-engine'))
import source_grade,qualify

def read(path):return json.loads(path.read_text())
plan=read(OUT/'plan.json');index=read(OUT/'audit-index.json');cor=read(OUT/'audit-selections.json') if (OUT/'audit-selections.json').exists() else {}
for name,digest in index['engine_hashes'].items():assert sha256((OUT/'audit-engine'/name).read_bytes()).hexdigest()==digest
rows=[];faults=[];pending=[]
for case in index['cases']:
 work=Path(case['input_directory']);assert qualify.tree_hash(work)==case['input_sha256'];key=read(work/'expected.json')
 assert key['must_find']==key['guards']==key['coverage']==[]
 for slot in case['reports']:
  rid=slot['report_id'];identity=case['case_id']+'/'+rid;dest=Path(case['output_directory']);selection=cor.get(identity,{})
  grade=dest/selection.get('claims',rid+'.json');advice_path=dest/selection.get('advice',rid+'.advice.json')
  row={'target':case['target'],'arm':slot['arm'],'report_id':rid,'commit':plan['targets'][case['target']]['commit'],'primary_report':f"{case['target']}.{slot['arm']}.run-1/report.md"}
  if not grade.exists() or not advice_path.exists():row['status']='pending_audit';pending.append(identity);rows.append(row);continue
  try:
   report=(work/'reports'/f'{rid}.md').read_text();assert report==(OUT/row['primary_report']).read_text()
   audit=read(grade);assert audit['report_id']==rid;_,verdict=source_grade.score(report,audit,key,work)
   advice=read(advice_path);assert set(advice)=={'report_id','recommendations'} and advice['report_id']==rid and isinstance(advice['recommendations'],list)
   seen=set()
   for rec in advice['recommendations']:
    assert set(rec)=={'id','report_quote','status','reason','preserves_controls','required_validation','evidence'}
    assert isinstance(rec['id'],str) and rec['id'] and rec['id'] not in seen;seen.add(rec['id'])
    assert rec['status'] in {'supported_direction','conditional_direction','unsupported','regressive'}
    assert isinstance(rec['report_quote'],str) and rec['report_quote'] and rec['report_quote'] in report
    assert isinstance(rec['reason'],str) and rec['reason']
    for field in ['preserves_controls','required_validation']:
     assert (isinstance(rec[field],str) and rec[field]) or (isinstance(rec[field],list) and rec[field] and all(isinstance(x,str) and x for x in rec[field]))
    assert isinstance(rec['evidence'],list) and rec['evidence']
    for evidence in rec['evidence']:
     assert set(evidence)=={'path','quote'};path=Path(evidence['path']);assert not path.is_absolute() and '..' not in path.parts and path.parts[0] in {'repo','research','skill'}
     if path.parts[0]=='skill':assert path.parts[:2]==('skill','references')
     target=(work/path).resolve();assert target.is_relative_to(work.resolve()) and target.is_file() and evidence['quote'] and evidence['quote'] in target.read_text()
   errors=[claim for claim in audit['claims'] if claim['error_type'] is not None]
   row.update(status='audited',claims_grade=str(grade.relative_to(OUT)),advice_grade=str(advice_path.relative_to(OUT)),claim_groups=len(audit['claims']),incorrect_or_unsupported_assertions=len(errors),errors=errors,recommendations={status:sum(x['status']==status for x in advice['recommendations']) for status in ['supported_direction','conditional_direction','unsupported','regressive']},recommendation_count=len(advice['recommendations']),report_checks={k:verdict[k] for k in ['evidence_valid','source_authority_valid','no_deployment_verdict']},source_supported_findings=verdict['additional_supported_gaps'],scope_notes=verdict['notes'])
  except (AssertionError,KeyError,TypeError,ValueError,OSError) as exc:row.update(status='audit_error',error=str(exc));faults.append(identity)
  rows.append(row)
summary={'complete':len(rows)==6 and all(row['status']=='audited' for row in rows),'scope':'One real-source report per arm per implementation. No complete vulnerability ground truth, recall denominator, semantic-exhaustiveness guarantee or deployment/release verdict. Recommendation and claim error counts may overlap.','grader_identity':'Fresh independent agents inherited orchestrator default; exact served identity/cost unavailable.','rows':rows,'pending':pending,'validation_errors':faults,'by_arm':{}}
for arm in ['plain','skill']:
 group=[x for x in rows if x['arm']==arm and x['status']=='audited'];summary['by_arm'][arm]={'audited_reports':len(group),'reports_with_incorrect_assertions':sum(x['incorrect_or_unsupported_assertions']>0 for x in group),'incorrect_or_unsupported_assertions':sum(x['incorrect_or_unsupported_assertions'] for x in group),'recommendations':{status:sum(x['recommendations'][status] for x in group) for status in ['supported_direction','conditional_direction','unsupported','regressive']}}
(OUT/'advice-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({key:summary[key] for key in ['complete','pending','validation_errors','by_arm']},indent=2))
