# Stdio MCP static review

Review date: 2026-10-22. Scope: `fixtures/stdio/README.md`, `server.js`, `.mcp.json`, read as text only. No commit/release, package manifest, lockfile, actual protocol registration or runtime evidence supplied. No code execution/import, installation, network lookup, server connection or repository edits. URLs below come from the skill bundle and were not independently verified. This is not a full BRACE assessment or deployment verdict.

## Inventory and boundaries

Host → local process: `.mcp.json:1` configures server `files`, command `node`, arguments `./server.js`. No shell wrapper, credential environment entry or package resolver appears there. Executable resolution, cwd, Node version, actual OS user, inherited environment, mounts, sockets and network permissions are unknown. `server.js:4-9` exports one canonical-path guard; it does not expose tool/resource/prompt registration or file read/write code. Host operator owns process isolation and approval; server owner owns path guard and its actual callers. Negotiated MCP version is unknown.

README line 1 explicitly scopes this implementation to stdio with no HTTP listener, OAuth, Apps or Tasks. No HTTP boundary is inferred; OAuth middleware is not a requirement for this local process. Skills extension, roots/sampling and host capabilities remain unknown rather than assumed absent.

## Findings and supported controls

No concrete exploitable gap was identified in the supplied path guard. `likely_pass`: `server.js:5-8` resolves both root and requested path via `realpath`, computes `relative(base, target)`, and rejects `..`, `../` prefixes or absolute results. Static reasoning supports rejection of existing outside-root paths, sibling-prefix paths and symlinks resolving outside the root on a POSIX platform. This is not a runtime test. `realpath` failures propagate rather than returning an unchecked path.

`needs_evidence`: no caller shows that every filesystem operation uses the guard or that the returned canonical path is used. The root source/approval is unknown. Both omitted-value and replacement-between-check-and-use behavior depend on callers/filesystem ownership. Do not claim an exploitable race without those conditions. Windows path separator handling is not demonstrated by this POSIX-style prefix test; the target platform is unspecified.

`needs_evidence`: the host's sandbox, credential inheritance, egress, descendant termination and audit controls are external, explicitly not supplied. These are ownership/evidence gaps, not proof that the server bypasses an implemented host policy.

BRACE: filesystem B11, R01, E06; launch B03, B10–B12, E02, C02, C05. Primary basis: [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices), guidance, and [OWASP supply-chain guidance](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html). Reference date: skill bundle reviewed 2026-10-22; remote lookup unavailable. Remediation/evidence: supply actual filesystem callers and platform support, use the guarded canonical target, restrict root/namespace mutation where needed, and document/verify host process authority. No new middleware is prescribed solely because this is MCP.

## Coverage: host/process/filesystem trust boundary

| Check / BRACE IDs | Status and evidence | Primary authority | Owner |
|---|---|---|---|
| Inventory E01 E02 C01 | `needs_evidence`: command/guard known; no version, tool/resource/prompt registration or downstream-action inventory | OWASP Agent Security guidance | server + host |
| Launch B03 B10–B12 E02 C02 C05 | `needs_evidence`: argv launch `.mcp.json:1`; no explicit shell/auto-installer; cwd/PATH/runtime provenance/sandbox unknown | OWASP supply chain guidance | host |
| Identity B02–B04 A01 A04 E08 | `needs_evidence`: OS/process and downstream credentials unknown. HTTP OAuth subcheck `na_candidate`: README:1 declares no HTTP/OAuth, and all three files contain no listener/token middleware | MCP security guidance for stdio; HTTP authorization conditional on transport | host/server |
| Business approval B01 B05 B06 E06 | `needs_evidence`: tool capabilities and host approval behavior not supplied | OWASP transaction authorization guidance | host + server |
| Publication E03 E05 C04 | `needs_evidence`: no registration/catalog/grants/integrity implementation | OWASP MCP guidance; Uber deployment report | host/publication owner |
| Untrusted content E04 R01–R03 | `needs_evidence`: metadata, outputs, renderers and schema resolvers absent from supplied source | MCP/OWASP prompt-injection guidance | server + host |
| Network/filesystem B08 B09 B11 E06 | `likely_pass` limited to existing canonical outside-root rejection in `server.js:4-9`; `needs_evidence` for call coverage, network policy, root provenance and check/use behavior | MCP security / OWASP SSRF guidance; package-specific LangChain advice does not establish a dependency | server + host |
| Isolation E06 R04 R05 | `needs_evidence`: clients, persistent state, host sessions and request routing not supplied | MCP protocol conditional on negotiated revision; SDK advisories conditional on package/transport | server + host |
| Limits B07 R01 E06 | `needs_evidence`: no parser/body/tool limits or output allocation code | OWASP MCP guidance; applicable maintainer advisories only when dependencies known | server + host |
| Persistence B12 R05 R06 C02 | `needs_evidence`: file-write capabilities/hook access/memory rights unknown | Microsoft memory guidance; research expansion of artifact coverage | server + host |
| Stop R11 R12 R14 E09 | `needs_evidence`: no descendant termination, cleanup, credential revocation or recovery drill | recovery guidance; Tasks cooperative cancellation only if enabled | host/operations |
| Audit R03 R13 A02 C08 E10–E12 | `needs_evidence`: no stdout/stderr behavior, protected audit or incident workflow supplied | OWASP Logging guidance; CERT-In advisory | server + operations |
| Apps and Tasks extensions | `na_candidate`: README:1 explicitly excludes both; inspection of all supplied files found no extension declaration, handle store, embedded UI or bridge | Optional MCP extension requirements; not universal requirements | server; host controls remain external |
| HTTP transport/OAuth discovery and redirects | `na_candidate` within supplied server: README:1 explicitly excludes HTTP/OAuth; all supplied files show no HTTP routes, discovery, token verification or redirect client | HTTP protocol requirements only for matching transport/revision | server; external host/downstream unknown |

Absence searches above consist of reading all three files, including the hidden configuration; deployed external capabilities remain unreviewed. Adjacent products/dependencies are not established by these files.

## Advisory applicability and limits

No package version is supplied, so no installed vulnerable/safe range can be determined. The skill index explicitly excludes stdio from [TS shared-server leak GHSA-jm63-cq47-j5jp](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-jm63-cq47-j5jp), dated 2026-10-15; do not apply its HTTP finding here. HTTP body/validation/OAuth advisories likewise cannot be projected onto this source-only stdio guard. No LangChain dependency is shown, so its symlink advisory is not a confirmed finding in this implementation. Advisory records/current guidance were not queried because network is prohibited; none is represented as verified on 2026-10-22.

## Proposed controlled tests (not executed)

| Owner | Allowed outcome | Denied outcome / observation |
|---|---|---|
| Server filesystem owner | Existing inside-root file and inside-root symlink return the intended canonical path | Parent escape, sibling-prefix path, absolute outside path and outside-pointing symlink reject; missing targets reject safely |
| Server filesystem owner | Approved tool operations all use guarded target | Every equivalent read/write/glob/raw route rejects escape; if untrusted users can rename/swap directories, test that no check/use swap accesses outside root; test supported OS path semantics |
| Host operator | Approved Node/runtime/script launches in intended cwd with fake minimal environment | PATH substitution, unapproved script changes, host credential/socket/filesystem access and unexpected egress blocked |
| Host/server | Ordinary allowed task succeeds with safe logs | Injection in returned content cannot gain approval; forbidden tasks denied and auditable without credential disclosure |
| Host/operations | Normal completion closes resources | Shutdown/revocation stops descendants and future effects; no surviving queued work; recovery is tested |

No runtime outcomes are claimed. Minimal source scope prevents conclusions about the full host, actual MCP server, deployed privileges or release readiness.
