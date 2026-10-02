# billing-agent

Accounts-receivable agent for Ledgerly customers. One deployment serves every customer
company (tenant); each run is bound to exactly one tenant.

What it does:

- reads invoices and payment records (Postgres, read replica) and the accounting system (MCP);
- chases overdue customers by email;
- issues refunds and account credits through the Payrail payments API;
- opens tickets for disputes;
- looks up collection policy in a per-tenant pgvector store;
- remembers past payment-plan negotiations per customer contact (Redis);
- hands letter drafting to a smaller sub-agent (`drafter`).

Runs are started by the internal API (user-initiated, JWT from the Ledgerly IdP) or by the
nightly dunning sweep (`python -m src.main sweep`).

## Layout

| Path | Purpose |
|---|---|
| `src/agent.py` | model loop |
| `src/identity.py` | verified run context, agent-type-id |
| `src/budget.py` | per-run budgets and spend quotas |
| `src/tools/` | tool registry and tool implementations |
| `src/mcp_client.py` | accounting MCP client, tool pinning and metadata checks |
| `src/drafter.py` | letter-drafting sub-agent |
| `config/agent.yaml` | runtime config, budgets, tool allowlist |
| `config/tool_pins.json` | approved MCP tool fingerprints |
| `k8s/` | deployment, network policy, admission policy |
| `sql/grants.sql` | database roles |

## Secrets

| Secret | Format | Source |
|---|---|---|
| Payrail access token | JWT, 15 min | STS token exchange from the pod's projected service-account token |
| Accounting MCP token | `lgr_pat_` + 40 hex | `ACCOUNTING_MCP_TOKEN` |
| Anthropic API key | `sk-ant-api03-...` | `ANTHROPIC_API_KEY` (k8s Secret) |
| Database passwords | — | `INVOICES_DSN`, `POLICY_DSN` (k8s Secret) |

## Threat model notes

Risk review RR-2026-031 (approved by the CISO, 2026-08-14) rates this deployment high-stakes
(it moves money) and medium autonomy. Deliberate model misalignment is out of scope for this
deployment per that review; hijack through customer email content and invoice notes is in scope.

## Policy store

Chunks are written only by the `policy-ingest` job (separate repo, `policy_ingest` DB role).
The agent connects as `billing_agent_ro`, which can only `SELECT`, and row-level security limits
results to the run's tenant and to active, unexpired chunks. There is no query cache, so a
quarantined or expired chunk stops appearing on the next search.

## Running locally

```
pip install -r requirements.txt
python -m src.main run --task "chase invoice INV-1042" --token "$DEV_JWT"
```
