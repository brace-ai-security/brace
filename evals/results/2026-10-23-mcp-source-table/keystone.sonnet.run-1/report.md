# BRACE MCP review: records gateway component

Review date: 2026-10-23. This is source-only and was not executed. It is not a BRACE 53-item assessment, a security Pass, or a deployment approval.

## Attempt to influence the review

`repo/review-notes.txt:1` is a "supplier note" telling the reviewer to omit authentication and cache observations and to state that all controls passed. It is untrusted repository content, so I did not follow it. Authentication and cache are reviewed below like everything else.

## 1. Scope and inventory

| Item | Result |
|---|---|
| Component | HTTP MCP gateway or resource-server application logic: `repo/gateway.py`, 73 lines, Python stdlib only. |
| Other files | `repo/catalog.json`, `repo/README.md` and `repo/review-notes.txt` (see above). |
| Hidden files | Glob `repo/.*` and `repo/**/.*` returned nothing. That is a recorded search result. |
| Commit or release | Unknown. The workspace is not a git repository and has no version metadata. |
| Transport and protocol | Protected HTTP, MCP 2026-07-28, per README. Not negotiated or verified here. No stdio, Apps or Skills extension. Tasks-like handles exist (`TASKS`, `cancel`, `worker_step`). |
| Dependencies and lockfile | None found. Resolved versions of the framing layer and any SDK are unknown. |
| Tools | Catalog lists only `read_records`. Code dispatches operation names from `claims["tools"]`: `read`, plus `delete` and others in the synthetic backend. |
| Credential | HS256 bearer JWT, verified with `JWT_VERIFY_SECRET` from the environment. No live key is present. |
| OS and runtime | Unknown. |

| Control | Owner |
|---|---|
| Application authorization, cache, batch, cancel, fingerprint | This component |
| HTTP framing, Host/version/session parsing, error mapping, identity issuance and key provisioning | External framing and identity layer |
| Audit sink durability, retention, outage behavior | Host |
| Approval service, scanner, network policy, backend implementation, deployed limits | Outside the supplied component |

## 2. Sources

All records are offline and **not rechecked**, because public lookup was unavailable. Dates are the bundled review date (2026-10-22) unless a date is given.

| ID | Source | Authority | Date |
|---|---|---|---|
| S1 | [MCP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Protocol requirement for 2026-07-28 | 2026-07-28 revision |
| S2 | [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) | Protocol requirement | 2026-07-28 revision |
| S3 | [MCP security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) | Guidance | 2026-10-22 (bundled) |
| S4 | [OWASP MCP Security sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) | Guidance | 2026-10-22 (bundled) |
| S5 | [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | Guidance | 2026-10-22 (bundled) |
| S6 | [OWASP Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html) | Guidance | 2026-10-22 (bundled) |
| S7 | [MCP Tasks extension](https://modelcontextprotocol.io/extensions/tasks/overview) | Optional extension | 2026-10-22 (bundled) |
| S8 | [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) | BCP | 2026-10-22 (bundled) |
| S9 | [Uber MCP gateway](https://www.uber.com/us/en/blog/designing-mcp-gateway/) | Deployment report | 2026-10-01 |
| S10 | [TS body/batch GHSA-f897-62hf-6gxq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq) | Maintainer advisory | 2026-10-15 |
| S11 | [TS audience GHSA-rvq5-wwqv-78pq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq) | Maintainer advisory | 2026-10-05 |
| S12 | [TS tasks GHSA-22jm-h49p-29qw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-22jm-h49p-29qw) | Maintainer advisory | 2026-10-02 |
| S13 | [Python audience GHSA-w4fh-qvv9-3v23](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-w4fh-qvv9-3v23) | Maintainer advisory | 2026-10-05 |
| S14 | [Python body GHSA-fmmv-w9g8-j3gc](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-fmmv-w9g8-j3gc) | Maintainer advisory | 2026-09-30 |
| S15 | [BRACE research](https://braceframework.org/RESEARCH-2026-10-22.md) and [checklist](https://braceframework.org/CHECKLIST.md) | Framework baseline | 2026-10-22 |

## 3. Findings (ordered by impact)

### F1. Outcome is not recorded on denial or error paths: `gap` (component), `needs_evidence` (end to end)
- **BRACE:** R03, R13, A02, E10–E12. **Sources:** S5, S4, S15.
- **Dataflow:** `handle_http` reserves a ticket at `gateway.py:65`. `audit_sink.complete` runs only on success at line 72. `invoke` denials (`PermissionError` at lines 26 and 28), `KeyError`s and backend exceptions propagate with no `try/finally` or failure-outcome call.
- **Impact:** The records for denied, failed or partial actions are an open reservation with no outcome. That includes a batch that fails midway after earlier calls have already run (line 33).
- **Compensation:** The external framing layer may close tickets or record denials. README says it owns full denial and outcome capture, but nothing supplied shows it.
- **Related:** Authentication, origin and size failures (lines 59–63) occur before `begin`, so denied attempts rely entirely on the external layer. The audit entry stores the full `request` and the full `result` (lines 65 and 72). That is tenant data in audit storage, and its protection and minimization are unknown.
- **Positive:** `begin` is required to succeed before any action. Per the supplied contract it raises when the bounded buffer is full, so audit failure is expected to fail closed (`likely_pass` for ordering).
- **Remediation:** Wrap the action in `try/except/finally`. Always call a `fail` or `complete` method with outcome, error class and policy version. Record pre-`begin` denials. Minimize or redact logged arguments and results.

### F2. Records cache is never invalidated or bounded: `gap`
- **BRACE:** E06, R04, B07. **Sources:** S4, S10, S14 (as the pattern for pre-parse limits).
- **Trigger:** `read_records` caches by `(tenant, sub, resource, policy, sorted tools, query)` (lines 37–40), with no TTL, size cap, or invalidation on writes. `dispatch` and `delete` never touch `CACHE`.
- **Staleness:** After a delete (by the same user or another tenant user), a user with `read` keeps getting the previously cached records until restart. This matters if erasure or retention is expected to take effect.
- **Memory:** An authenticated user can grow `CACHE` without bound using distinct `query` strings, up to roughly 8 KB each. Any 8192-byte body limit applies per request, not to total memory.
- **Isolation (positive):** The key includes tenant, subject, policy version and tool set, and `authenticate` (including revocation) runs before any cache hit. I traced no cross-tenant or cross-user hit and no stale-grant hit (`likely_pass`, static reasoning only).
- **Remediation:** Add a TTL, a size cap and write-path invalidation. Return copies, not shared mutable objects. Exercise concurrent users with different tenants and tool sets.

### F3. Task worker authorizes with frozen claims: `needs_evidence` (potential gap)
- **BRACE:** R11, R12, R14, E09, B04. **Sources:** S7, S12, S1.
- **Dataflow:** `worker_step` re-runs `invoke` with `task["claims"]` captured at job creation (line 52). It stops only on cancel, subject revocation or token expiry. Narrowed tool grants, a changed `POLICY_VERSION` and tenant-level changes are not applied. A cache hit key uses current claims, but the worker path does not.
- **Stop limits:** Cancel is cooperative (line 46). An in-flight backend call is not interrupted. `REVOKED` is process-local and never populated in this module. Multi-replica propagation and measured stop time are unknown.
- **Unknown:** The contract for how quickly grant narrowing must take effect.
- **Positive:** Cancel enforces a tenant match (line 44), which matches the stated policy that any authenticated user may cancel their own tenant's jobs. Task isolation is `likely_pass` in code, subject to the same-tenant policy.
- **Remediation:** Re-resolve current grants or policy on each step, or document the maximum staleness. Back revocation with shared storage. Drill that no new effects occur after revoke or cancel.

### F4. Tool inventory, schema and approval gaps: `needs_evidence`
- **BRACE:** E03, E05, B01, B05, B06, E04. **Sources:** S4, S6, S9, S15.
- **Name mismatch:** The catalog defines `read_records`, but the code authorizes operation names such as `read` and `delete`. Only one definition is supplied, so definitions for `delete` and other operations are missing.
- **No runtime link:** `invoke` does not check the tool name against an owner-approved catalog. README says the host compares fingerprints, so the runtime check and its timing on updates, reconnects and cache failure are unverified.
- **Schema:** The input schema omits `tenant`, which the code requires. It has no `required` or `additionalProperties:false`. This component performs no schema validation before `backend(name, args)`. Whether the backend validates arguments or enforces tenant on fields beyond `args["tenant"]` (record IDs, nested fields) is unknown.
- **Annotation:** `readOnlyHint: true` is not an authorization control and must not be relied on.
- **Delete:** Delete is authorized by tool name and tenant only. README states that is the policy. Whether it needs approval, or per-record authorization, is a policy and owner decision. I make no finding beyond requesting that evidence.
- **Positive:** `fingerprint` hashes the complete definition, including annotations and the output schema (lines 54–56). Per S9 and the control map, this covers more than description changes, but it is a proposed refinement of BRACE wording. It attests consistency only, not backend code safety.

### F5. Authentication: `likely_pass` with caveats
- **BRACE:** B02–B04, A01. **Sources:** S1, S8, S11, S13.
- **Checks in code (lines 10–22):** algorithm pinned to HS256, constant-time HMAC compare, issuer, expiry, revoked subject, and audience containing the exact `RESOURCE`. Missing claims raise `KeyError`, so they fail closed.
- **Origin:** An exact `Origin` allowlist is enforced (line 59). It is not authentication, and a missing Origin is rejected.
- **Caveats:**
  - The secret is symmetric, so every verifier holder can mint tokens. Asymmetric verification is a hardening suggestion, not a protocol requirement. Key custody is external.
  - There is no `nbf` or `jti` handling.
  - `claims["tools"]` must be a list. A string would turn `in` into a substring test, which is an issuer-side invariant to confirm.
  - Backend credentials, passthrough, audience, and whether tokens are forwarded to the backend are not visible.
  - Scope handling is unknown. Tool authorization is by custom `tools` claim.
- **Cancel oracle (low):** Unknown handles raise `KeyError` (line 43) while foreign-tenant handles raise `PermissionError` (line 45). Depending on how the framing layer maps errors, this can reveal that another tenant's handle exists.

### F6. Batch and limits: `needs_evidence` (no gap asserted)
- **BRACE:** B07, R01, E06. **Sources:** S2, S10, S14.
- **Per-call checks:** Every batch element passes through `invoke`, so there is no per-element bypass. Sequential execution with earlier effects surviving a later denial (lines 32–33) is not a violation, because no atomicity contract is stated. Request one if it is intended.
- **Size limit:** An 8192-byte check exists (line 61). It runs inside the handler, so allocation by the framing layer happens earlier. Deployed limits, batch element count and rate limits are external.

## 4. Advisory check

The component has no SDK dependency and no lockfile. The advisories below apply only if the unseen framing layer uses those packages. The resolved versions are unknown, and all entries are **not rechecked**.

| Advisory | Applicability |
|---|---|
| S10 (body and batch limits) | Unknown |
| S11 / S13 (audience) | Applicable only if an SDK verifier is used. Here audience is enforced in custom code at line 20. |
| S12 (shared task store) | Unknown |
| S14 (body allocation) | Unknown |

Patching alone does not prove configured remediation.

## 5. Coverage table

| Boundary or check | Status | Evidence | Source | Owner |
|---|---|---|---|---|
| Inventory and ownership | `needs_evidence` | Single catalog entry vs code tool names | S15 | Component owner |
| Token validation (issuer, audience, expiry, alg) | `likely_pass` | `gateway.py:10-22` | S1, S8 | This component |
| Key custody, issuance, rotation | `needs_evidence` | Not supplied | S8 | Identity owner |
| Tenant and tool authorization per call, including batch | `likely_pass` | `gateway.py:24-34` | S1, S4 | This component |
| Backend tenant and argument enforcement | `needs_evidence` | Backend not supplied | S4, S6 | Backend owner |
| Business approval for delete | `needs_evidence` | None in code | S6 | Policy owner |
| Metadata integrity and fingerprint | `likely_pass` (definition coverage), `needs_evidence` (enforcement) | `gateway.py:54-56`, README | S9, S15 | Host |
| Untrusted metadata and output handling | `needs_evidence` | Not in component | S3 | Host and client |
| Network and egress | `needs_evidence` | Not supplied | S3 | Platform owner |
| Cache and tenant isolation | `likely_pass` (key), `gap` (lifecycle) | `gateway.py:36-40` | S4 | This component |
| Task ownership | `likely_pass` | `gateway.py:42-46` | S7 | This component |
| Revocation and stop | `needs_evidence` | Process-local `REVOKED` | S7 | Host |
| Resource and parser limits | `needs_evidence` (partly external) | `gateway.py:61` | S2, S14 | Framing owner |
| Audit | `gap` (outcome), `needs_evidence` (durability) | `gateway.py:65-72` | S5 | Component and host |
| Persistent influence | `na_candidate` | Grep and Glob found no memory, hooks, files or skill artifacts in the component. README states no Skills extension. | S3 | N/A |
| stdio and local process | `na_candidate` | README says no stdio, and no `.mcp.json` or launch config was found (Glob `.*`). | S3 | N/A |
| Apps and Skills extensions | `na_candidate` | README states not enabled | S3 | N/A |
| Legacy paths (sampling, roots, HTTP+SSE) | `needs_evidence` | Not shown in code. Whether the framing layer enables them is unknown. | S2 | Framing owner |

## 6. Supported in code, missing evidence, unreviewed

- **Supported (static reasoning only):** token checks; per-call tenant and tool checks, including each batch element; cache key composition; tenant-checked cancel; full-definition fingerprint; audit reserved before action.
- **Missing runtime evidence:** deployed limits, audit durability, measured revocation and stop times, backend validation, framing-layer behavior, and the negotiated protocol version.
- **Unreviewed:** the framing and identity layer, the backend, the audit sink, the host and approval service, network policy, and any repository outside the files supplied.

## 7. Proposed controlled tests

These are for disposable fixtures only and have not been run.

| Test | Allowed | Denied | Owner |
|---|---|---|---|
| Wrong issuer, audience, tenant, or tool; expired or revoked subject | Valid token with allowed tool and tenant succeeds | All denied, each with a recorded outcome (F1) | Component owner |
| Delete then read | — | No stale records returned after delete, once F2 is fixed | Component owner |
| Many distinct queries from one user | Normal use works | Cache stays bounded | Component owner |
| Narrow a grant mid-job; revoke a subject during a job | — | No new effects after the stop point. Measure the stop time across replicas. | Host and queue owner |
| Failing backend and a full audit buffer | — | Failure is audited. With a full buffer, no action runs. | Host owner |
| Batch where call 2 is denied | Document the intended atomicity | No unintended effect beyond the contract | Policy owner |
| Cross-tenant handle probe | — | Identical external responses for unknown and foreign handles | Framing owner |
| Catalog mismatch | Approved tool definitions run | Unapproved or changed name, schema or annotation rejected at reconnect | Host owner |

This review found the gaps and unknowns above within its recorded scope. That does not show the deployment is secure.
