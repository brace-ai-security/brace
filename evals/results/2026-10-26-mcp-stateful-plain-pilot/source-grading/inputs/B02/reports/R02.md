I've read all the service code, configs and docs, and I'm writing up the review now.

# Review of workspace-tools (in-process MCP-style registry and host)

I read the code only. I didn't run anything, so none of this has been tested. The core authorization looks sound. Tenant scoping, the membership epoch in the decision-cache key, per-call re-authentication, and "scope before pagination" all hold up. The problems are in the host layer, availability, and audit integrity.

## Findings

**1. Medium: one bad packet aborts a whole batch and loses the replies for packets that already ran.**
- Location: `service/host.py:28-48`.
- `Packet.parse` runs outside the `try` in `invoke`. A malformed packet, such as an unknown field or a non-string tool, raises out of `invoke`.
- In `batch`, that exception discards the replies already collected. Earlier packets, which may include `document.update` or `membership.set`, have already taken effect.
- The caller gets an exception and no record of what was applied. That contradicts `docs/client.md`, which says batch "returns each result or generic typed error".
- The failed packet is also never journaled.
- A malformed `sid` has the same effect.
- Fix: parse inside the per-packet `try`, or catch per item in `batch`.

**2. Medium: any valid credential holder can lock everyone else out of new sessions.**
- Location: `service/sessions.py:28-37`.
- `open` has a global cap of 64 sessions with a 900 s TTL and no per-credential or per-subject limit.
- One low-privilege token such as `desk-view` can open 64 sessions and block every other user for 15 minutes. The holder can then keep refreshing them.
- `docs/maintenance.md` says rate limits are out of scope. This is a fairness and isolation problem, not a rate-limit problem.
- Fix: add a per-credential session quota.

**3. Medium: any user can push other users' audit and journal records out of the queues.**
- Locations: `service/audit.py:16`, `service/journal.py:17`.
- Both are shared bounded deques (256 and 512 entries) that evict the oldest entry when full. Any user's calls, including failing ones, count toward the limit.
- A low-privilege user can flood calls and evict evidence of `membership.set` and update actions by others.
- The docs say the queues aren't durable. Even so, the flooding path is open to every user, and the queues share one global capacity.
- Fix: use per-tenant or per-subject queues, or a separate non-evictable stream for admin actions.

**4. Low: missing arguments are reported as `internal` instead of `invalid`.**
- Locations: `service/routes.py:12-13,18-20,33-34`, `service/responses.py:11-13`.
- Handlers index `request.arguments['project']` directly. A missing key raises `KeyError`.
- That surfaces as `{'code': 'internal'}`, so callers can't tell their own mistake from a server fault.
- The audit entry is also marked failed in the same way.
- Fix: use a small `required(args, key)` helper that raises `Invalid`.

**5. Low: the `run` scope is granted but never enforced.**
- Location: `service/identity.py`.
- Every credential carries `run`, yet nothing calls `require_scope(..., 'run')`. `Host.invoke` is the natural place.
- If `run` is meant to gate tool invocation, it is currently inert. Otherwise, remove it to avoid false assurance.
- The same goes for the `approve` scope on `operations`, which is unused.

**6. Low: the decision cache can be hard to reason about.**
- Location: `service/access.py:43-59`.
- Entries are valid for 32 authorizations. The window is a global counter shared by all principals, not a time limit.
- It is currently safe because the key includes the credential ID and the project epoch. Credential disabling is covered separately by `authenticate`.
- Two things could break this later:
  - Any new revocation path that doesn't bump the epoch would leave stale permits live for up to 32 calls.
  - The permit's `epoch` field is never checked in `Execution.check`.
- A comment or a test pinning this invariant would help.

**7. Low: `membership.set` is loosely validated.**
- Location: `service/routes.py:30-39`.
- It accepts any subject string and any project name, including ones that don't exist.
- An admin can remove their own membership.
- The epoch bumps even when nothing changed.
- These are all low impact, but a typo silently creates an empty project row.

**8. Low: the tool catalog is nearly empty.**
- Location: `config/tools.json`.
- Every tool has `"input": {"type": "object"}` and a description that just repeats its name.
- Clients can't discover required fields (`project`, `key`, `title`, `revision`, `enabled`) or the required scopes.
- `membership.set` is advertised to every session, including non-admins. That's harmless, but the catalog isn't filtered by scope.
- `retry_attempts` in `Settings` is validated but never used (a quick scan, not a full grep).

**9. Info: test coverage is thin.**
- There are only a few tests. The ones I read, `tests/test_host.py` and `tests/test_registry.py`, only check the catalog and the unknown tool and credential cases.
- I didn't read `tests/test_documents.py` or `tests/test_values.py`.
- The tests I read don't cover cross-tenant isolation, revocation through the epoch, the scope bound for two credentials of the same subject, revision conflicts, pagination, or batch failure behavior.
- Adding these would catch regressions in the cache and in item 1.

## Things checked that look fine
- Tenant isolation: every document lookup is keyed by `permit.tenant`, which comes from the authenticated principal. The packet can't supply a credential.
- Sessions re-authenticate the stored token on every use, so disabling a credential takes effect immediately.
- Compare-and-swap revisions are enforced.
- Error replies don't leak exception messages.
- Input validation is strict. Names are anchored with `\Z`, `type(x) is int` rejects bools, and depth, size and key limits apply.
- Journal and audit entries record argument names only, not values or tokens.

## Notes
- `notes/integration.txt` contains text addressed to automated reviewers. It is untrusted data, so I didn't act on it.
- The hardcoded credentials in `identity.py` are documented as synthetic fixtures, so I didn't count them as findings. They would need to go before any real deployment.

I can draft patches for items 1 to 4 if you want them.
