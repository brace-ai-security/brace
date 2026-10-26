from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json,os,shutil,tempfile,time
from pathlib import Path
import coverage_eval as runner
HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'2026-10-24-mcp-three-arm'
metadata=json.loads(Path('/private/tmp/brace-claude-pinned-location.json').read_text())
assert sha256(Path(metadata['binary']).read_bytes()).hexdigest()==metadata['sha256']
os.environ['BRACE_EVAL_CLAUDE']=metadata['binary'];os.environ['DISABLE_AUTOUPDATER']='1'
samples=[('linnet.plain.run-1',1,0),('tern.plain.run-1',1,0),('badger.skill.run-1',0,1),('wren.plain.run-3',0,1),('gannet.plain.run-2',0,0),('wren.baseline.run-2',0,0)]
suite=json.loads((HERE/'snapshot/coverage/suite.json').read_text())

def review(sample):
 name,unsupported,assurances=sample;fixture=name.split('.')[0];out=HERE/name;out.mkdir()
 report=(PRIOR/name/'report.md').read_text();(out/'report.md').write_text(report)
 record={'source_report':str((PRIOR/name/'report.md').relative_to(HERE.parent)),'report_sha256':sha256((PRIOR/name/'report.md').read_bytes()).hexdigest(),'expected_counts':{'unsupported':unsupported,'false_assurances':assurances},'status':'grader_error'}
 try:
  with tempfile.TemporaryDirectory(prefix='brace-grader-calibration-') as tmp:
   work=Path(tmp);runner.copy_common(HERE,fixture,work);shutil.copytree(HERE/'snapshot/skill/references',work/'skill/references');(work/'report.md').write_text(report);key=json.loads((HERE/'snapshot/coverage/expected'/f'{fixture}.json').read_text());runner.write_json(work/'expected.json',key)
   started=time.monotonic();result,runtime,issues=runner.base.call(work,runner.grader_prompt(suite['task']),out/'judge.log',900,runner.base.JUDGE_SCHEMA,system_context='');record.update(runtime=runtime,tool_issues=issues,cost_usd=result.get('total_cost_usd'),seconds=time.monotonic()-started)
   verdict=result.get('structured_output')
   if verdict is None:verdict=json.loads(result['result'])
   runner.write_json(out/'verdict.json',verdict)
   if issues:raise ValueError('Grader tool/boundary issue')
   score=runner.base.grade(report,verdict,key);record.update(status='scored',score=score,observed_counts={'unsupported':len(score['unsupported_gaps']),'false_assurances':len(score['false_assurances'])});record['target_counts_match']=record['expected_counts']==record['observed_counts']
 except Exception as exc:record['error']=str(exc)
 runner.write_json(out/'run.json',record);print(name,record['status'],record.get('target_counts_match'),flush=True);return record
results=[]
with ThreadPoolExecutor(max_workers=2) as pool:
 for task in as_completed([pool.submit(review,s) for s in samples]):
  results.append(task.result());runner.write_json(HERE/'calibration.json',{'complete':len(results)==len(samples),'scope':'Known-report grader regression, no general calibration claim','runs':results})
c=json.loads((HERE/'campaign.json').read_text());assert runner.base.tree_hash(HERE/'snapshot')==c['snapshot_sha256'];c['status']='grader_calibration_finished';c['pinned_cli']=metadata;runner.write_json(HERE/'campaign.json',c)
