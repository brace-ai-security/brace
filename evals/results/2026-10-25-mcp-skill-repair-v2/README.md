# MCP skill repair regression: revision 2

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
- Provenance: **7/9**; two incorrect chronology interpretations, no fabricated dates or fresh verification.
- Reports with additional incorrect/unsupported assertions: **5/9**.
- Known primary-review cost: **$1.15**; audit work is excluded.

[Raw execution records](repair.json), per-run reports/traces and frozen inputs
are preserved. The local matrix summary is prepared/unscored because only this
nine-report subset ran; it is not a completed 72-review matrix.

This candidate was superseded by the [third repair revision](../2026-10-25-mcp-skill-repair-v3/README.md). Its failures remain retained.
