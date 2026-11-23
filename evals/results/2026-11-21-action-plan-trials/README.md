# Action-plan trials, 2026-11-21

Exploratory trials of the security map and action plan (`tools/brace/topology.py`,
`tools/brace/action_plan.py`, `brace-review` steps 2, 9 and 10). They test whether a
model can follow the new steps, and whether a beginner can follow the fix steps it
writes. **One fixture, one run per arm, model readers only.** No human reader was
tested. This does not qualify any model or show general reliability.

## Setup

- Fixture: `evals/fixtures/hr-agent` (a different fixture from the hand-written
  example in `tools/brace/examples/billing-agent/`).
- Input findings: the 19 G1 gaps and needs_evidence items from a real earlier
  review, `evals/results/2026-10-02-improved/hr-agent.strong.json`. Ratings,
  checks, evidence and summaries were left unchanged.
- Writers: fresh Sonnet subagents (the `sonnet` model alias) with no prior context, given
  only the skill file and the repo copy.
- Readers: fresh Haiku subagents (the `haiku` alias) told to act as a beginner,
  follow the steps literally and report every step as CLEAR or UNCLEAR. They got only
  the action plan and a clean fixture copy.
- Checks by the orchestrator: re-running the reader's tests, a syntax/import check
  and, in round 3, a mutation test.

## Results

| Round | What ran | Result | Changes made afterwards |
|---|---|---|---|
| 1 | Sonnet: map + fields + plan (`round1-sonnet-map/`) | 12 parts, 15 connections; `--strict` caught 3 steps above grade 12, which were rewritten; 0 notes at the end. | Skill: config discovery, the full list of risk names, the single-line quote rule. Script: read tools from a `tools:` map; merge duplicate nodes. Report: open actions per connection were overloaded (10-18 each), so now both ends must match; added `fix.problem` because 13 of 19 original summaries were above grade 12. |
| 2 | Fresh Sonnet, revised skill (`round2-sonnet-map/`) | 17 parts, 23 connections, 5 network zones; 0 notes on the first strict run. | `build` now prints its refs and finds nested model ids; added a check that cited files and lines exist (`--repo`). |
| Reader 1 | Haiku follows B01, B06, R13 from round 2 (`reader1-haiku/`) | Most steps UNCLEAR. Only B01 came close to its "done when". Problems: deleting lines broke the code, callers were not named, column types and event names were missing, one step had no hook to use, one done-when clause had no matching step. | Added the step-writing rules in SKILL.md step 9. |
| 3 | Sonnet rewrites B01, B06, R13 (`round3-sonnet-fixes/`) | 0 notes. | The checker now accepts "create" for new files; added rules for fix ordering and editing bottom-up. |
| Reader 2 | Haiku follows round 3 (`reader2-haiku/`) | 3/3 tests pass (verified by the orchestrator). Most steps CLEAR. B01 done; B06 and R13 code done, but they need database migrations run by the platform team. The reader found a deploy-order hazard. Remaining confusion was test code described in words. | Added `fix.test` (exact test code), a deploy-order rule and an indentation rule. |
| 4 | Sonnet rewrites B06, R13 with `fix.test` (`round4-sonnet-fixes/`) | 0 notes; the writer's 7 tests pass in a scratch copy. | — |
| Reader 3 | Haiku follows round 4 (`reader3-haiku/`) | 26 of 29 steps CLEAR, 2 minor UNCLEAR (an indent, a forward reference), 1 platform-team step it could not do. 7/7 tests pass (verified). Removing `AND scope = $7` makes a test fail. Gaps: B06 cannot be proven without a live database; the R13 done-when did not name which record holds the operation id. | `done_when` must name the exact thing to check and match the test. |

## Database check of the reader's B06 fix

The reader's tests used a fake database, so the orchestrator also ran the reader's
B06 code against a real local PostgreSQL 18. It applied the fixture's
`001_init.sql` and the reader's `002_approval_scope.sql`, then ran
`reader3-haiku/b06_db_check.py`. An approval for scope `hris.leave.request` was
**refused** when consumed under `hris.admin` and **accepted** under its own scope.
With the check replaced by `AND ($7::text IS NOT NULL)`, the mismatched approval
was accepted and the script failed. So the fix a beginner applied from the steps
works end to end on this path.

## Limits

- Model readers stand in for a grade 12 human; a human reading study has not been run.
  Flesch-Kincaid scores are a heuristic.
- One fixture and one run per arm; no repeated runs or comparison with the old skill.
- Full `brace-review` runs with the new steps (all 53 items, end to end) have not been
  evaluated. Historical qualification does not transfer to the changed skill.
- Fixes that need a database or platform action can be written and staged, but not
  proven from the repository alone. B06 was proven only with an extra local database.
