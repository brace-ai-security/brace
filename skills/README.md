# BRACE skills

Four focused sibling skills apply the [BRACE checklist](../CHECKLIST.md) to an agent's codebase. Each can be invoked directly; references inside a skill are conditional detail, not separately discoverable sub-skills. See [TOOLS.md](../TOOLS.md) for the workflow and [design evidence](DESIGN.md) for the research and evaluation limits.

| Skill | Use it to |
|---|---|
| [brace-review](brace-review/SKILL.md) | Review all 53 items with static inventories, quoted coverage/deviation ledgers, bypass attempts, bounded batches and independent discovery-first challenges. Sonnet is good enough; prefer Opus if your team can afford it, since subtler bugs are more likely to slip past a smaller model. Haiku and Luna are unsupported. See [results and limits](../evals/README.md#model-qualification). |
| [brace-mcp-review](brace-mcp-review/SKILL.md) | Review MCP servers, client/host configurations and gateway boundaries; map evidence and gaps to BRACE and dated primary research. Loads HTTP/stdio details as applicable. A focused static review, not a full assessment or live scanner. Not model-qualified yet. |
| [brace-tests](brace-tests/SKILL.md) | Write tests and drills that produce evidence, based on the verification recipes. |
| [brace-record](brace-record/SKILL.md) | Keep the `.brace/` record and draft exceptions and N/A decisions for approval. |

## Install

Install the folders you need. For Claude Code, copy them into your project's `.claude/skills/` folder, or into `~/.claude/skills/` to use them in every project:

```sh
cp -rf skills/brace-review skills/brace-mcp-review skills/brace-tests skills/brace-record .claude/skills/
```

`brace-record` calls `tools/brace/brace.py`, so copy `tools/brace/` into the project too. Other agent tools that read `SKILL.md` files can load the same folders.

For repo-local Codex discovery, copy the chosen folders into `.agents/skills/`.
`brace-mcp-review` is portable by itself: its transport, advisory and source mappings
live inside its own folder. The other skills remain usable without it. Handoffs
carry scope, evidence and unresolved conditions; they do not authorize more work.

## Keeping the skills in sync with the checklist

The files in `brace-review/references/` and `brace-tests/references/` are generated from `CHECKLIST.md`, `CHECKLIST-VERIFICATION.md`, `ROLES.md`, and the hand-written `brace-review/heuristics/*.yaml`. Don't edit the references by hand. After changing any source, run:

```sh
python skills/gen_references.py
```

CI runs `python skills/gen_references.py --check` and fails if the references are out of date.
