I found one serious authorization bug, plus several smaller issues. This was a read-only review: I didn't run the code or the tests. The existing tests only cover registry basics, so none of this is checked against a run.

## High: cached permits bypass the scope check (`service/access.py:43-59`)

The permit cache key is `(subject, tenant, project, action, epoch)`. It leaves out the credential and its scopes. On a cache hit (`access.py:48-50`), `authorize` returns before `require_scope` runs.

The seed credentials in `identity.py:7-8` show how this goes wrong. `desk-write` and `desk-view` are both subject `mira` in tenant `north`, but `desk-view` has no `write` scope. To get a write through with the read-only token:
1. Call `document.update` on `general` with `desk-write`. This caches a `write` permit.
2. Within the next 32 `authorize` calls, call `document.update` with `desk-view`. It gets the cached permit and the write goes through.

The expiry is `sequence + 32`, a count of global `authorize` calls rather than time. Any traffic from other callers shortens the window, and a quiet system leaves it open.

**Fix:** run `require_scope(principal, action)` before the cache lookup, and add `credential_id` to the key (or drop the cache). A regression test should assert that `desk-view` gets `Refused('scope')` on `document.update` right after a `desk-write` update.

## Medium

- **A batch is all-or-nothing on malformed packets** (`host.py:31-47`). `Packet.parse` runs outside the `try`, so one malformed packet raises out of `batch`. Replies for the earlier packets are lost even though they already executed and were journaled. Malformed packets are also never journaled. Parse failures should become a failure reply, like handler errors.
- **Session exhaustion** (`sessions.py:31`). Capacity is global (64) with no per-subject or per-credential limit. One valid token holder can open sessions until everyone else gets `Conflict('session capacity')`. Sessions only expire after the TTL of 900 seconds.
- **Tool catalog is not a usable contract** (`config/tools.json`). Every tool has `input: {"type": "object"}` and a description that only repeats its name. Required arguments (`project`, `key`, `title`, `revision`, `enabled`, `subject`) and the `admin` requirement on `membership.set` are not described. Discovery also ignores caller scope, so every session sees `membership.set`.
- **Not MCP wire-compatible**. The transport is an in-process `host-call`. There is no JSON-RPC, `tools/list` or `tools/call`, and no `inputSchema`. If the goal is a real MCP server, it needs an adapter layer.

## Low

- `membership.set` (`routes.py:30-39`) accepts any subject string and any project name. It creates membership rows for projects and subjects that don't exist, with no check against known credentials or projects.
- `retry_attempts` is validated in `settings.py` but never used.
- `Host.tools` doesn't check `closed`, unlike `open` and `invoke`. `Host.history` and `Host.batch` skip it too.
- Failed authentication isn't audited (`registry.py:24`). The docs say so, but it means brute-force token guessing leaves no trace.
- `Documents.update` accepts an empty `title`.
- Journal and audit entries are in-memory deques that overwrite their oldest entries. Under load, older security-relevant records disappear (documented as non-durable).

## What looks sound

- Tenant isolation: the `tenant` in every document lookup comes from the permit, not from request arguments.
- Epoch bumps on `set_member` correctly invalidate cached permits after a membership change.
- Revalidating the credential on each `Sessions.resolve` means disabled credentials stop working immediately.
- Input validation is strict: the name regex, the exact-`int` and exact-`bool` type checks, and the nesting and size limits.
- Journal reads are filtered by tenant and subject.

I'd fix the permit-cache bug first, with the regression test, then the batch error handling.
