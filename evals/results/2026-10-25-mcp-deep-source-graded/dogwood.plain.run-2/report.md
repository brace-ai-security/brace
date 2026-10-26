I found no exploitable authorization flaw in the default build. I read the code in `repo/` only. I did not read `research/`, the tests or the third-party note, and I did not run anything.

**Authorization checks out**
- `Registry.invoke` authenticates before any handler runs (`transport.py:25`).
- `get`, `batch` and `metadata` all resolve aliases to the canonical target first (`plans.py:12`, `:18`, `:23`). They check the role prefix and the `read` scope only after that.
- So `public/people` and `public/plan` resolve to `private/payroll` and `private/roadmap`. Owners get them and readers get `AccessDenied`.
- `issue()` checks every name in a batch, so order doesn't matter (`grants.py:19`).
- The name regex is anchored with `fullmatch` and `\Z`, and `text()` rejects control characters. I found no way to get a name past the prefix check that the Store would still resolve.
- Reader and owner can't switch roles. Identity comes from the server-side session table, and `Identity` is a frozen dataclass.
- `legacy.py` isn't registered by `bootstrap.build`, so it isn't reachable.

**Weaknesses and latent risks**
1. **Dispatch doesn't use the grant (`dispatch.py:3-6`).** `execute` checks only `grant.operation == "read"`, then fetches `plan.names`. It never checks that those names match `grant.selected`. This is safe today because `plans.py` builds both from the same `targets`. A future route that builds a `Plan` differently would get no protection from dispatch. Cheap fix: fetch `plan.grant.selected`, or assert the two are equal.
2. **Metadata skips the grant and dispatch path (`routes.py:22-24`).** It calls `require()` directly and then reads the Store, which has no access control. The policy is correct now, but it is a second copy of the check, and the two copies can drift apart.
3. **A non-string or unhashable token raises `TypeError` (`identity.py:19`).** `SESSIONS.get(token)` fails on a list or dict instead of raising `AccessDenied`. A host that passes the token through unchecked would see an untyped error. Add an `isinstance(token, str)` check.
4. **Denied attempts aren't audited (`routes.py`, `audit.py`).** Audit events are written only after a successful call. `request-lifecycle.md` admits this. A reader probing `public/people` leaves no trace, and the 128-event ring buffer drops the oldest events on overflow.
5. **`settings.max_response_records` is never used.** It is validated but never enforced. Only `MAX_BATCH = 8` in `limits.py` bounds responses. The `expose_diagnostics` setting is also unused.
6. **Unused scopes.** `export` and `purge` are granted to the demo identities but nothing checks them. Anyone adding an export or purge tool later must add a check for them. Nothing enforces one today.
7. **Hardcoded static tokens (`identity.py:12-16`).** The demo tokens are fine for a sample, but they must not be used as-is in a real deployment.
8. **Minor:**
   - Unknown tool names are rejected before authentication (`transport.py:23`). That reveals which tools exist to unauthenticated callers.
   - Alias cycles raise `InvalidRequest`. No seeded alias cycles, but if aliases ever become editable, the error would reveal which aliases exist.
   - Duplicate names in a batch are accepted.

**Dependence on the host**
The safety of this service depends on the host forwarding the caller's own token and the original, unmodified arguments (`host-contract.md`). It also depends on the trusted alias catalog staying read-only. Neither is enforced in this code.

Say if you want me to patch items 1, 3 and 4.
