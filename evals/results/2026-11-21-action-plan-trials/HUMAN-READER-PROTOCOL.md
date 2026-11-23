# Human reader test for BRACE fix steps

This test checks whether people with no knowledge of the project can follow BRACE fix
steps. It is the check the 2026-11-21 model-reader trials could not make.

## Who

Three to five people who:

- can edit a text file and run a terminal command, at about a final-year
  high-school level;
- have not seen the hr-agent code, BRACE, or these fixes;
- are not security engineers.

Record each person's background in one line. Don't record names in the results.

## What they get

1. A clean copy of `evals/fixtures/hr-agent`, as a git repo so the changes can be
   seen.
2. Only the `### B06` and `### R13` parts of
   `round4-sonnet-fixes/brace-action-plan.md`, printed or as a file.
3. A Python environment with the project's packages and pytest. Give the command
   to use in place of `python` and `pip install pytest`.
4. This instruction, word for word: "Follow these steps in order. Don't ask anyone
   for help. If a step is unclear, mark it, make your best guess, and keep going.
   Steps that say 'ask the platform team' can't be done here; just mark them."

Allow up to 60 minutes. Don't help during the test.

## What they record (one row per step)

| Fix | Step | Clear? (yes / no / can't do) | What I did | What confused me | Minutes |
|---|---|---|---|---|---|

At the end of each fix, they answer: "Did the test pass? Do you think you reached
'You are done when'? Why?"

## What the tester checks afterwards

- Run `python -m pytest tests` in their copy. Record pass or fail for each test file.
- B06: start a local Postgres, apply `migrations/001_init.sql` and their
  `002_approval_scope.sql`, then run `reader3-haiku/b06_db_check.py` from their
  copy. Pass = prints `{'mismatch': 'refused', 'match': 'accepted'}`.
- R13: check that a gateway outage writes a `tool_error` audit event with an
  `operation_id`. Their test, or the round-4 test, shows this.
- Read `git diff`. Note any change the steps did not ask for.

## Pass bar (set before running)

- At least 80% of steps marked clear across all readers.
- At least two-thirds of the readers reach a passing test and the B06 database
  check for each fix.
- Each step that more than one reader marks unclear gets a fix to the step-writing
  rules (`skills/brace-review/SKILL.md` step 9). Re-test after the fix.

## Results

Add the results as `human-reader-<date>.md` beside this file. Include one table per
reader, the tester's checks, and any rule changes made.
