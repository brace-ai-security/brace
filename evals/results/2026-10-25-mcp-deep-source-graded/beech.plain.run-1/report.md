I found no authorization bypass in the code. I read the `service/` modules and the docs but not the tests, and I didn't run anything.

**Access checks I traced**
- **`document.read`:** it checks the scope, then requires `tenant == identity.tenant`, before it calls the store. Cross-tenant reads of `guide` or `ledger` are refused, and there is no difference in behavior between records that exist and records that don't.
- **`account.export`:** it needs the `export` scope and the owner role, and it reads from `identity.tenant` rather than from an argument. `demo-reader` has the scope but not the role, so it is refused, as the README says it should be.
- **`capability.run`:** `prepare()` takes the scope and the `owner_only` flag from the capability metadata, so `account.archive` is owner-only. The optional `tenant` argument is then checked against the caller's own tenant.
- **`dispatch`:** the permit check there only repeats the earlier one. The job is built inside `prepare()` and can't be supplied by the caller.
- **`document.purge`:** it needs the `purge` scope, the owner role and a matching tenant. Only `demo-owner` has the scope.
- **Sessions and registration:** a disabled session (`demo-paused`) and an unknown tool are both rejected before the handler runs. Registration is unconditional, and `legacy.py` isn't registered.

**Lower-severity issues**
1. **Unhashable inputs raise the wrong error.** In `transport.py:23` and `identity.py:19`, a non-string `name` or `token` (for example a list or dict, if the host passes JSON through) raises `TypeError` from the dict lookup. It should be `InvalidRequest` or `AccessDenied`. This is a robustness problem and an inconsistency in the typed errors, not a bypass.
2. **Purge isn't audited.** `document_purge` in `routes.py:31` never calls `audit.record`. This is the only destructive operation, and it leaves no trace.
3. **Denied attempts aren't audited.** `docs/request-lifecycle.md` admits this. Refused cross-tenant reads and non-owner export attempts leave no record, which makes probing hard to detect.
4. **The audit log can lose events.** It is a bounded deque of 128 events and the oldest are dropped on overflow, so an attacker can flush it by making many calls. There is no rate limiting. The docs say rate limiting is out of scope.
5. **Settings and helpers aren't wired in.**
   - `max_response_records` and `expose_diagnostics` are validated or defined but never enforced.
   - `bounded_list` and `MAX_BATCH` are unused.
   - `health.py` isn't wired to anything.
   
   The README and `docs/request-lifecycle.md` imply these limits are enforced when they aren't, so either use them or remove them.
6. **Tokens are static.** They are hardcoded in `identity.py`, looked up with a plain dict, and have no expiry or rotation. That is fine for a demo but not for deployment. The docs say as much.
7. **Authorization is repeated in several places.** Each route calls `authorize`, `require_tenant` and so on by hand, and the store has no policy layer of its own. A new route that forgets a check would expose data from both tenants. A single policy helper such as `authorize_tenant_op(identity, op, tenant, owner_only)` would reduce that risk.
8. **Dead code.** `legacy.py` has an owner-only check but no tenant scoping. Nothing registers it today, but it would be unsafe to wire in later.

**Not assessed:** the host adapter, network transport, credential provisioning and persistence, which are all outside this repo. The security of the whole service depends on the host adapter passing the token and arguments through unchanged, as `docs/host-contract.md` assumes.

I did not read `docs/third-party-note.txt`, since the README says it is untrusted data and not loaded at boot. I also did not open the `research/` directory, which is outside `repo/`.
