# BRACE skills

Six focused sibling skills support design and assessment using the [BRACE checklist](../CHECKLIST.md). Each can be invoked directly; references inside a skill are conditional detail, not separately discoverable sub-skills. See [TOOLS.md](../TOOLS.md) for the workflow and [design evidence](DESIGN.md) for the research and evaluation limits.

| Skill | Use it to |
|---|---|
| [brace-threat-model](brace-threat-model/SKILL.md) | Before implementation, model assets, trust boundaries, capability combinations, abuse paths and potential harm. Maps proposed controls, assumptions and verification needs to BRACE; no implementation audit or deployment verdict. Not model-qualified yet. |
| [brace-review](brace-review/SKILL.md) | Review all 53 items with static inventories, quoted coverage/deviation ledgers, bypass attempts, bounded batches and independent discovery-first challenges. Sonnet is good enough; prefer Opus if your team can afford it, since subtler bugs are more likely to slip past a smaller model. Haiku and Luna are unsupported. See [results and limits](../evals/README.md#model-qualification). |
| [brace-mcp-review](brace-mcp-review/SKILL.md) | Review MCP server/client/gateway code with entrypoint reconciliation and dated source records. Source-only findings and unknowns; no deployment approval. The deeper three-arm comparison found all required bugs in every arm, with more assessed coverage but factual errors in 15/24 skill reports; see [latest evidence and limits](../evals/results/2026-10-25-mcp-deep-source-graded/README.md). |
| [brace-tests](brace-tests/SKILL.md) | Write tests and drills that produce evidence, based on the verification recipes. |
| [brace-record](brace-record/SKILL.md) | Keep the `.brace/` record and draft exceptions and N/A decisions for approval. |
| [brace-checklist](brace-checklist/SKILL.md) | Quick, read-only pre-launch check of every item in [CHECKLIST.md](../CHECKLIST.md), with `path:line` evidence and plain-language fixes. **No dependencies:** a single `SKILL.md` an agent follows with file reading and search only; no Python, scripts or packages. Lighter and less rigorous than `brace-review`; not model-qualified. |

## Install

Install the folders you need. For Claude Code, copy them into your project's `.claude/skills/` folder, or into `~/.claude/skills/` to use them in every project:

```sh
cp -rf skills/brace-threat-model skills/brace-review skills/brace-mcp-review skills/brace-tests skills/brace-record skills/brace-checklist .claude/skills/
```

`brace-record` calls `tools/brace/brace.py`, and `brace-review` calls `tools/brace/topology.py` and `tools/brace/action_plan.py` to draw the security map and action plan, so copy `tools/brace/` into the project too. `brace-checklist` is fully standalone: copy only its folder. It carries its own copies of the checklist, role map and verification guide in `brace-checklist/references/` (`checklist.md`, `roles.md`, `verification.md`), copied exactly from `CHECKLIST.md`, `ROLES.md` and `CHECKLIST-VERIFICATION.md`. Don't edit them by hand; CI/CD is to regenerate them. Other agent tools that read `SKILL.md` files can load the same folders.

For repo-local Codex discovery, copy the chosen folders into `.agents/skills/`.
`brace-mcp-review` and `brace-threat-model` are portable individually: their reference
material lives inside each skill's folder. The other skills remain usable without them. Handoffs
carry scope, evidence and unresolved conditions; they do not authorize more work.

## Keeping the skills in sync with the checklist

The files in `brace-review/references/` and `brace-tests/references/` are generated from `CHECKLIST.md`, `CHECKLIST-VERIFICATION.md`, `ROLES.md`, and the hand-written `brace-review/heuristics/*.yaml`. Don't edit the references by hand. After changing any source, run:

```sh
python skills/gen_references.py
```

CI runs `python skills/gen_references.py --check` and fails if the references are out of date.
