# research-agent

Internal research assistant for Northwind's strategy team. Staff ask a question in the web UI;
the agent searches the public web, reads pages, and writes a cited brief. It only reads. It has
no write tools, no memory between conversations, and does not start other agents.

- Users: Northwind employees, signed in through the company SSO proxy (oauth2-proxy).
- Data: public web pages only. Briefs are shown to the requesting user and not stored.
- Model: Claude Sonnet 4.5, pinned snapshot (see `config/agent.yaml`).

## Layout

- `src/web.py` – FastAPI app behind oauth2-proxy; one request = one run.
- `src/agent.py` – tool loop with hard limits.
- `src/tools/` – `web_search`, `fetch_page`.
- `src/render.py` – converts the model's Markdown answer to HTML for the UI.
- `src/telemetry.py` – OTel spans with identity fields.
- `src/agent_type_id.py` – content hash of the deployed agent.

## Stopping the agent

Set `research-agent-halt` to `"1"` in the `research-agent-control` ConfigMap (platform on-call
only; the agent's service account has no RBAC permissions), or scale the deployment to zero.
Running loops read the mounted flag before every model call and every tool call.

## Owners

Accountable: Director of Strategy. Operational owner: `@northwind/ml-platform`.
