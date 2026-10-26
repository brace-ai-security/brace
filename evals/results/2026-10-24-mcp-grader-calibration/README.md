# Known-report grader calibration: first revision

Six prior source-review reports were regraded with revised claim-classification
instructions. No new primary reviews or deep-case model reviews were run.
The exact frozen code/inputs, raw verdicts, traces and expected target counts
are retained. Expectations come from prior source-backed author adjudications;
this is a narrow regression exercise, not an independent accuracy benchmark.

- Attempts: 6; schema/tool-valid scored outputs: 6.
- Exact target-count matches: 3/6 attempted reports.
- Known provider grading cost: $0.43.

Mismatches may require source adjudication; evaluator faults are not zero-accuracy
reviews. The classifier has not met these calibration targets. Do not treat its
incorrect-claim totals as independently validated. Follow-up: `brace-ec9.6`.

[Raw calibration results](calibration.json). [Earlier three-arm source reports](../2026-10-24-mcp-three-arm/README.md).
