# cloudops-agent

On-call assistant for the platform team. It receives Alertmanager webhooks, investigates with
metrics and logs, and can scale a deployment, roll back a Flux HelmRelease, and resize or
replace nodes through the cloud MCP server. It posts what it did to the owning team's Slack channel.

Teams are tenants. Each team owns namespaces and node groups listed in `config/teams.yaml`.
High-impact tools (`impact: high` in `config/tools.yaml`) wait for a team approver in Slack.

| Path | What it is |
|---|---|
| `cmd/cloudops-agent` | Entrypoint: webhook server, wiring, audit retention |
| `internal/runner`, `internal/agent` | Model loop; identity and run budget |
| `internal/tools` | Registry, router, built-in tools, redaction |
| `internal/mcpclient` | Starts the cloud MCP server, checks and binds its tools |
| `internal/investigator` | Read-only sub-agents that test hypotheses in parallel |
| `internal/approval`, `internal/audit` | Approval grants; Postgres audit trail |
| `internal/killswitch` | Halt flag watcher |
| `deploy/k8s`, `terraform/` | Manifests; IAM |

## Context-size telemetry

Every action span and audit row carries `cloudops.context.tokens` and `cloudops.context.method`.
The value is the input side of the model call that proposed the action:
`input_tokens + cache_read_input_tokens + cache_creation_input_tokens` (`method=provider_usage`).
The loop never compacts or truncates history; a run that passes `max_input_tokens` stops. With no
usage block the value is NULL and `method=unavailable`, never 0. Provider-side context handling is
not visible to us and is not counted.

## Halting

```
kubectl -n cloudops patch configmap cloudops-control -p '{"data":{"halt":"true"}}'
```

The agent watches the ConfigMap and cancels every run, investigator and in-flight tool call.
