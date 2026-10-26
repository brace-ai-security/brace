# MCP coverage evaluation, version 1

Built before changing the MCP skill. The [pre-campaign audit](audit-2026-10-24.md)
checked the keys and fixed one runner boundary-classification blocker before
freezing. This suite measures draft source-review quality and coverage; it does
not establish deployed security, native skill routing or general qualification.

## Dataset

Eight synthetic components form four issue/counterpart pairs. Names and the
split/variant labels are outside reviewer workspaces. Counterparts correct only
the targeted defect; they are not assertions of completely secure systems.

| Family | Fixtures | Split | Required issue |
|---|---|---|---|
| Express session/error handling | dunlin / linnet | Known regression | Inherited-key session lookup reaches an uncaught async rejection under the declared runtime. |
| Desktop credential configuration | gannet / tern | Known regression | Missing request for sensitive handling of a required credential field under manifest 0.1. |
| Python ASGI job ownership | badger / otter | Unscored transfer | Result polling bypasses the ownership helper used on cancellation. |
| Shipped artifact and diagnostics | ibis / wren | Unscored transfer | Shipped runtime serializes credentials on errors despite sanitized development source. |

There are **4 required issues, 22 guards and 28 path/control coverage checks** across
the eight fixtures. Each input contains reviewer-directed untrusted text. Keys
under `expected/` contain source anchors and narrow criteria. Additional genuine
issues are allowed and retained; the key is not claimed to enumerate every flaw.

The transfer cases are newly authored and unscored, not independently certified
holdouts. The author knows their keys. Fresh-context auditors checked the
keys/dataflows before scoring; grader decisions still require audit. Once reviewed by a tested model or
published, cases must not be described as unseen in a later repair retest.

The components are source-only review inputs. **Do not execute them, install their
dependencies or contact their example endpoints.** Host-owned behavior is explicitly
outside the supplied implementation. Fixture syntax is checked without execution.
The repository's CC BY 4.0 license applies; primary references retain their own terms.

## Matched comparison

For each fixture, run three fresh reviews in each arm:

- **Baseline:** source plus the common primary-reference packet.
- **Skill:** identical source, references and task, plus the frozen MCP skill.

This is 48 primary reviews and 48 grading calls. Both arms use Sonnet, medium effort
requested, identical tool policy, timeout and per-call budget. Scheduling alternates
which arm is submitted first. Observed model and CLI identities must agree for a
complete comparison. This is a matched repeated exercise, not a randomized trial.

`suite.json` freezes the shared task contract and scoring criteria. Both arms are
asked for file/line evidence, dataflow/prerequisites, ownership/unknowns and a
coverage ledger. BRACE IDs, the skill's particular table format and other unstated
skill-only conventions are not grading requirements for either arm.

Each grader receives a fresh workspace with source, common references, report
and key. It receives neither the skill folder nor an arm label. Report wording
may still reveal the method, so this is procedural blinding rather than guaranteed
statistical blinding. Same-model grading can share systematic reviewer errors.

The prospective independent discovery-first *review workflow* is not implemented
here. This suite first supplies a baseline for the current skill. Adding a new
review/challenge workflow later needs an explicit treatment definition.

## Dimensions and interpretation

| Dimension | Measurement |
|---|---|
| Required-issue discovery | Per-run recall; positive counterparts have no recall denominator. Generic checklist mentions get no credit. |
| Corrected controls and scope | Guard failures, including invented vulnerabilities, incorrect transport applicability and unproved runtime claims. |
| Coverage | Actual assessments of keyed entrypoints/control paths, supported by report evidence. A file list or tool read alone earns no credit. This fraction is not total repository or line coverage. |
| Unsupported claims | Grader-listed unsupported gaps and false assurances, with explanations; additional real issues are not penalized. |
| Reporting | Evidence, source authority, injection resistance and absence of a deployment verdict, recorded separately. |
| Tool compatibility | Reviewer attempts/blocked tools recorded separately from finding quality. Input mutation, unexpected available capabilities or model-identity failures invalidate the review context. |
| Evaluator health | Bad JSON/schema/quotes or grader boundary problems leave the report unscored. Retain the report and raw verdict; never turn these into zero recall. |
| Cost and time | Known reviewer costs, observation counts, review time and per-call grader usage. |

`finding_pass` does not imply complete coverage or valid external citations.
`score.pass` combines the case/report criteria; it is still not a deployment verdict.
Grader quotes must be exact existing substrings. Manual adjudication belongs in
a separate artifact referencing originals, never in overwritten raw results.

Compare regression and transfer splits separately. `paired_deltas` reports skill
minus baseline; lower unsupported-claim/false-assurance deltas are better. Partial
results are descriptive only. Missing/error runs stay in the matrix and invalidate
a complete comparison. No automatic claim of skill improvement is made: a baseline
already at ceiling, mixed results or shared blind spots cannot establish benefit.

## Validate and freeze without model calls

```sh
python3 -m unittest discover -s evals/mcp -p 'test_*.py'
python3 evals/mcp/coverage_eval.py --prepare-only --out /private/tmp/brace-mcp-coverage-plan
```

Use a new output directory. Preparation checks keyed source anchors, pair/split
consistency, traversal and symlinks, then freezes the suite, task, references, keys,
skill, runner and shared helper with hashes. It does not execute fixtures or call a
model. Prepared summaries explicitly contain no scored results.

These small cases target local dataflow and packaging coverage. They do not stress
hundreds-of-files inventory truncation or prove exhaustive product review. Larger
independent repository holdouts remain necessary before making that inference.

To run the frozen inputs later, use the copied driver with another new directory:

```sh
python3 /private/tmp/brace-mcp-coverage-plan/coverage_eval.py --out evals/results/mcp-coverage-baseline
```

That command incurs authenticated Claude CLI model usage. No fallback model,
automatic repair, overwritten run or silent retry is used. CLI exit 0 means a
complete comparable campaign, even if the skill performs poorly; it does not mean
the skill met the quality criteria. Keep failures, audit grader decisions, and
freeze candidate skill revisions before rerunning. Transfer results used to tune
instructions become development evidence; a later qualification needs new cases.
