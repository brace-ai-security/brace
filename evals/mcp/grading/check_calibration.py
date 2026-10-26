"""Reproduce critical-target checks; disputed labels stay visible and unscored."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import source_grade

ROOT=Path(__file__).resolve().parents[3]
FOLDERS=['2026-10-25-mcp-source-calibration','2026-10-25-mcp-source-validation','2026-10-25-mcp-source-controls']
all_rows=[]
for name in FOLDERS:
 out=ROOT/'evals/results'/name
 rows=[]
 for gold in json.loads((out/'gold.json').read_text()):
  rid=gold['report_id'];job=out/'inputs'/rid;report=(job/'report.md').read_text();audit=json.loads((out/'grades'/f'{rid}.json').read_text())
  if audit['report_id']!=rid:raise ValueError('Grade identity mismatch')
  score,verdict=source_grade.score(report,audit,json.loads((job/'expected.json').read_text()),job)
  needle=gold['target_quote'];start=report.index(needle);end=start+len(needle)
  positive=all(o in {'supported','qualified'} for o in gold['allowed_outcomes'])
  # Positive controls are scoped statements; retain their full paragraph context.
  if positive:
   start=report.rfind('\n\n',0,start)+2 if '\n\n' in report[:start] else 0
   boundary=report.find('\n\n',end);end=boundary if boundary>=0 else len(report)
  hits=[]
  for claim in audit['claims']:
   cstart=report.index(claim['report_quote']);cend=cstart+len(claim['report_quote'])
   if max(start,cstart)<min(end,cend):hits.append(claim)
  allowed_errors=gold.get('allowed_error_types',[gold.get('error_type')])
  match=any(c['outcome'] in gold['allowed_outcomes'] and c['error_type'] in allowed_errors for c in hits)
  if positive:match=match and not any(c['error_type'] is not None for c in hits)
  row={'report_id':rid,'scorable':gold.get('scorable',True),'critical_target_match':match,'target_decisions':[{'id':c['id'],'outcome':c['outcome'],'error_type':c['error_type']} for c in hits],'score':score}
  rows.append(row);all_rows.append(row)
  (out/'scores').mkdir(exist_ok=True);(out/'scores'/f'{rid}.json').write_text(json.dumps({'score':score,'verdict':verdict},indent=2)+'\n')
 (out/'checks.json').write_text(json.dumps({'rows':rows,'method':'Negative targets require localization to the asserted sentence; positive controls include their full scoped paragraph. Counts are critical-target checks, not exhaustive error-count accuracy.'},indent=2)+'\n')
scorable=[r for r in all_rows if r['scorable']]
summary={'scorable_targets':len(scorable),'matched':sum(r['critical_target_match'] for r in scorable),'disputed_targets_retained':sum(not r['scorable'] for r in all_rows),'gate_pass':all(r['critical_target_match'] for r in scorable),'limits':'Narrow known-report protocol calibration/validation; no population accuracy or runtime proof.'}
(ROOT/'evals/results/2026-10-25-mcp-source-calibration/gate.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if not summary['gate_pass']:raise SystemExit(1)
