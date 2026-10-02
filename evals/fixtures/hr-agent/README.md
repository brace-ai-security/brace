# hr-helpdesk-agent

An HR helpdesk assistant for Acme employees. It answers policy questions from the HR handbook,
shows the signed-in employee their own leave balance, files leave requests (the manager approves
them in HRIS), and hands conversations to an HR advisor.

## Components

| Component | Code | Identity |
|---|---|---|
| Agent API and loop | `src/main.py`, `src/agent.py` | SA `hr-helpdesk-agent`, SPIFFE SVID |
| Tool gateway | `src/gateway.py` | SA `hr-tool-gateway` |
| HRIS MCP server | owned by hris-platform | `spiffe://acme.example/ns/hris/sa/hris-mcp` |
| Helpdesk MCP server | owned by it-service-desk | `spiffe://acme.example/ns/helpdesk/sa/helpdesk-mcp` |
| Audit, approvals, quotas, stop flags, handbook index | Postgres (`migrations/001_init.sql`) | per-component DB roles |

## How a request flows

1. The HR portal sends the employee's SSO token. `main.py` verifies issuer, audience, expiry and
   organisation; the employee id and tenant come only from that token.
2. The loop (`agent.py`) checks the stop flags and the run budget before every model call, and
   records usage against per-user, tenant and fleet quotas.
3. Tool calls are looked up by exact name in `config/tools.yaml`. Arguments are schema-checked.
   `file_leave_request` and `escalate_to_human` pause the run and show the employee exactly what
   will be sent; the approval is bound to the run instance, operation, target and argument hash,
   expires after 10 minutes, and is consumed once.
4. MCP calls go to the gateway with a 300-second token for that one tool scope, minted by STS
   from the agent's workload identity and the employee's token. The gateway verifies the token
   and its certificate binding, checks scope, stop flags, rate limits and argument schema, swaps
   the token for one addressed to the MCP server, and validates the response schema.
5. Tool output is size-, schema- and content-checked and redacted before the model sees it.
   Handbook passages are filtered at query time to documents the employee may see.
6. Every step writes an `audit.events` row with the six identity fields and trace context.
   If the audit write fails, the run stops.

Escalations are delivered even during gateway maintenance windows.

## Stopping the agent

Operators with the `hr_agent_operator` DB role insert into `control.stop_flags`:

```sql
INSERT INTO control.stop_flags (scope, value, reason) VALUES ('fleet', NULL, 'incident 2291');
-- or scope 'agent_type' / 'agent_instance' / 'subject' / 'agent_principal'
```

Running agents see the flag within 2 seconds and cancel in-flight work; the gateway refuses
calls immediately. Target stop time: 10 seconds. The agent's DB role can only read this table.
Last drill: see `docs/drills/` in the ops repo.

## Audit retention

Audit records are kept for six months (Acme records policy; employment-related AI use in the EU).
Partitions are created and dropped nightly by `k8s/audit-maintenance.yaml`. Access is limited to
`hr_audit_reader`.

## Releases

Merges to `main` build, sign and attest the image, compute the agent-type-id over every file in
`src/`, `prompts/`, `config/`, plus `requirements.txt`, `Dockerfile`, the image digest and the model
record, and stamp `release/manifest.yaml`. Pods refuse to start if the type id they compute
differs from the one they were deployed with. Kyverno admits only signed images built by this
workflow from `main`.
