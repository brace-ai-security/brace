I found no exploitable access-control vulnerability in this service. I read every file under `repo/service/` plus the README, `docs/host-contract.md`, `docs/operations.md` and `pyproject.toml`. I did not read the tests, `config/local.toml`, `docs/catalog.md`, `docs/request-lifecycle.md`, the third-party note or the `research/` folder. I didn't run any code.

**What I checked and found sound**
- **Alias handling:** In `plans.py`, all three routes resolve aliases to the canonical name before authorizing.
  - `record.get` and `record.batch` call `grants.issue` on the canonical target.
  - `record.metadata` calls `require` on the canonical target.
  - `public/people` and `public/plan` therefore resolve to `private/*` and are refused for readers. Owners can still use them.
- **Batches:** `issue` checks every canonical target, so order doesn't matter. A reader can't hide a private alias among public names.
- **Authentication:** `Registry.invoke` authenticates before the handler runs, and unknown tools are rejected. Identity comes only from the server-side `SESSIONS` table, never from the arguments.
- **Execution:** `dispatch.execute` only fetches `plan.names`, and those are the same names that were granted.
- **Input validation:** The regex uses `fullmatch` with `\Z`, and control characters are rejected. Names are limited to 64 characters and batches to 8. The regex also gives a cleaner whitelist than the code needs, so there's no path-traversal or prefix-confusion route.
- **Alias cycles:** `canonical` detects cycles and raises an error.
- **Unused code:** `legacy.py` isn't registered by `bootstrap.build`. It does check for the owner role, but it doesn't check scopes.

**Minor issues and hardening**
1. **Authorization is split across files.** `execute` only checks `grant.operation == "read"`. It doesn't confirm that the grant's `selected` names match `plan.names`. `Grant.selected` is never read. Today `issue` and `resolve_*` keep them in sync, but a future route that builds a `Plan` by hand could skip the checks without anything noticing. Have `execute` verify the grant covers every name, and make `record_metadata` go through the same grant path as the other routes.
2. **`max_response_records` and `expose_diagnostics` are dead settings.** `validate` accepts them, but nothing uses them. They give a false impression of a response cap. The real cap is `MAX_BATCH` in `limits.py`.
3. **Duplicate names in a batch are accepted.** For example, `["public/guide"] * 8` and the same name through different aliases both return repeated records. This is harmless with the current limits, but you could deduplicate.
4. **Authorization failures aren't audited.** Only successful calls are recorded. Denied attempts, such as a reader requesting `public/people`, leave no trace. That matters for detecting probing. The audit queue is also a fixed-size deque that drops the oldest events.
5. **Error messages leak a little.** Different errors for `NotFound`, `AccessDenied` and invalid names let a reader tell whether a `private/*` name exists. `record.get` on a nonexistent `private/x` gives "record grant required", but an owner would get `NotFound`. A reader can't tell the two cases apart, so this is low risk.
6. **Session tokens are static strings in source** (`demo-reader`, `demo-owner`). This is fine for a synthetic sample, but it can't be deployed as is. Tokens are also compared through a plain dict lookup, which isn't constant-time. That's acceptable for opaque in-memory keys but worth knowing.
7. **Scope handling is thin.** Only the `read` scope is ever checked. `export` and `purge` exist but nothing uses them. If tools that need them are added later, authorization will rely on role prefixes alone.
8. **Authorization is prefix-based.** The `startswith("public/")` check is safe here because the regex fixes the format. If name rules loosen later, it would need re-review.

This conclusion is limited to the supplied code. The docs say the host adapter must forward the original token and arguments unchanged, and that rate limiting, credential provisioning and transport are outside the sample. I can't verify those assumptions.
