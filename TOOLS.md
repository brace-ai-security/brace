# BRACE in your codebase

These tools bring the [sign-off checklist](CHECKLIST.md) into an agent's repository. AI skills review the code and write tests. A `.brace/` folder records outcomes, exceptions, and N/A decisions. A CI check turns that record into a GO or NO-GO.

The split is deliberate. **The AI drafts. People approve.** An AI reading a repository can be misled by what's in it, so no AI output counts as a Pass or an approval.

## The pieces

| Piece | What it does | Where |
|---|---|---|
| `brace-review` skill | Reads the agent's code and config and rates all 53 items: likely_pass, gap, needs_evidence, or na_candidate, with file and line evidence. Reports text in the repo that tries to steer the review. | [skills/brace-review/](skills/brace-review/SKILL.md) |
| `brace-tests` skill | Turns the [verification recipes](CHECKLIST-VERIFICATION.md) into tests and drill scripts that produce dated evidence files. | [skills/brace-tests/](skills/brace-tests/SKILL.md) |
| `brace-record` skill | Sets up `.brace/`, records outcomes with evidence, and drafts exceptions and N/A decisions for people to approve. | [skills/brace-record/](skills/brace-record/SKILL.md) |
| `brace.py` | Checks the `.brace/` record against the gates, verifies approvals on GitHub, recomputes the agent-type-id, and returns GO or NO-GO. | [tools/brace/](tools/brace/README.md) |
| Evals | Sample agent repos with planted gaps, used to measure how well `brace-review` works. | [evals/](evals/README.md) |

## How it fits together

1. **Set up.** Copy `tools/brace/` into the agent's repo and run `python tools/brace/brace.py init`. Fill in `.brace/deployment.yaml`: the task, tenants, data, worst damage, the people in each [role](ROLES.md), and who may approve. Governance fills in the stakes and autonomy rating.
2. **Review.** Run the `brace-review` skill. It writes `brace-findings.json` and a readable report. Fix the gaps it finds, starting with G1.
3. **Test.** Run the `brace-tests` skill on items rated `needs_evidence` or `likely_pass`. Run the tests and drills in a test environment. Each one writes a dated evidence file.
4. **Record.** Use the `brace-record` skill, or edit by hand, to mark each item in `.brace/record.yaml`. A Pass needs an evidence link and date. For a gap you choose to accept, the skill drafts an exception file.
5. **Approve.** Open a pull request. Governance approves exceptions and N/A decisions by approving that pull request. `CODEOWNERS` makes their review required.
6. **Gate.** CI runs `brace.py check --approvals github --strict` on every pull request and on main. It blocks release when a G1 item isn't met, an exception lacks an approval, an item wasn't reviewed, or the agent changed since the last review.

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
- **They don't replace people's judgment.** The stakes rating, risk acceptances, N/A decisions, and the GO/NO-GO decision stay with the roles in [ROLES.md](ROLES.md).
- **The review's accuracy is measured, not assumed.** See the [eval results](evals/README.md) before trusting `brace-review` on its own, and re-run the evals when the skill or the checklist changes.
- **Use a strong model for `brace-review`, such as Claude Sonnet or Opus.** On eight agent codebases the skill had never seen, a strong model found all 92 planted gaps with no false passes. A small model (Claude Haiku) found 64 of 92, missed gaps hidden behind code that looks like a working control, and passed 9 broken controls. If only a small model is available, use `--conservative` and treat the output as a partial gap list.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
