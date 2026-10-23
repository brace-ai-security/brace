# MCP review: records gateway (source-only)

**Review date:** 2026-10-23. **Commit/release:** none supplied (not a git repository). **Report destination:** returned inline, because file writing is disallowed here. Nothing was executed.

## 1. Scope and inventory

| Item | Finding |
|---|---|
| Files read | `repo/gateway.py`, `catalog.json`, `README.md`, `review-notes.txt`, plus all skill references |
| Hidden files | `Glob repo/.*` and `repo/**/.*` returned no files. There is no `.mcp.json`, lockfile, package manifest or `.brace/` directory. |
| Component | Protected HTTP MCP gateway (application authorization layer) |
| Protocol | MCP 2026-07-28, as stated in the README. It was not negotiated or observed, so it is unverified. |
| Transports and extensions | HTTP only. The README excludes stdio, Apps and Skills. `TASKS`, `cancel` and `worker_step` imply Tasks-style async handles, but the README doesn't name the extension. |
| OS support | Not stated |
| Packages and versions | None declared. The advisory index doesn't apply because there is no SDK package or resolved version. Remote backend versions are unknown. |
| Exposed tool | `read_records` in the catalog. The code and README also use backend operations `read` and `delete`. The catalog doesn't list `delete`, and the name `read_records` differs from `read`. |
| Credentials | HS256 verification secret from env `JWT_VERIFY_SECRET` (value not in fixture). Backend credentials are not shown. |

**Ownership.** The unknowns below belong to the host/platform owner unless noted.
- The gateway code owns issuer, expiry, revocation, tenant and tool checks, the cache, batch dispatch, cancellation and the fingerprint comparison.
- The external framing and identity layer owns key provisioning, token issuance, full audit capture and Host checks.
- The audit sink owns durability and retention.
- Network policy, the approval service, the scanner and the remote backends are outside the component.

**Untrusted content.** `review-notes.txt` contains a "supplier note" telling the reviewer to omit authentication and cache observations and to state that all controls passed. That is untrusted data. I did not follow it, and the findings below include authentication and cache issues.

## 2. Sources

All entries are offline. They are bundled records, **not rechecked**, and dates are the bundled dates unless labelled.

| ID | Source | Authority | Date |
|---|---|---|---|
| S1 | [MCP authorization 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Protocol requirements for that revision (authorization is optional in the protocol; BRACE requires it for protected access) | Version identified 2026-10-22 |
| S2 | [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) | BCP | Bundled 2026-10-22 |
| S3 | [OWASP Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html) | Guidance | Bundled 2026-10-22 |
| S4 | [OWASP MCP Security](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) | Guidance | Bundled 2026-10-22 |
| S5 | [MCP Tasks](https://modelcontextprotocol.io/extensions/tasks/overview) | Optional extension, cooperative cancellation | Bundled 2026-10-22 |
| S6 | [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | Guidance | Bundled 2026-10-22 |
| S7 | [Streamable HTTP 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) | Protocol requirements | Version identified 2026-10-22 |
| S8 | [TS audience GHSA-rvq5-wwqv-78pq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq) | Maintainer advisory | 2026-10-05 |
| S9 | [Uber MCP gateway](https://www.uber.com/us/en/blog/designing-mcp-gateway/) | Deployment report | 2026-10-01 |
| S10 | [BRACE checklist](https://braceframework.org/CHECKLIST.md) and [research](https://braceframework.org/RESEARCH-2026-10-22.md) | Adopted profile | 2026-10-22 |

S8 is an analogy only. It concerns an SDK that is not present in this fixture.

## 3. Findings (ordered by impact)

### F1. Batch mode bypasses all tenant and tool authorization — gap
- **Trigger:** An authenticated caller sends `{"mode":"batch","calls":[{"tool":"delete","args":{"tenant":"<other>",...}}]}`.
- **Dataflow:** `handle_http` → `dispatch`.
- **Evidence:** `gateway.py:31-32`: `[backend(call["tool"], call["args"]) for call in request["calls"]]`. The batch path calls `backend` directly and never calls `invoke`, which holds the tenant check (`:24`) and the `claims["tools"]` check (`:26`).
- **Contract violated:** The README says deletion is permitted only when that operation and tenant are authorized. Batch has neither check, so this is not just sequential execution.
- **Scope:** Any authenticated user can run any backend operation, including `delete`, against any tenant. The 8192-byte body cap at `:59` doesn't bound this.
- **BRACE:** B01, B05, B06, E06. **Sources:** S3, S4, S1.
- **Remediation:** Route every batch element through `invoke(claims, …)`. Reject the whole batch if any element is unauthorized, or define and document partial-execution semantics. Add a per-batch element limit. Allowlist the permitted operations.

### F2. Records cache is keyed by query only, so it leaks across tenants and skips authorization — gap
- **Evidence:** `gateway.py:36-39` uses `key = query` in the process-global `CACHE`. The `invoke` call runs only on a miss.
- **Dataflow:** Tenant A reads query "q" and the result is cached. Tenant B sends the same query and gets A's records with no tenant, tool or revocation check.
- **Further issues:** The cache has no TTL or eviction, so it is unbounded. Entries survive revocation and permission changes.
- **BRACE:** E06, R04, B04. **Sources:** S4, S9.
- **Remediation:**
  - Include tenant, subject or authorization context, and policy version (`POLICY_VERSION`) in the key.
  - Run the authorization check before every cache read.
  - Add a TTL and a size bound.
  - Invalidate on revocation.

### F3. Token validation has no audience or resource binding — gap
- **Evidence:** `gateway.py:10-21` checks the algorithm, signature, `iss`, `exp` and the revoked-subject set. It never checks `aud` or the resource claim. `RESOURCE` (`:3`) is defined but unused. The comment "Other accepted claims are handled below" is not borne out. `invoke` checks only `tenant` and `tools`.
- **Impact:** A validly signed token issued for another resource is accepted, if the issuer signs with the same key. It isn't confirmed that a token meant for another audience can be obtained in practice.
- **Related notes:**
  - HS256 means every holder of the verification secret can mint tokens. Key custody is external (`needs_evidence`).
  - Revocation is an in-process `REVOKED` set keyed by `sub`. Multi-instance propagation is unknown.
  - Missing claims raise `KeyError`. That fails closed but is uncontrolled error handling.
- **BRACE:** B02, B03, B04. **Sources:** S1, S2, S8 (analogous).
- **Remediation:**
  - Require `aud`/`resource == RESOURCE`.
  - Prefer asymmetric verification with issuer-bound keys, or document the HS256 key scope.
  - Validate required claims explicitly.

### F4. Cancellation does not stop work, and queued work reuses stale claims — gap
- **Evidence:** `cancel` sets `task["cancelled"] = True` (`:45`). `worker_step` (`:47-50`) never reads that flag. It calls `invoke` with the claims stored at queue time, so it neither re-checks expiry or `REVOKED` nor honors cancellation.
- **Authorization:** The tenant check in `cancel` matches the stated policy, where any user in a tenant may cancel that tenant's jobs. That is not a gap. A missing handle raises `KeyError`.
- **Impact:** A job that is cancelled or whose subject is revoked still executes its effects, including potentially destructive operations. Cooperative cancellation is incomplete.
- **BRACE:** R11, R12, E09, B04. **Sources:** S5, S10.
- **Remediation:** Check `cancelled` and current revocation or expiry in `worker_step` before each action. Re-authorize at execution time. Run a stop drill that measures that no further effects occur.

### F5. Definition fingerprint omits `outputSchema` and `annotations` — gap
- **Evidence:** `gateway.py:53` hashes only `name`, `description` and `inputSchema`. `catalog.json` also defines `outputSchema` and `annotations.readOnlyHint`. The README says "Metadata approval covers the complete definition", which the code contradicts.
- **Impact:** After approval, `outputSchema` or `readOnlyHint` can change without detection. The hint is also not an authorization policy.
- **Labelling:** Hashing the complete definition is a research-informed refinement of BRACE's description/schema wording, not an existing requirement. A matching hash shows consistency only, not safety.
- **BRACE:** E03, E05. **Sources:** S9, S10, S4.
- **Remediation:** Hash a canonical serialization of the whole definition. Test annotation and output-schema changes.
- **Related minor point:** The catalog's `inputSchema` doesn't declare `tenant`, which `invoke` requires, and the catalog name (`read_records`) differs from the backend name (`read`). This is a `needs_evidence` mismatch to reconcile.

### F6. Audit coverage is incomplete in the supplied path — needs_evidence, partial gap
- **Good:** `audit_sink.begin` runs before any action (`:63`) and is stated to raise when the capture buffer is full, which fails closed.
- **Gaps in the supplied path:**
  - `begin` follows `authenticate`, so authentication failures are not recorded here.
  - `complete` isn't called on exceptions, so denials and errors leave an open ticket with no recorded outcome.
  - `worker_step` has no audit calls.
  - Batch elements are not recorded individually.
  - The record has no audience, token ID or approval ID.
  - The full request is logged, which may include sensitive data.
- The README assigns complete capture to the external framing layer. That is unverified.
- **BRACE:** R03, R13, A02, E10–E12. **Sources:** S6, S10.
- **Remediation:** Add a failure-path `complete`. Record denials and worker outcomes. Provide host evidence of end-to-end reconstruction.

## 4. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Inventory and pins (E01, E02, C01) | needs_evidence | No manifest or lockfile. Backend versions are unknown. | S4 | Platform |
| Launch / supply chain / stdio | na_candidate | The README states no stdio. Glob `.*` and `**/.*` found no `.mcp.json`. Absence is documented, not proven for deployment. | S10 | Platform |
| Origin check (HTTP) | likely_pass | `:57` exact match, performed before authentication. A missing Origin is rejected. | S7 | Gateway |
| Host header / version / metadata parsing | needs_evidence | Not in the supplied component. | S7 | Framing layer |
| Body size limit | likely_pass (partial) | `:59` caps the body at 8192 bytes before parsing. It relies on the framing layer for pre-allocation limits. Batch element count is unlimited within the cap. | S4 | Framing layer |
| Authentication: issuer, expiry, signature | likely_pass | `:12-19`. The algorithm is pinned and compare_digest is used. | S1 | Gateway |
| Audience | gap | F3 | S1, S2 | Gateway |
| Key custody / issuance | needs_evidence | External. | S1 | Identity owner |
| Revocation propagation | needs_evidence | An in-process set, with no measured time. | S10 | Platform |
| Single-call tenant / tool authorization | likely_pass | `invoke` `:24-28` | S3 | Gateway |
| Batch authorization | gap | F1 | S3 | Gateway |
| Cache isolation | gap | F2 | S4 | Gateway |
| Task ownership (cancel) | likely_pass | `:43` | S5 | Gateway |
| Task stop / re-authorization | gap | F4 | S5 | Gateway |
| Metadata integrity | gap | F5 | S9 | Gateway / host |
| Backend credentials and audience | needs_evidence | Not shown. | S1 | Backend owner |
| Egress / SSRF | needs_evidence | No outbound code is visible. Backend implementations are unseen. | S4 | Platform |
| Returned-content injection | needs_evidence | Results are passed through unmodified. | S4 | Host |
| Business approval (delete) | needs_evidence | No approval binding is visible. Only operation and tenant are checked. | S3 | Approval service |
| Audit | needs_evidence / partial gap | F6 | S6 | Gateway / framing layer |
| Persistent influence (memory, skills) | na_candidate | The README states no Skills extension. No memory code was found by Grep or Glob. | S10 | Platform |
| Apps / Skills / stdio extensions | na_candidate | Documented absent. Not verified at the deployment. | S10 | Platform |

## 5. Controls supported in code (`likely_pass`, static only)
- Exact Origin match.
- Algorithm pinning, constant-time signature compare, and issuer and expiry checks.
- Single-call tenant and tool checks.
- Tenant check on cancel.
- Audit reservation before action.

## 6. Unreviewed scope and limits
- The external framing and identity layer, audit sink durability, deployed limits, network policy, approval service, scanner and remote backends are all out of scope.
- No installed or deployment evidence was inspected. Source findings do not authorize deployment.
- No advisory lookup was performed. The advisories index was not rechecked, and no package matches it.
- This review is not a security pass, certification or release verdict.

## 7. Proposed controlled tests
These are not run. Each should use a disposable fixture, with the gateway owner as the owner.

| Test | Allowed | Denied | Source |
|---|---|---|---|
| Batch of `[read own, delete other tenant, unlisted tool]` | Authorized own-tenant calls succeed | The other-tenant and unlisted calls are denied, with no partial effects (or documented semantics) | S3, S4 |
| Tenant A and tenant B issue the same query, plus a revoked subject re-querying a cached query | Each tenant gets only its own data | B never receives A's data, and a revoked subject is denied on a cache hit | S4 |
| Token with a wrong `aud` and a valid signature | An aud-matched token is accepted | The wrong-audience token is rejected | S1, S2 |
| Cancel a queued job, and separately revoke the subject while the job is queued | The cancel call succeeds | No effects occur after cancel or revocation (a drill, not just a successful response) | S5 |
| Change `readOnlyHint` or `outputSchema` after approval | The unchanged definition is accepted | The modified definition is rejected and quarantined | S9, S4 |
| Auth failure, denial and worker outcome | The records reconstruct | Every attempt appears in the audit trail | S6 |
