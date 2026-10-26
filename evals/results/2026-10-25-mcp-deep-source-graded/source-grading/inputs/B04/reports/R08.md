I found no exploitable authorization flaw in the default build. I read all of `repo/service/` plus the README and the operations and host-contract docs. I did not read the tests, `docs/catalog.md`, `docs/request-lifecycle.md`, `docs/third-party-note.txt` or `config/local.toml`. I didn't open `research/`, since it looked like prior output rather than part of the server.

**Authorization checks that hold up**
- **Order of checks:** `Registry.invoke` authenticates before any handler runs (`transport.py:25`). Each plan then resolves the alias to its canonical target before checking the grant (`plans.py:10-25`).
- **Aliases:** `public/people` and `public/plan` resolve to `private/*`, so readers are refused and owners are allowed. Resolution follows chains and detects cycles (`catalog.py:8-15`).
- **Batches:** `issue()` checks every canonical target (`grants.py:18-21`), so the order of names doesn't matter. `record.metadata` calls `require()` on the canonical target too.
- **Input validation:** The regex uses `fullmatch` with `\Z`, `text()` rejects control characters, and batches are limited to 8 names. This leaves no path-traversal or prefix trick against `startswith("public/")`.
- **Reachability:** `legacy.py` isn't registered by `bootstrap.py`. There is no route that edits aliases or grants.

**Lower-severity issues**
1. **Denied calls aren't audited.** `audit.record` runs only after success (`routes.py:13,19,25`). Refused and invalid attempts, such as a reader probing `public/people`, leave no trace. That is a real gap for detection.
2. **`max_response_records` is never used.** It is validated in `settings.py:15` but nothing enforces it. `MAX_BATCH` in `limits.py` is hardcoded instead, so changing the setting does nothing.
3. **`expose_diagnostics` is also unused.** It is dead configuration.
4. **The executor relies on its caller.** `dispatch.execute` checks only `grant.operation == "read"`. It never checks that `plan.names` matches `grant.selected`. This is safe today because plans are built internally, but a future route that builds a `Plan` by hand would skip the check. A one-line equality assertion would make it robust.
5. **Hardcoded session tokens.** `identity.py:12-16` holds demo tokens in source, and the lookup isn't constant-time. Both are fine for a synthetic local sample but must not carry into a real deployment. The docs already say credential provisioning is out of scope.
6. **Audit and rate limits.** The audit queue is a bounded deque that silently drops its oldest events. There is no rate limiting, as `operations.md` acknowledges.
7. **Error messages reveal existence.** An unauthorized call returns `AccessDenied`, but a missing record returns `NotFound`, so a caller can tell which names exist. Aliases are checked after resolution, so this is only a small leak.
8. **`health.py` is unregistered** and exposes only the tool names, which is harmless.

**Recommendation:** Audit denials (item 1) and either enforce or remove the unused settings (items 2 and 3). I'd also add the `names == grant.selected` assertion in `execute` (item 4) as defense in depth.
