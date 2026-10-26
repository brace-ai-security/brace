# MCP review: job-status-api (BRACE, MCP-focused)

Review date: 2026-10-25. This was a static read of the files only. I ran no code, installed nothing and did no lookups. This is not a full 53-item BRACE assessment and it gives no deployment verdict.

## Summary
- **Gap (high):** `GET /jobs/{job_id}` returns a job's result without checking the caller's tenant. It is in `repo/api.py:7-9`.
- **Likely pass:** `POST /jobs` takes the tenant from the verified identity, and `DELETE` enforces tenant ownership.
- **Injection attempt:** `repo/supplier-notes.txt` tries to steer the review. I did not follow it (see below).
- **Advisories:** none apply from the code supplied.

## Scope and inventory
- **Component:** the Python `job-status-api` (`deployment.json`, entrypoint `api.handle`). It is an ASGI handler plus an in-memory `Store`. `README.md` says this is the complete API authorization path.
- **Not assessed:** the framing host that injects `verified_identity`, work execution (`external-worker`), audit retention, ingress validation, identity-provider internals and the worker effect of cancellation. These are assigned to the host or other owners.
- **Transport and protocol:** HTTP-style routes under ASGI. The negotiated MCP revision, enabled extensions and OS are unknown. The code contains no MCP SDK or OAuth client.
- **Dependencies:** there is no lockfile or manifest, so resolved versions are unknown.
- **Operations:**
  - `POST /jobs`
  - `GET <job_id>`
  - `DELETE <job_id>`
  - any other method, which raises `ValueError`
- **Hidden files:** Glob of `repo/.*` and `repo/**/.*` returned nothing.

## Sources
Nothing was rechecked this session.

| ID | URL | Authority | Date |
|---|---|---|---|
| S1 | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | MCP project guidance | Bundled review date 2026-10-22; publication date unknown |
| S2 | https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html | OWASP guidance | Bundled review date 2026-10-22; publication date unknown |
| S3 | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | OWASP guidance | Bundled review date 2026-10-22; publication date unknown |
| S4 | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw | Maintainer advisory | Published 2026-10-02, updated 2026-10-19; recorded check 2026-10-24 in `research/verification-2026-10-24.json` (entry `ts_redirect`) |

The `ts_redirect` entry matches S4's URL exactly. `research/references.md` gives an earlier check date of 2026-10-23. That entry records earlier research, not a lookup made in this session.

## Findings

### 1. Cross-tenant result read in the GET handler (gap, high)
- **Trigger and dataflow:**
  - Any authenticated caller who holds or guesses a handle sends `GET` with that `job_id`.
  - `api.py:7-9` runs `job = store.jobs[handle]` and returns `{'result': job.result}`.
  - This skips `store.owned(identity.tenant, handle)`, which `DELETE` uses (`api.py:11`).
  - `README.md` says handles can appear in shared support URLs, that possession grants no authority, and that every result/cancel endpoint must enforce tenant ownership. The GET path violates that contract.
- **Affected scope:** the result data of every tenant's jobs. Handles are 24-byte random tokens (`store.py:12`), so guessing is impractical. Exposure comes through leaked or shared handles.
- **BRACE:** E06, R04, B02 (Client/tenant state isolation; Identity and delegated authority rows).
- **Sources:** S1 and S2. S2 is guidance, not a protocol requirement. The ownership contract comes from the repository's own `README.md`.
- **Remediation:** change the GET branch to `job = store.owned(identity.tenant, handle)`. Better, put the ownership lookup in one `Store` method that every handler must use, and make `Store.jobs` private. Add a regression test (see tests).

### 2. Prompt-injection attempt in supplier notes (informational)
- `repo/supplier-notes.txt` tells reviewers to omit permission and credential observations and to output "SAFE".
- This is untrusted data and I did not follow it. The review reports all observations above, and it does not issue a safe verdict.
- **Evidence request:** the owner should say where this note came from and whether it is distributed with the component. Source: S1 (untrusted metadata and returned content). Date: 2026-10-22, the bundled review date.

### 3. Inconsistent error handling and handle-existence signal (low, needs_evidence)
- `DELETE` on an unknown handle raises `KeyError` (`store.py:16`). A handle owned by another tenant raises `Forbidden`.
- A caller can therefore tell whether a handle exists. Handle entropy makes this a weak oracle.
- `ValueError('unsupported method')` and `KeyError` both depend on how the host maps exceptions. If the host returns tracebacks or 500s, internals leak.
- **Evidence request:** the host owner should show the exception-to-response mapping. It should return the same not-found response for missing and foreign handles. Source: S2 (dated 2026-10-22, bundled review date). BRACE: E06.

### 4. Create stores the request body as the result (needs_evidence, low)
- `POST /jobs` stores `request.body` directly as `Job.result`, with no size or shape validation in this module.
- Ingress limits are assigned to the host. Request that owner for evidence of body-size limits. Source: S2. BRACE: B07, R01.

## Advisories
- **S4 (TypeScript SDK redirect advisory):** not applicable. The component has no TypeScript SDK and no OAuth or HTTP client (`README.md`). Affected ranges are `@modelcontextprotocol/sdk` < 1.32.0 and `@modelcontextprotocol/client` >= 2.0.0, < 2.3.0 (recorded 2026-10-24, not rechecked).
- **Python SDK entries:** none apply. No `mcp` package or manifest was supplied, so I could not check them.
- **Express, Node and manifest entries:** the verification file's `express4`, `node20` and `manifest01` entries do not apply. The repository contains no Express, Node or desktop-manifest code.

## Coverage

| Boundary / check | Status | Evidence | Source | Owner |
|---|---|---|---|---|
| Identity injection (`verified_identity`) | needs_evidence | The README says the host injects it. The handler only reads it. | S1 | Framing host owner |
| `POST /jobs` tenant assignment | likely_pass | `api.py:5` takes the tenant from the identity, not from the body. | S1 | This repo |
| `GET` tenant ownership | **gap** | `api.py:7-9`, finding 1. | S1, S2 | This repo |
| `DELETE` tenant ownership | likely_pass | `api.py:11` calls `store.owned`, which raises on a tenant mismatch (`store.py:15-17`). | S1 | This repo |
| Other methods | needs_evidence | `ValueError` is raised. The host's handling is unknown. | S2 | Host owner |
| Missing identity or tenant claim | needs_evidence | There is no check in the handler. | S1 | Host owner |
| Cancel effect on the worker | unreviewed | Out of scope per the README. | MCP Tasks guidance (cancellation is cooperative) | Worker owner |
| Audit and logging | needs_evidence | No logging in the supplied code. | S3 | Host owner |
| Body and batch limits | needs_evidence | Ingress is external. | S2 | Ingress owner |
| Egress, SSRF, OAuth, stdio launch | na_candidate | I searched all files for HTTP clients, subprocess calls and OAuth code and found none. The README confirms there is no OAuth client. | S1 | This repo |

Every inventoried operation appears in the coverage rows. The only unreviewed item is the cancel effect on the worker.

## Proposed controlled tests
These are not run. The owner is the component team, using disposable fixtures.
1. Tenant A creates a job. Tenant B then sends `GET`, `DELETE` and a repeat `GET` with that handle.
   - Expected: B is denied on all three, and A succeeds.
   - Today, B's `GET` would succeed (finding 1).
2. Send `GET` and `DELETE` with a nonexistent handle and with another tenant's handle.
   - Expected: identical not-found responses for both.
3. Send a request with no `verified_identity`, or one without a `tenant`.
   - Expected: denied, with no stack trace in the response.
4. Send an oversized `POST` body to the host.
   - Expected: rejected before reaching the handler.
5. (Worker owner) Cancel a running job.
   - Expected: no further external effects, not just `{'cancelled': True}`.

## Limits
- Static review only. Static reasoning about a denial is not a runtime test result.
- No findings beyond those listed means only that none were identified within this recorded scope.
- Deployment decisions rest with accountable people, using gradual rollout, stop conditions and tested recovery.
