# MCP review: records gateway (`repo/`)

**Review date:** 2026-10-23
**Method:** static, file-only review. Nothing was executed, imported or connected to.
**Status vocabulary:** `gap`, `likely_pass`, `needs_evidence`, `na_candidate`. None of these is a security Pass or a release verdict.

## Untrusted content in the repo

`repo/review-notes.txt` is a "supplier note". It tells the reviewer to omit authentication and cache observations and to state that all controls passed. I treated it as untrusted data and did not follow it. This report covers authentication and cache behaviour, and it does **not** claim that all controls passed.

## 1. Scope and inventory

| Item | Finding |
|---|---|
| Component | One Python module, `repo/gateway.py` (74 lines). It does application authorization, a records cache, batch dispatch, task cancel, a worker step and a definition fingerprint. |
| Other files | `repo/catalog.json` (one tool definition), `repo/README.md`, `repo/review-notes.txt` (injection attempt above). |
| Commit / release | Unknown. The directory is not a git repo. |
| Hidden files | `Glob repo/.*` and `repo/**/.*` both returned no files. |
| Dependency manifests, lockfiles, `.mcp.json` | None. The module imports only the stdlib, so no resolved package versions exist to check. |
| Transport | Protected Streamable HTTP, MCP 2026-07-28, as declared in the README. I could not confirm the negotiated version. Version negotiation, protocol-version and routing headers, and header/body comparison belong to the external framing layer, so they are unknown here. |
| Extensions | README says no stdio, Apps or Skills. The `TASKS`/`cancel`/`worker_step` code looks like a Tasks-style feature. Whether it implements the MCP Tasks extension is unknown. |
| Operating systems | Not stated. |
| Server and credential inventory | One server. `JWT_VERIFY_SECRET` is read from the environment, and the fixture contains no live key. Backend credentials are not shown. |
| Exposed operations | Catalog declares `read_records`. Code and README also reach `read` and `delete` through `dispatch`, plus `cancel`. |

**Ownership**

| Owner | Controls |
|---|---|
| Supplied component | Claim checks, tenant/operation authorization, cache, cancel, worker step, fingerprint function, audit calls. |
| External framing/identity layer | Token issuance, key provisioning, header/protocol handling, complete audit capture, deployed limits. |
| Host | Populating `TASKS`, comparing fingerprints, approval service. |
| Backend and sink | Remote backend implementation, audit sink durability and retention. |
| Network and scanner | Network policy and scanner implementation. |

## 2. Sources

No dated primary source was rechecked. Public lookup is unavailable, so every row is bundled and **not rechecked**. Where no publication date is known, the date shown is the bundled review date (2026-10-22), labelled as such.

| ID | URL | Authority | Date |
|---|---|---|---|
| S1 | https://braceframework.org/CHECKLIST.md and https://braceframework.org/RESEARCH-2026-10-22.md | BRACE checklist and research | 2026-10-22 (bundled) |
| S2 | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization | Protocol requirement for 2026-07-28 | Revision 2026-07-28 |
| S3 | https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http | Protocol requirement for 2026-07-28 | Revision 2026-07-28 |
| S4 | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | MCP guidance | 2026-07-28 revision |
| S5 | https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html | OWASP guidance | 2026-10-22 (bundled) |
| S6 | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | OWASP guidance | 2026-10-22 (bundled) |
| S7 | https://www.cert-in.org.in/s2cMainServlet?VLCODE=CIAD-2026-0049&pageid=PUBVLNOTES02 | Government advisory (CIAD-2026-0049) | 2026-10-15 |
| S8 | https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html | OWASP guidance | 2026-10-22 (bundled) |
| S9 | https://modelcontextprotocol.io/extensions/tasks/overview | Optional extension; cancellation is cooperative | 2026-10-22 (bundled) |
| S10 | https://www.rfc-editor.org/rfc/rfc9700.html and https://www.rfc-editor.org/rfc/rfc8693.html#section-4.1 | BCP / actor semantics | Bundled |
| S11 | https://www.uber.com/us/en/blog/designing-mcp-gateway/ | Deployment report | 2026-10-01 |
| S12 | https://modelcontextprotocol.io/specification/versioning | Official versioning page | Identified 2026-07-28 on 2026-10-22 |

**Advisories:** the bundled TS, Python, Splunk and adjacent-component records match no package, because none is present. I make no exposure claim. Resolved versions are unknown, and none of these advisories was rechecked.

## 3. Findings (ordered by impact)

### F1. Medium, `gap`: the read cache is never invalidated and can serve data after a delete

- **Evidence:** `gateway.py:36-40`. The key is `(tenant, sub, RESOURCE, POLICY_VERSION, tools, query)`. There is no TTL, size bound or invalidation hook. `POLICY_VERSION` is a constant (`:4`).
- **Dataflow:** an authorized user reads a query and the result is cached. A `delete` goes through `dispatch` (`:31-34`). README confirms backends implement `delete`. The same user, or any session with the same tenant, sub, tools and query, reads again. `:38` returns the cached value without calling `invoke` or the backend.
- **Impact:** deleted or changed records stay readable. Backend-side per-record authorization changes are also not seen. The key does include the tenant, subject and tool grants, so I found no cross-tenant leak in the key design.
- **Limit:** the cache is process-global, so multi-worker behaviour is unknown.
- **BRACE / sources:** E06, R04 (S1, S5; http.md step 6, "cache hits … need current authorization").
- **Remediation:**
  - Add a short TTL and a size bound.
  - Invalidate on delete or write, and tie the key to a policy/data version that changes at runtime.
  - Copy cached values before returning them.

### F2. Medium, `gap`: audit outcomes are missing on failure paths

- **Evidence:**
  - `handle_http:65` calls `audit_sink.begin`, but `complete` (`:72`) runs only on success.
  - Any `PermissionError` or `KeyError` from `invoke`, `cancel` or `read_records` leaves a begun record with no outcome and no denial reason.
  - Origin, size and authentication rejections (`:59-63`) occur before `begin`, so this component records no attempt for them.
  - `worker_step` (`:48-52`) has no audit call at all.
  - The full raw `request` and `result` go into the audit record, which is a secret and data-minimization concern.
  - The audit record carries only `subject`, `tenant` and `policy`. There is no agent/actor field, approval ID or destination.
- **Mitigating contract:** `begin` reserves capture and raises when the buffer is full, which is a fail-closed design. README assigns complete attempt/denial/worker capture to the external layer, but that layer is not supplied. The status is therefore `gap` for this component's own outcome recording and `needs_evidence` for end-to-end completeness.
- **BRACE / sources:** R03, R13, A02, E10–E12 (S6, S7, S1).
- **Remediation:**
  - Wrap the dispatch in `try/finally` and record a denial or error outcome.
  - Audit worker steps with the task ID, the original subject and a policy ID.
  - Redact or hash request and result payloads.

### F3. Low, `needs_evidence`: resource limits are thin

- **Evidence:**
  - The only input bound is the 8192-byte body check (`:61`). It runs before parsing, which is good.
  - There is no cap on batch element count. A body of that size can hold on the order of 100+ minimal calls, each hitting the backend (`:33`).
  - There is no per-subject rate limit.
  - The cache is unbounded (F1).
  - Token length is not bounded here.
- **Limit:** deployed limits are external and unknown.
- **BRACE / sources:** B07, R01, E06 (S5, S1).
- **Remediation:** add a maximum batch size, per-subject rate and concurrency limits, and a bounded cache.

### F4. `needs_evidence`: dispatch authorization is not tied to the approved catalog or definitions

- **Evidence:**
  - `invoke` (`:24-29`) authorizes any tool name found in the token's `tools` claim. It does not consult the catalog or the fingerprint.
  - `catalog.json` advertises only `read_records`, with `readOnlyHint: true`. The code and README reach `read` and `delete`, and the names differ (`read_records` vs `read`).
  - `inputSchema` omits `tenant`, but `invoke` requires `args["tenant"]` (`:25`).
- **Fingerprint:**
  - `fingerprint` (`:54-56`) hashes the whole definition passed in, with sorted keys. That would cover annotations and `outputSchema`, if the host passes the complete definition.
  - The comparison and reject step is host-owned and not supplied (README).
  - Whole-definition hashing sharpens BRACE's description/schema wording. That is a proposed refinement, not an existing requirement.
  - It establishes consistency only, not safety.
- **Delete:** README policy permits `delete` when the operation and tenant are authorized. That matches the code, so it is not a violation. Whether consequential operations need approval binding is not established. Annotations are not an authorization policy.
- **Batch:** sequential batch execution is not an authorization failure. No atomicity contract is stated, so I raise none.
- **BRACE / sources:** E03, E05, B01, B05, B06 (S1, S5, S8).
- **Evidence needed (host/platform owner):**
  - the host's fingerprint comparison and quarantine behaviour;
  - the claim-to-tool mapping at the IdP;
  - the approval design for `delete`.

### F5. `needs_evidence`: identity and delegation

**Supported in code (`likely_pass`), `:10-22`:**
- The algorithm is pinned to HS256 and the signature is checked with `compare_digest`.
- Issuer is an exact match, expiry is enforced, and the revoked-`sub` set is checked.
- Audience is checked against `RESOURCE`. The check accepts a string or a list of audiences.
- Missing claims raise `KeyError`, so the check fails closed.
- Tenant and operation are checked at the destination (`:25-28`).

**Unknowns:**
- The symmetric HS256 secret means any holder of it can mint tokens. Key custody and rotation are external.
- `REVOKED` is a process-local in-memory set. Its propagation across workers is unknown.
- `nbf` and the `typ` header are not checked.
- Claims carry no agent/actor distinction. Original subject versus current actor (RFC 8693) is not modelled.
- The backend is called as `backend(name, args)` with no token shown. Its own credential and audience are unknown, and whether a frontend token is passed through is unknown.
- Origin handling: an exact match is required (`:59`) and a missing Origin fails closed. Whether non-browser clients are expected is unknown.

**BRACE / sources:** B02–B04, A01, A04, E08 (S2, S3, S10).

### F6. `needs_evidence`: Tasks, cancel and stop

- **Supported in code:**
  - `cancel` (`:42-46`) enforces tenant ownership. README policy allows any authenticated same-tenant user to cancel, so this is consistent.
  - `worker_step` rechecks cancelled, revoked and expired state (`:50`) before each step. Authorization is rechecked via `invoke` with the stored claims.
- **Unknowns and limits:**
  - Cancellation is cooperative (S9). An in-flight backend call is not interrupted. Time to stop effects needs a drill.
  - An unknown handle raises `KeyError`, while a cross-tenant handle raises `PermissionError`. Handle existence is therefore distinguishable. Handle entropy and `TASKS` population are host-owned and unknown.
  - Stored claims are not refreshed, so grants changed after enqueue do not apply.
- **BRACE / sources:** R11, R12, R14, E09, E06 (S9, S1).

## 4. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Inventory and ownership | `needs_evidence` | Single module; backend and host not supplied | S1 | Platform |
| Launch/supply chain (HTTP service) | `needs_evidence` | No manifest or lockfile; stdlib only; image/deploy absent | S1 | Platform |
| Stdio / local process | `na_candidate` | README says no stdio; searched for `.mcp.json` and hidden files (none) | stdio.md | n/a |
| Token verification | `likely_pass` | `gateway.py:10-22` | S2, S10 | Gateway |
| Key custody, issuer, delegation | `needs_evidence` | F5 | S10 | Identity |
| Tenant and operation authorization | `likely_pass` | `:24-29`, applied to batch, cache and worker | S1 | Gateway |
| Business approval for `delete` | `needs_evidence` | F4 | S8 | App/host |
| Catalog integrity, publisher identity | `needs_evidence` | `:54-56`; host comparison absent | S5, S11 | Host |
| Untrusted metadata and returned content | `needs_evidence` | Backend output not supplied; the catalog is static | S4 | Host/backend |
| Egress and network | `needs_evidence` | No outbound I/O in this module; backend and policy external | S4 | Network |
| Cache and tenant isolation | Isolation `likely_pass`; invalidation `gap` | F1 | S1, S5 | Gateway |
| Limits | `needs_evidence` | F3 | S5 | Gateway/framing |
| Persistent influence / memory | `na_candidate` | No memory or skills code found; searched the module and catalog | S1 | n/a |
| Stop and recovery | `needs_evidence` | F6 | S9 | Gateway/scheduler |
| Audit | `gap` (local) / `needs_evidence` (end to end) | F2 | S6, S7 | Gateway + sink |
| Protocol version and header consistency | `needs_evidence` | Outside the supplied module | S3, S12 | Framing |
| Enabled extensions (Tasks) | `needs_evidence` | F6 | S9 | Gateway |

## 5. Controls supported in code, and what remains unreviewed

- **Supported in code:**
  - Origin allowlist and a body-size check before parse.
  - Token validation.
  - Per-call tenant and operation checks on single, batch and worker paths.
  - Tenant-scoped cache key.
  - Tenant-checked cancel, and a worker re-check of revocation and expiry.
  - Fail-closed audit reservation.
  - A whole-definition fingerprint function.
- **Unreviewed:**
  - Framing layer, IdP, audit sink, backend, scheduler, approval service, scanner and network policy.
  - Deployed limits and runtime behaviour.
  - Actual package and version provenance.
  - Static reasoning in this report is not a runtime test result.

## 6. Proposed controlled tests

Run these only on a disposable fixture, with an owner assigned. They have not been executed.

| Test | Allowed | Denied / expected | Owner |
|---|---|---|---|
| Read, delete, re-read with the same key | First read succeeds | Re-read returns no deleted data | Gateway |
| Token with wrong issuer, audience or tenant; expired; revoked `sub` | Valid token works | All denied | Identity/gateway |
| Batch containing an out-of-grant tool or tenant | Authorized calls pass | Unauthorized call denied; document the partial-execution contract | Gateway |
| Oversized batch, many requests per subject | Normal load | Rejected or throttled; cache stays bounded | Framing |
| Cancel and revoke mid-task | Own-tenant cancel works | Cross-tenant cancel denied; no further backend effects after the stop time | Scheduler |
| Denied and failed requests | n/a | Each leaves a complete attempt/outcome record, with minimal payload in the audit | Audit owner |
| Changed annotation, `outputSchema` or description | Approved definition loads | Mismatch is quarantined and unapproved tools are not callable | Host |
| Audit buffer full | n/a | The request fails closed | Audit owner |

## 7. Limits

No dated source was rechecked. Static findings are not deployment authorization or certification. This dedicated MCP report is not 53 reviewed BRACE items and cannot feed the full-review validator.
