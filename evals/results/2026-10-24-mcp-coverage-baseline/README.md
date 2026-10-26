# Matched MCP coverage eval: 2026-10-24

## Results after documented adjudications

Both arms found all four required issues in all three repetitions. There was
**no observed gain in keyed discovery or coverage** from adding the skill to the
shared expert prompt/reference packet. This suite is at ceiling on those measures.

| Measure | Baseline | Skill |
|---|---:|---:|
| Required-issue observations | 12/12 | 12/12 |
| Guard checks | 66/66 | 66/66 |
| Path/control coverage checks | 84/84 | 84/84 |
| Reports meeting all exercised criteria | 23/24 | 21/24 |
| Source/report checks met | 23/24 | 21/24 |
| Detected unsupported-claim groups | 0 | 2 |
| Detected false-assurance groups | 0 | 0 |
| Primary review cost, 24 reviews | $1.49 | $3.17 |
| Grading cost, 24 calls | $1.66 | $1.91 |
| Mean primary review time | 34.2 s | 52.5 s |

Primary review cost was **2.12×**, and mean primary review time **1.54×**, with
the skill. Costs are provider-reported call costs, excluding preflights and human
or agent audit work. Total review plus grading cost was $8.23. No timing or cost
claim covers native skill routing or live product reviews.

| Split | Required observations, each arm | Coverage, each arm | All criteria: baseline / skill |
|---|---:|---:|---:|
| Known regression | 6/6 | 42/42 | 11/12 / 10/12 |
| Transfer before this run | 6/6 | 42/42 | 12/12 / 11/12 |

The baseline reporting failure omitted primary references for runtime semantics.
The skill failures were one incorrect ownership-source attribution, one omitted
source date, and one report with two grouped unsupported claims. These small
counts do not establish a comparative false-positive rate or overall superiority.

The [derived summary](combined-audited-summary.json) combines only unstarted-call
recoveries with originals and applies three explicit adjudications. It retains
24 matched pairs, actual identities, per-split results, cost/time and provenance.
Its `comparison_valid` flag checks matrix/model consistency, not general
reliability or deployment suitability. Reviewer traces recorded no tool-policy
diagnostics. Run `python3 assemble.py` from this directory to reproduce the
derived JSON using frozen helpers; assertions verify snapshots, raw hashes,
replacement eligibility and adjudicated scores.

## Method and audit

The [pre-campaign audit](../../mcp/coverage/audit-2026-10-24.md) independently
checked the source-backed keys and runner. It found and fixed one blocker: the
runner could score unverified out-of-workspace or unexpected tool access as a
compatibility diagnostic. Only confirmed blocked attempts now stay diagnostic;
unverified or successful access invalidates that review. The 128 existing and
harness tests passed before freezing. The MCP skill was unchanged.

Eight source-only fixtures, three repetitions, two arms: 48 reviews and 48 fresh
Sonnet grading calls. Both arms receive the same detailed task and primary-source
packet; the treatment additionally receives the skill. This is a strong
structured-prompt/reference baseline, not an unprompted or minimally prompted
model. Observed model: `claude-sonnet-5-5`; Claude Code: `2.1.310`; medium effort
requested. Keys and arm labels are absent from reviewer workspaces; graders get
keys but no skill or arm label. Report style can still reveal the arm.

Snapshot SHA-256:
`d0b3efb76e706cdac0d8616dcd54fb71e2cdf8b2503f1846743926c2abc5ca50`.
Both campaigns use identical frozen source, tasks, references, keys, skill and
runner/helper hashes. Reference provenance is retained in the
[frozen verification record](snapshot/coverage/research/verification-2026-10-24.json).

## Launch recovery and grading audit

The [original matrix](summary.json) retains all 48 attempts: 26 scored, 21 launcher
errors and one exact-quotation grading error. Sixteen launch errors were ENOENT
and five ENOEXEC. Those 21 calls produced no review process metadata, report or
nonempty review log. The global CLI path temporarily disappeared or was
unexecutable; its cause was not established.

A [separate recovery](../2026-10-24-mcp-coverage-launch-recovery/recovery.json)
completes only those 21 unstarted calls. Scored reviews and the quotation error
were not rerun. The restored native CLI was copied to a private temporary path,
verified as version 2.1.310, and passed a structured-output preflight. Recovery
used that fixed PATH prefix and `DISABLE_AUTOUPDATER=1`. Binary SHA-256:
`ffb64331bc0ee1b69efb7c2c428bd3ab516bc31b75bf60886b356c97c1c25ffd`.
The binary is not included in this repository. Recovery timing/environment differ
from the original, so scheduling is not a randomized controlled comparison.

[Tern's separate adjudication](tern.skill.run-3/adjudication.json) repairs the
quotation's capitalization only in a derived verdict. Fresh-context inspection
also finds two grouped unsupported claims: unconditional process/host exposure
from environment-variable delivery, and security/inventory conclusions from
packaging omissions without an established requirement. Its keyed checks still
pass; finding quality and source-authority criteria do not. Raw report, verdict
and run record remain unchanged.

A [balanced four-report audit](balanced-audit.json) checked Dunlin run 1 and
Badger run 2 in both arms, finding no further unsupported claims. For Badger's
skill report it retains the citation-date failure but rejects the raw grader's
objection that a skill reference was unavailable to the reviewer: access was
authorized. This changes the explanation, not the boolean score.

Follow-up checks retain the Gannet skill run 1 failure (README contracts attributed
to the injection file) and Dunlin baseline run 2 failure (explicitly uncited runtime
semantics). [Otter skill run 3](otter.skill.run-3/adjudication.json) is corrected
to valid: the cited sources and dates exist in the authorized skill references.
The grader lacked those files; its raw failure is preserved. Before another
campaign, both graders need the same complete, arm-neutral reference universe.

[Gannet baseline run 3](../2026-10-24-mcp-coverage-launch-recovery/gannet.baseline.run-3/adjudication.json)
removes a grader penalty for ambiguous package-provenance wording. The raw
grader itself accepted the substantive uncertainty; awkward phrasing alone did
not establish an unsupported security claim.

## Limits

Four distinct required issues repeated three times are twelve observations, not
twelve independent vulnerabilities. Regression and transfer splits are reported
separately. Transfer cases were unscored before this campaign; after use and
publication they are regression evidence, not fresh holdouts.

The same model reviews and grades. Manual audits inspect nine reports at differing scopes, including
one selected because of a grading fault; detected unsupported claims are a
lower bound, not an unbiased comparative false-positive estimate. Automated
acceptance is not exhaustive human validation. Small synthetic cases do not
stress large-repository inventory/truncation or reproduce the public-product
misses at their original scale. Shared expert prompts and references can produce
a ceiling on these cases. A ceiling on discovery and coverage cannot establish general qualification
or show that the skill has no value in other settings.

No fixture was executed, dependency installed, MCP server connected or live
product API exercised. This eval reports what was and was not found; it does not
authorize deployment. High-risk use still needs a carefully monitored slow rollout.
