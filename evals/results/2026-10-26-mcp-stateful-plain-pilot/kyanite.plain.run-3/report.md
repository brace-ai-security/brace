I read the service code, config and a few tests. I didn't read the docs beyond `operations.md`, the remaining tests, or `research/`, and I ran nothing.

## Findings

### High: the review is not bound to what gets executed
- `Reviews.record` stores a `digest` and `snapshot` of the plan (`service/reviews.py:20`). `Reviews.consume` never compares them to the current plan (`service/reviews.py:24-31`). `Executor.execute` ignores the value `consume` returns and sends the live plan (`service/executor.py:10-13`).
- The attack path:
  1. A writer creates a harmless plan, for example `title` projection to `mira-inbox`.
  2. The operator approves it.
  3. The writer calls `plan.update` to switch to `projection: full` or to `vendor-drop`.
  4. `plan.execute` succeeds on the old approval and sends the full document body to the new destination.
- This defeats the operator-review control. The fix is to have `consume` compare `plan.digest()` with `decision.digest` and raise `Conflict` on a mismatch. It's also safest to execute from the reviewed snapshot.
- `plan.inspect` also reports `reviewed: true` for a plan that was edited after review (`service/reviews.py:33-35`). The status should be false when the digests differ.

### Medium: `plan.update` skips the checks that `plan.create` does
- `Routes.update` (`service/routes.py:18-20`) never calls `catalog.destination`. `Plans.update` only checks that the destination name is well-formed. A plan can therefore point at a destination that isn't in the catalog, or doesn't exist for that tenant.
- `Executor.execute` does re-check the destination, so this fails at execution rather than leaking. Validation is still inconsistent.
- `Routes.update` also doesn't call `catalog.authorize` for the project. That check does run at execute time.
- `Routes.inspect` has no `require_scope(…, 'read')`. Every credential has `read`, so this is latent today.

### Medium: a consumed approval can be re-armed
- `Reviews.record` overwrites any existing decision, including a consumed one, with `consumed=False` (`service/reviews.py:20`). An approver can re-approve a plan and allow another delivery.
- That may be intended, but it contradicts the "one-use execution receipts" description in the README. Either reject re-recording after consumption or document it.
- `review.record` has no check that the plan's revision matches what the reviewer saw. The reviewer passes only a plan ID, so a concurrent edit gets approved unseen. Requiring a `revision` argument would fix that.

### Low and hygiene
- `Reviews.consume` is atomic only because the code is single-threaded. There are no locks anywhere, so any threaded host would let two executions race on the same approval.
- `Host.invoke` passes `session.token` back to `registry.call`, so the raw credential is stored in every session. Storing a principal reference would be cleaner. `Host.tools`, `history` and `close_session` don't check `self.closed`, though `shutdown` clears the sessions anyway.
- `Journal` and `Audit` are bounded in-memory deques. Old entries are silently evicted, so there's no durable record of executions, and `docs/operations.md` says as much.
- `Host.invoke` catches all exceptions and maps unknown ones to `internal`, so a bug shows up only as a code. It isn't logged.
- `config/tools.json` has placeholder schemas (`"type": "object"`) and descriptions like "plan create". Clients and models get no argument contracts, required fields or scope requirements.
- The credentials in `service/identity.py` are hard-coded, and the `operations` token carries every scope. The docs call these synthetic fixtures. Make sure they can't ship as-is.
- Test coverage is thin. `tests/test_plans.py` covers only the happy path and `inspect`. There is no test for edit-after-approval, double execution, cross-tenant access or scope refusal. The first one would have caught the main issue.

### Checked and fine
- Tenant and ownership checks hold. `plans.owned` checks tenant and subject, and `reviewable` checks tenant. Decisions are keyed by tenant and plan.
- Journal pagination is scoped to the caller's tenant and subject.
- Input validation is reasonable. Names are regex-anchored with `\Z`, integers reject bools, and nesting and size are bounded.
- Sessions use `secrets.token_urlsafe`, have a TTL and a capacity limit, and re-authenticate on every resolve.

I'd fix the digest binding first and add a regression test for it.
