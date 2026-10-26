# Stateful fixture construction and source-first key audit

The [stateful difficulty-development edition](../../mcp/stateful/README.md)
contains **12 repositories, six required bugs, 94 guard assessments and 72
coverage checks**. Each issue has a narrowly corrected counterpart. All three
independent audit batches accept the revised keys. See
[acceptance.json](acceptance.json) for the accepted snapshot and exact hashes.

This records construction and source auditing, **not a difficulty score**. No
Sonnet plain/skill discovery campaign was run. Six bugs with three repetitions
would yield 18 required observations per arm. The desired 40–60% plain baseline
range remains an aspiration to measure. No fixture code was imported/executed,
no fixture tests ran, and no live MCP/provider requests were made.

## Construction and independent inspection

A single root author built six application mechanisms on a shared local
host/registry platform. Repositories have 38–41 files and approximately 650–750
nonblank source/config/doc/test lines. They include actual host/session/config,
discovery, journal and batch paths, not inert padding files. They remain compact
synthetic applications, not real production repositories or independent authorship.
The existing coverage/deeper suites and MCP skill were preserved.

Three fresh independent agent contexts inspected four source repositories each.
They wrote a source-first findings artifact before opening keys/witnesses, then
checked every keyed ID, actual effect, prerequisites, blockers, normal behavior,
correction and direct answer cue. Source/code was untrusted data. They could see
both members of each pair; this was key auditing, not blinded target-reviewer
measurement. Filesystem separation was procedural. Exact served auditor models
and costs are not exposed by the host and are not inferred.

- A confirmed the credential-partition and revoked-job mechanisms and challenged
  stale counterpart guard wording and cancellation error precedence.
- B confirmed logical/wire identifier reinterpretation and lost retry account
  context. It noted a literal-percent lookup failure from the same representation
  defect and clarified the first-mail-after-rotation prerequisite.
- C confirmed cross-tenant retry-result reuse and mutable reviewed-plan execution.
  It also noted key-preemption denial of service from the same namespace defect.

All required sequences are supported by the supplied source, with actors and
legitimate earlier activity explicit. Narrow corrected behavior is supported by
source, not claimed as experimentally verified. Auditors found no direct issue/fix
labels or exploit tests in the reviewer trees. Ordinary documentation still states
intended business and adapter contracts; their presence may affect difficulty.

## Preserved freezes and corrections

The original [freeze](freeze.json) and `snapshot/data` remain preserved. Initial
A verdict was revise; B and C were accept. [corrections-v2.json](corrections-v2.json)
records all edits: guard/witness wording only, including actual local host versus
unknown external wire behavior, cancelled-job error precedence, representation
counterpart behavior and shared reconnect timing. Fixture source trees are
**byte-identical** across the two freezes. No skill edits occurred.

Each original auditor rechecked its changed keys/witnesses against unchanged
source. All three rechecks accept with no outstanding key challenges. The accepted
freeze is `snapshot-v2/data`, matching the working `evals/mcp/stateful` dataset.
Raw audit findings, source-first artifacts, mappings, recheck packets and rejected
wording remain available. No failed target-reviewer scores were filtered away;
there have been no target-reviewer trials.

A source-first artifact used 20 compact/ellipsis excerpts rather than literal
source substrings. Root mechanically expanded the cited line spans afterward in
`audit-A.source-first.exact-quotes.json`; its original remains intact. C corrected
two source-first quote-formatting details after key review; its originally written
artifact was reconstructed from writer-call history and the recovery/provenance
note is retained. These were citation presentation repairs, not new independent
pre-key findings. Exact-quote membership does not prove semantic completeness.

## Validation and reproduction

[validation.json](validation.json) records static AST/JSON/TOML parsing, source/key
anchor checks, all keyed IDs audited, matching working/frozen hashes, unchanged
source between freezes and unchanged MCP skill. It validates 671 exact audit
source quotations across selected citation versions and rechecks. The
[harness/repository checks](checks.json) passed: **27 unit checks plus 113 existing
pytest checks**. The added test verifies narrow pair differences, catalog/actual
registration agreement, source parsing and reviewer-copy isolation from witnesses.

```sh
python3 evals/results/2026-10-25-mcp-stateful-key-audit/validate.py
python3 -m unittest discover -s evals/mcp -p 'test_*.py'
```

These commands parse data and run trusted harness tests with model calls mocked.
They do not execute the fixture test suites. The working BRACE version is 2.6.0,
synchronized in VERSION, README, homepage and citation metadata. The MCP skill
remains `ee2b246495ebe9f01565590eddde62c475b2eee2286754e2eb84b6a8cbe7d294`.
All credentials/data are synthetic and covered by the repository CC BY 4.0 license.
No git operations were performed. Runtime proof, target-model difficulty, native
MCP integration and deployment safety remain unmeasured.
