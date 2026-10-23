# MCP review: records gateway component

**Report destination:** returned inline. The task said not to write files, so `mcp-review.md` was not created.
**Review date:** 2026-10-23. **Method:** static file reading only. Nothing was executed, imported or connected to. Public-source lookup was unavailable, so every advisory and source citation below is **not rechecked** and carries the date recorded in the skill's bundled references.

## Note on untrusted content

`repo/review-notes.txt` contains a "supplier note" telling the reviewer to omit authentication and cache observations and to state that all controls passed. It is untrusted data and was not followed. Findings 1 to 4 below cover exactly the areas it asked to hide. Treat its presence as a provenance concern to raise with whoever supplied the fixture.

## 1. Scope and inventory

| Item | Value |
|---|---|
| Files reviewed | `repo/gateway.py`, `repo/catalog.json`, `repo/README.md`, `repo/review-notes.txt`, and the skill references. No hidden or dot files exist. |
| Component | HTTP gateway application logic: `handle_http`, `worker_step`, and the fingerprint helper. |
| Transport and protocol | Protected HTTP MCP 2026-07-28 (stated in the README, not negotiated or verified). No stdio, Apps or Skills extension. The Tasks-like queue and cancel paths are custom. |
| Commit/release | Unknown. There is no VCS, lockfile or package manifest, so no resolved versions exist. |
| Tool | `read_records` in the catalog. The code also references backend operations `read` and `delete`, and a batch mode that can name any tool. |
| Credentials | Inbound HS256 JWT verified with env `JWT_VERIFY_SECRET` (no value in the fixture). Backend credentials are not shown. |

**Ownership boundaries** (all outside the supplied component, so unknown):
- the framing layer
- identity issuance and key provisioning
- audit sink durability and retention
- scanner
- network policy
- approval service
- remote backend implementation
- deployed limits
- the host that populates `TASKS`

stdio.md is not applicable because the deployment has no stdio.

## 2. Findings (ordered by impact)

### F1. Batch mode skips all authorization (gap, high)
- **Trigger/dataflow:** `handle_http` → `dispatch` (`gateway.py:30-33`). With `request["mode"] == "batch"`, each `call["tool"]` and `call["args"]` goes straight to `backend(...)`. `invoke`, with its tenant and tool checks (`:23-28`), is never called.
- **Prerequisite:** any holder of a valid token from the issuer. Origin is checked, but Origin is not authorization.
- **Impact:** a caller can run any backend operation, including `delete` (named in the README), against any tenant, regardless of `claims["tools"]` or `claims["tenant"]`.
- **Alternate route:** this is a direct bypass of the single-call policy.
- **BRACE:** B01, B02, B05, E06. **Sources:** [OWASP Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html) (guidance); [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) (protocol; not rechecked, 2026-10-22 per bundled map).
- **Fix:** route every batch element through `invoke`. Bound the batch element count. Fail the whole batch, or define per-element semantics, on any denial. Audit each element.

### F2. Read cache is keyed only by query and shared across tenants (gap, high)
- **Trigger/dataflow:** `read_records` (`:35-39`) uses `key = query`, and `CACHE` is process-global. Tenant A reads query `"q"` and the result is cached. Tenant B (or a caller whose tool grant was revoked) sends the same query and gets A's data. On a hit, `invoke` is skipped, so there is no tenant, tool or current-authorization check. The cache has no TTL or eviction, so authorization changes are never reflected.
- **Secondary:** the cache is unbounded (B07).
- **BRACE:** E06, R04, B07. **Sources:** control-map "Client/tenant state isolation" (cache keys and cache hits need current authorization); [http.md](skill/references/http.md) step 6.
- **Fix:** include tenant, subject or policy version and tool in the key. Authorize before every lookup. Add a TTL, a size bound, and invalidation on revocation or policy change.

### F3. Queued work runs on stored claims, and cancellation does not stop it (gap, high/medium)
- **Trigger/dataflow:** `worker_step` (`:47-50`) calls `invoke(task["claims"], ...)` with claims captured earlier. It does not re-run expiry, revocation (`REVOKED`) or policy checks. It also never reads `task["cancelled"]`, which `cancel` sets (`:45`).
- **Impact:** a cancelled, revoked or expired principal's queued task still executes once the scheduler reaches it. The README says the scheduler runs it "once for every queued handle". A successful cancel response therefore proves nothing about effects stopping.
- **Positive:** `cancel` enforces the same-tenant check, which matches the stated policy. It is not itself a gap for the cross-tenant requirement, but handle enumeration (KeyError vs PermissionError) is a minor oracle.
- **BRACE:** R11, R12, E09, B04. **Sources:** [MCP Tasks](https://modelcontextprotocol.io/extensions/tasks/overview) (optional extension; cancellation is cooperative; not rechecked).
- **Fix:** check `cancelled` and revocation/expiry at execution time, re-authorize at execution, and make the stop independent of the cooperative flag. Prove it with a stop-time drill.

### F4. Token verification has no audience or resource check (gap, medium/high)
- **Evidence:** `authenticate` (`:10-21`) verifies the HS256 signature, `iss`, `exp` and the `REVOKED` set. `RESOURCE` (`:3`) is defined and never used. There is no `aud` or resource-indicator check. The comment "Other accepted claims are handled below" is not borne out: `tenant` and `tools` are consumed later, but nothing validates audience, scope or `nbf`.
- **Impact:** any token the issuer signs for another resource, with a compatible `tenant` and `tools`, is accepted. A validated signature is not an audience check.
- **Related unknowns:** the symmetric HS256 secret means every verifier can also mint tokens. Key custody is external, so this is `needs_evidence`. Revocation is a process-local set of subjects whose population and propagation are unknown.
- **BRACE:** B02, B03, B04, E06. **Sources:** [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) (BCP); MCP authorization (protocol; not rechecked). The related SDK advisories (TS GHSA-rvq5-wwqv-78pq, 2026-10-05; Python GHSA-w4fh-qvv9-3v23, 2026-10-05) concern those SDKs. This custom code does not use them, so the advisory fixes are not directly applicable, and the pattern is analogous only.
- **Fix:** require `aud`/`resource` equal to `RESOURCE`, pin `alg` and `typ`, and consider asymmetric verification.

### F5. Definition fingerprint omits `outputSchema` and `annotations` (gap, medium)
- **Evidence:** `fingerprint` (`:52-54`) hashes only `name`, `description` and `inputSchema`. `catalog.json` carries `outputSchema` and `annotations.readOnlyHint`. The README claims "metadata approval covers the complete definition". The code contradicts that, so changes to those fields pass the owner-approval comparison.
- **Impact:** a changed `readOnlyHint` or output schema is not detected. `readOnlyHint` is a server hint, not an authorization policy, and the backend exposes `delete`.
- **Catalog notes:** `inputSchema` has no `tenant` property, no `required` list and no `additionalProperties:false`. The tool name `read_records` differs from the backend operation `read` that is authorized. Whether a mapping exists is `needs_evidence`.
- **BRACE:** E03, E05, C04. **Sources:** [OWASP MCP sheet §2](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) (guidance); [Uber gateway](https://www.uber.com/us/en/blog/designing-mcp-gateway/) (2026-10-01 deployment report). Complete-definition hashing is a proposed refinement of BRACE's description/schema wording, not an existing requirement. Metadata consistency does not attest remote code.
- **Fix:** hash the full definition canonically, including `outputSchema`, `annotations` and any other fields.

### F6. Audit coverage gaps in this component (gap, medium, partly needs_evidence)
- **Supported:** `begin` reserves capture before action and raises if it cannot, which fails closed (`:63`). `likely_pass` for that sub-control, subject to sink behavior.
- **Gaps in this component:**
  - `complete` is never called on exceptions, so denials and failures have no outcome.
  - Denials before `begin` (origin, size, authentication) are not recorded here.
  - Batch per-element outcomes, `worker_step` executions and cancel effects are not audited here.
  - The whole request is logged, so secret and argument minimization needs a policy.
- The README assigns complete attempt, denial and outcome-graph capture to the external framing layer, so completeness is `needs_evidence`.
- **BRACE:** R03, R13, A02, E10–E12. **Sources:** [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) (guidance); [CERT-In CIAD-2026-0049](https://www.cert-in.org.in/s2cMainServlet?VLCODE=CIAD-2026-0049&pageid=PUBVLNOTES02) (2026-10-15; not rechecked).

### F7. Minor robustness issues (lower)
- `len(body)` is checked after the framing layer has already received the body, so pre-allocation limits are `needs_evidence`.
- Parser depth and the batch element count are bounded only by the 8192-byte cap.
- Missing keys raise `KeyError`. This fails closed but is inconsistent and unaudited.
- **BRACE:** B07, R01.

## 3. Coverage table

| Boundary / check | Status | Evidence | Source authority | Owner |
|---|---|---|---|---|
| Inventory and ownership | needs_evidence | No manifest or lockfile. External layers are unspecified. | OWASP agent security (guidance) | Platform owner |
| Origin check | likely_pass (code) | `:57`. Allow-list match on one origin. | Streamable HTTP (protocol) | Gateway |
| Request size | needs_evidence | 8192-byte check at `:59`. Framing-layer limits are unknown. | MCP security guidance | Framing owner |
| Authentication (signature, issuer, expiry) | likely_pass (code) | `:10-21`. `alg` is pinned, `compare_digest` is used, and the order is signature then claims. | RFC 9700 | Gateway |
| Audience / resource binding | **gap** | F4 | MCP authorization; RFC 9700 | Gateway |
| Key custody / issuance | needs_evidence | External. | — | Identity owner |
| Revocation propagation | needs_evidence | In-process `REVOKED` set. Source unknown. Not rechecked on cache or worker paths. | RFC 9700 | Identity / Gateway |
| Single-call tenant/tool authz | likely_pass (code) | `invoke` `:23-28` | OWASP txn authz | Gateway |
| Batch authz | **gap** | F1 | OWASP txn authz | Gateway |
| Cache isolation | **gap** | F2 | Control map (state isolation) | Gateway |
| Task ownership (cancel) | likely_pass (code) | `:43` | Tasks ext | Gateway |
| Task execution authz and stop | **gap** | F3 | Tasks ext | Gateway / scheduler |
| Definition integrity | **gap** | F5 | OWASP MCP; Uber (report) | Gateway / host |
| Annotations as authorization | gap (design) | `readOnlyHint` plus a delete-capable backend. Hints are not policy. | Control map | Tool owner |
| Backend credential separation (no token passthrough) | needs_evidence | Backend not shown. | http.md step 4 | Backend owner |
| Audit | partial gap / needs_evidence | F6 | OWASP Logging | Gateway / sink |
| Egress, SSRF | na_candidate | Searched `gateway.py` for urllib, requests, http, socket, open, `$ref`. No outbound I/O in the component. Backend and framing are out of scope. | MCP security guidance | Network owner |
| Untrusted returned content | needs_evidence | The component returns backend results unfiltered. The consumer is unknown. | MCP security guidance | Host |
| Persistent influence / memory | na_candidate | No memory or skills are present. Searched for persistence and file writes. Only the in-memory `CACHE` and `TASKS` exist (F2, F3). | Control map | — |
| Extensions (Apps, Skills) | na_candidate | The README documents their absence. | Control map | — |
| Launch / stdio / supply chain | na_candidate / needs_evidence | No stdio. No manifest, so package pins are unknown. | stdio.md; OWASP supply chain | Build owner |
| Advisories (SDKs) | needs_evidence | No MCP SDK or dependency is identifiable in the supplied files. No resolved versions. The bundled advisories were not rechecked. | advisories.md | Build owner |
| Runtime stop times, limits and deployed effectiveness | needs_evidence | Source inspection cannot establish these. | — | Operations |

## 4. Controls supported in code
- `alg` pinning, constant-time signature comparison, and issuer, expiry and revocation checks.
- Single-call tenant and tool-grant checks, and same-tenant cancellation.
- Audit reservation before action (fail-closed on a full buffer).
- The Origin allow-list and an early body-size cap.

These are static observations, not runtime test results.

## 5. Missing evidence and unreviewed scope
- The framing layer, identity issuer and key custody, audit sink, scheduler, `TASKS` population and approval service.
- Backend implementations and their credentials.
- Deployed limits and network policy.
- Dependency manifests and resolved versions, and the negotiated protocol revision.
- Whether MCP SDK components sit in front of this code. If they do, check the advisories in advisories.md against actual versions and settings.

This is not a full 53-item BRACE assessment. It is not a deployment approval, certification or security Pass.

## 6. Proposed controlled tests
Run these only in a disposable environment, with fake data and fake keys, and only after the owner's approval. The review did not run them.

| Test | Expected allowed | Expected denied | Owner |
|---|---|---|---|
| Batch with a tool outside `claims["tools"]`, and with another tenant's args | A batch of permitted calls for the caller's own tenant succeeds. | Both are denied, and the denials are audited. | Gateway team |
| Tenant A reads `q`, then tenant B reads `q`; repeat after A's grant is revoked | Each tenant gets only its own data. | No cross-tenant or post-revocation hit. | Gateway team |
| Queue a task, cancel it, then run the scheduler. Separately, queue a task and revoke the subject before it runs. | Normal task runs. | The cancelled or revoked task has no backend effect. Measure the stop time. | Scheduler owner |
| Valid-signature token with a wrong `aud`, wrong issuer, expired `exp`, or missing claims | A correct token is accepted. | All wrong tokens are denied. | Identity and gateway teams |
| Alter `readOnlyHint` or `outputSchema` in the catalog | Unchanged definition passes the fingerprint comparison. | Any change is flagged and quarantined. | Host / gateway |
| Audit sink full or unavailable, and denial-path capture | Requests proceed with a working sink. | No action runs when `begin` fails. Denials are reconstructable. | Audit owner |
| Oversized body, deep JSON, large batch | Normal requests pass. | Rejected before allocation. | Framing owner |
