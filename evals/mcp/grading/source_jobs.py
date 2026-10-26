"""Prepare opaque, source-only grading batches from completed reviewer reports."""
from pathlib import Path
from hashlib import sha256
import json,random,shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qualify


def prepare(campaign, protocol, engine, seed=20261025):
    campaign=Path(campaign).resolve();root=campaign/'source-grading';root.mkdir()
    (root/'inputs').mkdir();(root/'grades').mkdir();(root/'engine').mkdir()
    for path in [Path(protocol),Path(protocol).with_name('TASK.md'),Path(engine),Path(qualify.__file__)]:
        shutil.copyfile(path,root/'engine'/path.name)
    suite=json.loads((campaign/'snapshot/coverage/suite.json').read_text());mapping=[]
    for n,fixture in enumerate(suite['fixtures'],1):
        slots=[{'fixture':fixture['name'],'arm':a,'run':r} for r in range(1,4) for a in ['baseline','plain','skill']]
        random.Random(seed+n).shuffle(slots)
        mapping.append({'case_id':f'B{n:02}','fixture':fixture['name'],'reports':[dict(slot,report_id=f'R{i:02}') for i,slot in enumerate(slots,1)]})
    record={'seed':seed,'protocol_sha256':sha256(Path(protocol).read_bytes()).hexdigest(),'task_sha256':sha256(Path(protocol).with_name('TASK.md').read_bytes()).hexdigest(),'engine_sha256':sha256(Path(engine).read_bytes()).hexdigest(),'helper_sha256':sha256(Path(qualify.__file__).read_bytes()).hexdigest(),'cases':mapping,'grader_configuration':'Independent agents inherit orchestrator default; exact served-model metadata is unavailable','context_policy':'One fresh grader context per fixture, nine shuffled reports; no arm labels or skill workflow. Style may reveal arm. Filesystem separation is procedural, not an OS grader sandbox.'}
    (root/'index.json').write_text(json.dumps(record,indent=2)+'\n');return record


def ready_batch(campaign, case_id):
    campaign=Path(campaign).resolve();root=campaign/'source-grading';index=json.loads((root/'index.json').read_text());case=next(c for c in index['cases'] if c['case_id']==case_id);dest=root/'inputs'/case_id
    if dest.exists():return False
    for slot in case['reports']:
        run=campaign/f"{slot['fixture']}.{slot['arm']}.run-{slot['run']}"
        if not (run/'run.json').exists():return False
        if json.loads((run/'run.json').read_text())['status']!='review_complete':return False
    dest.mkdir();data=campaign/'snapshot/coverage'
    shutil.copytree(data/'fixtures'/case['fixture'],dest/'repo');shutil.copytree(data/'research',dest/'research');shutil.copytree(campaign/'snapshot/skill/references',dest/'skill/references');shutil.copyfile(data/'expected'/f"{case['fixture']}.json",dest/'expected.json');shutil.copyfile(root/'engine/PROTOCOL.md',dest/'PROTOCOL.md');shutil.copyfile(root/'engine/TASK.md',dest/'TASK.md');(dest/'reports').mkdir();jobs=[]
    for slot in case['reports']:
        rid=slot['report_id'];run=campaign/f"{slot['fixture']}.{slot['arm']}.run-{slot['run']}";shutil.copyfile(run/'report.md',dest/'reports'/f'{rid}.md');jobs.append({'report_id':rid,'report':f'reports/{rid}.md','output':f'../../grades/{case_id}/{rid}.json'})
    (root/'grades'/case_id).mkdir();(dest/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n');(root/f'{case_id}.input-hash.json').write_text(json.dumps({'sha256':qualify.tree_hash(dest)},indent=2)+'\n');return True


if __name__=='__main__':
    campaign=Path(sys.argv[1])
    for case in json.loads((campaign/'source-grading/index.json').read_text())['cases']:
        if ready_batch(campaign,case['case_id']):print(case['case_id'],'ready')
