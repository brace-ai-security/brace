# .brace — BRACE sign-off record

This folder holds the security sign-off record for this agent, checked by
`brace.py check` (from the BRACE project, usually vendored at `tools/brace/`).

| File | What it is |
|---|---|
| `deployment.yaml` | What the agent is, what it may do, how risky it is (stakes and autonomy), who holds each role, and who may approve. |
| `record.yaml` | One entry for each of the 53 checklist items: the outcome (pass, gap, na, not_reviewed), who leads it, and links to evidence. |
| `manifest.yaml` | The inputs that define this agent type: container, harness, prompt, model, config. `brace.py hash` turns them into the agent-type-id. |
| `exceptions/` | One file per accepted risk (a G2 gap, or a G3 gap on a low-stakes, low-autonomy deployment). G1 gaps can't be accepted. |
| `na/` | One file per item that doesn't apply, with the reason, evidence, and reviewer. |

## How approval works

Approval is not a name typed into a file. A risk acceptance or N/A counts as
approved only when the pull request that added or last changed it was merged
with an approving review from someone listed under `approvals.approvers` in
`deployment.yaml`. The person who opened the pull request can't approve it.
If the file changes later, it needs a new approved pull request.

## Commands

    python tools/brace/brace.py check      # GO or NO-GO, with reasons
    python tools/brace/brace.py hash       # print the agent-type-id
    python tools/brace/brace.py items      # list the checklist items
