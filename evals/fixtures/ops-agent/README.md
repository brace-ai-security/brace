# ops-agent

Platform-team DevOps agent. Engineers ask it in Slack (`/ops <request>`) to investigate incidents,
restart workloads, roll back Helm releases, open fix-up branches, and clean up stale resources in
the `prod-eu1` and `prod-us1` clusters.

For larger jobs the agent splits the work and starts worker sub-agents, one per cluster or
namespace. Each worker runs the same loop with a narrower goal.

## Layout

- `src/main.py` – Slack slash-command handler, starts a run.
- `src/agent.py` – the tool loop.
- `src/tools/` – tool registry, shell runner, git helper.
- `src/subagents.py` – starts worker sub-agents.
- `src/checkpoint.py` – saves run state to S3 so a crashed run can resume.
- `k8s/` – deployment, RBAC, network policy, image verification policy.

## Release

Images are built in GitHub Actions, signed with cosign keyless (GitHub OIDC), and deployed by digest.
The Kyverno policy in `k8s/kyverno-verify-images.yaml` rejects unsigned images in the `ops-agent`
namespace.

## Owners

Accountable: Head of Platform. Operational owner: `@acme/platform-sre` (PagerDuty: platform-sre).
