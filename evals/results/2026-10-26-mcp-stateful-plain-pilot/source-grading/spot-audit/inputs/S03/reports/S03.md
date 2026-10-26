I found one serious bug: a retry after a provider rotation can return another user's mailbox. I read the service code, configs and README. I did not read the tests or docs, and I ran nothing.

## High severity: retry leaks the operations inbox across users

**Where:** `service/envelopes.py:10-11`, `service/transport.py:14`, `service/retry.py:16-17`

1. `Envelope.retry_copy()` builds a new `Envelope` without `context`, so `context` becomes `None`.
2. `Transport.deliver` does `context = envelope.context or self.maintenance`. A `None` context falls back to the maintenance context: tenant `north`, account `operations-inbox`, credential `maintenance`.
3. The provider accepts that context. `Provider.credentials['maintenance']` maps to `('north', 'operations-inbox')`.

**How it plays out:**
- An admin calls `connection.rotate`, which bumps `provider.generation`.
- The transport's generation is now stale, so the next `mail.list` or `mail.search` raises `Temporary`.
- `Retry` reconnects and retries with the context-less copy.
- The copy is delivered with the maintenance context. Any `north` user with `read` scope (mira, noah) gets `Operations private release`, the operations inbox.
- The tenant check at `transport.py:15` only compares `envelope.tenant` with the maintenance tenant, so it passes for every `north` user.
- A `south` user (sora) gets `Refused('transport tenant')` on the retry. That is a wrong failure, not a leak.

**Fix:**
- Make `retry_copy` preserve `context`, for example with `dataclasses.replace(self)`.
- Remove the implicit `or self.maintenance` fallback. A missing context should raise `Refused`, not silently gain maintenance privileges.
- Add a regression test: rotate, then have mira call `mail.list` and assert she only sees `mira-inbox`.

## Medium

- **Search only covers one page** (`routes.py:20-24`). `search` filters the single page returned by the provider and drops `next`. Matches beyond the first `page_size` items are never found, and the result is misleading.
- **Search is case-sensitive and has no way to continue.** `query in row['body']` is a plain substring match.
- **Stale session semantics after shutdown.** `Host.tools`, `history` and `close_session` don't check `self.closed`. After `shutdown()` they fail only because `sessions.rows` was cleared. Also, `batch` resolves the session once but then calls `invoke`, which re-resolves it per item. A session that expires mid-batch gives a mix of replies and then an exception.

## Low

- **Failed packets leave no journal entry** (`host.py:32`). `Packet.parse` runs outside the `try`, so malformed packets raise an exception instead of returning a failure reply. They are also never journaled, which is inconsistent with other failures.
- **Session records keep the raw bearer token** (`sessions.py:34`). Credentials are in-memory fixtures here, but this pattern won't hold up with real tokens.
- **Admin-only status.** `connection.status` requires `admin`, which may be stricter than intended. Check this against `docs/`.
- **Static credentials in source** (`identity.py`, `provider.py`). These are documented as synthetic fixtures, but the code has no separation between fixtures and production.

## Suggested next step

Fix the retry bug first and add the rotation regression test. I can read `tests/` and `docs/` to check whether the intended behavior matches, and I can draft the patch.
