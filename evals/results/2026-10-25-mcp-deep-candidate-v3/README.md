# Latest prepared deeper MCP comparison

**No reviewer-model runs or grading calls on these new cases.**

The accepted edition has 8 paired source components, 8 required findings, 42 guard
assessments and 64 coverage checks. Two authors worked in separate fresh contexts;
two source-first auditors checked causal reachability, attacker prerequisites,
paired corrections and decoys. The first frozen edition exposed answers in tests
and docs; those cues were removed and the revised edition re-audited.

The [accepted source/key freeze](../2026-10-24-mcp-deep-key-audit-v2/acceptance.json)
preceded every skill edit. This candidate contains exactly that data and the
latest repaired skill; [plan.json](plan.json) records hashes and follow-ups.
Earlier prepared candidates remain preserved and unrun.

The [known-case repair audit](../2026-10-25-mcp-skill-repair-v3/README.md) found all
three expected findings and correct provenance in all nine reports, but four
reports still had factual/unsupported assertions and one launch mapping was
partial. The current Sonnet workflow is not generally qualified.

The 72-review plan retains the detailed source-review prompt, plain request
`Please review this mcp server for issues`, and short invocation
`Please review with brace-mcp-review`. Three repetitions give each arm 24 required
issue observations, 126 guard assessments and 192 coverage checks. Discovery and
substantive incorrect claims are separate from report completeness.

The automatic grader still misses known-report calibration targets. Comparison
`brace-ec9.9` depends on `brace-ec9.6` or a reliable source-backed independent
adjudication protocol. Source-claim verification/model work is `brace-ec9.10`.
The new data has not been consumed for reviewer or grader outcome tuning.

Once the evaluation protocol is ready, this frozen driver can prepare/run a fresh
output directory using its own immutable inputs:

```sh
python3 evals/results/2026-10-25-mcp-deep-candidate-v3/coverage_eval.py --out evals/results/mcp-deep-three-arm --claude /path/to/private/fixed/claude
```

That command incurs model usage; it has not been run. No fixture code was executed
or imported, dependencies installed, server contacted or live exploit exercised.
Native skill routing, general qualification and actual difficulty remain untested.

## Subsequent use

The statements above describe preparation time. The same frozen skill and data
were subsequently used in the [72-review source-graded campaign](../2026-10-25-mcp-deep-source-graded/README.md)
with a review-only runner and separately calibrated source grading. This prepared
snapshot and its original metadata remain unchanged. The cases are now known
regressions, not an unused holdout.
