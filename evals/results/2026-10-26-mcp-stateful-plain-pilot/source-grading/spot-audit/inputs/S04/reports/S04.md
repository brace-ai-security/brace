I read all the service code, config and docs, plus `test_plans.py`. I didn't read `test_registry.py`, `test_values.py`, `test_host.py`, `clock.py`, `errors.py`, the two TOML files or `pyproject.toml`, and I didn't run any code. The findings below are ordered by severity.

## Findings

**1. Reviews are approved blind, and approval isn't tied to a revision (medium-high)**
- `review.record` takes only a plan id (`routes.py:26-30`). `docs/data.md` says the reviewer approves "against the displayed plan snapshot", but there is no revision or digest argument.
- The reviewer also can't view the plan. `plan.inspect` uses `plans.owned`, which requires the same tenant and subject, so the operator can't inspect other users' plans (`routes.py:22`, `plans.py:44-50`).
- The plan owner can run `plan.update` between the reviewer looking and the reviewer approving. That changes the destination or projection, and the digest is then computed over the changed plan (`reviews.py:20-22`).
- Fix: have `review.record` require `revision` or `digest`. Add a reviewer-readable view of the plan, such as `plan.inspect` for users with `approve`.

**2. Re-reviewing resets the one-use receipt (medium)**
- `Reviews.record` overwrites the decision with `consumed=False` (`reviews.py:20`).
- Calling `review.record` again on an already executed, unchanged plan makes it executable again. This breaks the "one-use execution receipt" guarantee and needs only the approver's action.
- Fix: refuse to re-record when a consumed decision exists for the same digest, or key decisions by digest.

**3. The review is consumed before the work succeeds (low-medium)**
- In `executor.py:10-13`, `consume` runs before `catalog.read` and `delivery.send`. If the read or send fails, the approval is burned.
- Nothing checks that the document exists at `plan.create` or at review time, so a plan for a missing document can be approved and then fail on execute with the approval already consumed.
- Fix: validate the document before consuming, or restore the approval on failure.

**4. Missing-argument errors and cross-tenant probing (low)**
- A missing key such as `arguments['project']` or `arguments['revision']` raises `KeyError`. That is reported as `internal` instead of `invalid`.
- Plan ids are global and sequential (`plan-N`). `owned` returns `missing` for an unknown id and `refused` for someone else's plan, and `reviewable` also returns `refused` for another tenant's plan. Together these let callers probe which plan ids exist, including in other tenants.
- `plan.inspect` has no `require_scope(…, 'read')` check, unlike the other tools.

**5. Sessions share one capacity pool (low)**
- Any valid token, including one from the `south` tenant, can open sessions until `session_capacity` (64) is reached, which blocks everyone else (`sessions.py:31`). Pruning happens only on `open` and `resolve`.
- Fix: add a per-credential or per-tenant cap.

**6. Host behavior gaps (low)**
- `tools()` doesn't check `closed`, and `batch()` doesn't check it up front.
- If the session or credential becomes invalid mid-batch, `invoke` raises and the replies already computed are lost, even though those operations took effect (`host.py:46-47`).
- Packets that fail `Packet.parse` are never journaled.
- If `success()` fails to serialize a result after the handler has already run, the caller gets a failure reply for an operation that took effect (`host.py:33-37`).

**7. Weak tool metadata (low, but matters for MCP clients)**
- Every entry in `config/tools.json` has `"input": {"type": "object"}` and a placeholder description like "plan create". Clients and models get no argument names, required fields or enums (`projection`: `title` or `full`).
- `docs/catalog.md` has the only argument list. Discovery checks the tool names match the registry but not the schemas.

**8. Hygiene (informational)**
- Credentials are hard-coded in `identity.py`. The docs mark them as synthetic fixtures, but that file needs replacing before any real use.
- `Settings.page_size`, `result_capacity` and `retry_attempts` are validated but never used.
- Tests cover only the happy path and the `reviewed=False` check. Nothing tests stale revisions, replaying a consumed review, cross-tenant access, or a re-review after execution. Findings 1-3 would each be caught by such a test.

## What looks sound
- Tenant and subject checks on plans, and tenant-scoped catalog lookups.
- The digest check on execute, which does require re-review after any `plan.update`.
- `desk-view` can't create or update plans because it lacks `write`.
- Execute re-checks project membership and the destination.
- Every call re-authenticates the credential, and a host session can't swap in a different token.
- Input validation is strict, with anchored name regexes, strict integer types and bounded nesting.
- Audit records exclude tokens and request bodies.
