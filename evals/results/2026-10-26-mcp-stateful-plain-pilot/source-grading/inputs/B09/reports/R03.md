I found one high-severity bug, in the retry-key handling, plus several medium and low issues. I only read the code. I didn't run the tests or any code.

## High

**1. Retry keys are shared across all tenants and subjects (`service/commands.py:19-21`, `service/receipts.py:16-22`)**
- `storage_key()` hashes only `{'operation': 'transfer', 'request': request_key}`. The tenant and subject are left out, and `fingerprint()` is just `(source, destination, units)`.
- `docs/data.md` says other subjects and tenants have independent key spaces, so the code contradicts the docs.
- **Cross-tenant replay:** `sora` (south) sends `primary → reserve, 10 units, key "monthly-close"` after `mira` (north) has used the same key and values. Account names are per-tenant, so these are valid for both. `authorize` passes. `execute` then returns mira's cached receipt without running the transfer.
  - sora gets mira's balances, revisions, tenant, subject and receipt id.
  - sora's transfer silently doesn't happen, but sora is told it succeeded.
- **Key probing:** If the fields differ, the caller gets `Conflict('request shape')`. That tells them whether another user has already used that key.
- **Key squatting:** The docs say keys are often business identifiers like `month-close`, which are easy to guess. A user can use a key first and make others' transfers with that key replay or conflict.
- **Fix:** Include `tenant` and `subject` in `storage_key()`, and ideally in the fingerprint too. Add a test where two principals use the same key.

## Medium

**2. The retry index is small, shared, and evictable by anyone (`service/receipts.py:29-30`)**
- One index of 128 entries serves every user. A user who makes 128 small transfers evicts other people's keys. The victim's later retry then runs as a new transfer, so it executes twice.
- `self.records` is never evicted, so it grows without bound.

**3. A batch fails as a whole, and failures aren't journaled (`service/host.py:28-48`)**
- `Packet.parse` and `sessions.resolve` raise inside `invoke`, outside the `try`. A malformed packet at position 3 aborts the batch.
  - The replies for packets 1 and 2 are lost, even though those transfers already ran.
  - Parse failures are also missing from the journal.
- Per-packet errors should become `failure()` replies.

**4. The `run` scope is never checked (`service/host.py`, `service/identity.py`)**
- Nothing calls `require_scope(..., 'run')`. The `admin` and `approve` scopes are also unused, even though `docs/operations.md` refers to admin management actions in the catalog. No such tools exist.

**5. Any credential can fill the session table (`service/sessions.py:31`)**
- There's a global cap of 64 sessions and no per-credential limit. One holder can open 64 sessions and block everyone else for the 900-second TTL.

## Low

- **Account existence leak:** `authorize` and `balance` return `Missing` for an unknown account and `Refused` for someone else's. Within a tenant, this reveals which account names exist (`service/accounts.py:27-38`).
- **Shutdown handling:** `Host.tools()` and `batch()` don't check `closed` before resolving. `shutdown()` clears the sessions without taking any lock.
- **Thread safety:** `Audit`, `Journal` and `Sessions` mutate shared state without locks, and `Receipts.owned` reads without taking the lock. This is only safe if the host is single-threaded. `Accounts.get` also reads without the lock.
- **Weak tool catalog (`config/tools.json`):**
  - Every tool has `"input": {"type": "object"}` and a description that just repeats its name, such as "transfer create".
  - There are no field names, types or limits, so a model client can't tell how to call these tools.
  - `Discovery` only checks that the names match the registered handlers.
- **Unused settings:** `retry_attempts` and `page_size` are validated but never used.
- **Thin tests:** The transfer tests cover only a same-user repeat and one balance read. There are no tests for cross-subject keys, eviction, scope denial, batch errors or session expiry.
- **Hardcoded credentials:** The tokens are in source (`service/identity.py`). The docs say they're synthetic, which is fine for local use. They shouldn't ship as they are.

## Notes

- This isn't an MCP server. There's no wire transport, and the docs say so. It's an in-process registry with an MCP-like shape.
- The transfer arithmetic itself is atomic under the lock.
- Input validation is mostly solid. The integer check rejects bools, the name regex is anchored, and nesting and size limits are enforced.

I'd fix issue 1 first, since it leaks data across tenants and can drop a user's transfer without telling them. Issues 2 and 3 come next.
