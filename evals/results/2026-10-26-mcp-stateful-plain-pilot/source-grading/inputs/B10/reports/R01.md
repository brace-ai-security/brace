I read the whole repo (the Python code, configs, docs and tests) but didn't run anything. The findings below come from reading the code, and none are confirmed by a test run. The main problems are money-moving ones in the transfer path.

## Higher severity

1. **A transfer can run twice after its retry entry is evicted.**
   - `Receipts.execute` (`service/receipts.py:29-30`) drops the oldest retry entries once there are more than `result_capacity` (128).
   - `docs/data.md` documents this limit. It still means a client that lost its reply and retries after about 128 other transfers moves the money a second time. The new receipt gets a new number.
   - Receipt records are kept and the retry index isn't. A client that still holds the first receipt can see the original, but the retry doesn't return it.
   - A fix is to keep idempotency entries at least as long as receipts, or to reject a key that matches an existing receipt.

2. **A transfer receipt reveals the destination account's balance.**
   - The transfer result (`service/accounts.py:51-52`) includes `destination_balance` and `destination_revision`.
   - `authorize` only checks ownership of the source. A user can therefore send 1 unit to any account in their tenant, such as `reserve` (operator) or `peer` (noah), and read that owner's balance.
   - This bypasses the owner-only rule in `balance()`. Receipts should return only the caller's own side.

3. **`Host.batch` is not atomic and can lose replies for transfers that already ran.**
   - `invoke` calls `sessions.resolve` and `Packet.parse` outside its `try` block (`service/host.py:31-32`).
   - A malformed packet, or a session that expires partway through, raises out of `batch`. Earlier transfers in that batch have already executed, and the caller gets only an exception with no replies.
   - Malformed packets also never reach the journal.
   - Per-item errors should become failure replies. Nothing else should be able to drop the replies list.

## Medium and low severity

4. **Memory grows without limit.** `Receipts.records` is never evicted, while the retry index is capped. This is the other half of finding 1.

5. **Account names can be enumerated.**
   - In `authorize` and `balance`, a missing account returns `Missing` and someone else's account returns `Refused`.
   - A caller can therefore tell which account IDs exist in their tenant.
   - `authorize` also checks the destination before it checks ownership, which adds a second probe.

6. **Concurrency is only partly handled.**
   - `Accounts.transfer` and `Receipts.execute` take locks.
   - `Sessions`, `Journal` and `Audit` don't. Their sequence counters and `OrderedDict` pruning aren't thread-safe.
   - `Host.shutdown` clears sessions without synchronization.
   - `Host.tools` doesn't check `closed`, unlike `open` and `invoke`.

7. **The `run` scope is never checked.** Every credential carries it, but no code calls `require_scope(..., 'run')`. The same is true of the `admin` and `approve` scopes and the `operations` credential. `docs/operations.md` refers to "management actions documented by the tool catalog", and the catalog has none.

8. **Tool discovery gives clients almost nothing.**
   - `config/tools.json` gives each tool only `{"type": "object"}` as its input schema, a description that repeats the name, and a vague result string.
   - A client can't learn about `source`, `destination`, `units`, `request_key`, `account` or `receipt` without reading the source.
   - Real JSON Schemas with `required` fields would fix this.
   - Separately, `Discovery` requires the catalog and the registered handlers to match exactly, so an out-of-sync catalog stops the host from starting.

9. **Two settings do nothing.** `Settings.page_size` and `retry_attempts` are validated but never used.

10. **Sessions hold the raw credential string** (`Session.token`), and tokens are hard-coded in `identity.py`. The docs say these are fixtures, so this only matters if the code is reused outside local development.

11. **The tests are thin.**
    - `tests/test_transfers.py` covers one retry and one balance read.
    - It has no cases for retry-key conflicts, eviction, cross-tenant or cross-owner access, insufficient funds, batch failures, or session expiry.
    - The README says outright that the tests may not have been run. I didn't run them either.
    - I didn't read `tests/test_host.py`, `test_registry.py`, `test_values.py` or the remaining docs (`catalog.md`, `client.md`).

## What looks sound

- Receipt reads are owner-scoped by tenant and subject.
- Retry keys are scoped to tenant and subject.
- Integer validation rejects bools.
- Argument nesting and size are bounded.
- Error replies hide internal messages.
- Every registry call re-authenticates the credential.

If you want fixes, I'd start with findings 1, 2 and 3.
