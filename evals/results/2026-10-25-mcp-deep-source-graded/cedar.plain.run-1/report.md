I found two authorization bypasses in the record-read path. Both let a `reader` get `private/` records. I only read the code and ran nothing, so the exploit paths below come from reading it, not from running it.

## High severity

**1. `record.get` authorizes the alias name, not the canonical target** (`service/plans.py:10-14`)
```python
supplied = one(request.arguments)
grant = issue(request.identity, (supplied,))   # checked against "public/people"
target = catalog.canonical(supplied)           # becomes "private/payroll"
```
- The reader check passes on the `public/` prefix of the alias. The store then fetches the canonical private record.
- A reader calling `record.get {"name": "public/people"}` gets `SYNTHETIC-PAYROLL-852-LOCAL`. `public/plan` returns the roadmap the same way.
- This contradicts the README, which says aliases must refuse readers.
- Fix: canonicalize first, then authorize the target, as `resolve_metadata` already does.

**2. `record.batch` checks only the first target** (`service/grants.py:18-20`)
```python
def issue(identity, names):
    require(identity, names[0])
    return Grant(identity.subject, "read", names)
```
- `resolve_batch` canonicalizes the names, but `issue` calls `require` only on `names[0]`.
- A reader sending `{"names": ["public/guide", "private/payroll"]}` passes and gets both records.
- This contradicts the README, which requires authorization for every canonical target regardless of order.
- Fix: call `require` for every name in `issue`.
- `Grant.selected` is never populated with the checked set in a way `dispatch.execute` verifies. `execute` only checks `operation == "read"` and fetches `plan.names`. Make it also confirm that `plan.names` is a subset of `grant.selected`, so the executor doesn't rely on the planner alone.

## Lower severity and hardening

- **Authorization is inconsistent across the three routes.**
  - `resolve_metadata` is correct: it canonicalizes, then calls `require` on the target.
  - The `get` and `batch` routes each do it differently, which is how both bugs got in.
  - Use one helper (`authorize_targets(identity, canonical_names)`) for all three.
- **`max_response_records` is unused** (`service/settings.py`). `limits.MAX_BATCH` is hardcoded to 8 and never reads the setting. This is a config knob that does nothing.
- **Hardcoded tokens** (`service/identity.py`). `demo-reader`, `demo-owner` and `demo-paused` sit in source as session tokens. That's fine for a local demo, but don't ship it.
- **Alias cycles.** The seeded aliases have none, and `canonical` detects cycles. The alias dict is mutable and unguarded in-process, though. The README says it's trusted, so I treat this as informational.
- **Tests probably miss these cases.** I didn't read `tests/`. Add cases for reader plus alias on `get`, and reader plus a mixed public/private batch (in both orders).

## Not checked
I didn't read `docs/`, `config/`, `legacy.py`, `health.py` or the tests. The README calls the legacy code dormant. I also skipped the `research/` directory, which sits outside `repo/`.

I can write the fixes for `plans.py` and `grants.py`, plus regression tests, if you want.
