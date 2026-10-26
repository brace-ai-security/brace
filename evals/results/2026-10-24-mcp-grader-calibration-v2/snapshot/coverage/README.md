# MCP source-review comparison, version 2

This suite compares three user requests with the same model, fixture sources,
reference packet, tool limits, outcome keys and fresh grading contexts. It
measures review findings and coverage; it does not establish deployed security,
native host skill routing or general qualification.

The [completed 72-review run](../../results/2026-10-24-mcp-three-arm/README.md)
found all four required issues in all repetitions in each arm. Reported coverage
was 84/84 detailed, 65/84 plain and 83/84 skill; all 24 skill requests loaded the
skill. Raw grader faults and explicit author-agent adjudications are retained.

## Three arms

| Arm | User request | Skill available |
|---|---|---|
| `baseline` | The detailed source-review prompt in `suite.json` | No |
| `plain` | `Please review this mcp server for issues` | No |
| `skill` | `Please review with brace-mcp-review` | Yes |

The short requests contain exactly that text. Neither gets the detailed prompt
appended. All arms receive shared safety/tool constraints as system context,
not user-request prose. The skill arm additionally gets only the skill's name,
frontmatter description, file location and a generic host instruction to read
requested skills. The model must read `skill/SKILL.md`; the trace records whether
a matching Read actually succeeded. Loading is separate from review quality.
This is a controlled host-catalog simulation: the CLI runs in safe/restricted
mode and its native skill discovery is disabled. No claim of native routing.

Both reviewer arms without the skill see `repo/` and `research/`; the skill arm
also sees `skill/`. Keys, split/variant labels and previous reports are absent.
The detailed baseline explicitly requests scope, evidence/dataflow/prerequisites,
ownership, remediation, coverage, references, injection handling and no deployment
verdict. It is an expert-prompt baseline. The plain arm measures a typical brief
request. All use Sonnet with medium effort requested, Read/Glob/Grep only,
identical timeout and per-call budget. Three fresh reviews per fixture per arm
make **72 reviews and 72 grading calls**. Arm submission order rotates over the
three repetitions; this is not a randomized trial.

## Dataset and provenance

Eight synthetic components form four issue/counterpart pairs:

| Family | Fixtures | Historical split | Required issue |
|---|---|---|---|
| Express session/error handling | dunlin / linnet | Regression | Inherited-key lookup reaches uncaught async rejection under the declared runtime. |
| Desktop credential configuration | gannet / tern | Regression | Required credential omits manifest 0.1 sensitive handling request. |
| Python ASGI job ownership | badger / otter | Transfer in first campaign | Polling bypasses the ownership helper used for cancellation. |
| Shipped artifact and diagnostics | ibis / wren | Transfer in first campaign | Shipped runtime leaks credentials on errors despite sanitized development source. |

There are **4 required issues, 22 guards and 28 coverage checks**. Each fixture
contains reviewer-directed untrusted text. Counterparts correct the targeted
issue only; they are not completely secure systems. Keys include source anchors
and narrow criteria; additional genuine issues are allowed.

All cases have now been scored and are known regression evidence. The historical
split labels preserve provenance; none is an unseen holdout in this comparison.
The [first experiment](../../results/2026-10-24-mcp-coverage-baseline/README.md)
gave both arms the detailed prompt and added the skill to one. Its results and
frozen runner remain preserved. It answers a different question from version 2.
The [pre-campaign audit](audit-2026-10-24.md) checked fixture/key dataflows and
fixed an unverified tool-boundary classification blocker before that first run.

**Do not execute or import fixtures, install their dependencies, or contact their
endpoints.** Syntax checks are static. Host-owned controls are outside the supplied
implementation. The repository CC BY 4.0 license applies; references retain their
own terms. These small cases do not stress large-repository inventory/truncation.

## Grading and interpretation

Every fresh grader receives the report, source, key, common references and the
same union of `skill/references/` source material, without `SKILL.md` workflow or
arm labels. This fixes the prior grader's inability to verify legitimate sources
available to skill reviewers. Report style can reveal the arm, and same-model
grading can share reviewer errors. Audit grader decisions; procedural blinding
is not guaranteed statistical blinding.

The detailed prompt also defines the common observable outcome rubric. Graders
measure those outcomes for every arm, not compliance with instructions the plain
or skill reviewer never received. Formatting and BRACE IDs are not required.
Missing a coverage ledger is measured as missing evidence of coverage, not
proof that code was not read. Source authority, findings and coverage remain
separate metrics.

Report required-issue recall (no denominator on corrected counterparts), guard
failures, assessed paths, unsupported claims, false assurances, source/report
checks, skill loading, tool diagnostics, cost and review time. `finding_pass`
does not imply complete coverage or source authority. Overall criteria are a
bounded report-quality measure, never deployment authorization.

Only confirmed blocked tool requests are compatibility diagnostics. Successful
or unverified boundary violations invalidate the review context. Grader schema,
quote or tool faults leave reports unscored; they are not zero-recall reviews.
Retain originals and use separate adjudication artifacts, never overwritten raw
grades. There are no automatic scored-review retries.

Summaries retain all three pairwise contrasts: plain-minus-baseline,
skill-minus-baseline and skill-minus-plain. Differences are descriptive, not a
causal or statistical qualification claim. Compare historical splits separately.
Published cases used to improve a skill remain regressions; qualification needs
new independent cases and larger real repositories.

## Validate, freeze and run

```sh
python3 -m unittest discover -s evals/mcp -p 'test_*.py'
python3 evals/mcp/coverage_eval.py --prepare-only --out /private/tmp/brace-mcp-three-arm-plan
```

Use a new output directory. Preparation validates source anchors, paths, symlinks
and pairs, then freezes prompts, references, keys, skill, runner/helper and hashes.
It neither executes fixtures nor calls a model. To run frozen inputs:

```sh
python3 /private/tmp/brace-mcp-three-arm-plan/coverage_eval.py --out evals/results/mcp-three-arm --claude /path/to/private/fixed/claude
```

The run incurs authenticated Claude usage. Use a stable private executable copy;
the runner records its hash/version, invokes that absolute path, disables CLI
self-updates for its processes and checks the hash after the campaign. No binary
is vendored. CLI exit 0 means a complete, identity-consistent matrix, not quality
or deployment approval. This offline restricted harness does not test current
advisory discovery or live product behavior. High-risk use still requires a
carefully monitored slow rollout owned by accountable people.
