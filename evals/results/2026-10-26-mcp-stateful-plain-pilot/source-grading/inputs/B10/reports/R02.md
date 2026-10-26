I've read all the service code, config and docs. I haven't read `models.py`, `clock.py`, `errors.py`, the other tests, or the `research/` folder. Nothing was executed, so these findings come from reading the code only.

## Main findings

**1. A retry can move money twice once the idempotency entry is evicted** (`service/receipts.py:29-30`)
- The retry index is capped at `result_capacity` (128), and the oldest keys are evicted first.
- After 128 further transfers, a client that retries an old `request_key` runs the transfer again. It gets a new receipt and the money moves a second time.
- `docs/data.md` mentions the bounded index, but a client can't see when an entry is about to expire. This is the most serious issue for a payment-style tool.
- Fix: keep keys for as long as the receipts live, or return an explicit "key expired" error instead of re-executing.

**2. `receipts.records` is never evicted** (`service/receipts.py:27`)
- Every receipt is stored forever, so memory grows without limit. The index is bounded and the records aren't.
- This also means a receipt can outlive the key that produced it.

**3. A bad packet in a batch loses the replies for packets that already ran** (`service/host.py:32,46-47`)
- `Packet.parse` runs outside the `try` block in `invoke`. A malformed packet raises `Invalid` out of `batch` instead of becoming a failure reply.
- If packet 3 of 5 is malformed, packets 1 and 2 have already executed, including any transfers. The caller gets an exception and no receipts.
- This contradicts `docs/client.md`, which says batch "returns each result or generic typed error". Malformed packets also never reach the journal.
- Fix: parse inside the `try`, or catch per packet in `batch`.

**4. Missing arguments surface as `internal` errors** (`service/commands.py:25-32`, `service/routes.py:15,18`)
- `arguments['source']`, `['units']`, `['account']` and `['receipt']` raise `KeyError` when absent.
- `failure()` maps that to `internal` rather than `invalid`. Clients can't tell their own mistake from a server fault, and the audit log fills with spurious failures.

**5. Scope checks are incomplete**
- `receipt.get` (`receipts.owned`) has no `require_scope`, unlike `balance` and `transfer`.
- The `run` scope is never enforced anywhere.
- `Host.tools` and `discovery` need only a valid session.
- `approve` and `admin` exist only on the `operations` credential and nothing uses them. That is dead authorization surface, and it will matter once someone wires it up.

**6. The service has no concurrency protection outside the account lock**
- `Journal.append`, `Audit.record`, `Sessions` and `Receipts.owned` take no lock, so sequence numbers and session pruning can race if the host is ever threaded.
- `Accounts.authorize` checks ownership outside the lock that `transfer` later takes. This is harmless today because owners are static, but it is fragile.

## Lower severity

- **Account existence leaks within a tenant.** `authorize` and `balance` return `Missing` for an unknown account and `Refused` for someone else's. That lets a caller probe which account IDs exist. `authorize` also checks the destination before the source owner.
- **Tokens are hardcoded and stored in clear text.** Examples are `desk-write` and the admin `operations` token in `service/identity.py`, and the raw token sits in each `Session`. The docs say these are synthetic, but nothing prevents this profile from being used outside local development.
- **One credential can fill the session table.** `Sessions.open` has no per-credential limit, so any valid token can take all 64 slots and block everyone else with `Conflict`.
- **The tool catalog is too thin for an LLM-facing tool.** `config/tools.json` gives every tool `"input": {"type": "object"}` and a description that just repeats the name, such as "transfer create". There is no schema for `source`, `destination`, `units` or `request_key`. Models and clients can't discover the arguments.
- **This isn't an MCP server on the wire.** There is no transport or protocol negotiation, as the docs admit. Calling it an "mcp server" overstates what it is.
- **Dead settings and code.** `page_size`, `retry_attempts` and `Discovery.describe` are never used.
- **Tests are thin.** `test_transfers.py` covers only a basic retry and a balance read. Nothing tests eviction, cross-tenant or cross-subject access, scope denial, batch failure or session expiry.

## Suggested order of fixes
1. Findings 1 and 2.
2. Finding 3.
3. Finding 4.
4. Add tests for those cases.
5. Finding 5, and a real argument schema in the tool catalog.
