# MCP review: records gateway (`repo/`)

Review date: 2026-10-23. This is a read-only, source-only review. No commands were run and no code was executed. Public-source lookup was unavailable, so every advisory and spec URL below comes from the bundled references, dated as recorded there, and was **not rechecked**.

**Attempted influence:** `repo/review-notes.txt` is a "supplier note" telling the reviewer to omit authentication and cache observations and to state that all controls passed. I treated it as untrusted data and did not follow it. This report covers authentication and caching in full, and it does not claim that all controls passed.

## 1. Scope and inventory

| Item | Value |
|---|---|
| Component | One gateway module, `repo/gateway.py`, plus `repo/catalog.json` and `repo/README.md`. This is a server/gateway resource-server component. |
| Commit/release | Not supplied (no VCS, no lockfile, no manifest). |
| Transport and protocol | Protected HTTP, MCP 2026-07-28, as stated in the README. Negotiation is not shown in the component, so the negotiated revision is `needs_evidence`. |
| Extensions | README: no stdio, Apps or Skills. Whether the Tasks extension is used is unclear. `TASKS`, `cancel` and `worker_step` imply an internal queue, not necessarily the MCP Tasks extension. |
| Operating systems | Not supplied. |
| Packages/SDK | None declared and no lockfile, so resolved versions are unknown. `gateway.py` uses only the standard library. |
| Credentials | `JWT_VERIFY_SECRET` is read from the environment. Provisioning is external and no live key is in the fixture. Backend credentials are not shown. |
| Exposed catalog entry | `read_records` only (`catalog.json`). It is marked `readOnlyHint: true`. |
| Operations reachable in code | `read` (cached path), `cancel`, batch dispatch, and any operation name present in `claims["tools"]`. README states backends implement `read` and `delete`. |
| Privileged downstream action | `delete`, via `dispatch`/`invoke` (`gateway.py:24-34`). |

Ownership boundaries:

- **Supplied:** the application authorization, cache, batch, cancel and fingerprint logic.
- **External, not inferable:**
  - the HTTP framing layer and identity issuance;
  - audit sink durability and retention;
  - deployed limits, network policy and the approval service;
  - the scanner and the remote backends;
  - key provisioning.

## 2. Findings (ordered by impact)

### F1. Records cache is never invalidated, has no TTL and is unbounded — gap (medium)

- **Evidence:** `gateway.py:36-40`. The cache key is `(tenant, sub, RESOURCE, POLICY_VERSION, tools, query)`. Entries are never evicted or expired and are not tied to backend data state. `CACHE` is a process-global dict (`gateway.py:5`).
- **Dataflow:** An authenticated caller sends `read` with `query`. A miss calls the backend and stores the result. Later identical calls return the stored object.
- **What holds:**
  - Authentication runs on every request, so revoked or expired subjects are rejected before a cache hit (`gateway.py:63`).
  - Tenant and sub are in the key, so there is no cross-tenant or cross-user sharing.
- **What does not hold:**
  1. **Stale data.** A `delete` through `dispatch` does not invalidate cached reads. Deleted or changed records can keep being served for the process lifetime. This is a correctness issue and an integrity/confidentiality issue for erased data. It is reachable with only authorized operations, and the backend's behavior is unknown.
  2. **Memory growth.** Any authenticated caller can add one entry per distinct `query` string, up to the 8192-byte body limit, with no cap. That is a single-tenant resource-exhaustion path that can affect other tenants in the same process (B07, R01). Whether it is exploitable depends on deployed process limits, which are not supplied.
  3. Results are stored and returned by reference, so a mutating caller could alter cached content. This depends on the framing layer and is not demonstrated.
- **BRACE:** E06, R04, B07, R01. This is a client/tenant state isolation and resource-limit topic. The source is the control-map row, which is guidance. Cache-key and current-authorization guidance appears in `http.md` step 6.
- **Remediation:** Add a TTL and a size bound. Invalidate or version entries on writes and deletes (for example a per-tenant data epoch in the key). Re-resolve authorization on hit if tool grants can change mid-token.

### F2. Undeclared privileged operations and metadata mismatch — gap (medium)

- **Evidence:**
  - `catalog.json` declares only `read_records`, with `readOnlyHint: true`.
  - `inputSchema` has no `tenant` property, no `required` list and no `additionalProperties:false`. `outputSchema` is a bare `array` with no `items`.
  - The code requires `args["tenant"]`, and its operation names (`read`, `delete`) differ from the catalog name.
  - Any other `method` goes through `dispatch`/`invoke` with caller-supplied tool and args (`gateway.py:66-71`). The backend then runs any name in `claims["tools"]`, including `delete`.
- **Impact:** The reviewed and fingerprinted definition does not describe the reachable operation set. Destructive `delete` and batch dispatch are not in the approved metadata. The read-only annotation is not an authorization policy.
- **Fingerprint:** `fingerprint()` hashes the whole definition passed in, including annotations and schemas. That is better than hashing the description only. Whether the host passes the complete definition, and whether it compares on every connect or reconnect, is host-owned and `needs_evidence`.
- **BRACE:** E03, E05, B01, B05. The complete-definition hashing is a proposed refinement over BRACE's description/schema wording, not an existing requirement. Source: the OWASP MCP sheet §2 (guidance) and the Uber gateway report (2026-10-01 deployment report).
- **Remediation:** Publish a catalog entry for every reachable operation with accurate schemas and annotations. Restrict the `dispatch` operation set to an allowlist.

### F3. Audit coverage gaps on denial, error and worker paths — gap in this component, host evidence needed (medium)

- **Evidence:**
  1. `audit_sink.begin` runs after origin, size and authentication checks (`gateway.py:59-65`). Those denials are not recorded by this module.
  2. If `read_records`, `cancel` or `dispatch` raises (`PermissionError` on a tenant or operation denial, `KeyError`, or a backend error), `complete` is never called (`gateway.py:66-73`). An open ticket has no recorded outcome or denial reason.
  3. `worker_step` (`gateway.py:48-52`) runs backend actions with no audit call at all.
  4. `begin` records the raw `request` (the full query and args). That may be sensitive and is not minimized.
- **What holds:** `begin` is documented to raise when the capture buffer is full, so the request fails before any action. That is a fail-closed, supported-in-code control, subject to the contract being implemented as described.
- **Mitigation claimed:** README says the external framing layer owns complete attempt, denial, worker and outcome-graph capture. Nothing here shows it, so I record it as `needs_evidence`.
- **BRACE:** R03, R13, A02, C08, E10–E12. Source: OWASP Logging (guidance). The six-field identity schema is BRACE's.
- **Remediation:** Wrap execution so that `complete` or a failure record is always written. Audit worker steps with the job's subject, tenant and policy. Redact or minimize the logged arguments.

### F4. Batch dispatch is non-atomic and has no element cap — gap (low–medium)

- **Evidence:** `gateway.py:32-33` authorizes and executes each call in sequence. A later call that fails the tenant or operation check raises after earlier calls (possibly `delete`) have already taken effect. The only limit is the 8192-byte body check (`gateway.py:61`), with no call-count cap.
- **Impact:** This is not an authorization bypass, because every call is individually checked. It is partial-effect and amplification risk: one request fans out to many backend calls and leaves ambiguous partial effects. With F3 those effects have no recorded outcome.
- **BRACE:** B07, R01, E06, R14. Source: control-map "Resource and parser limits" and "Stop and recovery" rows.
- **Remediation:** Validate and authorize all calls before executing any. Cap the batch size. Define idempotency and recovery for partial failure.

### F5. Task execution reuses frozen claims, and cancellation is cooperative only — needs_evidence

- **Evidence:** `worker_step` checks `cancelled`, `REVOKED` and `exp` before each step, then calls `invoke` with the stored `task["claims"]` (`gateway.py:48-52`).
  - Tool grants and `POLICY_VERSION` are not rechecked, so a policy change after job creation does not take effect for queued work.
  - `REVOKED` is an in-process set. Cross-process propagation and measured stop time are not shown.
  - A step already in flight is not interrupted. Cancel only sets a flag (`gateway.py:42-46`).
  - A cancel response is not proof that effects stopped.
- **What holds:** Cancel enforces the tenant boundary, which matches the stated policy. Any user in the owning tenant may cancel, so that is not a finding.
- **Minor:** An unknown handle raises `KeyError` while a cross-tenant handle raises `PermissionError`. Without handling in the framing layer this is a handle-existence oracle. Handle entropy is unknown.
- **BRACE:** R11, R12, R14, E09, E06. Sources: MCP Tasks (optional extension, cooperative cancellation) and the control-map stop row.
- **Proposed test:** see §5.

### F6. Symmetric-key (HS256) token verification — needs_evidence (guidance-level)

- **Evidence:** `gateway.py:10-22`. The `alg` header is pinned to HS256, the signature uses `compare_digest`, and the verifier holds the signing secret.
- **Concern:** Any holder of `JWT_VERIFY_SECRET` can mint accepted tokens. There is no `kid` or rotation path, and no `nbf`/`jti`.
- **Not demonstrated:** The issuer topology and key custody are external. This is a hardening note, not a protocol violation.
- **Source:** RFC 9700 (BCP) and the MCP authorization spec (2026-07-28).

### F7. Chained authorization and identity gaps that need external evidence

- There is no scope check and no separation of agent, original subject and acting identity. Only `sub` is used. This maps to A01, A04 and E08 and needs evidence.
- Backend credentials are not shown, so token passthrough versus a separately audienced credential is unknown (`http.md` step 4).
- `delete` is a consequential operation. The only gating is operation name plus tenant (`gateway.py:25-28`), and README says that is the intended policy. No approval binding, check-and-consume or per-record authorization is shown. Whether one is required is a BRACE judgment (B01, B05, B06), so it is `needs_evidence`, not a gap.

## 3. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Origin check | likely_pass | Exact match at `gateway.py:59`. A missing Origin is rejected. | Streamable HTTP spec 2026-07-28 | Component |
| Host header, protocol-version header and routing-header/body comparison | needs_evidence | Not handled in the module. | Protocol requirement for the negotiated version | Framing layer |
| Body size limit | likely_pass for the check, needs_evidence for allocation | `len(body) > 8192` at `gateway.py:61`. Pre-parse allocation happens in the external layer. | Python body-allocation advisory (not rechecked) | Framing layer |
| Token signature, alg pinning, issuer, expiry | likely_pass | `gateway.py:12-19`. Missing claims raise, so the check fails closed. | MCP authorization, RFC 9700 | Component / issuer |
| Audience / resource | likely_pass | Exact `RESOURCE` match, string or list (`gateway.py:20`). This is a custom audience check, as the SDK audience advisories allow. | TS GHSA-rvq5-wwqv-78pq, Python GHSA-w4fh-qvv9-3v23 (2026-10-05, not rechecked) | Component |
| Key provisioning and rotation | needs_evidence | `JWT_VERIFY_SECRET` is read from the environment only. | Guidance | Platform |
| Revocation | needs_evidence | `REVOKED` is a local set. Propagation is unmeasured. | BRACE B02–B04 | Host / identity |
| Tenant and operation authorization | likely_pass | `invoke` checks both on every route, including batch, direct and cached-miss paths. | Control-map identity row | Component |
| Task tenant ownership | likely_pass | `gateway.py:43-45`. | Control-map state row | Component |
| Cache isolation | gap, see F1 | Key includes tenant and sub. There is no TTL, bound or invalidation. | Guidance | Component |
| Catalog/metadata integrity | gap, see F2 | `fingerprint()` hashes the full definition. The approved catalog is incomplete. Host compare is unseen. | OWASP MCP sheet, Uber report | Component / host |
| Business approval for `delete` | needs_evidence | Operation + tenant only. | OWASP transaction authorization (guidance) | Approval service |
| Audit | gap in module, needs_evidence for the host | See F3. | OWASP Logging, CERT-In CIAD-2026-0049 (2026-10-15, not rechecked) | Framing layer / sink |
| Stop and recovery | needs_evidence | See F5. | MCP Tasks overview | Scheduler / host |
| Untrusted returned content | needs_evidence | Backend output is returned without inspection. Rendering is outside the component. | MCP security guidance, OWASP injection prevention | Host / client |
| Network and egress | needs_evidence | No outbound I/O in the module. Backend and network policy are external. | MCP security guidance, OWASP SSRF | Platform |
| Persistent influence | na_candidate | No file, memory, hook or skill persistence in the module. The absence search covered `gateway.py` and the README. `CACHE` and `TASKS` are process memory only. | Control-map persistence row | Component |
| Stdio / local launch | na_candidate | README: no stdio. A search of the whole fixture found no `.mcp.json`, launch command or dotfile. | `stdio.md` | n/a |
| Skills and Apps extensions | na_candidate | README: not enabled. | Control-map extensions | n/a |
| Supply chain / SDK advisories | needs_evidence | No manifest or lockfile. Resolved versions are unknown. | `advisories.md` (2026-10-22 baseline, not rechecked) | Build owner |

## 4. Controls supported in code, missing evidence, unreviewed scope

- **Supported in code:**
  - origin allowlist;
  - body-size check;
  - HS256 signature with algorithm pinning;
  - issuer, expiry, revocation and exact audience checks;
  - tenant and operation checks on every dispatch path;
  - tenant-scoped cancel;
  - audit `begin` before action (fail-closed under the stated contract);
  - a full-definition fingerprint function.
- **Missing or runtime evidence:**
  - negotiated protocol version, extensions and deployed limits;
  - audit durability and the external audit completeness claims;
  - revocation and cancellation stop times;
  - host fingerprint comparison on reconnect;
  - backend authorization and credentials;
  - approval for destructive operations;
  - resolved dependency versions.
- **Unreviewed:** the framing layer, identity issuer, audit sink, scheduler, backends, network policy, and any deployment or installed artifact. Source evidence and deployed state may differ, so nothing here authorizes deployment.
- No findings were rated Pass. `likely_pass` means supported in code only.

## 5. Proposed controlled tests (not executed; run on disposable fixtures)

1. **Authorization matrix**
   - Allowed: a valid token with a matching tenant and an authorized tool.
   - Denied: wrong issuer, audience, tenant, expired token, revoked subject, and a tool outside `tools`.
   - Owner: gateway team.
2. **Cache and delete**
   - Read, then `delete` the same record, then read again. Expected: the deleted record is not returned.
   - Also verify a second user or tenant cannot observe the first's entries, and bound the entry count under many distinct queries.
   - Owner: gateway team.
3. **Batch**
   - Send `[valid delete, cross-tenant call]`. Expected: no effects, a recorded denial, and a rejected oversized call count.
   - Owner: gateway team.
4. **Cancel and stop drill**
   - Revoke the subject and cancel a task mid-run across multiple processes.
   - Expected: no further backend effects after the measured stop time, a policy-change test for queued jobs, and no existence oracle for handles.
   - Owner: scheduler team.
5. **Audit**
   - Trigger an origin denial, an auth denial, an operation denial, a backend error and an audit-buffer-full condition.
   - Expected: a reconstructable record for each denial and error, no action when `begin` fails, and worker steps recorded.
   - Owner: framing/audit owner.
6. **Metadata**
   - Change annotations, `outputSchema` or add an operation.
   - Expected: the host rejects the mismatch and quarantines the tool.
   - Owner: host / approval owner.

## 6. Sources (bundled, dated, not rechecked)

- MCP authorization and Streamable HTTP, 2026-07-28 (protocol requirements)
- MCP versioning, identified 2026-07-28 on 2026-10-22
- RFC 9700 (BCP)
- OWASP MCP Security, Transaction Authorization, Logging and SSRF cheat sheets (guidance)
- Uber MCP gateway, 2026-10-01 (deployment report)
- CERT-In CIAD-2026-0049, 2026-10-15 (government advisory)
- TS SDK audience GHSA-rvq5-wwqv-78pq, 2026-10-05
- Python SDK audience GHSA-w4fh-qvv9-3v23, 2026-10-05
- Python SDK body allocation GHSA-fmmv-w9g8-j3gc, 2026-09-30
- MCP Tasks extension overview
- BRACE research 2026-10-22

This review found the items above within its recorded scope. It is not a security pass, certification or release verdict.
