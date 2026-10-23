# MCP skill repair retest — 2026-10-23

The final frozen skill found all nine keyed issues in every applicable review:
27 of 27 issue observations, with all 45 positive/unknown guard observations met.
All 12 reviewer reports meet the exercised reporting and tool-use criteria after
one documented grader-quote adjudication. No reviewer requested an unavailable
shell tool in this final matrix. This supports bounded source-review utility.

The **full automated harness did not strictly pass**: 10 raw passes, one invalid
quote, and one grader workspace-policy failure. Neither evaluator fault is a
security-analysis miss. Raw reports, verdicts and statuses remain unchanged.
See [audit.json](audit.json), [summary.json](summary.json) and the
[quote adjudication](keystone.sonnet.run-1/adjudication.json).

| Fixture | Keyed gaps | Reviews | Substantive/report checks after audit | Raw harness |
|---|---:|---:|---:|---|
| harbor | 5 | 3 | 3/3 | 3 pass |
| keystone | 0 | 3 | 3/3 | 1 pass, 1 quote error, 1 grader boundary failure |
| meadow | 4 | 3 | 3/3 | 3 pass |
| cobalt | 0 | 3 | 3/3 | 3 pass |

The mistaken grader path was rejected by the restricted CLI; no external content
was returned. The invalid quote differs only by an en dash in a line range. The
separate adjudication substitutes the exact existing report quote; it changes no
report, finding or substantive judgment.

## Retained iterations

- [Original diagnostic campaign](../2026-10-23-mcp-qualification/): all keyed gaps
  found, four blocked shell attempts, one graded authorization overstatement;
  citation omissions accepted by an insufficiently explicit grader.
- [First repair](../2026-10-23-mcp-repair/): all keyed gaps found, three blocked
  directory-listing attempts, inconsistent citation completeness, and additional
  overstatements retained in raw grades.
- This final retest: concrete Glob instructions, source-table references, offline
  citation dates, and explicit distinction between sequential authorized batches
  and authorization failures. Available tools are named in the runner prompt.

Observed model: `claude-sonnet-5-5`, Claude CLI `2.1.309`, medium effort requested.
Each primary review and grader used a fresh isolated context. Input snapshots,
runner hashes, tool traces, reports, costs and verdicts are retained. The current
runner additionally distinguishes reviewer and grader policy issues; use each
campaign's saved runner to reproduce its original behavior.

## Scope and publication

These are four source fixtures in **two paired transport families**, HTTP and
stdio. Repeated fixes were tested on already observed fixtures, so this is a
repair/regression result, not a fresh holdout qualification. Same-model grading
and maintainer-agent adjudication do not establish general reliability. Gap recall
is 1.0 in each of three runs for each negative fixture (sample deviation 0); the
positive fixtures have no predeclared gaps and therefore no gap-recall denominator.

No native routing, live servers, deployment effectiveness, current-advisory web
discovery or no-skill comparison was tested. No deployment approval is implied.

[Public fixtures](../../mcp/fixtures/), [separate answer keys](../../mcp/expected/)
and the [protocol](../../mcp/README.md) are published under the repository's CC BY
4.0 license. The credential is synthetic. Once public, these are regression inputs;
future independent qualification needs fresh holdouts.
