# Full review with the action-plan stage: hr-agent, Sonnet, 2026-11-21

Pilot runs (`repeat.py --pilot`), not qualification evidence.

## Map and fix stage on an existing full review (`existing-review-action-stage/`)

A fresh Sonnet session got the complete 53-item review in
`evals/results/2026-10-02-improved/hr-agent.strong.json` and ran only the new steps:
mapping, step 9 and step 10. The harness then checked the result itself.

| Check | Result |
|---|---|
| Gap and needs_evidence findings | 43 |
| With components / fix steps / done_when | 43 / 43 / 43 |
| With fix.test | 11 |
| `action_plan.py --strict --repo` | exit 0, no notes |
| Topology valid (CycloneDX 1.7) | yes, 15 parts |
| Ratings, checks, evidence and other fields unchanged | yes |
| Wrote `.brace/` | no |

## Full reviews with the new skill (this folder and `run2/`)

Both runs stopped at bounded batch 2 (B06–B10), before challenges and before the
action-plan stage. The cause was the same both times: pre-scan hit H008 (B06,
`src/main.py:106`, approval flag read from tool arguments) was never resolved.
Each batch log lists hits H001–H007 only. The batch reviewer did not see or did
not handle the eighth hit. The harness keeps such runs as failures and never retries
them. These runs give no evidence about the new steps. They do show a repeatable
review-process miss on this fixture. Batch 1 (B01–B05) passed validation both times.

## Run 3 (`run3/`): after giving each batch its own pre-scan hits

The harness now writes `batch-prescan.json` for each batch. It lists the hits for
that batch's items, and the batch prompt asks the reviewer to resolve each one by id.

- All 11 bounded batches passed validation, including batch 2, which failed in runs 1 and 2.
  The challengers ran, and final validation and challenge application reported no problems.
- Review score: gap recall 1.0 (5/5 keyed gaps), 0 false passes, 53/53 findings, **FAIL**
  on false gaps. The review rated B01, B02 and A02 as gaps, but the key says the code
  meets them (3/5, above the 25% limit). This is a strictness problem in the review
  itself. It comes before the action-plan stage and is not caused by it.
- Action-plan stage (fresh Sonnet session on the final findings): **pass**. 47/47 gap
  and needs_evidence findings have components, fix steps and done_when; 3 have test
  code. `--strict --repo` exit 0 with no notes, valid 12-part map, no other field
  changed, nothing written to `.brace/`.

This is the first end-to-end run of the changed skill: review, challenges, map, fix
steps and action plan. One pilot run is not qualification. The false gaps need their
own investigation before anyone relies on these ratings.

## Beginner-role reader on run 3's fix steps (`reader-on-run3/`)

A fresh Haiku reader, acting as a beginner, followed B02, B05, R04 and E06 from run
3's plan on a clean fixture copy. The orchestrator re-ran its tests: 2/2 passed.

- B02, B05 and R04: done, with tests passing. Minor gaps: no step said to create
  `tests/`, a code snippet was unclear about its quotes, and R04 repeated B02's test
  without saying so.
- E06: **not reached.** The steps never mention `src/tools.py`, so the steps' own
  check (`grep direct_route` must print nothing) still fails.

The run-3 session wrote fix steps for 47 findings at once. Its steps were thinner
than the focused writer in the trials. The writer in trial round 4 tried its own
steps in a scratch copy, and a reader then got 7/7 tests passing. So step 9 now
requires that self-check for every G1 gap. This change has not been re-run end to end.

## Action stage with the self-check (`run3-action-stage-selfcheck*/`)

- `run3-action-stage-selfcheck/`: the harness prompt still said read-only, so the
  writer could not try its steps and wrote no test code (0/47 with `fix.test`). It
  said so in its report. That was a harness limit, not a skill result.
- `run3-action-stage-selfcheck2/`: the harness now allows a scratch copy in the
  workspace. The writer followed its own steps there and found and fixed 3 mistakes
  (a line range that dropped a `)`, an import that needed a stub, a missing `tests/`
  folder); 9 tests pass. Result: 47/47 with components, steps and done_when; 15 with
  test code; strict exit 0; nothing else changed.

## Beginner-role reader on the self-checked plan (`reader-on-selfcheck2/`)

A fresh Haiku reader followed B02, B05, R04 and E06 (and B01, which E06 says to do
first) on a clean copy. The orchestrator checked: 4/4 tests pass with the changes;
with the code changes removed, 3 of those tests fail. The direct-route fallback is
gone. Every action reached its "done when" in code. The only steps not done were
"ask the identity team" steps. Unclear points were minor: wording about edit order,
where one `return` goes, and "no other URLs" with no list. Compare the reader on the
plan written without the self-check: E06 could not be completed there.

## False-gap audit of run 3 (brace-fjm.7)

The orchestrator read the code. B01 and B02 are real defects filed under the wrong
item: they are the keyed E06 and R04 gaps. The key is right for those two. A02 is a
judgment call: failed logins are not audited, and gateway denials before login log
"unknown" identity. The maintainer must decide whether those count as denied
actions under A02.2. The key is unchanged.
