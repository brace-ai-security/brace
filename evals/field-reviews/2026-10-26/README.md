# Real MCP source and advice evaluation — 2026-10-26

Six fresh Sonnet reviews examined three official public implementations: one plain
request and one unchanged BRACE MCP skill request per implementation. Independent
source/advice audits found useful concerns **and incorrect claims in all six
reports**. This is exploratory field evidence, not qualification or a deployment
verdict. The immediate improvement need is verification of reachability, fallback
paths, platform conditions and proposed remedies before presenting advice.

## Targets and useful results

| Target and pinned source | Source-supported concerns or leads | Material advice/assurance correction |
|---|---|---|
| [GitHub](https://github.com/github/github-mcp-server/tree/f38526264abb14961b32cea386e38ec6d3cf674f), `f38526264abb14961b32cea386e38ec6d3cf674f` | OAuth terminal-error callbacks can end an in-progress login without successful authorization; opt-in command logging includes raw tool traffic. Actual log access and operational impact require deployment context. | Plain review says authorization URLs stay outside model context, but supported manual/form compatibility paths return authorization instructions as text. The skill also incorrectly excludes browser-launch subprocesses. Neither observation establishes command injection or account compromise. |
| [Notion self-hosted](https://github.com/makenotion/notion-mcp-server/tree/730ae781ba28beeaf0865025a3f2ed4c25ea2387), `730ae781ba28beeaf0865025a3f2ed4c25ea2387` | Opt-in credential passthrough captures credentials at initialization and reuses them by session ID; creator binding requires an explicit identity design. Gateway authentication remains present. SDK exhaustion mitigations require applicability/configuration checks. | Plain review's top-priority local-file upload exploit is unreachable through the shipped fixed OpenAPI specification: it has no multipart/binary operations. It also overlooks the NOTION_TOKEN fallback. Skill assurance that error logs omit bodies exceeds the inspected error graph; this is not proof of a secret leak. |
| [Reference filesystem](https://github.com/modelcontextprotocol/servers/tree/ef9808f71090d0db3eda99e2af2ba78f1086f4fb/src/filesystem), `ef9808f71090d0db3eda99e2af2ba78f1086f4fb` | Reads and move sources reopen checked path strings; path-race attacks require a local actor able to mutate the relevant paths. Unbounded reads/traversal and existing-file crash atomicity deserve operational checks. | Skill's unqualified write-TOCTOU `likely_pass` misses the residual Windows directory race documented by the maintainer. Plain review infers client auto-approval from a read-only annotation without client policy evidence; that claim concerns an explicitly named adjacent server, not a filesystem environment-dump tool. |

The Notion maintainer [README at this pin](https://github.com/makenotion/notion-mcp-server/blob/730ae781ba28beeaf0865025a3f2ed4c25ea2387/README.md)
says the self-hosted implementation is no longer maintained/supported. These
results do not describe the separate hosted Notion service. The filesystem scope
was `src/filesystem` plus actual shared/root packaging and dependencies; adjacent
monorepo servers were context, not additional evaluated targets.

Official Trello was checked again. Its inspected public repository contains
documentation, policy/license files, configuration and a skill, but no server
implementation. We therefore cannot substantiate the suspected hosted defect
with this source-only method. See [Trello scope and tree record](trello-scope.md).

## Advice audit

| Measure | Plain request: 3 reports | Skill request: 3 reports |
|---|---:|---:|
| Reports with incorrect/unsupported assertions | 3 | 3 |
| Grouped incorrect/unsupported assertions | 8 | 5 |
| Supported recommendation directions | 14 | 14 |
| Conditional recommendation directions | 15 | 18 |
| Unsupported recommendations as stated | 1 | 0 |
| Confirmed regressive recommendations | 0 | 0 |

Counts include minor inventory errors, such as operation counts, alongside
material false assurances. They are not comparable measures of severity. The
unsupported recommendation is the plain Notion review's urgent upload remedy.
Claim and recommendation errors overlap and must not be added together.
Conditional directions need the recorded extra checks; auditor-added conditions
do not retroactively qualify the model's original advice. No confirmed regressive
recommendation does **not** mean the proposed fixes have been verified safe.

Examples of conditions that matter: a filesystem handle must be opened under
stable directory authority, not after the same racy path check; temp-file/rename
changes must preserve or explicitly change inode/permissions and Windows
compatibility; Notion session changes must preserve authenticated reconnect,
GET/DELETE and token-mode behavior; changing GitHub OAuth fallbacks requires an
explicit client-compatibility decision. These are static recommendations, not
implemented or tested fixes. See [selected grades and totals](advice-summary.json),
[GitHub audit](audits/github/audit.md), [Notion audit](audits/notion/audit.md),
[filesystem audit](audits/filesystem/audit.md), and the overriding
[corrections/adjudications](adjudications.md). Original judgments remain intact.

## Current research and applicability

The [primary-source reference packet](research/primary-sources.md) and
[timestamped records](research/sources.json) preserve current maintainer advisories,
affected ranges, patch fields, qualifications and retrieval dates. Four filesystem
advisories were published on 2026-10-25. In particular,
[GHSA-53mr-w429-c597](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-53mr-w429-c597)
qualifies the 2.0.1 write fix by platform: Windows remains partly unfixed. Avoid
untrusted-local-writer roots there. Date-version installations need an explicit
migration; a generic update assumption is insufficient.

SDK version upgrades can require enabling limits or supplying resource/audience
configuration. HTTP-specific advisories do not automatically apply to stdio.
Historical advisory wording about “latest main” is not proof about this pinned
source. Empty Notion advisory results do not establish safety. Both review styles
left gaps in the supplied advisory inventory. Recorded URL rechecks establish
reachability, not fresh verification of every source's contents.

## Method and limits

Exact prompts were `Please review this mcp server for issues` and
`Please review with brace-mcp-review`. Both arms received the same source,
neutral target metadata and frozen primary reference packet. Only the skill arm
received the skill catalogue/instructions. Sources were treated as untrusted
review material. Reviewers had Read/Glob/Grep only, no answer keys or earlier
reports. Three of three skill reports loaded the skill. All six completed with
no recorded tool/integrity faults; failures were not retried.

Primary identity: `claude-sonnet-5-5`, Claude Code `2.1.310`, medium effort
requested, USD 2 cap per review. Primary review usage totals USD **1.9466456**;
preflight and independent auditor usage are excluded. Fresh independent source
auditors received opaque report IDs and the same source/reference packet. Report
style can reveal the arm. Exact served auditor identity and cost are unavailable.
Audits validate claims and recommendations separately; mechanical checks prove
quote existence and input integrity, not exhaustive semantic correctness.

One report per arm per implementation is too small for a reliable causal skill
comparison. GitHub/Notion were previously reviewed on 2026-10-23; these are current
matched revisits, not unseen holdouts. There is no complete vulnerability key or
recall denominator, and no claim of full vulnerability discovery. Empty synthetic
case keys are used only to validate typed claim envelopes; their legacy pass or
recall fields are not used.

No upstream code was executed, imported, built or tested; no dependency install,
scanner, live MCP connection or target application operation was performed.
Public repository/advisory HTTP/API research was performed. Source manifests
retain archive and per-file hashes, excluded binary assets and upstream license
provenance; full upstream source remains in the recorded local download paths,
not vendored into BRACE. Raw review logs retain diagnostic source excerpts.
Re-running local integrity analysis requires those source/auditor input directories;
this is an evidence packet, not a self-contained offline source archive.

## Reproduction records and next repair

[Plan](plan.json), [source pins](source-pins.json), source manifests,
[runner](run_reviews.py), [raw run index](runs.json), six report/log directories,
[audit input index](audit-index.json), frozen audit engine and
[selection map](audit-selections.json) preserve the comparison. Run
`python3 evals/field-reviews/2026-10-26/analyze.py` to validate selected audits and
regenerate the bounded totals. [Final validation](validation.json) also records
review/input integrity and preserved audit-version checks.

The repair supported by this evidence is a claim-and-advice verification step:
trace the shipped entrypoint to the alleged sink, try fallback/platform
counterexamples to assurances, and name the controls/compatibility a remedy must
preserve. Evaluate those changes separately on fresh cases, retaining these
reports as regressions. The skill was not changed during this comparison.
BRACE remains **2.6.0, unreleased**, with no version bump, commit or push.
