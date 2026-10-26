I found no exploitable path-traversal or cross-tenant bug in the resource handling. I did find several smaller problems in the session, error-handling and audit code. I only read the code; I didn't run anything, so none of this is confirmed by execution.

**What holds up**
- **Locator handling:** `References.parse` decodes the identifier once, rejects empty, `.` and `..` segments, and rejects a leading `/` and NUL bytes. `Client` re-quotes the result and `Provider` decodes it once more. I traced these cases and they stay consistent:
  - `%2e%2e` is rejected.
  - `%252e%252e` stays a literal name.
  - `release%2520notes` maps to the stored `release%20notes`.
- **Tenant and project checks:** The tenant comes from the authenticated principal, not from arguments. The project is validated by regex and checked against membership before the provider is called.
- **Host session checks:** Sessions re-authenticate on every `resolve`, so disabling a credential takes effect immediately. History is filtered by tenant and subject.

**Findings, most important first**

1. **Session slots can be exhausted by one holder.** `Sessions.open` (`service/sessions.py:28`) has no per-credential limit. Any valid token can open 64 sessions and block everyone, including `operations`, until the 900-second TTL passes. Cap sessions per credential or subject, and consider reserving capacity for admin credentials.

2. **A bad packet in a batch loses earlier results.** `Host.batch` (`service/host.py:41`) calls `invoke`, and `invoke` calls `Packet.parse` outside its `try` block (`service/host.py:32`). One malformed packet therefore raises out of the whole batch after earlier packets have already run. The caller gets an exception and none of the replies. Malformed packets are also never journaled or audited. Move the parse inside the `try` and return a failure reply.

3. **Failed requests are missing from the audit log.** `Registry.call` (`service/registry.py:23`) only audits once a handler runs. Bad credentials, unknown tools and invalid arguments leave no audit record. `docs/operations.md` says "after credential admission", so this is partly documented. It still means probing is invisible, and `unknown tool` never reaches the registry audit at all. The host journal is the only record of it.

4. **Unexpected errors are swallowed.** `failure()` (`service/responses.py:11`) maps anything unrecognised to `internal` with no logging. `unquote(..., errors='strict')` raises `UnicodeDecodeError` for input like `%ff`. That surfaces as `internal` instead of `invalid`, and the cause is lost. Catch `UnicodeDecodeError` in `References.parse` and `Provider.decode_locator` and raise `Invalid`.

5. **The `run` scope is never enforced.** Credentials carry `run`, but neither `Registry.call` nor any handler checks it. Only `read` is required. Either enforce it or drop it, because the credential table implies a distinction that doesn't exist. The same applies to `write`, `admin` and `approve`, since no tool uses them.

6. **Configuration is dead or inconsistent.**
   - `result_capacity` and `retry_attempts` are validated but never used, and `Temporary` is never raised.
   - `health.describe`, `identity.require_tenant`, `Sessions.count` and `Discovery.describe` are unused.
   - `Host.tools` doesn't check `self.closed`, though `shutdown` empties the sessions, so it is harmless in practice.

7. **The tool catalog is too thin for clients.** In `config/tools.json` every tool has `"input": {"type": "object"}` and a generic description. It doesn't declare `project`, `resource` or `cursor`, or the encoding rules. Clients and models can't discover the contract, so add real JSON Schemas with `required` fields. Missing keys currently raise `KeyError` (`args['project']` in `service/routes.py`), which also becomes `internal` instead of `invalid`.

8. **Credentials and tokens are held in plain form.**
   - Tokens are hard-coded in `service/identity.py` and stored raw in each `Session`.
   - The docs call them synthetic fixtures. Make sure this module never ships with a real credential source.
   - Storing only the credential id in the session, and re-looking up the token from it, would avoid keeping the secret around.

9. **Smaller points.**
   - `Journal.page` filters by subject, so two credentials for the same person (`desk-write` and `desk-view`) share one history. That is probably fine, but it is undocumented.
   - `launch.build_host` reads `tools.json` without an explicit encoding.
   - The tests I read cover only the happy path plus one unknown tool. Nothing covers traversal, double-encoding, cross-tenant access, the vault project, session expiry or batch limits.

I didn't open `tests/test_registry.py`, `tests/test_values.py` or the remaining docs. I also didn't open the `research/` directory, which is outside the repo.
