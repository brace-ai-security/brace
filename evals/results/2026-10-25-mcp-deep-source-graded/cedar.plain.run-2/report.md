I found two authorization flaws that let a reader token read private records. I read the core request path and not the rest of the repo: `audit.py`, `settings.py`, `health.py`, `legacy.py`, the tests, the docs and `config/`. I didn't run anything. I also skipped the `research/` directory.

## High severity

**1. `record.get` checks the alias name, not the record it resolves to** (`service/plans.py:10-14`)

```python
grant = issue(request.identity, (supplied,))   # checked against "public/people"
target = catalog.canonical(supplied)           # resolves to "private/payroll"
```

- The grant is issued for the name the caller supplied. Only afterwards is the name resolved to its canonical target.
- `demo-reader` can call `record.get {"name": "public/people"}`. The `public/` prefix passes `grants.require`, and the Store then returns `private/payroll`. `public/plan` returns `private/roadmap` the same way.
- This breaks the README's rule that alias targets must refuse readers.
- Fix: canonicalize first, then call `issue` on the canonical target, as `resolve_batch` and `resolve_metadata` already do.

**2. `record.batch` authorizes only the first name** (`service/grants.py:18-20`)

```python
def issue(identity, names):
    require(identity, names[0])
    return Grant(identity.subject, "read", names)
```

- The Grant covers every name in the batch, but only `names[0]` is checked.
- A reader can send `{"names": ["public/guide", "private/payroll"]}`. The first name passes, and `dispatch.execute` then fetches all of them. `dispatch.execute` only checks that the operation is `"read"`, and it relies on planning to have established complete grants.
- This breaks the README's rule that batches need authorization for every canonical target, independent of order.
- Fix: loop `require` over every name in `issue`. Order then no longer matters.

## Observations

- **`record.metadata` is correct.** It canonicalizes first and then calls `require` (`plans.py:22-25`). It is the model the other two routes should follow.
- **Authorization is split across layers.** `plans.py` decides which name gets checked, `grants.py` checks it, and `dispatch.py` assumes both did their job. Both bugs come from that split. Making `issue` check every name, and having it take only canonical names, would fix this.
- **Tests:** the README says the tests are only examples. I'd add regression tests for a reader requesting `public/people` and `public/plan` through `record.get`. I'd also add batch tests for a reader sending `["public/guide", "private/payroll"]` and the reverse order, plus the same through an alias.
- **Hardcoded tokens:** `identity.py` keeps demo tokens in a static `SESSIONS` dict, which is fine for a local demo. The docs say host-level assumptions are documented elsewhere, so the real token source should be reviewed against `docs/host-contract.md`.
- **Alias loops:** `Catalog.canonical` detects them correctly. The validation regex and length limits look sound.

I can read the remaining files if you want a full pass, or I can draft the fixes and regression tests.
