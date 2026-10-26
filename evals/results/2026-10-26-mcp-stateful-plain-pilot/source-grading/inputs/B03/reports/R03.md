I read the core service code but not everything. I skipped `launch.py`, `host_settings.py`, `clock.py`, `models.py`, `errors.py`, the tests, the docs, `config/*.toml` and `research/`. I ran nothing, so these findings come from reading the code only.

## Security / correctness

1. **Revoking a membership doesn't stop jobs that already exist (high).**
   - `Membership.change` bumps `epochs[key]` on every change, and `Lease` records the epoch.
   - Nothing ever compares the epoch. `Worker.read` (`worker.py:10-23`) only checks that the lease matches the subject, tenant and project, and `Worker` holds `membership` without using it.
   - A user who started a job and was then removed with `membership.set enabled=false` can keep calling `job.resume` and reading the project's rows.
   - Fix: in `Worker.read`, re-authorize against current membership and require `lease.epoch == membership.epochs.get((tenant, project), 0)`.

2. **`job.status` and `job.cancel` have no scope check (medium).**
   - `routes.py:25-29` skips `require_scope`, while `start` and `resume` require `run`.
   - `cancel` changes state, so it should require `run`, or `write`, like the other job mutations. `status` should at least require `read`.
   - All the current fixture credentials hold these scopes, so nothing breaks today. Any lower-privilege credential would be able to cancel jobs.

3. **Job ownership errors reveal which job IDs exist.**
   - `Jobs.owned` raises `Missing` for an unknown ID and `Refused` for someone else's job, so a caller can tell the two apart.
   - IDs are sequential (`job-N`), so other tenants' activity is easy to enumerate.
   - Return the same error for both cases, and consider random IDs.

4. **Hard-coded bearer tokens in source (`identity.py:6-12`).**
   - Tokens like `operations`, which holds `admin` and `approve`, are the literal credential strings.
   - The README calls them local fixtures, but nothing stops them loading in a non-local profile.
   - `Settings.validate` does restrict the profile to `local`, which limits the risk.
   - Sessions also store the raw token (`sessions.py:34`). Store the credential ID and look the principal up on each call instead.

## Robustness / design

5. **`Host.batch` is not atomic and loses replies.**
   - `Packet.parse` runs outside the `try` in `Host.invoke`. A malformed packet in the middle of a batch raises and aborts the whole call.
   - Earlier packets have already executed, so their side effects stand but their replies are lost.
   - Parse failures are also not journaled, and they surface as exceptions rather than the `failure` reply shape.
   - Fix: parse inside the `try`, or in `batch`, turn each packet's error into a failure reply.

6. **Unbounded growth and unused limits.**
   - `Jobs.records` and the membership tables never evict anything and have no per-subject cap.
   - `Settings.result_capacity` and `retry_attempts` are defined and validated but never used.
   - Sessions have a global capacity (`Conflict('session capacity')`) but no per-subject limit, so one credential can fill every slot and lock out everyone else.

7. **Authentication failures aren't audited.** `Registry.call` authenticates before anything is recorded, and `Host.open` doesn't record failures either. Failed logins and bad tokens leave no trace.

8. **Tool catalog is nearly empty (`config/tools.json`).** Every tool has `"input": {"type": "object"}` and a description that just repeats its name, such as "job start". Clients get no parameter names (`project`, `job`, `subject`, `enabled`), so a model can't tell how to call the tools. Add real JSON schemas with `required` fields.

9. **Minor.**
   - `Host.tools` doesn't check `closed`, though it fails anyway once shutdown clears the sessions.
   - `Host.invoke` checks no scope itself and relies on every handler to do it, which is how items 1 and 2 happened. A per-tool required-scope table enforced in `Registry.call` would be safer.
   - `dataset.preview` ignores `cursor` and always returns the first page.
   - `cancel` on an already-cancelled job succeeds without complaint. This is harmless but inconsistent with the `Conflict('completed')` path.

## What looks good
- Input validation is strict: `bool` is rejected where an `int` is expected, names are regex-anchored, and nesting, size and key limits apply.
- Responses expose only generic error codes, with no internal detail.
- Tenant and subject scoping in `Journal.page` and `Jobs.owned` is correct.
- Session expiry and credential-disable checks run on every resolve.

The first thing to fix is item 1, since it's an authorization bypass. I can sketch the patch for items 1, 2 and 5 if you'd like.
