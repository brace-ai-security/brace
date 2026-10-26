"""Freeze opaque report/source packets for advice audits; no upstream execution."""
from pathlib import Path
from hashlib import sha256
import json,random,shutil
import qualify

OUT=Path(__file__).resolve().parent
plan=json.loads((OUT/'plan.json').read_text());base=Path(plan['frozen_common']);packets=base.parent/'audit-inputs';packets.mkdir(exist_ok=True)
index_path=OUT/'audit-index.json'
if not index_path.exists():
 cases=[]
 for n,(name,target) in enumerate(plan['targets'].items(),1):
  arms=['plain','skill'];random.Random(20261026+n).shuffle(arms)
  cases.append({'case_id':f'A{n:02}','target':name,'reports':[{'report_id':f'R{i:02}','arm':arm,'run':1} for i,arm in enumerate(arms,1)]})
 index={'cases':cases,'method':'One fresh independent source/advice auditor per implementation; two opaque reports. No source/advice recall denominator. Filesystem blinding procedural; style may reveal arm. Exact served auditor identity/cost not exposed.','engine_hashes':{p.name:sha256(p.read_bytes()).hexdigest() for p in (OUT/'audit-engine').iterdir() if p.is_file()}}
 index_path.write_text(json.dumps(index,indent=2)+'\n')
index=json.loads(index_path.read_text())
for case in index['cases']:
 dest=packets/case['case_id']
 if dest.exists():continue
 target=case['target']
 runs=[OUT/f"{target}.{row['arm']}.run-1" for row in case['reports']]
 if not all((run/'run.json').exists() and json.loads((run/'run.json').read_text())['status']=='review_complete' for run in runs):continue
 dest.mkdir();shutil.copytree(Path(plan['targets'][target]['source_directory']),dest/'repo');shutil.copytree(base/'research',dest/'research');shutil.copytree(base/'skill/references',dest/'skill/references');(dest/'reports').mkdir()
 for name in ['PROTOCOL.md','CLARIFICATIONS.md','FIELD-TASK.md']:shutil.copyfile(OUT/'audit-engine'/name,dest/name)
 (dest/'expected.json').write_text(json.dumps({'must_find':[],'guards':[],'coverage':[],'forbidden_output':[]})+'\n')
 jobs=[];output=OUT/'audits'/target;output.mkdir(parents=True,exist_ok=True)
 for row,run in zip(case['reports'],runs):
  rid=row['report_id'];shutil.copyfile(run/'report.md',dest/'reports'/f'{rid}.md');jobs.append({'report_id':rid,'report':f'reports/{rid}.md','output_directory':str(output)})
 (dest/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n');case.update(input_directory=str(dest),input_sha256=qualify.tree_hash(dest),output_directory=str(output));index_path.write_text(json.dumps(index,indent=2)+'\n');print(case['case_id'],target,'ready')
