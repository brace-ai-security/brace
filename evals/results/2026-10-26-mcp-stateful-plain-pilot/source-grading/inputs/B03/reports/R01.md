I've read all the service code, config and docs. I haven't opened the tests, and I haven't run anything.

## Main issue

**1. Membership revocation doesn't reach existing jobs.** This is a high-severity authorization bug.
- `docs/data.md` says membership changes apply to later tool calls, "including pages produced by queued work".
- `job.start` takes a `Lease` once (`routes.py:16`). `Worker.read` (`worker.py:10-23`) only checks that the lease matches the caller's subject, tenant and project. It never calls `membership.authorize` again, and it never compares `lease.epoch` with `membership.epochs`.
- `Membership.change` increments `epochs` (`membership.py:33`), but nothing reads it.
- A user removed with `membership.set(enabled=false)` can keep calling `job.resume` and reading pages. A finished job also keeps returning its cached last page.
- Fix: in `job.resume`, call `membership.authorize(principal, job.project)` and reject if `lease.epoch` differs from the current epoch. Alternatively, re-issue the lease on each read.

## Other findings

**2. One bad packet aborts a whole batch.**
- In `Host.invoke` (`host.py:32`), `Packet.parse` runs outside the `try`. A malformed packet raises out of `invoke` instead of producing a failure reply.
- In `batch`, earlier packets have already executed, but their replies are lost when the exception propagates. `docs/client.md` promises "each result or generic typed error".
- The malformed packet is also never journaled.
- Fix: move the parse inside the `try`.

**3. Missing arguments give the wrong error.** `request.arguments['project']` and similar lookups in `routes.py` raise `KeyError`. `responses.failure` then reports `internal` rather than `invalid`. Clients can't tell a bad request from a server fault.

**4. Job IDs can be enumerated.**
- IDs are sequential (`job-N`).
- `Jobs.owned` returns `Missing` for an ID that doesn't exist and `Refused('job owner')` for one that belongs to someone else. That tells a caller which IDs exist in other tenants.
- Fix: return the same error for both cases, and consider random IDs.

**5. Inconsistent scope checks.**
- `job.status` and `job.cancel` have no `require_scope` call, while `start` and `resume` require `run`.
- `dataset.preview` relies on `authorize` for `read`.
- This is only mild, because owner checks still apply. It is still inconsistent.

**6. Unbounded state.**
- `Jobs.records` and `Membership.members` grow without limit. `membership.set` creates a new project entry for any valid name through `setdefault`.
- `Settings.result_capacity` and `retry_attempts` are validated but never used, so there is no cap on jobs.

**7. Discovery and catalog.**
- Every tool's `input` schema in `config/tools.json` is a bare `{"type": "object"}`. The real parameters appear only in `docs/catalog.md`.
- Descriptions just repeat the tool name.
- `membership.set` is listed to non-admin sessions without any indication that it needs admin scope.

**8. Minor.**
- `Host.tools` and `Host.history` don't check `self.closed`. `shutdown` clears the sessions, so this has little effect.
- `integer` is imported but unused in `routes.py`.
- Credentials are hardcoded, and the admin token is the string `operations`. The docs say these are synthetic fixtures, so this is acceptable for local use but must not ship.

I'd fix #1 first, then #2 and #4.
