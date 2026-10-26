I found two authorization flaws in `capability.run`, both in `prepare()`. I read the code but didn't run anything.

## High severity

**1. Cross-tenant access through `capability.run`** (`service/adapters.py:13-20`)
- `prepare()` takes `tenant` from the caller's arguments. It never compares it with `permit.tenant`, and nothing downstream does either. `dispatch()` only checks the permit's operation name, and `Store` applies no policy, as the README says.
- Any reader can send `{"capability":"document.preview","tenant":"<other tenant>","key":"guide"}` and get another tenant's document body. `document.read` blocks this with `require_tenant`.
- Any caller with the `export` scope can send `{"capability":"account.archive","tenant":"<other tenant>"}` and get that tenant's full account rows. `account.export` pins the tenant to `request.identity.tenant`.
- This breaks the README rule that every operation, including capabilities, must stay inside the caller's tenant.

**2. Owner-only check skipped for `account.archive`** (`service/adapters.py:15`, `service/contracts.py:13`)
- The capability is declared `owner_only=True`, but `prepare()` calls `authorize(identity, spec.scope)` without `owner_only=spec.owner_only`.
- `demo-reader` has the `export` scope, so it can run `account.archive` and export its whole tenant. The dedicated `account.export` route correctly refuses it. The README says owners alone may export.
- Combined with finding 1, a reader can export any tenant's account rows.

**Suggested fix:** in `prepare()`, call `authorize(request.identity, spec.scope, owner_only=spec.owner_only)`. Then call `require_tenant(request.identity, tenant)`, or drop the `tenant` argument and always use `permit.tenant`. Add regression tests in `tests/test_routes.py`: reader running `account.archive`, and cross-tenant `preview` and `archive`. I didn't read the existing tests, so I don't know what they cover.

## Lower severity and notes

- **Audit gap:** `document_purge` records no audit event, although it is the most destructive operation (`service/routes.py:31-35`). Denied attempts aren't audited anywhere.
- **Audit records the wrong tenant:** events hold only the subject, action and count, not the target tenant. The cross-tenant access above would not show up in the audit log.
- **Hardcoded session tokens:** `SESSIONS` in `service/identity.py` holds static demo tokens (`demo-owner` and so on) that grant real roles. This is fine for a local demo, but make sure it can't ship as the production auth path.
- **Token comparison:** `authenticate` uses a plain dict lookup, which is acceptable here. It has no rate limiting or expiry.
- **Unchecked arguments:** `limits.bounded_list` and `MAX_BATCH` appear unused, and the legacy manifest helpers are dormant. Neither is a vulnerability today. If someone registers the legacy helpers later, `require_operator` checks only the role, not the tenant.

I didn't open `research/`, since it looks like prior review output. I also skipped `settings.py`, `health.py`, the docs and the tests, so this isn't a full review of the service.
