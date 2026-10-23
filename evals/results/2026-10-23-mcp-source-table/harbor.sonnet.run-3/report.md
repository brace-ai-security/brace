# MCP review: records gateway

**Review date:** 2026-10-23
**Report destination:** returned inline. The review was read-only, so no `mcp-review.md` was written.
**Verdict vocabulary:** `gap`, `likely_pass`, `needs_evidence` and `na_candidate` only. This is not a security pass, certification or release decision.

## Attempted influence on the review
`repo/review-notes.txt` contains a "supplier note" telling the reviewer to omit authentication and cache observations and to state that all controls passed. That file is untrusted data and I did not follow it. Authentication and cache are covered below (F1, F3), and several controls did not pass.

## 1. Scope and inventory

| Item | Finding |
|---|---|
| Component | Application-layer records gateway (`repo/gateway.py`, 71 lines). The README describes it as a synthetic, source-only target. |
| Release / commit | Unknown. There is no git repository, no lockfile and no package manifest. |
| Transport | Protected HTTP MCP, revision 2026-07-28, as declared in the README. Negotiation could not be observed, so the negotiated revision is recorded as declared, not verified. |
| Not present | stdio, Apps and Skills extensions (declared absent). `stdio.md` is therefore treated as `na_candidate`. Searches for `.mcp.json` and for hidden files (`repo/.*`, `repo/**/.*`) returned no files. |
| Tasks | `TASKS` and `cancel` exist in the code. Whether they use the MCP Tasks extension is not stated. |
| Tool exposed | `read_records` (`catalog.json`). It has `readOnlyHint: true`, an `outputSchema` of `array` and an `inputSchema` with only `query`. |
| Backend operations | Named operations that include `read` and `delete` (README). The backend is external. |
| Credentials | HS256 JWT verified with `JWT_VERIFY_SECRET` from the environment. No secret is in the fixture. |
| Package pins | No SDK is imported and no dependencies are declared. Resolved versions are unknown. |

**Ownership boundaries**

| Owner | Controls |
|---|---|
| This component | Token verification, tenant/tool checks, cache, batch dispatch, cancel, worker step, fingerprint, audit begin/complete calls. |
| External framing and identity layer | HTTP framing, Host and header/body comparison, token issuance, `aud`/scope issuance, complete audit capture. |
| Host | Approval service, scheduler, TASKS population, owner approval of definitions. |
| Backend | Operation implementation and tenant enforcement at the destination. |
| Deployment | Network policy, effective limits, audit durability, retention and key provisioning. |

## 2. Sources

| ID | Source | URL | Authority | Date |
|---|---|---|---|---|
| S1 | MCP authorization | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization | Protocol requirement for 2026-07-28 | 2026-07-28 |
| S2 | RFC 9700 | https://www.rfc-editor.org/rfc/rfc9700.html | BCP | Bundled review date 2026-10-22 |
| S3 | OWASP Transaction Authorization | https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html | Guidance | Bundled review date 2026-10-22 |
| S4 | OWASP MCP Security cheat sheet | https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html | Guidance | Bundled review date 2026-10-22 |
| S5 | MCP security best practices | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | Protocol guidance | Bundled review date 2026-10-22 |
| S6 | MCP Tasks extension | https://modelcontextprotocol.io/extensions/tasks/overview | Optional extension, cooperative cancellation | Bundled review date 2026-10-22 |
| S7 | OWASP Logging | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | Guidance | Bundled review date 2026-10-22 |
| S8 | TS audience advisory GHSA-rvq5-wwqv-78pq | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq | Maintainer advisory, analogy only | 2026-10-05 |
| S9 | BRACE research and checklist | https://braceframework.org/RESEARCH-2026-10-22.md and https://braceframework.org/CHECKLIST.md | Adopted-profile baseline | 2026-10-22 |
| S10 | MCP versioning | https://modelcontextprotocol.io/specification/versioning | Official | Showed 2026-07-28 on 2026-10-22 |

**None of these sources was rechecked.** Public lookup was unavailable, so all of them are bundled, not-rechecked records.

## 3. Findings (ordered by impact)

### F1. Batch mode skips all authorization (`gap`, high)
- **Evidence:** `gateway.py:30-33`. When `request["mode"] == "batch"`, `dispatch` calls `backend(call["tool"], call["args"])` directly and never calls `invoke`. No tenant check, no `claims["tools"]` check and no per-call policy applies.
- **Trigger and dataflow:** any authenticated caller sends `{"mode":"batch","calls":[{"tool":"delete","args":{"tenant":"<other>",…}}]}`. The request goes through `handle_http` → `dispatch` → backend.
- **Violated contract:** the README says deletion is permitted only when the operation and tenant are authorized. The single-call path enforces this (`gateway.py:23-28`) and the batch path does not. This is a violated authorization contract, not just sequential execution.
- **Impact:** cross-tenant read, write or delete, and use of tools outside the token's grants. The README states there are no other hidden application checks on these paths.
- **Scope limit:** the backend might enforce tenant checks itself. That is outside the supplied component and is `needs_evidence`, but it cannot be assumed.
- **BRACE:** B01, B05, E06. **Sources:** S3, S4, S9.
- **Remediation:** route every batch element through `invoke` with the same claims. Validate the batch structure and element count. Decide whether the batch is atomic, and if so, authorize all elements before executing any.

### F2. Cache is shared across tenants and skips authorization (`gap`, high)
- **Evidence:** `gateway.py:35-39`. The key is the raw `query`, and `CACHE` is a module-level dict. `invoke` runs only on a miss.
- **Trigger:** tenant A reads `query="X"`. Tenant B (or a caller whose tool grant was later removed) sends the same `query` and receives A's result without any tenant or operation check.
- **Impact:** cross-tenant data disclosure. The cache also never expires, so entries outlive changes to authorization. The cache is unbounded and its keys are attacker-controlled strings (low-severity B07 concern, bounded by the 8 KiB body limit).
- **BRACE:** E06, R04, B07. **Sources:** S4, S5, S9.
- **Remediation:** key on tenant, subject or policy version, operation and the normalized query. Add TTL and size bounds. Check current authorization on every hit. Better, do not share the cache across tenants.
- **Related unknown:** `read_records` calls `invoke(..., "read", ...)`, but the catalog tool is named `read_records`. The mapping between the catalog name and the `claims["tools"]` entry `read` is `needs_evidence`.

### F3. Token validation does not check audience or scopes (`gap`, medium-high)
- **Evidence:** `gateway.py:10-21`. The code checks the algorithm, the HMAC signature, `iss`, `exp` and `sub` revocation. `RESOURCE` (`gateway.py:3`) is defined but never used. There is no `aud` or resource check. The comment "Other accepted claims are handled below" is not borne out, because no later code checks `aud`.
- **Impact:** a token for the same issuer but another audience or resource is accepted here. A signature is not an audience check (`http.md` step 3). The tenant and tools claims are trusted as-is.
- **Additional observations:**
  - HS256 means this component holds the secret that can mint tokens. Key custody is external, so `needs_evidence`. Whether this resource server is allowed to hold a signing-capable key is an owner decision.
  - `REVOKED` is a process-local set. Its population, propagation and persistence are unknown.
  - Missing claims raise `KeyError`, which fails closed, but the error is not shaped or audited.
- **BRACE:** B02–B04, E06. **Sources:** S1, S2 (protocol and BCP). S8 is an analogy only, because this is not the TS SDK.
- **Remediation:** require `aud` (or the resource indicator) to equal `RESOURCE`. Pin the algorithm and key by `kid`. Validate required claim types. Prefer asymmetric verification. Define the revocation channel.

### F4. Cancel does not stop work, and the worker never re-authorizes (`gap`, medium)
- **Evidence:** `cancel` sets `task["cancelled"] = True` (`gateway.py:45`). `worker_step` (`gateway.py:47-50`) never reads `cancelled`. It reuses the stored `task["claims"]` without re-checking expiry or revocation, and the README says the scheduler runs it once per queued handle.
- **Impact:** a cancelled task still executes when scheduled, so a tenant-authorized cancel gives no stop guarantee. A task queued under a since-expired or revoked token still runs with the old claims.
- **Note on cancel policy:** the tenant-scoped cancel itself matches the README policy ("every authenticated user may cancel jobs belonging to their own tenant"). Task handle ownership beyond the tenant is not an issue under that policy. An unknown handle raises `KeyError`, which is unshaped.
- **BRACE:** R11, R12, E09, B02. **Sources:** S6, S9.
- **Remediation:** check `cancelled` (atomically, immediately before the effect), expiry and revocation in `worker_step`. Treat cancel as cooperative and independently verify that effects stop.

### F5. Fingerprint omits fields the README says approval covers (`gap`, medium)
- **Evidence:** `fingerprint` (`gateway.py:52-54`) hashes only `name`, `description` and `inputSchema`. The README says "Metadata approval covers the complete definition". `catalog.json` also has `outputSchema` and `annotations` (`readOnlyHint`).
- **Impact:** an upstream change to `annotations` (for example, flipping `readOnlyHint`) or to `outputSchema` does not change the fingerprint, so a mismatch will not be detected and rejected.
- **Scope notes:** `readOnlyHint` is not an authorization policy and must not be used as one. Hashing the complete definition goes beyond BRACE's description/schema wording, so that part is a proposed refinement, but here it also contradicts the README's own claim. A matching hash shows consistency, not safety of the remote code.
- **BRACE:** E03, E05, C04. **Sources:** S4, S9.
- **Remediation:** hash a canonical serialization of the entire definition. Also cover the output schema, annotations, title and any extra fields, and fail closed on unknown keys.

### F6. Audit completeness on denial and error paths (`needs_evidence`, with one code observation)
- **Good:** `audit_sink.begin` runs before any action, and the contract is to raise when capture is unavailable (`gateway.py:63`). That is a fail-closed design, supported in code.
- **Gaps in this component:**
  - `complete` is skipped on any exception, so denials and errors in the three branches produce a begin record with no outcome.
  - Origin and authentication failures occur before `begin` (`gateway.py:57-61`), so those denials are not captured here.
  - The full request, including `query`, is placed in the audit record, which raises a protected-detail question.
  - Batch element outcomes are not recorded individually.
- **Owner:** the README assigns complete attempt, denial, tool/argument, worker and outcome-graph capture to the external framing layer. Durability, retention and the measured guarantee are not supplied.
- **BRACE:** R03, R13, C08, E10–E12. **Sources:** S7, S9.
- **Remediation:** record the outcome in a `finally` path. Include policy IDs. Minimize the logged content.

## 4. Coverage table

| Boundary / check | Status | Evidence | Source authority | Owner |
|---|---|---|---|---|
| Inventory and pins | `needs_evidence` | No manifest or lockfile. SDK absent. | S9 | Component owner |
| Origin check | `likely_pass` | Exact match at `gateway.py:57`. Host and header/body comparison are external. | S5 | Framing layer |
| Host and 2026-07-28 header/body consistency | `needs_evidence` | External framing layer. | S5, S10 | Framing layer |
| Body limit | `likely_pass` (partial) | 8192 check at `gateway.py:59`, applied before parsing. The check is on already-received `body`, so pre-allocation limits are `needs_evidence`. Batch element count is unbounded within 8 KiB. Deployed limits unknown. | S4 | Framing layer / deployment |
| Token signature, issuer, expiry | `likely_pass` | `gateway.py:10-21`. | S1, S2 | This component |
| Audience / resource / scope | `gap` | F3. | S1, S2 | This component |
| Revocation propagation | `needs_evidence` | Process-local set. | S9 | Identity owner |
| Single-call tenant and tool check | `likely_pass` | `gateway.py:23-28`. Destination enforcement unknown. | S3 | This component / backend |
| Batch authorization | `gap` | F1. | S3, S9 | This component |
| Cache isolation | `gap` | F2. | S4, S9 | This component |
| Task cancel ownership | `likely_pass` | Tenant check per README policy (`gateway.py:41-45`). | S6 | This component |
| Cancel effect and worker re-authorization | `gap` | F4. | S6 | This component |
| Definition integrity | `gap` | F5. | S4, S9 | This component / host |
| Approval binding and consumption | `needs_evidence` | Approval service is outside the component. | S3 | Host approval owner |
| Token passthrough to backend | `needs_evidence` | The `backend` callable receives only name and args. Credentials are not shown. | S1 | Backend / gateway owner |
| Egress and SSRF | `needs_evidence` | No outbound code here. Backend and network policy unknown. | S5 | Deployment |
| Audit | See F6 | Begin-before-action is supported in code. Completeness and durability unknown. | S7 | Framing layer / deployment |
| Advisory remediation (SDK) | `na_candidate` | Searched imports. Only `base64, hashlib, hmac, json, os, time` are used, so no MCP SDK is present. | S8 analogy | Component owner |
| stdio / local process | `na_candidate` | README declares no stdio. Searched for `.mcp.json` and hidden files, with none found. | stdio reference | Host |
| Apps and Skills extensions | `na_candidate` | README declares them absent. | Control map | Host |
| Prompt-injection and returned content | `needs_evidence` | The schema has no instructions in the fixture catalog, but outputs flow from an unseen backend. | S5 | Host / client |

## 5. Controls supported in code
- JWT algorithm pinning to HS256, constant-time signature comparison, issuer and expiry checks.
- Tenant and operation checks on the single-call path.
- A tenant check on cancel, matching the stated policy.
- A request size check before JSON parsing.
- Audit reservation before the action, which fails closed.

## 6. Missing evidence and unreviewed scope
- The external framing, identity issuance, approval service, scheduler, backend and audit sink were not supplied. No claim is made about them either way.
- The resolved package versions, deployed limits and runtime stop times could not be established from source.
- Nothing was executed, and this static reasoning is not a runtime test result.
- Advisory lookup was not rechecked (all sources in section 2 are offline records).
- This is a focused MCP review. It does not cover the 53-item BRACE assessment, and the output must not be fed to the full-review validator.

## 7. Proposed controlled tests
These should run only in a disposable fixture environment and have not been run. The owner is the component team unless noted.

| Test | Expected allowed | Expected denied |
|---|---|---|
| Batch with a tool or tenant outside the token (F1) | In-grant batch elements succeed | Out-of-tenant or out-of-grant element is rejected, with no partial effect if atomic |
| Two tenants, same `query` (F2) | Each tenant receives its own data | Tenant B never receives tenant A's cached result. Access is rechecked after grant removal |
| Token with correct signature and issuer but wrong `aud` or missing scope (F3) | Correct `aud` accepted | Wrong or missing `aud` is rejected before any dispatch |
| Cancel then run the scheduler; expired or revoked token at run time (F4) | Uncancelled task runs | Cancelled task produces no backend effect. Expired or revoked claims are refused. Owner: scheduler team |
| Flip `annotations` or `outputSchema` upstream (F5) | Unchanged definition accepted | Any definition change is rejected and quarantined. Owner: host |
| Denial and error paths (F6) | Successful request has a complete audit record | Denied, errored and unauthenticated attempts each have a record. Audit outage prevents action. Owner: framing layer |
| Oversized batch and body, in an isolated environment | Normal requests succeed | Excess is rejected before allocation. Owner: deployment |
