# Review: workspace-tools MCP server

I read the code only and ran nothing. The main problem is that revoking a membership doesn't stop jobs that were already started. There are also scope-check gaps and a few smaller issues.

## Findings

### 1. High: membership revocation doesn't affect existing jobs
- **Where:** `service/membership.py:19-33`, `service/worker.py:10-23`, `service/jobs.py:29-35`
- **What happens:**
  - `membership.change` bumps `epochs[key]` on every change, and `Lease` records that epoch.
  - Nothing ever compares the epoch afterwards. `Worker.read` only checks that the lease matches the principal and project.
  - `Worker` is given `membership` but never uses it.
- **Impact:**
  - If an admin removes a user from a project, that user can keep calling `job.resume` on a job started earlier. They keep getting dataset pages until the job is done.
  - The `read` scope isn't re-checked either.
  - A job started before the revocation is never invalidated.
- **Fix:** in `Worker.read`, call `membership.authorize(principal, job.project)` again. Also require `lease.epoch == membership.epochs.get((tenant, project), 0)`, and fail closed if they differ.

### 2. Medium: `job.status` and `job.cancel` don't check any scope
- **Where:** `service/routes.py:25-29`
- **What happens:** `job.start` and `job.resume` require `run`, but `status` and `cancel` check only ownership.
- **Impact:**
  - A credential that has lost `run` can still cancel jobs and read their state.
  - Disabling a credential is checked in `authenticate`, but scope changes aren't enforced consistently across the job tools.
- **Fix:** require `run` (or at least `read`) on both.

### 3. Medium: `dataset.preview` skips the `run` scope
- **Where:** `service/routes.py:31-35`
- **What happens:** `preview` calls `authorize`, which requires `read`, so it is probably intended. But it is inconsistent with `job.start`, which needs `run`, and the catalog doesn't document the required scopes.
- **Impact:** `desk-view` and similar credentials can read project data without any job. Decide whether that is intended and document it.

### 4. Medium: job and membership state is unbounded and not tenant-scoped
- **Where:** `service/jobs.py:18-27`, `service/membership.py:26-33`, `service/settings.py`
- **Job records:**
  - `Jobs.records` grows forever. `result_capacity` and `retry_attempts` are validated in `Settings` but never used.
  - Job IDs are sequential (`job-N`) and global. Ownership checks stop cross-user access, but the IDs leak activity volume.
  - A `Refused('job owner')` versus `Missing('job')` response lets any caller find out which job IDs exist, including other tenants' jobs.
- **Membership:**
  - `membership.change` uses `setdefault`, so an admin can create arbitrary `(tenant, project)` entries without limit.
  - `subject` isn't checked against known identities.
  - Admin scope is limited to the admin's own tenant, which is correct.

### 5. Low: session handling
- **Where:** `service/sessions.py`, `service/host.py`
- **Session capacity:**
  - Any valid credential can open sessions up to `session_capacity` (64) with no per-credential limit. One user can fill the pool and block everyone else with `Conflict`.
  - Sessions are never refreshed or revoked on credential disable, though `resolve` does re-authenticate each time, so a disabled credential stops working.
- **Batch handling:**
  - `Host.batch` runs each packet one by one, so a batch can hit session expiry partway through and fail with an exception instead of per-item replies.
  - `Host.tools` doesn't check `closed`, unlike `open` and `invoke`.
- **Journal:** `history` requires `read`. `invoke` itself works for credentials without `read`, so those users have no way to see their own history.

### 6. Low: error and robustness details
- **`Host.invoke`:** `Packet.parse` runs outside the `try`. A malformed packet raises an exception to the caller, so it never reaches the structured error reply and is never journaled.
- **`responses.failure`:** all unexpected exceptions become `internal` with no logging. That is safe for callers but makes debugging hard.
- **`validation.name`:** `NAME.fullmatch` with `\Z` is fine. `integer` correctly rejects bools.
- **Catalog:** `config/tools.json` gives every tool an input schema of just `{"type": "object"}`, so clients get no argument names, types or required scopes. `Discovery` only checks that the names match.
- **Audit:** `Audit` records only after authentication, so failed-credential attempts are not logged.

### 7. Test coverage
- The visible tests (`tests/test_host.py`, plus `test_registry.py`, `test_jobs.py` and `test_values.py`, which I didn't open) are thin.
- There is nothing for revocation after job start (finding 1), cross-tenant isolation, or scope enforcement on `status` and `cancel`.
- The README says tests describe intended behavior but may not have been run. I couldn't run them either.

## Priorities
1. Fix finding 1, with a regression test that revokes membership mid-job.
2. Add scope checks to `status` and `cancel`.
3. Add real input schemas and required scopes to `tools.json`.
4. Bound `Jobs.records`, and make the Refused/Missing responses uniform so job IDs can't be probed.
