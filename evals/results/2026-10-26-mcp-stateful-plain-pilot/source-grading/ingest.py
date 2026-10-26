"""Derive source-audited scores without overwriting reviewer or grader artifacts."""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import json,statistics,sys

CAMP=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(CAMP));sys.path.insert(0,str(CAMP/'source-grading/engine'))
import coverage_eval as runner
runner.ARMS = ('plain',)
import source_grade


def read(path):return json.loads(path.read_text())

root=CAMP/'source-grading';index=read(root/'index.json');campaign=read(CAMP/'campaign.json');suite=read(CAMP/'snapshot/coverage/suite.json')
assert runner.base.tree_hash(CAMP/'snapshot')==campaign['snapshot_sha256']
for name,field in [('PROTOCOL.md','protocol_sha256'),('source_grade.py','engine_sha256'),('qualify.py','helper_sha256'),('TASK.md','task_sha256')]:
 assert sha256((root/'engine'/name).read_bytes()).hexdigest()==index[field]
rows=[];errors=[];corrections=read(root/'corrections.json') if (root/'corrections.json').exists() else {}
for case in index['cases']:
 workspace=root/'inputs'/case['case_id'];key=read(CAMP/'snapshot/coverage/expected'/f"{case['fixture']}.json")
 if workspace.exists():assert runner.base.tree_hash(workspace)==read(root/f"{case['case_id']}.input-hash.json")['sha256']
 for slot in case['reports']:
  run=CAMP/f"{slot['fixture']}.{slot['arm']}.run-{slot['run']}";rid=slot['report_id'];identity=case['case_id']+'/'+rid
  if not (run/'run.json').exists():continue
  row=deepcopy(read(run/'run.json'));row['raw_review_status']=row['status']
  if row['status']!='review_complete':rows.append(row);continue
  grade=root/'grades'/case['case_id']/f'{rid}.json'
  if identity in corrections:grade=root/corrections[identity]['path']
  if not grade.exists():
   row['status']='pending_source_grade';rows.append(row);continue
  try:
   audit=read(grade);assert audit['report_id']==rid,'Grade identity mismatch'
   report=(run/'report.md').read_text();assert (workspace/'reports'/f'{rid}.md').read_text()==report
   score,verdict=source_grade.score(report,audit,key,workspace)
   row.update(status='scored',score=score,source_grade=str(grade.relative_to(CAMP)),source_grade_sha256=sha256(grade.read_bytes()).hexdigest(),grading_method='Independent source-evidence audit; three opaque reports per fixture context')
   if identity in corrections:row['adjudication']=corrections[identity]
   dest=root/'scores'/case['case_id'];dest.mkdir(parents=True,exist_ok=True);runner.write_json(dest/f'{rid}.json',{'verdict':verdict,'score':score})
  except (AssertionError,ValueError,KeyError,TypeError,OSError) as exc:
   row.update(status='source_grader_error',error=str(exc));errors.append({'id':identity,'error':str(exc)})
  rows.append(row)
summary=runner.summarize(rows,suite,3)
summary['legacy_cli_grader_comparison_valid']=summary.pop('comparison_valid')
models={r.get('review_runtime',{}).get('model') for r in rows};versions={r.get('review_runtime',{}).get('claude_code_version') for r in rows}
summary['reviewer_identity_consistent']=len(models)==len(versions)==1 and None not in models and None not in versions
summary['source_audit_complete']=summary['complete'] and not errors and all(r['status']=='scored' for r in rows) and summary['reviewer_identity_consistent']
summary['grader_configuration']=index['grader_configuration'];summary['context_policy']=index['context_policy'];summary['grade_errors']=errors
summary['grading_cost_usd']=None
summary['interpretation']='Plain-only difficulty-development pilot. No skill effect comparison, independent-vulnerability sample size or deployment qualification.'
summary['limits']='Exact grader model identity/cost not exposed. Source/report quote validation does not prove semantic completeness. Narrow known-report calibration; no general qualification or deployment verdict.'
summary['totals']={}
for arm in runner.ARMS:
 attempts=[r for r in rows if r['arm']==arm];scored=[r for r in attempts if r['status']=='scored'];total={'reports':len(attempts),'scored_reports':len(scored)}
 for field in ['must_find','guards','coverage']:
  checks=[(r,c) for r in scored for c in read(CAMP/'snapshot/coverage/expected'/f"{r['fixture']}.json")[field]]
  total[field]={'met':sum(r['score']['case_results'][c['id']] for r,c in checks),'scored_total':len(checks)}
 total.update(discovery_and_claims_met=sum(r['score']['discovery_and_claims_ok'] for r in scored),unsupported_claims=sum(len(r['score']['unsupported_gaps']) for r in scored),false_assurances=sum(len(r['score']['false_assurances']) for r in scored),report_checks_met=sum(r['score']['checks_ok'] for r in scored),all_criteria_met=sum(r['score']['pass'] for r in scored),known_review_cost_usd=sum(r.get('review_cost_usd') or 0 for r in attempts),mean_review_seconds=statistics.mean(r['review_seconds'] for r in attempts if 'review_seconds' in r) if attempts else None,skill_loaded=sum(r.get('skill_loaded') is True for r in attempts) if arm=='skill' else None)
 summary['totals'][arm]=total
runner.write_json(CAMP/'source-audited-summary.json',summary)
print(json.dumps({'reports':len(rows),'source_audit_complete':summary['source_audit_complete'],'grade_errors':errors,'totals':summary['totals']},indent=2))
