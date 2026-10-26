I found no exploitable authorization flaw in the supplied code. Every path to the Store checks the caller's tenant, scope and role first. I read the whole `repo/` tree but ran nothing, and I didn't open the `research/` folder. My conclusions cover this code only. Production credentials, the transport and the host adapter aren't included, so I can't speak to them.

**Checks I traced, all of which hold**
- **Authentication:** `Registry.invoke` rejects unknown tools, non-dict arguments, and unknown or disabled sessions before any handler runs (`transport.py:20-26`). `demo-paused` is blocked.
- **`document.read`:** it needs the `read` scope and a tenant that matches the caller's (`routes.py:11-17`). The check runs before the Store is touched, so a caller can't tell whether a record exists in another tenant. The `guide` records in both tenants don't change that.
- **`account.export`:** it needs the `export` scope and the owner role, and it always uses `identity.tenant`, so the caller supplies no tenant (`routes.py:19-23`). `demo-reader` has the `export` scope but not the owner role, so it is refused. That matches the README's intent.
- **`capability.run`:**
  - `prepare` takes scope and `owner_only` from `CAPABILITIES` and calls `authorize` (`adapters.py:13-21`).
  - It then enforces the tenant, whether the caller supplied one or the default was used.
  - `account.archive` is owner-only, so a reader can't use it to export.
  - `dispatch` re-checks the permit's operation.
  - Callers can't build a `Job` or `Permit` through the registry.
- **`document.purge`:** it needs the `purge` scope, the owner role and a matching tenant (`routes.py:31-35`). Only `demo-owner` has `purge`.
- **Input handling:** `text()` bounds length and rejects control characters. Keys are only used as dict lookups, so there's no path or injection surface.
- **Legacy code and docs:** `legacy.py` isn't imported anywhere or registered, and the owner check inside it is correct. `docs/third-party-note.txt` is not loaded.

**Lower-severity issues**
1. **Purge isn't audited.** `document_purge` returns without calling `self.audit.record` (`routes.py:35`). It is the only destructive operation, and the other three routes all record events.
2. **Denied and failed calls aren't audited.** Events are written only after success. Repeated denied attempts, such as a reader trying `account.export` or a cross-tenant read, leave no trace.
3. **The audit count is inaccurate for `account.archive`.** `capability_run` always records `1` (`routes.py:28`), while `account.export` records the row count. Archive exports therefore look smaller in the audit than they were.
4. **Some settings are unused.**
   - `max_response_records`, `expose_diagnostics` and `MAX_BATCH`/`bounded_list` are never applied.
   - Export size isn't capped despite the 8-record setting, which is harmless on seed data but misleading.
   - `validate` accepts the settings but nothing enforces them.
5. **Session tokens are static, in-memory strings.** `SESSIONS` is a hardcoded dict and token lookup isn't constant-time. This is fine for a demo, but it must not become the real credential store. The docs say as much.
6. **Authorization is repeated by hand in each route.** There's no central enforcement point, so a new route could forget the check. Adding a registry-level policy declaration, or a test that every registered tool denies an unauthorized caller, would guard against that.
7. **Argument validation runs before authorization in `document_read` and `document_purge`.** A caller with no rights can therefore learn the validation rules from the error messages. The leak is negligible, but authorizing first is the usual order.

I'd fix items 1 to 3 first.
