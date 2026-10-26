I found one serious bug: a project-authorization bypass caused by double URL-decoding of resource identifiers. I read all the code under `repo/service`, plus the config files and `docs/provider.md`. I did not read the other docs or `tests/test_registry.py`, `tests/test_values.py` and `tests/test_host.py`. I did not run anything, so the exploit below comes from reading the code, not from running it.

## High: project access check bypassed by double decoding

- **Where:** `service/client.py:7-8`, `service/references.py:15`, `service/provider.py:16-17`.
- **Cause:**
  - `References.parse` decodes the resource identifier once, then rejects `..` segments.
  - `Client.wire_locator` returns that already-decoded locator without re-encoding it.
  - `Provider.decode_locator` then decodes it a second time and runs `normpath`.
  - `docs/provider.md` says the provider expects a URI-encoded locator and decodes one layer. The client breaks that contract.
- **Exploit:** `mira` holds `desk-view`, which only has access to `north/general`. Calling `resource.read` with `project='general'` and `resource='a/%252e%252e/%252e%252e/vault/budget'` proceeds as follows:
  1. `References.parse` decodes the resource to `a/%2e%2e/%2e%2e/vault/budget`. No segment is literally `..`, so the check passes.
  2. `Policy.require` checks membership of `general`, which `mira` has.
  3. The locator `/general/a/%2e%2e/%2e%2e/vault/budget` goes to the provider.
  4. The provider decodes it to `/general/a/../../vault/budget`, and `normpath` turns that into `/vault/budget`.
  5. The row `north/vault/budget` is returned, though only `operator` is a member of `vault`.
- **Reach:** `resource.head` is affected the same way. This breaks the project boundary within a tenant. The tenant is passed separately, so I don't see a cross-tenant path.
- **Related bug:** `/general/release%20notes` is stored as a literal-percent name, and the client can't reach it. Sending `release%2520notes` gets decoded twice and becomes `release notes`, which is not found.
- **Fix:**
  - Make `Client.wire_locator` return `quote(reference.locator, safe='/')`. `list_project` already quotes its prefix, so this makes the two paths consistent.
  - Add regression tests for `%252e%252e` traversal and for the literal `release%2520notes` case.
  - Consider rejecting any resolved locator that falls outside its project in `Provider.get`, as defense in depth.

## Medium

- **No per-principal session limit** (`sessions.py:28-32`): one valid token can open sessions until `session_capacity` (64) is reached. That blocks every other user with `Conflict`. Add a per-credential cap.
- **Failed packets are not journaled** (`host.py:31-32`): a bad packet makes `Packet.parse` raise before the `try`, so it never reaches the journal. A bad session ID also raises before any journal entry. Rejected calls therefore leave no record. Decide whether that is intended.
- **Missing arguments give `internal` errors** (`routes.py:12,23`): `args['project']` raises `KeyError` when the argument is absent. The caller sees `internal` instead of `invalid`, and the audit log records it as a generic failure. Validate required keys explicitly.

## Low

- **`tools()` ignores shutdown** (`host.py:24`): it skips the `closed` check that `open` and `invoke` do. After shutdown the session table is cleared, so it only fails because the session lookup fails.
- **`batch` doesn't stop early** (`host.py:41-48`): it continues after a failed item and journals each one. That is fine, but it should be documented.
- **Tokens are stored in plaintext:** the credential table is hard-coded in `identity.py`, and `Session` keeps the raw token. This is acceptable for the local fixtures, but it needs replacing before any real use.
- **Unused settings:** `Settings.result_capacity` and `retry_attempts` are validated but never used.
- **`Discovery.describe`:** it has an inline import, and I didn't see anything call it.
- **Catalog schemas:** `config/tools.json` declares `"input": {"type": "object"}` for every tool. Clients get no argument schema (`project`, `resource`, `cursor`), so a schema with required fields would help.

## Tests

`tests/test_resources.py` covers only the happy paths: a nested read and a head call. It has no test for encoded traversal, cross-project access, or the literal-percent resource, which is why the high-severity bug isn't caught.
