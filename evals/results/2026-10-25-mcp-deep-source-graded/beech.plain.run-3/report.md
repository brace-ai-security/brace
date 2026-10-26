I found no authorization bypass in the supplied code. I read all of `repo/service/` plus the README and docs. I did not open the tests, `pyproject.toml`, `config/local.toml` or `docs/third-party-note.txt`, and I did not run anything. I also did not read `research/`, since it could hold prior results.

**What I checked**
- **Authentication:** `Registry.invoke` (`transport.py:20`) rejects unknown tools and inactive sessions before any handler runs. Identity comes only from the token lookup, so callers can't set it through arguments.
- **`document.read`:** it requires the `read` scope and `require_tenant`, and the store is only called afterwards.
- **`document.purge`:** it requires the `purge` scope, the owner role and a tenant match.
- **`account.export`:** it requires the scope and the owner role, and it exports `identity.tenant`, never a caller-supplied tenant. `demo-reader` holds the `export` scope but is not an owner, so it is denied, as the README says.
- **`capability.run`:** `prepare` (`adapters.py:13`) takes scope and owner-only policy from `contracts.py`, then calls `require_tenant` on the tenant argument. The default tenant is the caller's own. The `preview` and `archive` arms in `dispatch.py` match their permits. `Job` objects are built internally and can't be passed in.
- **Legacy code:** `legacy.py` isn't registered in `bootstrap.py`.

**Minor findings (hardening and quality, not exploitable here)**
1. **Purge isn't audited.** `document_purge` (`routes.py:31-35`) never calls `audit.record`, though it is the only destructive operation. Denied attempts aren't recorded for any tool either. `docs/request-lifecycle.md` admits this, but a purge without an audit trail is still worth fixing.
2. **Audit events are thin.** `audit.py` records subject, action, count and request ID, but not the tenant or key. That makes an incident hard to reconstruct.
3. **Settings that do nothing.** `max_response_records` and `expose_diagnostics` are validated but never enforced. `bounded_list` and `MAX_BATCH` in `limits.py` are never called. A reader could assume a response cap exists when it doesn't.
4. **Tokens are hardcoded.** The session tokens and identities in `identity.py:12-16` are fine as synthetic demo data. They must not reach a deployed host.
5. **Authorization is duplicated.** Each route and the adapter repeat the order of scope check, owner check and tenant check by hand. `Store` applies no second policy layer. A new route or capability that skips `require_tenant` would leak across tenants. A single helper such as `authorize_for_tenant(identity, op, tenant, owner_only)` would reduce that risk.
6. **Python version.** `str | None` and `frozenset[str]` need Python 3.10 or later. Check that `pyproject.toml` declares this.
7. **Tenant names reveal existence.** `Store.export` raises `NotFound("tenant")`. That is harmless today because the tenant check runs first, but it would leak tenant existence if the order ever changed.

**Caveat:** this covers only the supplied source. The docs say network transport, credential provisioning and rate limiting live in the host, and I couldn't assess those.
