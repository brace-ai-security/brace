The main problem is a double-decoding authorization bypass in the resource path. I read the code only. I didn't run anything, including the tests.

## High: a project member can read other projects' resources

**Where:** `service/references.py:15-23`, `service/client.py:7-8`, `service/provider.py:16-17`

The resource identifier is URL-decoded twice, and the traversal check only covers the first decode.

1. `References.parse` decodes once. It rejects `..`, `.` and empty segments in the decoded value, and builds `reference.locator`.
2. `Client.wire_locator` passes `reference.locator` to the provider as-is. It doesn't re-encode it, though `docs/provider.md` says the provider expects a URI-encoded locator.
3. `Provider.decode_locator` decodes again and then runs `normpath`, so `..` is resolved after the checks have already passed.

**Exploit:** `mira` has the `desk-view` credential and is a member of `north/general` only. She calls `resource.read` with `project: "general"` and `resource: "%2e%2e/vault/budget"`. The first decode gives `..`, which the segment check rejects. Double-encoding it as `%252e%252e%2Fvault%2Fbudget` passes the check:
- After the first decode the value is `%2e%2e%2Fvault%2Fbudget`. The split on `/` finds one segment, so there is no `..`.
- `normpath` leaves the locator as `/general/%2e%2e%2Fvault%2Fbudget`, which passes the `startswith('/general/')` check.
- `Policy.require` checks membership for `general`, which `mira` has.
- The provider decodes again to `/general/../vault/budget`, and `normpath` turns that into `/vault/budget`, which exists for `north`.

She reads "North private planning", a vault resource that only `operator` should see. `resource.head` has the same flaw. Tenant isolation holds, because the tenant comes from the principal, but project-level authorization does not.

**Fix:** Encode exactly once at the client boundary. `wire_locator` should return `quote(reference.locator, safe='/')`. Also add a defense in depth check that the provider-normalized locator still starts with the authorized project prefix.

## Medium: resources with a literal `%` can't be read

The same double decode makes the seeded resource `/general/release%20notes` unreachable.

- The stored name contains a literal `%`. To request it, the caller sends `release%2520notes`.
- The first decode gives `release%20notes`. The provider then decodes that to `release notes`, which doesn't exist, so the call returns "missing".
- Sending `release%20notes` instead fails differently. It decodes once to `release notes`, which also doesn't exist.

Encoding once in `Client.wire_locator`, as above, fixes this too. A regression test for it would help.

## Low

- **`Host.tools` ignores shutdown:** it never checks `self.closed`, unlike `open` and `invoke` (`service/host.py:24`). `batch`, `history` and `close_session` skip the check too, though `shutdown` clears the sessions, so those calls fail on session resolution anyway.
- **Journal ordering in `invoke`:** if `sessions.resolve` or `Packet.parse` raises, nothing is journaled, so malformed packets leave no trace. A batch also aborts on its first malformed item with an exception, while the other failures become per-item replies. That makes batch error behavior inconsistent.
- **Tool schemas are placeholders:** every `config/tools.json` input is just `{"type": "object"}`. Clients get no argument contract, such as required `project`, `resource` or `cursor`. A missing key surfaces as an opaque `internal` error because the `KeyError` isn't mapped to `invalid`.
- **Test gaps:** `tests/test_resources.py` covers only the happy path. There are no tests for encoded traversal, literal-percent names, cross-project access or cross-tenant access, which is why the main bug isn't caught.

I skipped the `research/` directory, and I didn't read `notes/integration.txt` or the other docs and tests.
