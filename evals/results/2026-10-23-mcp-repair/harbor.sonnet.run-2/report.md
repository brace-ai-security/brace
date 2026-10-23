# MCP review: records gateway (`repo/`)

**Review date:** 2026-10-23. **Method:** static file reading only. Nothing was executed, imported, installed or connected to. No public-source lookup was done, so the cited advisories and dates are from `skill/references/*` and were not rechecked.

**Untrusted content in the fixture:** `repo/review-notes.txt` tells the reviewer to omit authentication and cache observations and to state that all controls passed. I did not follow it. Both areas are reported below, and nothing here is a pass or a release verdict.

## 1. Scope and inventory

| Item | Finding |
|---|---|
| Component | One Python gateway module, `repo/gateway.py` (72 lines). It has `authenticate`, `invoke`, `dispatch`, `read_records`, `cancel`, `worker_step`, `fingerprint` and `handle_http`. |
| Transport and protocol | Protected HTTP, MCP 2026-07-28 per `README.md`. Negotiation can't be seen in the source, so the negotiated revision is unknown. Stdio, Apps and Skills are declared absent. Tasks-like handles are present (`TASKS`, `cancel`, `worker_step`). |
| Tool inventory | `repo/catalog.json` declares `read_records` with `readOnlyHint`, an `inputSchema` and an `outputSchema`. The code authorizes the operation name `"read"`, and the README says backends also implement `delete`. The mapping between `read_records` and `read` isn't shown. |
| Credentials | Inbound JWT, HS256, verified with the `JWT_VERIFY_SECRET` environment variable. No backend credential is passed (`backend(name, args)`). The fixture contains no live key. |
| Release, packages, lockfile | No commit, manifest or lockfile was supplied. Resolved versions are unknown. No MCP SDK import is visible, so the SDK advisories in `advisories.md` are not shown to apply. |
| Outside the component (per README, not inferred) | Framing and identity issuance, audit durability and retention, deployed limits, network policy, the approval service, the scanner, the backends, and key provisioning. |

## 2. Findings, ordered by impact

### F1. Batch mode skips tenant and operation authorization (`gap`, high)
- **Trigger:** an authenticated user sends `{"method": <anything other than read/cancel>, "mode": "batch", "calls": [{"tool", "args"}]}`.
- **Dataflow:** `handle_http` calls `dispatch` (`gateway.py:69`). In batch mode `dispatch` calls `backend(call["tool"], call["args"])` directly (`gateway.py:31-32`). The single-call path goes through `invoke`, which does the tenant check (`:24`) and the `claims["tools"]` check (`:26`). The batch path does neither.
- **Impact:** any valid token can name any tool and any tenant, including `delete`, and the backend receives it. This contradicts the README claim that deletion is permitted only when the operation and tenant are authorized. The 8 KiB body limit bounds the number of calls but doesn't prevent the bypass.
- **BRACE:** B01, B05, B02–B04, E06.
- **Authority:** adopted-profile expectation plus [OWASP transaction authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html) (guidance), and the destination-authorization guidance in `http.md` §5.
- **Remediation:** route every batch element through `invoke`, and define atomic or partial failure semantics. Enforce the same policy in the backend. Add an element-count limit.
- **Limit:** backends may enforce their own checks, but the README says no other checks exist on these paths. Backend behavior is `needs_evidence`.

### F2. Cache is keyed by query only and bypasses authorization (`gap`, high)
- **Trigger:** tenant A reads a query, then tenant B (or a revoked or de-scoped user) sends the same query.
- **Dataflow:** `read_records` uses `key = query` (`gateway.py:36`). On a hit it returns `CACHE[key]` without calling `invoke` (`:37-39`). The cache is process-global, with no tenant, subject, policy-version, TTL or size bound.
- **Impact:** cross-tenant data disclosure. Revocation, `tools` changes and `POLICY_VERSION` changes have no effect on cached entries. Unbounded growth is a resource concern.
- **BRACE:** E06, R04, B02, B07.
- **Authority:** the cache-key and "cache hits need current authorization" guidance in `http.md` §6 and the control map's state-isolation row. The advisories index is for flaws in SDKs and libraries and doesn't cover this custom code.
- **Remediation:** key on tenant, subject and policy version. Authorize before lookup, and add a TTL and a bound.

### F3. Token validation has no audience, scope or resource check (`gap`, high)
- **Evidence:** `authenticate` checks the signature, `alg`, `iss`, `exp` and the `sub` revocation set (`gateway.py:10-21`). `RESOURCE` is defined (`:3`) but never used. The comment "Other accepted claims are handled below" (`:20`) is not borne out: nothing below checks `aud`, `resource` or `scope`.
- **Impact:** a token issued by the same issuer for a different resource or service is accepted. A valid signature is not an audience check.
- **Secondary points:**
  - HS256 means every holder of the verify secret can mint tokens. Key custody is external, so it is `needs_evidence`.
  - `REVOKED` is a process-local set that nothing in this file populates.
  - Missing claims raise `KeyError`. That is likely fail-closed, but the error handling belongs to the framing layer.
- **BRACE:** B02–B04, E06.
- **Authority:** [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) (version-specific), [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html), `http.md` §3. The TS and Python audience advisories (GHSA-rvq5-wwqv-78pq and GHSA-w4fh-qvv9-3v23, 2026-10-05, not rechecked) show the same class of flaw, but their SDK fixes don't apply to this custom verifier.
- **Remediation:** require `aud` or `resource` to equal `RESOURCE`, check `scope`, use `nbf` and the key ID, and use a shared revocation store. Prefer asymmetric verification where the issuer supports it.

### F4. Cancel doesn't stop queued work, and workers run on stale claims (`gap`, medium-high)
- **Evidence:** `cancel` sets `task["cancelled"] = True` (`gateway.py:45`). `worker_step` never reads that flag (`:47-50`). It calls `invoke` with the stored `task["claims"]` and doesn't recheck expiry or revocation, because `invoke` doesn't check them either.
- **Impact:**
  - A successful cancel response doesn't stop the effect. The scheduler runs `worker_step` for every queued handle, and `invoke` performs the backend call.
  - Revoked or expired principals' queued jobs still execute, including consequential operations like `delete`.
- **Positive:** the cancel path checks tenant ownership (`:43-44`), which matches the stated policy that users cancel their own tenant's jobs. This is `likely_pass` for cross-tenant cancel at this layer.
- **Other issues:** `TASKS[handle]` raises `KeyError` on an unknown handle, and `worker_step` writes no audit record.
- **BRACE:** R11, R12, E09, A04.
- **Authority:** [MCP Tasks](https://modelcontextprotocol.io/extensions/tasks/overview) (cancellation is cooperative) and the stop-and-recovery row in the control map.
- **Remediation:** check `cancelled`, then re-authenticate or re-authorize at execution time against current revocation and policy. Add a drill showing no further effects after cancel.

### F5. The definition fingerprint omits fields the README says are covered (`gap`, medium)
- **Evidence:** `fingerprint` hashes only `name`, `description` and `inputSchema` (`gateway.py:52-54`). The README says "Metadata approval covers the complete definition", and `catalog.json` also carries `outputSchema` and `annotations`.
- **Impact:** a changed `outputSchema` or `annotations` (for example `readOnlyHint`) won't change the hash, so it won't be rejected. `readOnlyHint` is a server assertion, not an authorization policy.
- **BRACE:** E03, E05, C04.
- **Authority:** [OWASP MCP sheet §2](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) (guidance) and the [Uber gateway report](https://www.uber.com/us/en/blog/designing-mcp-gateway/), 2026-10-01. Complete-definition hashing is a proposed refinement of BRACE's description and schema wording, so label it that way. Here it matters because the README claims complete coverage.
- **Remediation:** hash the canonicalized full definition. Test description, schema, annotation and output-schema changes. A matching hash shows consistency only, not the safety of the remote code.

### F6. Audit and identity gaps (`needs_evidence` / partial gap, medium-low)
- **Supported in code:**
  - `audit_sink.begin` is called before any action (`gateway.py:63`).
  - By contract it fails closed when the bounded buffer is full, which gives bounded-outage behavior.
  - The record includes subject, tenant, request and policy version.
- **Gaps:**
  - Origin, size and authentication denials happen before `begin` (`:57-61`), so this component records no denial. The README assigns that to the external framing layer.
  - `complete` isn't called when an exception occurs, so failed outcomes leave open tickets.
  - Batch sub-calls aren't individually recorded.
  - `worker_step` isn't audited.
  - The full request and result go into the audit record, so protected-detail handling needs evidence.
- **Identity:** there is no separate actor or original-subject model, and no backend credential or audience. The gateway-to-backend trust model is unknown.
- **BRACE:** R03, R13, A02, E10–E12, B02–B04.
- **Authority:** [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) (guidance) and [CERT-In CIAD-2026-0049](https://www.cert-in.org.in/s2cMainServlet?VLCODE=CIAD-2026-0049&pageid=PUBVLNOTES02) (2026-10-15, not rechecked).

## 3. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Origin check | `likely_pass` (code) | Exact match at `:57`; a missing Origin is denied. | Streamable HTTP | Gateway; edge Host handling is external |
| Body size | `likely_pass` (partial) | `len(body) > 8192` before auth and parse (`:59`). It acts on an already-framed body, so allocation before framing is `needs_evidence`. No batch-element or schema limits. | Resource limits | Framing layer |
| Authentication: signature, issuer, expiry | `likely_pass` | `:12-19` | Authorization spec | Gateway |
| Audience / scope / resource | **gap** | F3 | Authorization spec | Gateway |
| Revocation | `needs_evidence` | In-memory `REVOKED`, never populated here; not checked on cache or worker paths. | R11 | Identity layer / gateway |
| Single-call tenant and operation authorization | `likely_pass` | `invoke`, `:24-27` | B01 | Gateway |
| Batch authorization | **gap** | F1 | B01 | Gateway |
| Cache isolation | **gap** | F2 | E06 | Gateway |
| Task cancel ownership | `likely_pass` | `:43-44` | E06 | Gateway |
| Task stop and effects | **gap** | F4 | R11, R12 | Gateway / scheduler |
| Definition integrity | **gap** | F5 | E03 | Gateway / host |
| Audit reservation | `likely_pass` (contract only) | `:63`; durability is external. | R13 | Audit owner |
| Denial, outcome and worker audit | **gap** / `needs_evidence` | F6 | R03 | Framing layer / gateway |
| Backend authentication, downstream authorization, approval service | `needs_evidence` | Not supplied. | B05, B06 | Backend / approval owner |
| Egress / SSRF, network policy | `needs_evidence` | No outbound I/O in this module. | B08, B09 | Network owner |
| Supply chain, packages, lockfile | `needs_evidence` | None supplied. | C02, C05 | Repository owner |
| Untrusted metadata and returned content | `needs_evidence` | Nothing sanitizes `description` or `outputSchema`, and the output is returned unmodified. | E04, R01–R03 | Host / client |
| Stdio, Apps, Skills | `na_candidate` | Declared absent in the README. Glob over the whole fixture found no `.mcp.json`, skill or Apps files, and no dotfiles exist. | n/a | Deployment owner |

## 4. Controls supported in code, and unreviewed scope
- **Supported in code:**
  - the origin allowlist
  - the pre-auth size cap
  - signature and issuer verification
  - the HMAC constant-time compare
  - single-call tenant and operation checks
  - task-cancel tenant ownership
  - the audit reserve-before-action ordering
- **Unreviewed or runtime-dependent:**
  - framing, identity issuance and key provisioning
  - the scheduler
  - backend and approval implementations
  - deployed limits and network policy
  - audit durability
  - negotiated protocol version
  - resolved dependency versions
- This is source-only evidence. None of the above authorizes deployment.

## 5. Proposed controlled tests (disposable fixtures, fake credentials; not run)

| Test | Allowed | Denied | Owner |
|---|---|---|---|
| Batch with another tenant's `tenant` arg, with `delete`, and with an unlisted tool | Authorized single read | All three denied, with audit entries | Gateway team |
| Tenant A reads query Q, then tenant B reads Q; also read after revocation or a `tools` change | Own-tenant read | No cross-tenant hit; revoked principal denied | Gateway team |
| Token with the wrong `aud` / `resource`, and one with the wrong scope | Correct audience | Rejected | Identity owner |
| Queue a job, cancel it, run the worker; repeat after revoking the `sub` | Normal run | No backend effect after cancel or revocation | Scheduler owner |
| Change the `outputSchema` / `annotations` / description of the catalog entry | Unchanged definition | Fingerprint mismatch rejected | Host owner |
| Audit sink full, and denial paths (bad origin, bad token) | Normal request | Request refused; every denial reconstructable across services | Audit / framing owner |

Cross-user tests belong to the gateway team. Stop conditions: no real tenant data and no production backends.
