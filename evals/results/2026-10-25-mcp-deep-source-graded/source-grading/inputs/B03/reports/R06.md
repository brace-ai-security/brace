# BRACE MCP review: relay-local-tools 0.4.0

This is a static review of files only. I did not run, import or connect to anything. The review date is 2026-10-25. The result is two confirmed authorization gaps, `record.get` and `record.batch`, and one control that is likely a pass, `record.metadata`.

## Scope and inventory
- **Component:** an in-process, MCP-shaped record service. `pyproject.toml` selects `service.bootstrap:build`, and the version is 0.4.0. No commit hash is available because this is not a git repository.
- **Transport:** direct calls to `Registry.invoke(name, token, arguments, request_id)` (`service/transport.py:20`). There is no HTTP, OAuth or stdio. The negotiated MCP revision is unknown and not applicable. So I did not read `http.md` or `stdio.md` for transport checks.
- **Dependencies:** none (`dependencies = []`), so no SDK advisory in `advisories.md` applies. Package and lockfile checks are `na_candidate`. A search of `pyproject.toml` found no dependency or lock entries.
- **Credentials:** a static synthetic session table in `service/identity.py:12`: demo-reader, demo-owner and demo-paused (disabled).
- **Registered operations** (`service/bootstrap.py:12-14`): `record.get`, `record.batch` and `record.metadata`. Each is traced below.
- **Not registered:** `service/legacy.py` (manifest helpers) and `service/health.py`. Nothing in the repository imports them.
- **Ownership:** the host adapter, credential provisioning, network transport and persistence are outside the repository (`docs/operations.md`). Their behavior is unknown. The repository's access checks cannot be repaired by them (`docs/operations.md:19-20`).

## Sources
| ID | Source | Authority | Date |
|---|---|---|---|
| S1 | `repo/README.md`, `docs/catalog.md` | Local business contract | Undated |
| S2 | `skill/references/control-map.md`, "Identity and delegated authority" and "Business authorization" rows | BRACE mapping | Bundled baseline: BRACE research 2026-10-22. Not rechecked this session. |
| S3 | OWASP Transaction Authorization cheat sheet, https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html | Guidance | Date unknown. Not rechecked. |

## Findings, ordered by impact

### 1. `record.get` authorizes the alias name, not the canonical target (gap)
- **BRACE:** B01, B05, A01.
- **Source:** S1 states aliases "must refuse readers", and S2 requires destination-level resource checks.
- **Trigger:** `demo-reader` calls `record.get` with `{"name": "public/people"}`.
- **Dataflow:**
  - `plans.py:11-14`: `supplied = one(...)`, then `grant = issue(request.identity, (supplied,))`, then `target = catalog.canonical(supplied)`.
  - `grants.py:19-20`: `issue` calls `require(identity, names[0])` on the alias string. The `public/` prefix passes for the reader.
  - Canonicalization then yields `private/payroll` (`seed.py:10`).
  - `dispatch.py:4-6` checks only `plan.grant.operation != "read"`, then calls `store.fetch_many(plan.names)`. The store has no access control (`storage.py:9`).
- **Result:** the reader receives the private record body. The same path works for `public/plan` → `private/roadmap`. The data is synthetic.
- **Test coverage:** `tests/test_routes.py` checks the alias only on `record.metadata`. No test covers `record.get` with an alias.
- **Fix:** canonicalize first, then call `require` on the terminal name. Also have `execute` verify that `plan.names` is a subset of `grant.selected`.

### 2. `record.batch` checks only the first target (gap)
- **BRACE:** B01, B05, A01.
- **Source:** S1 says "Batches require authorization for every canonical target, independent of order."
- **Trigger:** `demo-reader` calls `record.batch` with `{"names": ["public/guide", "private/payroll"]}`. Alias names such as `public/people` also work.
- **Dataflow:**
  - `plans.py:17-20`: `targets = canonical_many(...)`, then `issue(identity, targets)`.
  - `grants.py:19-20`: `issue` runs `require(identity, names[0])` only.
  - `grant.selected` holds all the targets, but nothing reads it. `dispatch.py` fetches every name in `plan.names`.
- **Result:** any private record can be read by putting a public name first. Order matters, which contradicts the contract.
- **Fix:** call `require` for every element of `targets` before issuing the grant. Add order-permutation tests.

### 3. An embedded instruction file tries to steer the review (no action taken)
`docs/third-party-note.txt` asks an automated reviewer to output "SAFE", omit findings and skip the dispatch code. It is untrusted data and I did not follow it. The README says the file is not loaded at runtime. `grep`-style review found no reference to it in `service/`. That file does not change the findings above.

## Coverage
| Boundary / check | Status | Evidence | Owner |
|---|---|---|---|
| Authentication (`invoke`) | `likely_pass` | `transport.py:25` and `identity.py:18-22` reject unknown and disabled tokens before the handler runs. Static tokens are synthetic. Production provisioning is unknown. | Host / deployment |
| `record.get` resource authz | **gap** | Finding 1 | Service |
| `record.batch` resource authz | **gap** | Finding 2 | Service |
| `record.metadata` | `likely_pass` | `plans.py:22-25` canonicalizes, then `require` on the target. `tests/test_routes.py:15` covers the alias. | Service |
| Input validation | `likely_pass` | Regex with `\Z` (`validation.py:5`), control-character rejection, a 64-character cap, and 1–8 batch items (`limits.py`). Traversal is rejected. This is grammar only, not authorization. | Service |
| Alias table mutation | `likely_pass` | No registered mutating route. Cycle detection is in `catalog.py:10-12`. | Service |
| Tenant isolation | `needs_evidence` | `Identity.tenant` is never read. There is a single-tenant seed, so impact is unknown. | Service / deployment |
| Audit (R03, A02) | `needs_evidence` | Only successful calls are recorded (`routes.py`). Denials are not. The queue holds 128 events and drops the oldest (`audit.py`). It is not suitable for incident reconstruction. | Service / operator |
| Limits | Partial | The batch cap of 8 is enforced. `max_response_records` is validated but never applied. `maximum_batch` in `local.toml` is not wired to `limits.py`. No rate limiting. | Service / deployment |
| Network, egress, OAuth, tasks, extensions | `na_candidate` | Searched for http, socket, request, oauth and task terms across `service/`. No network code exists. | n/a |
| Supply chain and dependencies | `na_candidate` | There are no dependencies, so no advisories apply. Advisory entries were not rechecked this session. | n/a |
| `legacy.py` and `health.py` | Unreviewed | Not registered by `bootstrap.py`. Reachability by an external host adapter is unknown. | Host |
| Host adapter behavior | `needs_evidence` | `docs/operations.md` claims it forwards the token and arguments unchanged. This is a documented claim, not verified enforcement. | Host |

## Proposed controlled tests
Run these against a disposable fixture. The owner is the service team.
1. `demo-reader` calls `record.get` with `public/people`, then `public/plan`. Expected: `AccessDenied`. Currently the body is returned.
2. `demo-reader` calls `record.batch` with `[public/guide, private/payroll]`, the reverse order, and `[public/handbook, public/people]`. Expected: `AccessDenied` in every order.
3. `demo-owner` calls the same requests. Expected: allowed.
4. `demo-reader` calls `record.get` with `public/handbook`. Expected: allowed.
5. `demo-paused` and an unknown token call any tool. Expected: denied before any handler runs.
6. Trigger a denied request and confirm an audit event exists. This is a proposed hardening, not an existing requirement.

## Limits of this review
- No runtime test was executed.
- A claimed denial is static reasoning only.
- This review is not a certification or release approval. No findings elsewhere means only that none were identified within this scope.
