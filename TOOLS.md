# BRACE in your codebase

These tools bring the [sign-off checklist](CHECKLIST.md) into an agent's repository. AI skills review the code and write tests. A `.brace/` folder records outcomes, exceptions, and N/A decisions. A CI check reports record findings.

The split is deliberate. **The AI drafts. People approve.** An AI reading a repository can be misled by what's in it, so no AI output counts as a Pass or an approval.

## The pieces

| Piece | What it does | Where |
|---|---|---|
| `open-agent-security` | Finds known-dangerous agent setups in seconds: disabled permission checks, unpinned MCP servers, secrets in agent config, `pull_request_target` agents, lethal capability combinations. Local, read-only, standard library only; also a GitHub Action with SARIF output. Not a review: a clean scan is not a Pass. | [tools/brace/SCAN.md](tools/brace/SCAN.md), [ANTI-PATTERNS.md](ANTI-PATTERNS.md) |
| `brace-threat-model` skill | Models a proposed design's assets, trust boundaries, capability combinations and harm paths, mapped to controls, assumptions and verification needs. | [skills/brace-threat-model/](skills/brace-threat-model/SKILL.md) |
| `brace-review` skill | Reads the agent's code and config and rates all 53 items: likely_pass, gap, needs_evidence, or na_candidate, with file and line evidence. Reports text in the repo that tries to steer the review. | [skills/brace-review/](skills/brace-review/SKILL.md) |
| `brace-mcp-review` skill | Focused static MCP server/client/gateway review, mapped to BRACE items and primary research. Reports evidence, gaps and unknowns; never launches servers or approves deployment. | [skills/brace-mcp-review/](skills/brace-mcp-review/SKILL.md) |
| `brace-tests` skill | Turns the [verification recipes](CHECKLIST-VERIFICATION.md) into tests and drill scripts that produce dated evidence files. | [skills/brace-tests/](skills/brace-tests/SKILL.md) |
| `brace-record` skill | Sets up `.brace/`, records outcomes with evidence, and drafts exceptions and N/A decisions for people to approve. | [skills/brace-record/](skills/brace-record/SKILL.md) |
| `brace-checklist` skill | Quick, read-only pre-launch check of every [checklist](CHECKLIST.md) item with file and line evidence and plain-language fixes. No dependencies: no Python, scripts or packages. Use when `brace-review` is too heavy or Python is unavailable. | [skills/brace-checklist/](skills/brace-checklist/SKILL.md) |
| `brace.py` | Checks the `.brace/` record against the gates, verifies approvals on GitHub, recomputes the agent-type-id, and reports the result described under [How results are worded](#how-results-are-worded). | [tools/brace/](tools/brace/README.md) |
| Evals | Sample agent repos with planted gaps, used to measure how well `brace-review` works. | [evals/](evals/README.md) |

## How it fits together

Before implementation, use `brace-threat-model` when design threat modeling is
needed. Its output supplies scope and verification questions for the workflow
below; proposed controls are not evidence that the controls exist.

1. **Set up.** Copy `tools/brace/` into the agent's repo and run `python tools/brace/brace.py init`. Fill in `.brace/deployment.yaml`: the task, tenants, data, worst damage, the people in each [role](ROLES.md), and who may approve. Governance fills in the stakes and autonomy rating.
2. **Review.** Run the `brace-review` skill. It writes `brace-findings.json`, a readable report, and `brace-action-plan.md`: a map of what the agent connects to, the risky connections, and an action list with a lead, a blank "assigned to" and plain fix steps for each item (also as `brace-actions.csv` for a tracker, a web page with diagrams, JSON for CI and SARIF for code scanning). The [BRACE GitHub Action](tools/brace/README.md#run-it-as-a-github-action) produces these in CI and fails the build on open Blocker gaps. Fix the gaps it finds, starting with Blocker.
3. **Test.** Run the `brace-tests` skill on items rated `needs_evidence` or `likely_pass`. Run the tests and drills in a test environment. Each one writes a dated evidence file.
4. **Record.** Use the `brace-record` skill, or edit by hand, to mark each item in `.brace/record.yaml`. A Pass needs an evidence link and date. For a gap you choose to accept, the skill drafts an exception file.
5. **Approve.** Open a pull request. Governance approves exceptions and N/A decisions by approving that pull request. `CODEOWNERS` makes their review required.
6. **Check evidence.** CI runs `brace.py check --approvals github --strict` on every pull request and on main. It flags unmet Blocker/Detection requirements, missing approvals/reviews and changes since review. Exit code 0 means record conditions were met, not deployment approval (see [How results are worded](#how-results-are-worded)).

## How results are worded

This is the one place the verdict rule is spelled out; other documents link here.

- **High-stakes, high-autonomy or unrated deployments** receive **FINDINGS**: what was checked, what was found, and what remains unverified or unknown. BRACE issues no GO/NO-GO deployment verdict for them, even when no gaps are found. A report with no gaps is not evidence of no vulnerabilities.
- **Lower-risk deployments** keep **GO/NO-GO**, which describes whether the checklist record conditions were met. It is not deployment authorization.
- Exit code 0 from `brace.py` means the record conditions were met, not that a deployment is approved.
- Accountable people own any high-risk rollout: small stages, bounded exposure, close monitoring, explicit stop conditions, tested recovery and review before expansion.

The machine-readable form (`decision`, `notice`, item status `blocked`) is described in [tools/brace/README.md](tools/brace/README.md).

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
- **Use a capable reviewer and fresh challengers.** Which models have been qualified for `brace-review`, and which have not, is recorded with the evidence in [evals/README.md](evals/README.md#model-qualification). `--conservative` produces a partial gap list and does not qualify a model.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
