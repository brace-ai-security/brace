# issuesmith

issuesmith picks up GitHub issues labelled `issuesmith`, writes a change in an isolated workspace,
runs the repository's tests, and opens a pull request for human review. It runs as a worker on the
`agents` namespace of the platform EKS cluster.

## How a run works

1. GitHub delivers an `issues.labeled` webhook to `POST /webhooks/github`. The signature is checked
   against the app's webhook secret before anything is parsed.
2. The webhook handler builds the run context (tenant, accountable party, instance id, trace) and
   checks per-user, per-installation and fleet quotas before enqueueing the job.
3. The worker mints a GitHub App installation token restricted to the one repository, clones it into
   `/workspace/<instance-id>`, and starts the agent loop with the Claude Agent SDK.
4. The agent can read and edit files in the workspace, run the project's test commands, push to
   `agent/*` branches, and ask the `reviewer` and `test_writer` sub-agents for help.
5. Opening a pull request or dispatching a workflow requires a maintainer approval in the approvals
   console. The approval is bound to this run, the exact arguments, and the branch head SHA.

## Identity and credentials

| Credential | Source | Lifetime |
|---|---|---|
| GitHub App installation token | minted per run from the `issuesmith[bot]` app, single repository | 60 min (GitHub maximum) |
| AWS (Secrets Manager, S3, RDS IAM auth) | IRSA role `issuesmith-worker` | 1 h STS session |
| Anthropic API key | Secrets Manager `issuesmith/anthropic`, rotated quarterly | rotated |
| Approvals DB | RDS IAM auth token | 15 min |

Installation tokens are requested with the narrowest permissions the run needs. We keep the 60 min
lifetime because a full run (clone, tests, review) regularly takes 20–40 minutes.

## Stopping a run

Maintainers add the `issuesmith:halt` label to the issue. The worker checks for the label on every
agent turn and aborts the run when it appears.

## Budgets

Per run: 60 turns, 45 min wall clock, 2M tokens, USD 15, 30 tool calls per minute, 4 sub-agents.
Quotas: 20 runs and USD 60 per user per day; 30 runs per hour and USD 200 per day per installation;
25 concurrent runs and USD 2,500 per day fleet-wide.

## Development

```bash
npm ci
npm run build
npm test
```

Releases are built by `.github/workflows/release.yml`, signed with keyless cosign, and deployed by
digest after approval on the `production` environment.
