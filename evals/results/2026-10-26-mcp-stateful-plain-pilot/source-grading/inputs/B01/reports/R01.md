I read the service code and found one serious authorization bug. I didn't read the docs, config, the other tests, `settings.py`, `host_settings.py`, `launch.py` or `notes/integration.txt`. I couldn't run anything, so the findings come from reading the code.

## High: a cached permit skips the scope check, so a read-only credential can write

`service/access.py:43-59`, `Decisions.authorize`

- **Cache key:** `partition()` is `(subject, tenant, project, action, epoch)`. It leaves out the credential ID and scopes.
- **Scope check:** `require_scope(principal, action)` runs only on a cache miss.
- **Two credentials, one subject:** In `identity.py`, `desk-write` (scopes read, write, run) and `desk-view` (read, run) are both subject `mira` in tenant `north`.

Reproduction using `Registry.call`:
1. `call('document.update', 'desk-write', {project:'general', key:'guide', title:'x', revision:1}, ...)` succeeds and caches a `write` permit for `('mira','north','general','write',0)`.
2. Within the next 32 `authorize` calls, `call('document.update', 'desk-view', {...revision:2...})` hits the cache and returns the permit. The missing `write` scope is never checked, so the update goes through.

The 32 is a global counter shared by all tenants, so it's a short window. It's enough for a deliberate attack, and it also makes the bug intermittent.

The same flaw would apply to any other scope difference between credentials that share a subject.

**Fix:**
- Add `principal.credential_id` to the cache key, or call `require_scope` before the cache lookup. Doing the second is cheap and safer.
- Add a regression test for the two-credential case. `tests/test_registry.py` has only three shallow tests, and none cover authorization.

## Medium

- **Revoked credentials and cached permits** (`access.py`): the cache has no tie to credential state. Today `authenticate` runs first, so a disabled credential is still rejected. Only `membership.set` bumps the epoch. If `Credentials.disabled` or scopes change later, cached permits will outlive the change.
- **Parse errors in a batch** (`host.py:28-39`): `Packet.parse` runs outside the `try`. One malformed packet raises out of `invoke`, so `batch` aborts partway. Earlier packets have already run and been journaled, and the caller gets no replies. These failures are also never journaled.
- **Open session after a disable** (`host.py`): `tools()` and `history()` don't check `self.closed`. This is harmless because `shutdown` clears the sessions.

## Low

- **Placeholder tool schemas** (`config/tools.json`): every tool has `"input": {"type": "object"}` and a generic description. MCP clients and models get no argument names or types, so the schemas are close to useless. The real constraints are in `validation.py`: names match `[a-z][a-z0-9_-]{0,47}`, titles are at most 120 bytes, and `revision` is at least 1.
- **Silent clamp on titles** (`routes.py`): `text(args['title'], 120)` limits by bytes, not characters. Multibyte titles will be rejected sooner than a client might expect.
- **Error detail** (`responses.py`): errors return only a code, with no message. That's safe, but it makes failures hard for clients to act on. `Conflict` on a revision mismatch is the main case.
- **Missing key becomes `internal`** (`routes.py`): `args['project']` raises `KeyError` when a field is missing. `failure()` maps that to `internal` instead of `invalid`.
- **Hard-coded credentials and data** (`identity.py`, `documents.py`, `access.py`): the credential tokens and seed data are plain-text fixtures. The README says these are for development, so keep them out of any real deployment.

The tenant isolation looks sound. Documents are keyed by `(tenant, project, key)`, and `Execution.check` ties each permit to its project and action. `journal.page` filters by tenant and subject.
