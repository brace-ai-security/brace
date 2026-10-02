# BRACE skills

Three AI skills for applying the [BRACE checklist](../CHECKLIST.md) to an agent's codebase. See [TOOLS.md](../TOOLS.md) for how they fit with the `.brace/` record and the CI check.

| Skill | Use it to |
|---|---|
| [brace-review](brace-review/SKILL.md) | Review an agent's code against all 53 items and write `brace-findings.json` and a report. Use a strong model, such as Claude Sonnet or Opus. |
| [brace-tests](brace-tests/SKILL.md) | Write tests and drills that produce evidence, based on the verification recipes. |
| [brace-record](brace-record/SKILL.md) | Keep the `.brace/` record and draft exceptions and N/A decisions for approval. |

## Install

For Claude Code, copy the three folders into your project's `.claude/skills/` folder, or into `~/.claude/skills/` to use them in every project:

```sh
cp -R skills/brace-review skills/brace-tests skills/brace-record .claude/skills/
```

`brace-record` calls `tools/brace/brace.py`, so copy `tools/brace/` into the project too. Other agent tools that read `SKILL.md` files can load the same folders.

## Keeping the skills in sync with the checklist

The files in `brace-review/references/` and `brace-tests/references/` are generated from `CHECKLIST.md`, `CHECKLIST-VERIFICATION.md`, `ROLES.md`, and the hand-written `brace-review/heuristics/*.yaml`. Don't edit the references by hand. After changing any source, run:

```sh
python skills/gen_references.py
```

CI runs `python skills/gen_references.py --check` and fails if the references are out of date.
