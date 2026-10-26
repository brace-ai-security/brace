I read all the service code, config, docs and tests, and found one critical flaw and several smaller ones. I didn't run any code, so these come from reading the source.

## Critical

**1. A review approval isn't tied to what was reviewed** (`reviews.py:24-31`, `executor.py:7-13`, `plans.py:60-68`)
- `Reviews.record` stores the plan's digest and a snapshot. `consume` never compares the digest or revision to the current plan, and the executor ignores the returned snapshot.
- It re-reads the live plan instead. So the owner can do this:
  1. Create a plan with `projection: title` and `destination: mira-inbox`.
  2. Get it approved by an operator.
  3. Call `plan.update` to switch to `projection: full` and `destination: vendor-drop`.
  4. Call `plan.execute`.
- The full document body then goes to a destination the reviewer never saw. This defeats the review control.
- **Fix:** in `consume`, require `decision.digest == plan.digest()`, and execute from the snapshot. Alternatively, invalidate the decision on `update`.

**2. A review can be reset, so "one-use" isn't enforced** (`reviews.py:19-22`)
- `record` unconditionally overwrites `decisions[(tenant, plan.id)]` with a fresh `consumed=False` decision.
- Anyone with `approve` can re-review a plan that has already run, and the owner can then execute it again. That gives repeated deliveries on a single approval.
- **Fix:** refuse to re-record when a decision exists and is consumed. Consider also keying decisions by revision.

## High

**3. No separation of duties** (`identity.py:11`, `routes.py:26-30`, `plans.py:52-58`)
- The `operations` principal holds `write`, `run` and `approve`. It can create, approve and execute its own plan.
- `reviewable` only checks the tenant, not that the reviewer differs from the owner.
- **Fix:** reject `reviewer.subject == plan.subject`.

**4. Approval is consumed before the work succeeds** (`executor.py:10-13`)
- `consume` runs before `catalog.read` and `delivery.send`.
- `plan.create` and `plan.update` never check that the document exists. A plan with a bad document name can be approved, and the approval is then burned on a `Missing('document')` failure.
- Any later delivery failure burns it too. Validate the document at create time, and consume only after the checks pass, or roll back on failure.

## Medium

- **`plan.inspect` has no scope check** (`routes.py:22-24`). Every other route calls `require_scope`. It's owner-scoped, so the exposure is small, but it's inconsistent.
- **`update` doesn't re-check the destination or project membership** (`plans.py:60-68`, `routes.py:18-20`). It only checks the name format. A bad destination surfaces at review or execute time instead.
- **`Host.tools` and `Host.history` don't check `closed`** (`host.py:24-26`, `50-53`). `batch` also doesn't check it up front, so it can reach `invoke` and then fail partway. After `shutdown` the session rows are cleared, so this mostly fails safe.
- **Rejected packets aren't journaled or audited.**
  - `Packet.parse` runs outside the `try` in `Host.invoke` (`host.py:32`), so malformed packets raise to the caller instead of returning a `failure` reply.
  - In `Registry.call`, authentication, unknown-tool and argument-validation failures happen before the audit `try` (`registry.py:24-29`).
  - Probing and failed auth attempts therefore leave no trace.
- **No per-principal session limit** (`sessions.py:31`). One valid credential can fill the global `session_capacity` (default 64) and block everyone else from opening sessions.
- **`batch` isn't atomic.** It runs the calls sequentially, so a caller can't tell which calls took effect if an earlier one raises. The first `resolve` also isn't repeated per call, so a session that expires mid-batch is handled per item.

## Low / hygiene

- **Everything is stored in memory with no persistence.** `docs/operations.md` states this. Plan, review and delivery state all reset on restart, so a "one-use" receipt doesn't survive a restart.
- **The credentials in `identity.py` are hard-coded.** They're documented as fixtures, but `desk-write` and `operations` are guessable. Don't ship this profile outside local use.
- **`tools.json` is thin.** Every tool has `input: {"type": "object"}` and a description like "plan create". Clients and models get no schema for required fields (`project`, `document`, `destination`, `revision`) and no hint about scopes or the review flow.
- **Dead code and weak tests.**
  - `Plans.digest()` is only stored, never used (see #1).
  - `deepcopy` is imported but unused in `plans.py`.
  - The settings fields `page_size`, `result_capacity` and `retry_attempts` look unused.
  - The tests cover only the happy path. Nothing tests update-after-review, double execute, re-review after consume, cross-tenant access or self-approval. The first two would fail today.
- **`failure` reduces errors to a bare code.** That's good for not leaking details. The catch-all `except Exception` also maps bugs to `internal` with no logging, which makes them hard to diagnose.

## What looks good

- Plans are scoped by tenant and subject.
- Sessions re-authenticate on every resolve, so a disabled credential stops working immediately.
- The name regex uses `fullmatch` with `\Z`.
- Input validation limits depth and size, and uses `type(value) is int` to reject bools.
- Journal paging is filtered by tenant and subject.

I'd fix #1 and #2 first, since together they let an approved plan be changed and run repeatedly. I can sketch the patch for `reviews.py` and `executor.py` and add regression tests if you'd like.
