"""Collect the fixed 36 plain reviews; independent source grading is separate."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json
import os
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import coverage_eval as runner

runner.ARMS = ('plain',)
campaign = json.loads((ROOT / 'campaign.json').read_text())
assert campaign['status'] == 'prepared_plain_only', 'Never overwrite or retry a campaign'
suite = json.loads((ROOT / 'snapshot/coverage/suite.json').read_text())
executable = Path(campaign['cli_executable']['path'])
expected_hash = campaign['cli_executable']['sha256']
assert sha256(executable.read_bytes()).hexdigest() == expected_hash
assert runner.base.tree_hash(ROOT / 'snapshot') == campaign['snapshot_sha256']
os.environ['BRACE_EVAL_CLAUDE'] = str(executable)
os.environ['DISABLE_AUTOUPDATER'] = '1'
campaign.update(status='running_plain_reviews',started_utc=datetime.now(timezone.utc).isoformat(),pilot_driver_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
runner.write_json(ROOT / 'campaign.json', campaign)
jobs = [(fixture['name'], n) for n in range(1, 4) for fixture in suite['fixtures']]
assert len(jobs) == 36
rows = []
for start in range(0, len(jobs), 3):
    assert sha256(executable.read_bytes()).hexdigest() == expected_hash
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(runner.run_one, ROOT, fixture, 'plain', n, 900, suite['task'], False)
                   for fixture, n in jobs[start:start + 3]]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            runner.write_json(ROOT / 'summary.json', runner.summarize(rows, suite, 3))
    expected = campaign['expected_runtime']
    if any(row['status'] != 'review_complete' or any(row.get('review_runtime', {}).get(k) != expected[k]
           for k in ['model', 'claude_code_version']) for row in rows):
        campaign['status'] = 'incomplete_or_invalid'
        break
else:
    campaign['status'] = 'reviews_finished_pending_source_grades'
assert runner.base.tree_hash(ROOT / 'snapshot') == campaign['snapshot_sha256']
assert sha256(executable.read_bytes()).hexdigest() == expected_hash
campaign['finished_reviews_utc'] = datetime.now(timezone.utc).isoformat()
runner.write_json(ROOT / 'campaign.json', campaign)
print(json.dumps({'status': campaign['status'], 'reviews': len(rows)}, indent=2))
raise SystemExit(0 if campaign['status'] == 'reviews_finished_pending_source_grades' else 1)
