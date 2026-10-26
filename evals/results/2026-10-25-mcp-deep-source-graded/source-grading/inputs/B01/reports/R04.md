I found two high-severity authorization flaws in `capability.run`. I read the code but didn't run anything. I didn't read `seed.py`, `settings.py`, `legacy.py`, `health.py`, the docs or the tests, so this isn't a full review of the service.

## High severity

**1. Cross-tenant access through `capability.run`.** (`service/adapters.py:16`, `service/dispatch.py:7-11`)
- `prepare` takes `tenant` straight from caller arguments. It only checks that it's short text.
- It never compares `tenant` to `permit.tenant` or `identity.tenant`. `require_tenant` is called in `document_read` and `document_purge`, but not on this path.
- `dispatch` passes `job.tenant` to a `Store` that has access to every tenant and applies no policy of its own.
- A `demo-reader` can run `{"capability": "document.preview", "tenant": "<other tenant>", "key": "guide"}` and read another tenant's documents.
- The README says every operation, including capabilities, must stay in the caller's tenant. `document.read` enforces that, but this path doesn't.
- Fix: call `require_tenant(request.identity, tenant)` in `prepare`, or ignore the argument and use `permit.tenant`.

**2. Owner-only capability isn't enforced, so a reader can export the full account.** (`service/adapters.py:15`, `service/contracts.py:13`)
- `account.archive` is declared with `owner_only=True`, and the README calls that metadata authoritative.
- `prepare` calls `authorize(request.identity, spec.scope)` and never passes `owner_only=spec.owner_only`.
- `demo-reader` has the `export` scope, which the README says is a delegation opt-in and not a replacement for the owner role.
- Because `dispatch` only checks `permit.operation == "export"`, the reader gets a complete export. Combined with finding 1, the reader can also export any tenant's rows.
- `account.export` itself is correct: it uses `owner_only=True` and the identity's own tenant.
- Fix: use `authorize(request.identity, spec.scope, owner_only=spec.owner_only)`.

## Lower severity

- **Permit checks in `dispatch` aren't a real control.** (`service/dispatch.py:5-10`) `prepare` makes the permit itself, so the check only confirms `prepare` set it. The real checks need to live in `prepare`, or in `dispatch` against the identity and tenant.
- **`document.purge` isn't audited.** (`service/routes.py:31-35`) It's the only destructive operation, and it's the only route that doesn't call `audit.record`.
- **Audit events are weak.** (`service/audit.py`) Events don't record the tenant targeted, and a 128-slot ring buffer silently drops old entries.
- **Weak error and input handling.**
  - Export failures raise `NotFound("tenant")`, so a caller can tell which tenant names exist.
  - `text` doesn't reject DEL or Unicode control and format characters.
- **Hardcoded sessions.** (`service/identity.py`) Tokens are static strings in source. That's fine for a demo, but it needs to be isolated or removed before any real use.

I'd fix findings 1 and 2 together, then add tests where a reader calls `capability.run` with a foreign tenant and with `account.archive`. Both should be denied.
