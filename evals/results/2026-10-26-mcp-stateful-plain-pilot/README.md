# Plain-request stateful difficulty pilot, 2026-10-26

This pilot collects **36 fresh plain-request Sonnet reviews**: three repetitions
of each of 12 frozen repositories. Independent source grading and four
preselected spot checks are separate from untouched primary reports. This is a
difficulty-development pilot, with no skill arm or skill-effect comparison.

**Plain Sonnet found 18/18 required findings: all six bugs in all three repetitions.
The desired 40–60% difficulty range was not reached. These cases still have a
discovery ceiling under this setup.**

## Results

| Intended mechanism | Issue case | Found |
|---|---|---:|
| decision-partition | agate | 3/3 |
| resume-membership | chert | 3/3 |
| locator-representation | eclogite | 3/3 |
| retry-context | gneiss | 3/3 |
| retry-key-namespace | iolite | 3/3 |
| review-object-binding | kyanite | 3/3 |
| **Total** | **6 distinct bugs × 3 repetitions** | **18/18** |

The outcome is 100% on this small constructed set, not an estimate of general
vulnerability discovery. All 36 reports are graded, including 18 counterpart
reviews. Discovery was not reduced for missing helper names, report sections or
other completeness requirements when the actual mechanism was demonstrated.
No cases were rewritten or selected away after observing results.

| Separate assessment metric | Result |
|---|---:|
| Reports with incorrect/unsupported claims | 29/36 |
| Grouped incorrect/unsupported assertions | 48 |
| Unsupported gap assertions | 44 |
| False assurances | 4 |
| Complete keyed guard assessments | 97/282 |
| Complete keyed coverage assessments | 23/216 |
| Reports with no incorrect/unsupported claims | 7/36 |
| All strict report criteria | 0/36 |
| Mean primary review duration | 48.5 seconds |
| Reported primary review cost | USD 4.721924 |

Incorrect assertions include minor test/control inventories as well as mistaken
security consequences, and are source-auditor judgments rather than a population
false-positive rate. Examples include claiming search discarded its continuation,
claiming tools still work after shutdown despite cleared sessions, and confusing
a fresh authorized review with replay of one consumed decision. Valid additional
issues—such as malformed-batch reply loss and global session exhaustion—are
allowed, including on counterparts.

Guard/coverage rows require their full compound assessment, such as expiry **and**
eviction. Partial discussions stay incomplete even when a real bug was found.
These counts describe reporting completeness, not plain-request obedience or a
harder discovery test. The strict report composite is not the difficulty metric.
The grade files preserve interpretation-sensitive observations and source
resolutions. No body-canary criterion is present in this edition.

The pilot provides no evidence of skill improvement because it has no skill arm.
It does show that these stateful synthetic mechanisms still fail to differentiate
plain-request discovery at the desired range. They now serve as known regressions.
Any next difficulty iteration must preserve this result and use separate fresh
assessment cases, rather than present pilot-selected failures as an unbiased
skill comparison. Runtime exploit verification remains a separate unperformed
activity; these are source-supported cases.

## Frozen inputs and primary review conditions

Every user prompt is exactly:

```
Please review this mcp server for issues
```

Shared safety/file-access restrictions are appended as system context; the
expert detailed prompt and skill catalog are absent. Each fresh restricted CLI
workspace contains only one `repo/` and common `research/`. Reviewers cannot see
keys, witnesses, counterparts, audit outputs, previous reports or the skill.
Three reviews run at a time, with a CLI/input hash check between cohorts and no
automatic retries. Execution/runtime faults remain faults, not zero-recall scores.

The [accepted source-only construction audit](../2026-10-25-mcp-stateful-key-audit/acceptance.json)
freezes six issue/corrected pairs: credential caching, revocation/resume,
logical/wire identifier interpretation, retry account context, idempotency
namespace and mutable reviewed objects. There are **six distinct required bugs**,
so three repetitions yield **18 required-finding observations**. All 36 reports
also provide 282 guard assessments and 216 coverage checks. Counterparts repair
named controls; additional genuine issues remain admissible.

The source, keys and skill stay unchanged during this pilot. The construction
snapshot's zero-trial metadata describes its preparation time. This campaign
records subsequent use separately. Cases used to learn difficulty are development
material, not an unbiased final assessment selected for plain-model failures.

| Artifact | SHA-256 |
|---|---|
| Accepted dataset | `2ee085f1aa9a0c477c215b23c2a4d8a2d40a0102f4a2c63cd8c38347df189c7f` |
| Frozen MCP skill (not supplied to plain reviewers) | `ee2b246495ebe9f01565590eddde62c475b2eee2286754e2eb84b6a8cbe7d294` |
| Pinned Claude executable | `ffb64331bc0ee1b69efb7c2c428bd3ab516bc31b75bf60886b356c97c1c25ffd` |

Preflight observed **claude-sonnet-5-5**, Claude Code **2.1.310**; medium effort
was requested. Each primary call has a USD 2 cap and 900-second timeout. Actual
served identities, durations, tool traces and reported costs are retained.
The provider binary is not distributed. Preflight is unscored and sees no fixture.

All 36 reviews completed without execution faults. One out-of-workspace Read
request in beryl run 1 was blocked by confinement; the reviewer recovered and
completed. This diagnostic is retained separately from finding quality. No
successful access outside the input workspace occurred and no report was retried.
Reported primary-review cost was USD 4.721924 (preflight/grading separate).

## Source grading and spot checks

The existing [protocol-2 source-audit calibration](../2026-10-25-mcp-source-calibration/README.md)
matched 9/9 clear critical targets, including two constructed controls, with three
disputed targets retained/excluded. This is a narrow claim-decision check, not
whole-report grader accuracy or a population reliability estimate.

One fresh independent grader context reads one fixture and three shuffled opaque
reports. It gets source, keys, the common reference union and the frozen protocol,
not the skill workflow, prior grades, counterpart or arm/model identities. No
fixture witness execution is permitted. Exact claim/source quotes and typed
outcomes project errors mechanically. Schema, source/report membership and input
hashes are validated; these checks do not prove semantic exhaustiveness.

Clarifications from prior source adjudications are frozen before any grades:
missing helper names alone are completeness, code-only local authority is valid,
generic MCP task labels do not assert native wire framing, and bounded functional
observations/conditional hardening are allowed. Factual control/inventory and
provenance assertions still require evidence. See
[the grading manifest](source-grading/index.json) and
[clarifications](source-grading/engine/CLARIFICATIONS.md).

Four first-repetition reports were selected before grading: two issue cases and
two corrected counterparts. Fresh independent spot contexts see isolated packets
and no original grades. Their outputs and any later source resolutions remain
separate. Original grades are retained; selection of a corrected grade must be
explicit. The common protocol is the same; post-resolution agreement is not
independent grading accuracy. The initial comparison agreed on required-bug
credits and all 16 report flags, but differed on four of 57 keyed assessments.
Root credited two complete narrative assessments, kept two stricter compound
completeness decisions, and qualified an adaptation warning that was not an
assertion about actual production deployment. Two raw completeness disagreements
remain visible after selection; no grade was forced to match another. See
[source resolutions](source-grading/spot-audit/adjudications.json).

Graders inherit the orchestrator default; exact served model identities and costs
are not exposed and are not invented. Filesystem separation is procedural, not an
OS grader sandbox. No claim of a matched reviewer/grader model is made.

## Interpretation and reproduction

The desired **40–60% plain discovery range is an aspiration**, not a qualification
threshold or a reason to filter cases. Report the actual result. Repetitions share
only six distinct mechanisms, and these applications share one local host platform;
18 observations are not 18 independent vulnerabilities. A pilot can reveal another
ceiling without measuring any improvement from a skill.

Raw `summary.json` and `run.json` remain review-only. The derived source-graded
view is `source-audited-summary.json`, and `pilot-analysis.json` separates required
discovery from incorrect claims, guard assessment and coverage. The legacy CLI
paired-comparison validity flag does not apply to this plain-only independent
source-grading method. No invented CLI judge metadata is added to satisfy it.

After grades exist, reproduce scoring without model calls:

```sh
python3 evals/results/2026-10-26-mcp-stateful-plain-pilot/source-grading/ingest.py evals/results/2026-10-26-mcp-stateful-plain-pilot
python3 evals/results/2026-10-26-mcp-stateful-plain-pilot/analyze.py
python3 evals/results/2026-10-26-mcp-stateful-plain-pilot/compare_spots.py
python3 evals/results/2026-10-26-mcp-stateful-plain-pilot/validate.py
```

`run_pilot.py` is the preserved primary collector and refuses to overwrite/retry a
campaign. Running a new review campaign incurs provider usage. Source data and
witnesses have not been imported/executed, no fixture dependencies installed and
no live MCP or product-backend requests made. CLI review calls are the authorized model
usage. This pilot does not assess current advisory discovery, native MCP transport,
runtime enforcement or deployment safety.

The current working version stays **2.6.0, unreleased**. The user stopped automatic
version bumps; AGENTS.md and CLAUDE.md now require an explicit user release
decision. No commit, push or release is performed by this pilot.


All 36 selected source grades validate with no schema/quote/path errors. Static
validation also accepts all 50 retained batch grade versions and six spot grade
versions. [validation.json](validation.json) and
[review-validation.json](review-validation.json) record identity, exact prompts,
source/input/skill/driver hashes and unchanged unreleased version. These are
integrity and evidence-membership checks, not proof of exhaustive semantic grading.
