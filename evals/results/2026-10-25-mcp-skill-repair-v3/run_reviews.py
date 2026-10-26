from concurrent.futures import ThreadPoolExecutor,as_completed
from hashlib import sha256
from pathlib import Path
import json,os,shutil,tempfile,time
import coverage_eval as runner
HERE=Path(__file__).resolve().parent
metadata=json.loads(Path('/private/tmp/brace-claude-pinned-location.json').read_text())
assert sha256(Path(metadata['binary']).read_bytes()).hexdigest()==metadata['sha256']
os.environ['BRACE_EVAL_CLAUDE']=metadata['binary'];os.environ['DISABLE_AUTOUPDATER']='1'
suite=json.loads((HERE/'snapshot/coverage/suite.json').read_text());campaign=json.loads((HERE/'campaign.json').read_text());campaign.update(status='repair_reviews_running',execution_scope='Nine fresh skill-only primary reviews of three known regression cases; no automatic grader calls',pinned_cli=metadata,selected_fixtures=['otter','badger','wren'],actual_planned_reviews=9,grader='Independent source/report/key audit after reviews, separate artifact');runner.write_json(HERE/'campaign.json',campaign)

def run(fixture,index):
 out=HERE/f'{fixture}.skill.run-{index}';out.mkdir();record={'fixture':fixture,'arm':'skill','run':index,'status':'review_error'}
 try:
  with tempfile.TemporaryDirectory(prefix='brace-mcp-repair-') as tmp:
   work=Path(tmp);runner.copy_common(HERE,fixture,work);shutil.copytree(HERE/'snapshot/skill',work/'skill');prompt=suite['prompts']['skill'];context=runner.skill_catalog(work/'skill');(out/'prompt.txt').write_text(prompt);(out/'system-context.txt').write_text(runner.base.SAFETY+context)
   started=time.monotonic();result,runtime,issues=runner.base.call(work,prompt,out/'review.log',900,system_context=context);text=result.get('result','');assert text.strip(),'Empty report';(out/'report.md').write_text(text+'\n');record.update(status='review_complete',runtime=runtime,tool_issues=issues,seconds=time.monotonic()-started,cost_usd=result.get('total_cost_usd'),skill_loaded=runner.skill_was_read(out/'review.log',work))
   if any(i.startswith(('Unexpected available','Input workspace changed','Assistant model changed','Requested Sonnet','Out-of-workspace','Parent traversal','Unexpected tool use')) for i in issues):raise ValueError('Review input/runtime integrity violation')
 except Exception as exc:record.update(status='review_error',error=str(exc))
 runner.write_json(out/'run.json',record);print(fixture,index,record['status'],flush=True);return record
results=[]
with ThreadPoolExecutor(max_workers=3) as pool:
 for task in as_completed([pool.submit(run,f,n) for n in range(1,4) for f in ['otter','badger','wren']]):
  results.append(task.result());runner.write_json(HERE/'repair.json',{'complete':len(results)==9,'planned_reviews':9,'scope':'Known-case repair regression, not a new holdout or three-arm comparison','runs':results})
assert runner.base.tree_hash(HERE/'snapshot')==campaign['snapshot_sha256'];assert sha256(Path(metadata['binary']).read_bytes()).hexdigest()==metadata['sha256'];campaign['status']='repair_reviews_finished_pending_audit';runner.write_json(HERE/'campaign.json',campaign)
