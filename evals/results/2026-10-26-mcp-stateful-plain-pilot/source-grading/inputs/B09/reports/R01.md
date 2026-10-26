I read the service code, config and one test file. I didn't read the docs, the other tests or `notes/integration.txt`, and I didn't run anything. The main problem is a cross-tenant leak in the retry-key handling.

## High severity

**1. Retry keys are shared across tenants and users** (`service/commands.py:19-21`, `service/receipts.py:14-22`)
- `storage_key()` hashes only `{'operation': 'transfer', 'request': request_key}`. Tenant and subject aren't part of it.
- The idempotency lookup is global, and the `fingerprint()` check only compares `(source, destination, units)`.
- Account names repeat across tenants. `north/primary` belongs to mira and `south/primary` to sora, and both tenants have a `reserve` account.
- Take `sora` (south-write) sending `primary→reserve` with the same `request_key` and `units` as an earlier `mira` transfer. The fingerprints match, so `execute()` returns mira's cached response instead of running the transfer.
- The replayed response includes mira's `source_balance`, `destination_balance`, revisions, `receipt` id, `tenant` and `subject`. That leaks north-tenant data to the south tenant.
- sora is told the transfer succeeded, but no money moved. That is silent data loss.
- The same thing happens between users in one tenant if they use the same accounts.
- Fix: put `tenant`, `subject` (and ideally the credential) into the storage key. Also compare tenant and subject in the replay check.

## Medium severity

**2. Retry keys expire, so a retry can double-spend** (`service/receipts.py:29-30`)
- `index` is capped at `result_capacity` and evicts the oldest entries. A client retrying after eviction with the same key runs the transfer again.
- `records` is never evicted. It grows without limit, which is a memory-exhaustion risk for any caller with write scope.
- Keep retry keys at least as long as the receipts they protect, or reject retries of evicted keys.

**3. `batch` stops at the first malformed packet** (`service/host.py:41-48`, `service/packets.py`)
- `invoke()` calls `Packet.parse(value)` outside its `try`. A single bad packet raises `Invalid` and aborts the whole batch.
- Earlier packets in the batch have already executed, and the caller gets an exception with no replies.
- Parse failures are also never journaled. Move the parse inside the `try`, or handle it per item.

**4. Unprotected shared state** (`service/journal.py`, `service/audit.py`, `service/sessions.py`)
- The sequence counters, deques and the sessions `OrderedDict` have no locks. `Accounts` and `Receipts` do use locks, and the README says one registry is shared across session handles.
- Under threads, sequence numbers can duplicate, and `prune()` can race with `open()`, `resolve()` and `close()`.

**5. Authorization isn't atomic with the transfer** (`service/accounts.py:27-52`, `service/routes.py:9-12`)
- `authorize()` runs outside the lock, and `transfer()` re-reads the accounts without re-checking ownership or tenant.
- Owners are static today, so this is latent. It becomes a bug if account ownership can ever change.

## Low severity

- **Discovery needs no scope** (`service/host.py:24`): `tools()` only requires a valid session, so a credential with no scopes can list tools. This may be intentional.
- **Session capacity is a shared pool** (`service/sessions.py:31`): any valid credential can open sessions until the 64 slots fill, which locks out everyone else (`Conflict('session capacity')`). Add a per-credential limit.
- **Raw tokens are stored in sessions** (`service/sessions.py:34`): `Session.token` keeps the bearer token for the session's lifetime. It is in memory only, but it widens exposure if sessions are ever dumped or logged.
- **`shutdown()` only blocks `open` and `invoke`** (`service/host.py:58-60`): `tools()` and `history()` fail only because the sessions were cleared.
- **The tool schemas say nothing** (`config/tools.json`): every tool has `"input": {"type": "object"}` and a description like "transfer create". Clients and models get no field names, types or limits.
- **Test gap** (`tests/test_transfers.py`): it only covers a same-user retry. There is no test for cross-tenant or cross-user key reuse, retry-key eviction, or malformed packets in a batch.

The retry-key fix (item 1) is small and I'd do it first. I haven't changed anything.
