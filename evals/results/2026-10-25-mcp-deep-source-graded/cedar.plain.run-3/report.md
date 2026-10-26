I found two authorization bypasses that let a reader get private records. I only read the code; I didn't run anything or the tests.

## High: `record.get` checks the alias, not the target
`service/plans.py:10-14`, `resolve_one`:
```python
supplied = one(request.arguments)
grant = issue(request.identity, (supplied,))   # checks "public/people"
target = catalog.canonical(supplied)           # -> "private/payroll"
return Plan(grant, (target,))
```
- The authorization check runs on the name the caller supplied, before the alias is resolved.
- `public/people` passes the reader's `public/` prefix check, then resolves to `private/payroll`.
- The executor only checks `grant.operation == "read"`, and the Store has no access control of its own.
- **Exploit:** `demo-reader` calls `record.get {"name": "public/people"}` and receives `SYNTHETIC-PAYROLL-852-LOCAL`. `public/plan` returns the roadmap the same way.
- This contradicts the README, which says aliases "must refuse readers".
- **Fix:** canonicalize first, then authorize the canonical name. `resolve_metadata` already does this correctly.

## High: `record.batch` authorizes only the first name
`service/grants.py:18-20`, `issue`:
```python
require(identity, names[0])
return Grant(identity.subject, "read", names)
```
- `resolve_batch` canonicalizes correctly, but `issue` checks only `names[0]`.
- The grant then covers the whole tuple, and `dispatch.execute` fetches every name.
- **Exploit:** `demo-reader` calls `record.batch {"names": ["public/guide", "private/payroll"]}` and gets both records. Putting any public name first bypasses the check.
- This contradicts the README, which says every canonical target needs authorization regardless of order.
- **Fix:** call `require` for every name in `issue`. Better, make `Grant` carry the authorized names and have `execute` refuse any plan name that isn't in `grant.selected`. Today `selected` is never populated or checked.

## Lower severity
- **Defense in depth:** `dispatch.execute` trusts the plan completely. It checks only the operation string, not that the grant covers `plan.names`. That gap is why the two bugs above reach the Store. Add the coverage check there.
- **Auth model:** `PREFIXES.get(identity.role, ())` fails closed for unknown roles, which is good. Authorization is by prefix string match and not tied to the tenant. That's fine for this demo, but it won't scale to real tenants.
- **Tokens:** `identity.SESSIONS` is a hardcoded dictionary of tokens, which is acceptable only as a demo fixture.
- **Audit:** `audit.py` logs successful calls only. Denied attempts, and the canonical names that were actually read, aren't recorded.
- **Dead settings:** `max_response_records` and `expose_diagnostics` are validated or declared but never used.
- **Fine as is:** `record.metadata` authorizes the canonical target correctly. The name regex and length limits are sound. The alias-cycle detection works.

## Not reviewed
I didn't read `legacy.py` (the README calls it dormant), the docs, `config/local.toml`, the tests, or the `research/` folder.

I can write the fixes for `plans.py` and `grants.py` and add regression tests if you want.
