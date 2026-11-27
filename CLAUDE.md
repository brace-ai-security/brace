# Project Instructions for AI Agents

## BRACE versioning

`VERSION` is the authoritative BRACE semantic version. Keep changes unreleased
while building, testing and evaluating. Change the version only when the user
explicitly decides to release after review; routine content, documentation,
website, tooling, evaluation and Beads work does not authorize a bump.

At an authorized release, choose semantic versioning: patch for compatible
corrections or maintenance; minor for compatible additions; major for incompatible
requirements, gates, IDs or interfaces. Reset lower components as appropriate and
synchronize `VERSION`, `index.html`, `README.md` and `CITATION.cff`.
The `open-agent-security` scanner package version follows `VERSION`: also set
`__version__` in `src/open_agent_security/__init__.py` (pyproject,
`--version`, SARIF, JSON and GitLab reports all read it; a test checks it
equals `VERSION`).
Mirror this rule in `AGENTS.md`.

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Build & Test

One distribution, `open-agent-security` (version from `VERSION`), with two packages in `src/`:
`open_agent_security` (the scanner: standard library only, safe under `python -I`) and
`brace_tools` (the `brace` command: record, map, plan, importers; needs the `[record]` extra).
`brace_tools` may import the scanner, never the reverse (tests/packaging/test_dependency_rule.py).

```bash
# The whole default suite, from the repository root (budget: under 5 minutes):
uvx --python 3.11 --with pyyaml==6.0.4 --with jsonschema==4.26.0 --with pytest==9.2.0 \
    --with pytest-xdist==3.8.0 --with pytest-timeout==2.4.0 pytest -q

python3 -I tools/brace/scan.py . --fail-on low   # this repository scans clean
uv build -o /tmp/dist                            # one wheel and sdist; remove src/*.egg-info after
python tools/dev/gen_items.py --check            # item data; also skills/gen_references.py and
                                                 # tools/site/gen_{checklist_page,doc_pages,mappings_json}.py --check
```

Scanner goldens (`tests/fixtures/oas_golden/`) must stay byte-identical unless a scanner change
is intended. Plan and map goldens (`tests/fixtures/char_golden/`) change only with a reviewed,
explained diff (`BRACE_REGEN_GOLDEN=1 pytest tests/plan/test_char_golden.py -n 0`).

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
