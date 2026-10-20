# clinic-agent

Patient-scheduling agent for the Northbay Clinic Group. Patients reach it by SMS or by the web chat
widget on each clinic's site. It looks up, books, reschedules, and cancels appointments in the EHR,
sends SMS reminders, refunds no-show deposits, and asks the insurance-eligibility agent whether a
visit is covered.

Each clinic is a tenant. A clinic's patients, appointments, deposits, and EHR credentials are kept
separate from every other clinic's.

## Components

| Piece | Where | Notes |
|---|---|---|
| HTTP service (Fastify) | `src/server.ts` | `/v1/sms/inbound` webhook, `/v1/chat` web chat |
| Agent loop | `src/agent/loop.ts` | Claude Sonnet 4.5 snapshot, tool use |
| Intent classifier | `src/agent/classifier.ts` | Claude Haiku 4.5 snapshot, routes emergencies and complaints to staff |
| Tool registry | `src/tools/registry.ts` | EHR MCP server plus native tools, scanned on load |
| Tool executor | `src/tools/executor.ts` | allowlist, kill switch, budgets, approvals, audit |
| EHR | `src/integrations/ehr-mcp.ts` | MCP over streamable HTTP with mTLS, per-clinic OAuth client |
| Payments | `src/integrations/payments.ts` | deposit refunds, provider idempotency keys |
| SMS | `src/integrations/sms.ts` | outbound reminders and replies |
| Eligibility peer | `src/integrations/eligibility-a2a.ts` | A2A `message/send`, token exchange per call |
| Reminder job | `src/workers/reminders.ts` | Kubernetes CronJob, 17:00 local each day |

There is no vector store and no conversation memory. Every run starts from the patient's message and
the EHR. Conversation transcripts are not stored by this service.

## High-impact actions

`config/policy.yaml` lists the tools that need a staff approval before they run. The agent asks for
the approval, a front-desk lead or clinic manager approves it in the staff console, and the agent
retries with the approval ID. Approvals expire after 15 minutes.

## Stopping the agent

Operators with the `clinic-agent-ops` role set `halted = true` on the `global` item (all clinics) or a
`tenant#<clinicId>` item in the `clinic-agent-control` DynamoDB table:

```bash
aws dynamodb put-item --table-name clinic-agent-control \
  --item '{"pk":{"S":"global"},"halted":{"BOOL":true},"by":{"S":"<you>"}}'
```

Running work checks the flag before each model turn and each tool call, and a watcher aborts in-flight
requests within 2 seconds.

## Identity

`src/agent/identity.ts` computes the agent-type-id from the image digest, harness version, prompts,
model IDs, and config. Each pod also gets a random agent-instance-id at start. Both are on every
audit record together with the accountable party, operational owner, tenant, and trace context.

## Build and test

```bash
npm ci
npm run lint
npm test
npm run build
```

## Release

Merges to `main` need two reviews and a code owner review for prompts, config, infra, and manifests.
`deploy.yml` builds, signs, and deploys by digest to the `production` environment, which has required
reviewers. Emergency deploys use the same workflow with `emergency: true` and must name an owner,
a reason, and an end date; the workflow opens a follow-up review issue.

## Owners

- Accountable party: Northbay Clinic Group, Patient Access (VP Patient Access)
- Operational owner: agent-platform team, `#agent-platform-oncall`
