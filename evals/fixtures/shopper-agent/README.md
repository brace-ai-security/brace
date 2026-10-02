# shopper-agent

Shops on behalf of consumers. The agent browses retailer sites in a headless Chromium, compares
prices, fills carts, and checks out with a tokenized payment method once the user approves the
order. It remembers sizes, brands, budgets, and shipping addresses between sessions.

Multi-tenant SaaS: every consumer belongs to a tenant (a white-label partner such as a bank's
rewards program). Tenants never see each other's users, carts, or memory.

## Components

| Component | Where | Notes |
|---|---|---|
| HTTP API | `src/server.ts` | Starts runs, streams events, receives approvals |
| Agent loop | `src/loop.ts` | Model calls, tool dispatch, budgets |
| Tools | `src/tools/` | Browser, cart/checkout, memory |
| Payments vault | `.mcp.json` | `vaultline-payments` MCP server (stdio), issues single-use card tokens |
| Deals peer | `src/peers/deals.ts` | A2A calls to DealsNet's coupon agent |
| Helper model | `config/models.yaml` | Price extractor that turns product pages into structured offers |
| Memory | `src/memory/store.ts` | DynamoDB `shopper-memory` |
| Infra | `infra/` | ECS Fargate, DynamoDB, IAM |

## Running locally

```bash
npm ci
npx playwright install chromium
cp .env.example .env   # fill in ANTHROPIC_API_KEY, IDP_ISSUER, VAULT_CLIENT_ID, ...
npm run build && npm start
```

## Approvals

Before any purchase, the agent calls `request_checkout_approval`. The user sees the cart summary
in the app and taps Approve. The agent then calls `checkout` with the approval id.

## Budgets

Per-run, per-user, per-tenant, and fleet limits live in `config/budgets.yaml`. Quotas are enforced
with conditional writes against the `shopper-control` table, so they hold across replicas.

## Release

`main` is deployed by `.github/workflows/release.yml`. Images are signed with cosign keyless.

## Operations

- Stop a tenant: set `killswitch#<tenantId>` to `on` in `shopper-control`.
- Stop everything: set `killswitch#global` to `on`.
- Revoke the agent's vault client: `vaultline clients disable shopper-agent-prod`.
