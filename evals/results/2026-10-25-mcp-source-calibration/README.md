# Source-evidence grader calibration, 2026-10-25

The source-audit protocol passed a narrow gate before the deeper campaign:
**9/9 clear critical targets matched; 3 disputed targets retained and excluded.**
This is a check of selected claim decisions, not nine complete reports graded
without error, a population accuracy estimate, or a model qualification.

The earlier Sonnet freeform count graders matched 3/6 and then 2/6 known targets.
Those failed packets remain in `2026-10-24-mcp-grader-calibration` and its `-v2`
sibling. They were not used to score the deeper study. The replacement requires
typed claim judgments with exact report/source quotations and derives incorrect
claim arrays mechanically. An explanation that accepts a statement cannot also
count it as an error. Report completeness remains separate.

## Gate composition

| Packet | Real reports | Clear targets | Disputed/excluded |
|---|---:|---:|---:|
| This calibration | 6 | 5 | 1 |
| [Separate validation](../2026-10-25-mcp-source-validation/README.md) | 4 | 2 | 2 |
| [Explicit contradiction controls](../2026-10-25-mcp-source-controls/README.md) | 0 (2 constructed controls) | 2 | 0 |
| Total | 10 + 2 controls | 9 | 3 |

Inputs, gold-label history, independent gold audits, raw grades and derived scores
are retained. Gold auditing and report grading used separate contexts. The three
disputed labels concerned source-contract versus runtime scope: a stated host
line limit, process authority, and consequences of cancelling reads. Independent
audits found that a forced negative label would overstate the evidence. Their
original labels and grader decisions remain visible; exclusion is not a match.

Protocol 2 clarifies that repeating an explicitly supplied contract in a bounded
source review does not claim independent runtime verification. Missing an unknown-
control caveat affects completeness; an actual unsupported assurance remains an
error. Code-only observations can use repository sources. Exact quotation
validation proves membership, not semantic entailment or exhaustive claim capture.

Grader agents inherited the orchestrator default. The host did not expose their
exact served model identities or costs; neither is inferred. Positive target
matching includes the statement's scoped paragraph; negative targets require
localization to the asserted sentence. Protocol revisions and prior labels are
preserved. See [gate.json](gate.json), [checks.json](checks.json), and
[the reproducible checker](../../mcp/grading/check_calibration.py).

```sh
python3 evals/mcp/grading/check_calibration.py
```

The subsequent [72-review deeper study](../2026-10-25-mcp-deep-source-graded/README.md)
uses this source-audit method without changing its frozen skill or fixture keys.
