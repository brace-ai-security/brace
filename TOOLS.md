# BRACE in your codebase

These tools bring the [sign-off checklist](CHECKLIST.md) into an agent's repository. AI skills review the code and write tests. A `.brace/` folder records outcomes, exceptions, and N/A decisions. A CI check reports record findings. High-stakes, high-autonomy and unrated deployments receive FINDINGS, without a BRACE release verdict.

The split is deliberate. **The AI drafts. People approve.** An AI reading a repository can be misled by what's in it, so no AI output counts as a Pass or an approval.

## The pieces

| Piece | What it does | Where |
|---|---|---|
| `brace-review` skill | Reads the agent's code and config and rates all 53 items: likely_pass, gap, needs_evidence, or na_candidate, with file and line evidence. Reports text in the repo that tries to steer the review. | [skills/brace-review/](skills/brace-review/SKILL.md) |
| `brace-tests` skill | Turns the [verification recipes](CHECKLIST-VERIFICATION.md) into tests and drill scripts that produce dated evidence files. | [skills/brace-tests/](skills/brace-tests/SKILL.md) |
| `brace-record` skill | Sets up `.brace/`, records outcomes with evidence, and drafts exceptions and N/A decisions for people to approve. | [skills/brace-record/](skills/brace-record/SKILL.md) |
| `brace.py` | Checks the `.brace/` record against the gates, verifies approvals on GitHub, recomputes the agent-type-id, and reports FINDINGS for high-risk deployments or GO/NO-GO record conditions for lower-risk deployments. | [tools/brace/](tools/brace/README.md) |
| Evals | Sample agent repos with planted gaps, used to measure how well `brace-review` works. | [evals/](evals/README.md) |

## How it fits together

1. **Set up.** Copy `tools/brace/` into the agent's repo and run `python tools/brace/brace.py init`. Fill in `.brace/deployment.yaml`: the task, tenants, data, worst damage, the people in each [role](ROLES.md), and who may approve. Governance fills in the stakes and autonomy rating.
2. **Review.** Run the `brace-review` skill. It writes `brace-findings.json` and a readable report. Fix the gaps it finds, starting with G1.
3. **Test.** Run the `brace-tests` skill on items rated `needs_evidence` or `likely_pass`. Run the tests and drills in a test environment. Each one writes a dated evidence file.
4. **Record.** Use the `brace-record` skill, or edit by hand, to mark each item in `.brace/record.yaml`. A Pass needs an evidence link and date. For a gap you choose to accept, the skill drafts an exception file.
5. **Approve.** Open a pull request. Governance approves exceptions and N/A decisions by approving that pull request. `CODEOWNERS` makes their review required.
6. **Check evidence.** CI runs `brace.py check --approvals github --strict` on every pull request and on main. It flags unmet G1/G3 requirements, missing approvals/reviews and changes since review. For high-risk or unrated deployments, its result is FINDINGS even with no gaps. Exit code 0 means record conditions were met, not deployment approval. Accountable people own any high-risk rollout: small stages, bounded exposure, close monitoring, stop conditions, tested recovery and review before expansion.

## The `.brace/` folder

| File | What it holds | Who changes it |
|---|---|---|
| `deployment.yaml` | The deployment description, stakes and autonomy rating, agent-type-id, people per role, and approvers. | Agent team and Business owner; Governance sets the rating. |
| `manifest.yaml` | The inputs hashed into the agent-type-id: container, harness, prompt, model, config. | Agent team. |
| `record.yaml` | One entry per checklist item: outcome, Lead, evidence links and dates, who verified. | Each item's Lead. |
| `exceptions/<ITEM>-<slug>.yaml` | One risk acceptance per file: the threat, compensating controls, who accepted it, the remediation owner, and the tracking link. | Drafted by anyone; approved by Governance through PR review. |
| `na/<ITEM>-<slug>.yaml` | One N/A decision per file: the reason and the evidence that the feature or exposure doesn't exist. | Drafted by anyone; approved by Governance through PR review. |

**Approval is the merged pull request, not a name in a file.** `brace.py` checks on GitHub that the last commit to change each exception or N/A file came from a merged pull request. That pull request must have been approved by a listed approver who isn't its author. If someone edits the file later without that review, the check fails again.

## Using the skills

The skills follow the common `SKILL.md` format. To use them with Claude Code, copy the `skills/brace-*` folders into your project's `.claude/skills/` folder, or into `~/.claude/skills/`. Other agent tools that read `SKILL.md` files can load them the same way. See [skills/README.md](skills/README.md).

## What these tools can't do

- **They don't prove an agent is secure.** A code review finds likely gaps and likely controls. Many items, such as stop times, revocation delays, and drift alerts, can only be shown by running the recipes.
- **They don't replace people's judgment.** The stakes rating, risk acceptances, N/A decisions, and deployment decisions stay with the roles in [ROLES.md](ROLES.md).
- **The review's accuracy is measured, not assumed.** See the [eval results](evals/README.md) before trusting `brace-review` on its own, and re-run the evals when the skill or the checklist changes.
- **Use a capable reviewer and fresh challengers.** The previous skill qualified `gpt-6.1-sol` on six repeated procurement/clinic runs; tested Sonnet and Luna failed that workflow. The revised skill adds static path inventories, required-control coverage/deviations, concrete bypass attempts, five-item batches and independent discovery before comparison. It requires separate qualification; Sonnet is being retested. Haiku remains unsupported. [All results and limits](evals/README.md#model-qualification) are recorded, with evaluated skill snapshots; historical Opus runs used older keys. `--conservative` produces a partial gap list and does not qualify a model.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
