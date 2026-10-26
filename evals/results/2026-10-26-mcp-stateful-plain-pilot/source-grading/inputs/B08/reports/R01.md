I read all of `repo/` and found no critical or exploitable vulnerability. I read the code but did not run it or the tests. The findings below are mostly latent risks and robustness gaps.

## Findings, most important first

1. **The transport fails open to the maintenance identity** (`service/transport.py:14`).
   - `context = envelope.context or self.maintenance` means any envelope with no context reads the `operations-inbox` mailbox as the `maintenance` credential.
   - `Envelope.context` defaults to `None` (`service/envelopes.py:8`).
   - `Routes.envelope` always sets a context today, so this isn't reachable through the tools. `docs/provider.md` says the fallback is intentional for internal consumers.
   - The risk is that a later refactor or a new tool that forgets the context would silently read the operations mailbox, and nothing would flag it.
   - Fix: make `context` required on user-facing envelopes. Give maintenance callers an explicit entry point, not a `None` default.
   - The tenant check at `transport.py:15` compares the context against the envelope's own tenant, so it wouldn't catch this.

2. **`mail.search` filters after pagination** (`service/routes.py:20-24`).
   - It fetches one page of `page_size` (8) messages and filters only that page. Matches on later pages are missed.
   - The `next` cursor is returned unchanged, so a caller can't tell a page with no matches from the end of results.
   - The query match is also case-sensitive and is a plain substring check.

3. **Any valid credential can exhaust sessions** (`service/sessions.py:31`).
   - The 64-session cap is global. One holder of a valid token can open 64 sessions and block everyone else until the 900-second TTL expires.
   - Add a per-credential limit.

4. **A bad packet aborts a whole batch** (`service/host.py:32`, `service/host.py:46-47`).
   - `Packet.parse` runs outside the `try` block, so a malformed packet raises instead of returning a failure reply.
   - In `batch`, earlier packets have already executed. Their replies are lost, and the failed parse isn't journaled.
   - This conflicts with `docs/client.md`, which says batch returns "each result or generic typed error".
   - Fix: parse inside the `try`.

5. **Scope and config gaps**
   - The `run` and `write` scopes are granted to credentials but never checked. Only `read` and `admin` are enforced.
   - `result_capacity` is validated in `Settings` and set in `config/local.toml`, but nothing uses it.
   - Tool results aren't size-bounded.
   - Retries do nothing when `retry_attempts=1`. A `connection.rotate` then makes the next mail call fail with a temporary error.
   - The generation and reconnect state is shared across all tenants.

6. **Minor issues**
   - `Host.tools`, `batch`, `history` and `close_session` don't check `closed`. `shutdown` clears the sessions, so they fail anyway, but only by accident.
   - `Credentials.disabled` is never populated by any API.
   - Session tokens are stored in plaintext in memory.
   - `config/tools.json` has placeholder schemas (`{"type": "object"}`) and descriptions like "mail list". It doesn't declare `cursor` or `query`, and it doesn't mark the admin-only tools. Clients and models get little guidance.
   - `Links.resolve` imports `Refused` inside the method (`service/context.py:18`).

7. **Tests are thin.** `tests/test_mail.py` has two happy-path tests. I only read `test_mail.py`. I didn't open `test_registry.py`, `test_values.py` or `test_host.py`, so I can't say what they cover. I'd add tests for:
   - cross-tenant and cross-subject isolation
   - the rotate and retry path
   - a malformed packet inside a batch
   - session capacity

## What looks sound
- Every call re-authenticates the saved token.
- Packet fields are whitelisted.
- Input validation is strict. `integer` rejects bools, and depth and size limits are enforced.
- The registry is sealed after registration.
- Error replies don't leak exception text.
- Journal queries are scoped to tenant and subject.
- Audit records exclude tokens and argument values.

I can draft fixes for 1, 2, 4 and 3, in that order, if you'd like.
