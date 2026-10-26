I read the service code, configs, docs and the plan tests, and checked the logic by reading it. I didn't run anything. I didn't open `tests/test_registry.py`, `tests/test_values.py`, `tests/test_host.py`, `settings.py`, `models.py`, `clock.py`, `docs/client.md`, `docs/data.md`, `docs/maintenance.md` or `research/`.

## High

**1. A review approval isn't tied to what was reviewed, so a plan can be changed after approval.**
- `Reviews.record` stores a digest and a snapshot of the plan (`reviews.py:20`).
- `Reviews.consume` never compares either one to the current plan (`reviews.py:24-31`).
- `Executor.execute` discards the return value of `consume` and sends using the live `plan` (`executor.py:10-13`).
- `plan.update` doesn't invalidate the review (`plans.py:60`). It only bumps the revision and can change `destination` and `projection`.
- Attack path:
  1. mira creates a plan with `title` projection to `mira-inbox`.
  2. The operator approves it.
  3. mira calls `plan.update` to set `projection=full` and `destination=vendor-drop`.
  4. mira calls `plan.execute`. The full document body goes to `vendor-drop` under the old approval.
- Fix: in `consume`, reject the call if `plan.digest() != decision.digest`. Better still, execute from `decision.snapshot`, and clear the decision in `update`.

## Medium

**2. "One-use" isn't enforced reliably.**
- `consume` sets `consumed = True` before the document read and the send (`executor.py:10-13`). If either fails, for example with `Missing('document')`, the approval is burned with no delivery.
- The check and the set aren't atomic. Concurrent callers on a shared host could both pass.
- `Reviews.record` overwrites an existing decision, including a consumed one, and resets `consumed` to false. Each re-approval silently grants another delivery, with no history.
- Fix: mark the decision consumed only after the send succeeds, and take a lock around check-and-set. Refuse to overwrite a consumed decision, or keep a history of decisions.

**3. Reviewers can approve their own plans.**
- `Plans.reviewable` checks only the tenant (`plans.py:56`).
- The `operations` credential holds `write`, `run` and `approve`. The operator can create, approve and execute their own plan alone.
- Fix: refuse review when `reviewer.subject == plan.subject`, if separation of duties is intended.

**4. `plan.update` skips checks that `plan.create` does.**
- `Routes.update` doesn't check that the new destination exists in the catalog (`routes.py:18-20`).
- It also doesn't re-authorize the project. A bad destination only fails later, at review or execute.
- Fix: call `catalog.destination` on the new destination in `update`.

**5. A batch can lose replies for calls that already ran.**
- `Host.invoke` calls `sessions.resolve` and `Packet.parse` outside its `try` (`host.py:31-32`).
- If the session expires mid-batch, or one packet is malformed, the exception aborts the whole batch.
- Earlier items have already run, including possible deliveries, and the caller gets no replies for them.
- Those failures also aren't journaled.
- Fix: parse per item inside the loop, and return a per-item failure reply.

## Low

- **Plan existence leaks across tenants.**
  - `plan.inspect`, `plan.update` and `plan.execute` return `Missing` for a nonexistent plan and `Refused` for another tenant's plan.
  - Plan IDs are sequential (`plan-N`), so another tenant can enumerate them.
  - Return the same error for both cases.
- **Missing arguments surface as `internal`.**
  - `request.arguments['project']`, `['plan']` and `['revision']` raise `KeyError`, which `failure()` maps to `internal`.
  - Validate required fields and raise `Invalid`.
- **Audit gaps.**
  - `Registry.call` raises on an unknown tool or non-dict arguments before the audited `try` block (`registry.py:25-28`). No audit record is written for those calls.
  - `docs/operations.md` says outcomes are recorded after credential admission, so this contradicts it.
- **`Host` doesn't consistently honor shutdown.**
  - `tools`, `batch`, `history` and `close_session` don't check `closed`.
  - `shutdown` only clears sessions.
- **Session capacity can be exhausted by one credential.**
  - A single credential can fill all 64 sessions and block everyone else with `Conflict('session capacity')`.
  - Add a per-credential cap.
- **Tool schemas are placeholders.**
  - Every entry in `config/tools.json` is `{"type":"object"}`, with no properties, required fields or scope hints.
  - `Discovery.list_tools` returns the whole catalog to every session regardless of scope.
- **Housekeeping.**
  - Unused imports: `deepcopy` in `plans.py` and `reviews.py`, and `Plan.digest` is otherwise unused.
  - `Sessions` keeps the raw token in memory. That's acceptable here, but worth knowing.
  - `Discovery.describe` imports `Missing` inline.

## Tests
`test_plans.py` covers only the happy path and an inspect call. Nothing covers update-after-review, replay of a consumed review, cross-tenant access, self-approval or a failed execute. Add a regression test for finding 1 first.

If you want a patch, I'd start with finding 1 and the consume ordering in finding 2.
