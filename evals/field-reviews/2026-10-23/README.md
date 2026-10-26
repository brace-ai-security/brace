# MCP product-source exercise — 2026-10-23

The repaired skill ran once in a fresh Sonnet context for each of three pinned
public components. All used `claude-sonnet-5-5`, Claude CLI 2.1.309, medium effort
requested, and Read/Glob/Grep only. No server, dependency installer, scanner,
credential or product API was used. Current public maintainer advisory records
were supplied as data; the model itself had no web tool.

Read the [adjudicated findings](audit.md) before the raw reports. The audit adds
two source-supported gaps that the skill missed and narrows several raw claims.

| Target | Useful result | Important limit | Raw report |
|---|---|---|---|
| Notion 2.5.2 source | SDK 1.29.0 and relevant HTTP batch advisory; follow-up inspection found an inherited-key session lookup with uncaught async rejection | Default bearer gate still applies. Process exit inferred from source and runtime documentation, not reproduced. Validation-exhaustion reachability remains unknown. | [Notion](notion/report.md) |
| GitHub MCP v2 source | Both advisory-described bugs have visible source remediations | Most individual tool implementations and deployed releases remain unverified. | [GitHub](github/report.md) |
| Stripe 0.3.3 adapter source | Two lockfiles select old SDK clients; follow-up inspection found missing secret-field metadata in the desktop manifest | No live redirect, installed key exposure or hosted authorization defect demonstrated. | [Stripe](stripe/report.md) |
| Official Trello | Public repository and official configuration identified | Repository has no server implementation; suspected service defect could not be assessed. | [Scope](audit.md#official-trello-implementation-evidence-unavailable) |

`runs.json` records commits, source/skill/research hashes, observed runtime identity
and model usage. `initial-runs.json` retains the Stripe source-copy failure, which
occurred before any model call. `stripe-copy-error/` and `stripe/excluded-links.json`
document the self-referential LICENSE link and the successful copy's root license.
No source code was changed in preparing the copy.

The [research metadata](research/) retains advisory URLs, dates and affected
ranges. Full source repositories remain upstream under their licenses; they are
not vendored here. Raw local tool logs retain third-party source/advisory content
and are diagnostic artifacts, not curated publication material. Reports preserve
their original wording; use the audit's qualifications and source references.

The three product reviews are incomplete static exercises, not qualification or
security certification. There is no ground-truth denominator for product recall.
Two misses after perfect small-fixture scores show why broader holdouts and
independent dataflow challenges matter. No high-risk deployment yes/no is issued.
