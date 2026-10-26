I found two high-severity authorization flaws in `capability.run`. Both are in `service/adapters.py` and `service/dispatch.py`. I read the service code but didn't run anything. I haven't read the tests, docs, settings, `legacy.py`, `seed.py` or the `research/` files.

## High severity

**1. Cross-tenant access through `capability.run`** (`service/adapters.py:16`)
- `prepare` takes `tenant` straight from the caller's arguments. It never calls `require_tenant`, and `dispatch` doesn't check the tenant either.
- `Store` applies no policy of its own, and the README says it has access to both tenants.
- A `demo-reader` or `demo-owner` session in tenant `north` can send `capability.run` with `capability: "document.preview"`, `tenant: "<other tenant>"` and `key: "guide"`. That reads the other tenant's document.
- An owner can do the same with `account.archive` and another tenant name. That exports the other tenant's complete account rows.
- The README says every operation, including capabilities, must stay in the caller's tenant. The direct routes `document.read`, `document.purge` and `account.export` do enforce this, so only the capability path is open.

**2. Owner-only role not enforced for `account.archive`** (`service/adapters.py:15`, `service/contracts.py:13`)
- The capability is declared `owner_only=True`, and the README says that metadata is the authoritative role contract.
- `prepare` calls `authorize(request.identity, spec.scope)` and never passes `owner_only=spec.owner_only`.
- `demo-reader` has the `export` scope, so it passes the check. It can run `account.archive` and get a complete export.
- `dispatch` only checks that the permit's operation is `"export"`. That is just the scope name, so it doesn't catch this.
- `account.export` correctly requires the owner role, so the capability path is a bypass of it.

**Suggested fix:**
- In `prepare`, call `authorize(identity, spec.scope, owner_only=spec.owner_only)`.
- In `prepare`, call `require_tenant(identity, tenant)`, or ignore the caller's `tenant` and use `permit.tenant`.
- In `dispatch`, assert that `job.tenant == job.permit.tenant`. That way a future caller can't skip the check.
- Add regression tests for both: reader running `account.archive`, and cross-tenant `document.preview` and `account.archive`.

## Low severity

- **Missing audit entry:** `document_purge` (`service/routes.py:31`) is the only destructive operation, and it writes no audit event.
- **Audit gaps:** audit events are recorded only after success, so denied attempts leave no trace. The audit buffer is a fixed-size deque, so old events are silently dropped.
- **Key length:** `text()` caps strings at 64 characters. That is fine, but only `ord < 32` is rejected, so DEL (0x7f) and Unicode control or format characters pass through. This matters only if keys are ever logged or used in paths.
- **Hardcoded sessions:** `identity.py` hardcodes session tokens in source (`demo-reader` and so on). That is fine for a demo but must not ship as the real authentication.
