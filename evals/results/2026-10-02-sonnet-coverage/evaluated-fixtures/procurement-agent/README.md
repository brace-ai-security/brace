# procurement-agent

Procurement agent for Example Corp business units. It reads vendor quotes and
invoices that arrive by email, checks them against department budgets, raises
purchase orders in the ERP, pays matched invoices, and talks to staff and
vendors in Slack. It keeps short per-department notes between runs.

## Architecture

```
mail gateway --HMAC--> /ingest/mail --> documents (Postgres, per business unit)
staff (OIDC JWT) ----> /runs --> ProcurementAgent loop (app/loop.py)
                                   |-- PolicyGate (app/gate.py) + approvals (Slack buttons)
                                   |-- Budget (app/budget.py)
                                   |-- audit graph (app/audit.py -> audit_events)
                                   |-- tools:
                                   |     read_document, extract_line_items -> LineItemExtractor sub-agent
                                   |     get_budget, erp_call, create_purchase_order -> ERP MCP via gateway
                                   |     pay_invoice -> payments API
                                   |     post_slack_message -> Slack (via slack-proxy)
                                   |     memory_read, memory_write -> dept_notes
```

* **Tenancy.** Each run belongs to one business unit, taken from the `bu`
  claim of the caller's verified OIDC token. Documents, notes, approvals and
  quotas are keyed by business unit.
* **Identity.** The agent runs as the `procurement-agent` service account.
  Its projected token (10-minute lifetime) is exchanged at the internal STS
  for audience-bound tokens for the ERP gateway, payments API and Slack
  proxy. User tokens are never forwarded.
* **Approvals.** `create_purchase_order`, `pay_invoice` and vendor messages
  require an approval from a role listed in `config/policy.yaml`. Approval
  requests are posted to `#approvals-<bu>` with the argument summary.
* **Budgets.** Per-run step, time, token, cost, tool-rate and sub-agent
  limits, plus per-user, per-business-unit and fleet quotas for daily spend
  and run starts. See `config/policy.yaml`.
* **Audit.** Every run step is a row in `audit_events` linked to its parent
  step, with the six identity fields, policy version, approval id and
  decision-time context size. The agent's database role can insert audit
  rows but not update or delete them.

## Context size

Logged on every audit row as `context_tokens` and `context_method`:

| method | meaning |
|---|---|
| `count_tokens_api` | exact request counted with the provider's token-count endpoint before the call (includes cached prefix) |
| `usage_sum_estimate` | counting failed; `input_tokens + cache_read + cache_creation` from the response |
| `unavailable` | neither available; `context_tokens` is NULL, never 0 |

`context_compacted` is true when the harness dropped earlier turns before the
call (`app/loop.py:_compact`). Provider-side truncation is not visible.

## Operating

* **Halt.** Insert or update a row in `control_flags` (`scope = 'fleet'` or
  `'tenant:<bu>'`, `halted = true`) as `procurement_ops`. New runs refuse to
  start while a halt is set.
* **Release.** Merges to `main` build, sign (keyless cosign), and attest the
  image (SLSA provenance and CycloneDX SBOM). Kyverno rejects unsigned or
  unattested images in `procurement-prod`.
* **Network.** Default-deny egress with explicit rules for DNS, the egress
  proxy, the Slack proxy, the database, the ERP gateway and the STS.

## Tests

```bash
pip install -e '.[test]'
pytest -q
```
