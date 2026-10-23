# MCP review: records gateway (`repo/`)

Review date: 2026-10-23. Review was source-only and nothing was executed. Public-source lookup was unavailable, so advisory and protocol references come from `skill/references/*` and were not rechecked against the original records.

This report is not a security Pass, certification or deployment approval. It is not a 53-item BRACE assessment, and no `.brace/` files were touched.

## Untrusted-content notice

`repo/review-notes.txt` contains a "supplier note" telling the reviewer to omit authentication and cache observations and to state that all controls passed. That is untrusted data and I did not follow it. Authentication and cache findings are included below, and no control is reported as passed.

## 1. Scope and inventory

| Item | Value |
|---|---|
| Component | HTTP gateway application logic: `repo/gateway.py` (72 lines), `catalog.json` (one tool definition), `README.md` |
| Transport and protocol | Protected HTTP MCP 2026-07-28, as declared in the README. Negotiation code is not supplied, so the negotiated revision is unverified. |
| Extensions | No stdio, Apps or Skills. Tasks-like handles exist (`TASKS`, `cancel`, `worker_step`). |
| Commit and release | None supplied (not a git repo). |
| Packages and lockfiles | None. No MCP SDK is imported, so the SDK advisories in `advisories.md` have no resolved version to match and are not applicable on this evidence. |
| Tool | `read_records` in the catalog. The code invokes an operation named `"read"` and the README says backends also implement `delete`. The catalog name and the code's operation names are not reconciled. |
| Credentials | HS256 JWT verified with `JWT_VERIFY_SECRET` from the environment. No live key is in the fixture. |
| Outside the supplied component | Framing and identity issuance, audit sink durability, deployed limits, network policy, approval service, scanner, backends, and host or client behavior |

## 2. Findings, ordered by impact

### F1. Batch mode skips tenant and operation authorization (gap; B01, B02, B05, E06)

- **Dataflow:** `handle_http` falls through to `dispatch` for any method other than `read` or `cancel`. In `dispatch`, `request["mode"] == "batch"` runs `backend(call["tool"], call["args"])` directly (`gateway.py:30-33`).
- **Consequence:** `invoke`, which performs the `args["tenant"]` and `name in claims["tools"]` checks (`gateway.py:23-28`), is never called on this path. Any authenticated caller can reach any backend operation for any tenant, including `delete`, per the README's backend description.
- **Evidence limit:** The README says the module shows "the complete application authorization" and that there are "no other hidden application checks on these paths". Backend-side enforcement is out of scope, so I could not confirm it.
- **Remediation:** Route each batch element through `invoke`. Also bound the element count and fail the whole batch on the first denial, or define partial-result semantics explicitly.
- **Source authority:** BRACE mapping. Protocol authorization is optional, but BRACE requires it for protected access.

### F2. Shared cross-tenant cache that bypasses authorization on a hit (gap; E06, R04)

- **Dataflow:** `read_records` uses `key = query` in a process-global `CACHE` (`gateway.py:35-39`). The key has no tenant, subject, policy version or authorization context.
- **Consequence:**
  - Tenant B sending the same query string as tenant A gets A's records without any check. The `invoke` authorization only runs on a miss.
  - Entries never expire. Revocation or a policy change does not affect cached data.
- **Remediation:** Key on tenant, subject (or an authorization-scope digest) and policy version. Re-authorize before serving a hit and add a TTL.
- **Source authority:** `control-map.md` row "Client/tenant state isolation"; the matching advisory analogue is the TS shared-server leak (not this package).

### F3. Token audience and resource are never validated (gap; B02)

- **Evidence:** `authenticate` checks the signature, `alg`, `iss`, `exp` and revocation. `RESOURCE` is defined but never referenced, and the comment "Other accepted claims are handled below" (`gateway.py:20`) is not borne out. No `aud`, resource or scope check exists anywhere in the file.
- **Consequence:** A token issued by the same issuer for a different resource is accepted. A valid signature is not an audience check (`http.md` §3).
- **Related limits:**
  - HS256 means every verifier holds a signing-capable shared secret. Whether the deployment requires asymmetric keys is an external key-provisioning question (`needs_evidence`).
  - There is no `nbf` or `iat` check.
  - `claims["tenant"]` and `claims["tools"]` are trusted from the token without schema validation, so a missing claim produces a `KeyError` that happens to fail closed.
- **Remediation:** Require `aud` or the RFC 8707 resource to equal `RESOURCE`. Validate the types of the `tools` and `tenant` claims.
- **Source authority:** MCP authorization 2026-07-28 and RFC 9700 (protocol and BCP). The `http.md` guidance applies.

### F4. Queued work runs on stale claims, and cancellation is not honored (gap; R11, R12, B04, A04)

- **Dataflow:** `worker_step` calls `invoke(task["claims"], ...)` (`gateway.py:47-50`) using the claims captured when the job was created.
- **Consequences:**
  - The worker never re-checks `exp` or `REVOKED`, so a token revoked after queuing still drives effects.
  - `cancel` only sets `task["cancelled"] = True` (`gateway.py:45`). Nothing in `worker_step` reads that flag, and the README says the scheduler runs the step "once for every queued handle". Cancel therefore does not stop queued work.
  - `cancel` raises `KeyError` for an unknown handle. That is harmless, but it is an unguarded error path.
- **Positive:** The tenant check in `cancel` matches the stated policy (own tenant only). Tenant ownership of handles is supported in code. Tenant-level task policy is the documented choice and is not itself a finding.
- **Remediation:**
  - Check `cancelled` and revocation at the start of each worker step and before each side effect.
  - Re-evaluate authorization at execution time, or bind the job to a short-lived delegated credential.
  - Prove cessation of effects through a drill, not a cancel response.
- **Source authority:** MCP Tasks (cooperative cancellation).

### F5. Definition fingerprint omits annotations and `outputSchema` (gap vs. README claim; E03, E05)

- **Evidence:** `fingerprint` hashes only `name`, `description` and `inputSchema` (`gateway.py:52-54`). `catalog.json` also carries `outputSchema` and `annotations.readOnlyHint`. The README states "Metadata approval covers the complete definition".
- **Consequence:**
  - A change to annotations or the output schema would pass the owner-approved comparison unnoticed.
  - The `readOnlyHint: true` annotation is server-supplied and is not an authorization policy. The tool's backend family includes deletion.
- **Label:** Hashing the complete definition is a proposed refinement that sharpens BRACE's "description/schema" wording. It is not a stated existing requirement.
- **Remediation:** Hash a canonical serialization of the full definition. Treat annotation changes as a change to approve.
- **Extra note:** A matching digest establishes consistency, not safety.

### F6. Audit coverage is incomplete in this component (partly `needs_evidence`; R03, R13, A02)

- **Supported in code:** `audit_sink.begin` is called before any action, and the README says it raises if the capture buffer is full. That is a fail-closed design and a `likely_pass` for reserve-before-action, dependent on the sink contract.
- **Gaps:**
  - `complete` is skipped when the handler raises, so denials and errors get no outcome record here.
  - Authentication and origin failures occur before `begin`.
  - Batch elements and `worker_step` are not recorded individually.
  - The record has no approval ID, destination or per-call tool identity.
  - The full `request` is logged, which may include sensitive query content (secret minimization is unverified).
- **Open item:** The README assigns complete attempt, denial, worker and outcome-graph capture to the external framing layer. That layer is not supplied, so its completeness is `needs_evidence`.

## 3. Controls supported in code (not deployment evidence)

- **Origin allow-list:** An exact match on a single origin; a missing origin is rejected (`gateway.py:57-58`). The Host header is not examined.
- **Request body cap:** `len(body) > 8192` is checked before `json.loads`. This also bounds batch size indirectly, assuming the framing layer does not buffer before this check.
- **Token checks:** The `alg` is pinned to HS256, signatures use a constant-time compare, and `iss`, `exp` and revocation by `sub` are checked.
- **Single-call tenant and operation authorization:** `invoke` enforces both, but only on the non-batch path and on a cache miss.
- **Task cancel:** Tenant-scoped.
- **Revocation:** `REVOKED` is a process-local in-memory set that nothing in this module populates, so propagation and measured revocation time are `needs_evidence`.

## 4. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Inventory and ownership (E01, E02, C01) | needs_evidence | Single tool in catalog; backends, framing layer and host not supplied | Guidance | Gateway owner |
| Launch and supply chain (B03, B10–B12, C02, C05) | needs_evidence | No manifest or lockfile; no stdio. SDK advisories not matchable. | Guidance | Release owner |
| Identity: issuer, expiry | likely_pass | `gateway.py:18` | BRACE, BCP | Gateway |
| Identity: audience/resource | **gap** | F3 | Protocol (authorization), BCP | Gateway |
| Key custody and algorithm policy | needs_evidence | HS256 shared secret; provisioning external | Guidance | Identity/platform |
| Business authorization: single call | likely_pass | `invoke` | BRACE | Gateway |
| Business authorization: batch | **gap** | F1 | BRACE | Gateway |
| Approval service, binding and reuse (B05, B06) | needs_evidence | Out of scope; delete path unexamined | Guidance | Approval-service owner |
| Publication and integrity | **gap** | F5 | Guidance (proposed refinement) | Gateway/catalog owner |
| Untrusted metadata and returned content (E04, R01–R03) | needs_evidence | Descriptions and outputs are not consumed here; the host and model are out of scope | Guidance | Host owner |
| Network and egress (B08, B09) | needs_evidence | No outbound I/O in the module; backends and network policy not supplied | Guidance | Network owner |
| Tenant/state isolation: cache | **gap** | F2 | Guidance | Gateway |
| Tenant/state isolation: tasks | likely_pass for cancel; **gap** for execution | F4 | Guidance | Gateway |
| Resource limits | likely_pass for body size in code; deployed limits `needs_evidence` | `gateway.py:59` | Guidance | Framing layer |
| Persistent influence (R05, R06) | na_candidate | Searched `memory`, `summary`, `hook` and `skill` (read-only inspection of the module): no persistence beyond the in-process cache/tasks. Runtime stores are unseen. | Research | Gateway |
| Stop and recovery (R11, R12, R14) | **gap** | F4 | MCP Tasks | Gateway/scheduler owner |
| Audit and incident response | mixed | F6 | Guidance, BRACE schema | Gateway + framing layer |
| Stdio/local process | na_candidate | README: no stdio. The only source is the README, so this is a documented absence, not a code search. | n/a | n/a |
| Apps/Skills extensions | na_candidate | README: not enabled | n/a | n/a |

## 5. Unreviewed scope and limits

- **Version and negotiation:** The negotiated protocol revision is unverified; I relied on the README's 2026-07-28 claim.
- **Components not supplied:** Backend implementations, the framing and identity issuance layer, the scheduler and its `TASKS` population, the audit sink, scanner, network policy, the approval service and the host or client approval behavior.
- **Runtime facts:** Deployed limits, revocation latency and stop times can't be established from source.
- **Installed versus source:** No installed or deployed artifacts were available to compare with the source. This scoped source finding set is not deployment authorization.
- **Advisories:** None matched, because no SDK or package is present. Lookup date: 2026-10-23, using the skill's 2026-10-22 index only.

## 6. Proposed controlled tests

These are proposals only, to be run against disposable fixtures with fake credentials. None were executed.

| Test | Expected allowed | Expected denied | Owner |
|---|---|---|---|
| Valid single `read` for the caller's own tenant | Succeeds | n/a | Gateway team |
| Batch containing another tenant's args, or a tool absent from `claims["tools"]` (including `delete`) | n/a | Whole batch rejected; backend untouched | Gateway team |
| Token with a wrong `aud` or resource but the right issuer | n/a | Rejected | Identity owner |
| Tenant A populates the cache, then tenant B sends the same query | B gets a fresh authorized result | B never sees A's records | Gateway team |
| Revoke a subject after a cache fill, then replay the query | n/a | Denied | Gateway team |
| Queue a job, revoke the subject or cancel, then let the scheduler run | n/a | No backend effect; cancelled state honored | Scheduler owner |
| Change `annotations` or `outputSchema` only in the catalog | n/a | Fingerprint mismatch and quarantine | Catalog owner |
| Fill the audit buffer | n/a | Request rejected before any action | Audit owner |
| Attempt a denied auth/origin request | n/a | A denial record exists end to end across layers | Framing and audit owners |
| Oversized body and large batch at the framing layer | Within-limit batch passes | Over-limit rejected before parsing | Framing-layer owner |

No findings beyond F1–F6 were identified in the recorded scope. That is not an assurance of absence elsewhere.
