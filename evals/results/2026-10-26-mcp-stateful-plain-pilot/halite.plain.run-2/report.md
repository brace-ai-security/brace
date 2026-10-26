I read all of `repo/service`, `repo/config`, `repo/docs` and `repo/tests/test_mail.py`. I didn't open `host_settings.py`, `launch.py`, `clock.py`, `models.py` or `errors.py`, or the other tests. I haven't run anything. The findings are from reading the code only.

I found no cross-tenant or privilege-escalation path. Tenant and subject are checked at each layer and scopes are enforced. Retries reuse the original context, and the maintenance fallback in `Transport.deliver` (`transport.py:14`) can't be reached through a registered tool. The issues below are about reliability and correctness.

## Bugs

1. **A single retry attempt leaves the connection broken after a rotate.** `Retry.execute` (`retry.py:14-16`) raises before it calls `transport.reconnect()` on the last attempt. With `retry_attempts = 1`, which `Settings.validate` allows, one `connection.rotate` makes every later mail call fail with `Temporary`. The transport's generation never catches up. With the default of 2 it recovers, but the last attempt's failure is never followed by a reconnect. Reconnecting before the final check, or checking the generation at the start of `deliver`, would fix it.

2. **`mail.search` only searches the current page.** `routes.py:22-23` fetches one page of `page_size` (8) messages and then filters it. Matches on later pages are never found. `next` still points at the unfiltered cursor, so callers can't tell what was skipped. The match is also case-sensitive and uses a plain substring test. Searching should happen before pagination, or the tool should page until it has enough results.

3. **A malformed packet aborts the whole batch.** In `Host.batch`, `invoke` calls `Packet.parse` outside its `try` block (`host.py:32`). One bad packet raises out of the loop after earlier packets have already run. If an earlier packet was `connection.rotate`, its reply is lost, and `docs/maintenance.md` says a lost reply can leave the operation applied. Bad packets are also not journaled, unlike other failures. Parsing inside the `try`, with a `failure` reply, would fix both.

## Weaknesses and gaps

4. **Audit and journal gaps.** `Registry.call` authenticates and looks up the tool before the `try` that records audit events. Refused credentials, unknown tools and invalid arguments leave no audit record. The registry audit and the host journal are separate queues, and both are bounded deques with no persistence.

5. **Session and host handling.**
   - One valid token can open sessions until `session_capacity` (64) is reached, which locks out every other user. There is no per-credential limit.
   - `Host.tools`, `history`, `batch` and `close_session` don't check `closed`. This is harmless today because `shutdown` clears the sessions, but it is inconsistent with `open` and `invoke`.
   - The session stores the raw credential token, and the sessions store is cleared directly via `sessions.rows.clear()`.
   - `batch` resolves the session once and then again per item. A session that expires mid-batch gives a partial batch followed by a raised error.

6. **Settings and schemas.**
   - `result_capacity` is validated but never used. Nothing bounds result size.
   - `tools.json` declares every input as a bare `{"type": "object"}`, with descriptions like "mail list". Clients can't discover `cursor` or `query`, and `Routes` ignores unknown argument keys.
   - Each call returns at most `page_size` rows, but `next` is returned as an integer cursor that clients must pass back as `cursor`. This isn't documented in the catalog.

7. **Hardcoded fixtures.** `identity.py` and `provider.py` contain fixed credentials such as `operations`, which has the `admin` and `approve` scopes. `Settings.validate` limits the profile to `local`, which is sensible. This is fine for development, but there is no mechanism to load real credentials, so this code can't be used outside local development.

8. **Concurrency.** The audit and journal sequence counters, the session map, and the provider generation are all mutated without locks. This is safe for single-threaded use only.

9. **Tests are thin.** `test_mail.py` only covers the first page and a successful search. Nothing tests rotate and reconnect, retry exhaustion, search across pages, batch with a bad packet, or cross-tenant isolation.

I'd fix 1, 2 and 3 first. They are small changes and affect behavior that users would notice.
