from pathlib import Path
import json
root=Path('/private/tmp/brace-real-mcp-2026-10-26/audit-inputs/A02')
out=Path('/Users/brenn/dev/brace/evals/field-reviews/2026-10-26/audits/notion')
def evidence(p,q):
 assert q in (root/p).read_text()
 return {'path':p,'quote':q}
def add(d,q,status,reason,*es):
 assert q in (root/'reports'/f"{d['report_id']}.md").read_text()
 d['claims'].append(dict(id=f"C{len(d['claims'])+1:02}",report_quote=q,outcome=status,error_type=None,reason=reason,evidence=[evidence(*e) for e in es]))
r1=json.loads((out/'R01.json').read_text())
add(r1,'`GET /health` is unauthenticated and returns the port and transport (low).','supported','Explicit unauthenticated health route; timestamp/status also returned. Does not imply debug credentials exposed.',('repo/scripts/start-server.ts',"app.get('/health', (req, res) => {"),('repo/scripts/start-server.ts',"transport: 'http',\n        port: options.port"))
add(r1,'the Dockerfile is Linux (`node:20-slim`).','supported','Declared Node Debian slim image is Linux; final image build or deployment not inspected.',('repo/Dockerfile','FROM node:20-slim'))
add(r1,'`docker-compose.yml` publishes no ports and passes no environment.','supported','Complete supplied compose has only build, stdin, tty, restart. Dockerfile default env remains distinct.',('repo/docker-compose.yml','services:\n  notion-mcp-server:\n    build: .\n    stdin_open: true\n    tty: true\n    restart: unless-stopped'))
add(r1,'Optional per-session Notion token via the `Notion-Token` header, when `--enable-token-passthrough` or `ENABLE_TOKEN_PASSTHROUGH=true` is set.','supported','Opt-in gate, dedicated token header, per-session headers, CLI/environment precedence match code. With gateway auth enabled Authorization is not reused for Notion.',('repo/scripts/server-options.ts',"let enableTokenPassthrough = process.env.ENABLE_TOKEN_PASSTHROUGH === 'true'"),('repo/scripts/start-server.ts','allowAuthorizationFallback: options.unsafeDisableAuth,'),('repo/src/openapi-mcp-server/mcp/token.ts',"export const NOTION_TOKEN_HEADER = 'notion-token'"))
add(r1,'No SDK OAuth client or server-auth code found in the files read','qualified','Source-bounded absence appropriately leaves unread auth helpers outside completeness assessment. Imported unused auth templates do not establish a reachable SDK OAuth server; active gateway uses own bearer.',('repo/scripts/start-server.ts',"app.use('/mcp', authenticateToken)"),('repo/src/openapi-mcp-server/mcp/proxy.ts',"this.server = new Server({ name, version: '1.0.0' }, { capabilities: { tools: {} } })"))
add(r1,'2026-10-15 / 2026-10-19','supported','S2/S3 dates in table agree with primary record publication/update. Source collection retrieval and reachability recheck are separate and not claimed as current review verification.',('research/sources.json','"published_at": "2026-10-15T13:10:32Z"'),('research/sources.json','"updated_at": "2026-10-19T20:06:02Z"'))
r2=json.loads((out/'R02.json').read_text())
c=next(c for c in r2['claims'] if c['id']=='C17')
c.update(outcome='qualified',error_type=None,reason='Read literally, this says a missing NOTION_TOKEN is concealed by a truthy {} header environment, not that a configured token is ignored. HTTP hasEnvNotionToken uses Boolean on the raw string, so missing passthrough/startup credentials can escape early rejection and fail upstream later. The precise upstream 401 depends on service response. Empty headers correctly fall through to a configured NOTION_TOKEN. Do not count this sentence as a fallback error.')
r2['case_verdict']['notes']=r2['case_verdict']['notes'].replace('Header fallback assertions and transport-registration timing overreach are material;','The unconditional non-object-header fallback assertion and transport-registration timing overreach are material; the Docker missing-token sentence is a qualified late-failure observation;')
r2['case_verdict']['additional_supported_gaps']=r2['case_verdict']['additional_supported_gaps'][2:]
for name,obj in [('R01.corrected.json',r1),('R02.corrected.json',r2)]:
 p=out/name
 assert not p.exists()
 p.write_text(json.dumps(obj,indent=2)+'\n')
