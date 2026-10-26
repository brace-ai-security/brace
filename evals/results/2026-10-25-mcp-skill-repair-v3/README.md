# MCP skill repair regression: revision 3

Nine fresh Sonnet skill-only reviews: Otter, Badger and Wren three times each.
Exact request: `Please review with brace-mcp-review`. The current skill was
exposed through the same minimal host catalog, with shared read-only constraints
as system context. All nine loaded the skill; source code was never executed.
This is a known-case repair trial, not a new holdout or three-arm comparison.

An independent source/report/key auditor inspected every report without reading
the proposed skill edits. [Exact audit and report hashes](audit.json). No automatic
grader calls were used because the known-report classifier remains uncalibrated.

- Required tenant-bypass findings: **3/3**.
- Coverage: **29/30 complete**, **1 partial omission**.
- Provenance: **9/9**; no demonstrably fabricated dates or verification claims.
- Reports with additional incorrect/unsupported assertions: **4/9**.
- Known primary-review cost: **$1.06**; audit work is excluded.

[Raw execution records](repair.json), per-run reports/traces and frozen inputs
are preserved. The local matrix summary is prepared/unscored because only this
nine-report subset ran; it is not a completed 72-review matrix.

The final trial has correct date/verification provenance and all Python operation
assessments, but one Wren report omits the parallel package-bin launch mapping.
Four reports still contain concrete factual/unsupported assertions: an incorrect
None-identity GET-flow claim, two unverified host/user-authority assertions, and
an unestablished shutdown/stop assessment. Citation URL omissions are separate
completeness issues. The current Sonnet workflow is not generally qualified.

UTC review-date24 versus Berlin date25 is not counted as false without clock
evidence. Ambiguous excerpt/event wording is recorded as uncertain, not invented
verification. Core dates and exact verification URL/entry membership are checked.

The [new deeper-case candidate](../2026-10-25-mcp-deep-candidate-v3/README.md)
remains unscored; its source/key audit preceded every skill edit. Automated grader
calibration and remaining report-verification work are `brace-ec9.6` and
`brace-ec9.10`; the later comparison is `brace-ec9.9`. These repeated known cases
cannot establish transfer, native host routing, live behavior or deployment safety.
