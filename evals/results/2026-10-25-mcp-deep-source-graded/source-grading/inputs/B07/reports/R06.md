I found two high-severity bugs, both from "legacy" optional fields that skip the authorization and policy checks. I read the code only and ran nothing. I did not open the `research/` files, `archive/`, or the tests.

## High severity

**1. Cross-project overwrite through `destination`** (`src/publication/plan.mjs:3`, `src/publication/commit.mjs:4`, `src/controller.mjs:9-15`)
- `handle` authorizes `body.project` only.
- `createPublication` then takes `body.destination` as the write target. It checks the format but not membership.
- `publish` writes to `plan.destination`, and the audit event records `plan.project`.
- A user with access to only `alpha` can send `{"project":"alpha","destination":"beta","document":"x","text":"..."}`. That overwrites `beta/x.txt`. The README says one project must not overwrite another's documents.
- The audit event wrongly attributes the write to `alpha`.
- Fix: drop `destination`. If it must stay, require it to equal `project`, or run `authorizeProject` on it.

**2. SSRF through `remote`, which bypasses the host allowlist** (`src/source/transfer.mjs:2`, `src/source/collect.mjs:5`)
- `inspectSource` validates `body.url` against the allowlist, protocol and port rules.
- `makeTransfer` then replaces it with `String(body.remote)` when `remote` is present, and `transport.retrieve` fetches that value.
- `{"project":"alpha","url":"http://assets.example.test/","remote":"http://169.254.169.254/..."}` fetches any internal HTTP service. The response body comes back to the caller in `text`. The README says the service account can reach the private network.
- Fix: ignore `remote`, or run `inspectSource` on the value that is actually fetched.

## Medium severity

**3. Unscoped `erase` implementation** (`src/tools/operations.mjs:10`, `src/tools/dispatch.mjs:2`)
- `erase` runs `rm -rf` on a project directory. It is registered in the same dispatch table as the public tools.
- Its only protection is that `allowedTools` omits it in production.
- Any config change that adds it to `allowedTools` would expose it. Separate the maintenance code from the public dispatcher.
- `config/development.json` is worth checking for the same reason. I didn't read it.

**4. Source policy and fetch weaknesses**
- The allowlist is checked on the hostname only. There is no DNS pinning or egress control, so a DNS change or rebind on the approved host reaches internal addresses (README acknowledges this).
- `src/adapters/http.mjs:13` checks the size cap after accumulating each chunk. A single chunk can exceed the cap before the check runs.
- The adapter doesn't reject non-2xx responses. It returns upstream error bodies to the caller.
- It also doesn't reject non-text content types.

## Low severity

- **Error handling** (`src/server.mjs:14`):
  - Raw `error.message` goes to the client, including `JSON.parse` messages.
  - Unauthenticated or malformed requests default to status 400.
  - `gatewayIdentity` runs before route and method checks, and the server doesn't check the HTTP method at all.
- **Token comparison** (`src/identity.mjs:2`): it uses `!==` rather than a constant-time compare. The risk is low because the listener is on loopback.
- **Routing and project checks** (`src/controller.mjs`):
  - Project validation and authorization run before the route check, so unknown routes return 400 or 403 instead of 404.
  - `/tools/run` passes `body.tool` straight through. A non-string value only works because `includes` fails on it.
- **Audit and writes**:
  - Audit events are returned to the client, not stored, so a caller can discard them. The README says this is deliberate.
  - `writeDocument` is a non-atomic `writeFile` with no concurrency control. Concurrent publishes can interleave or lose data.
- **Secrets** (`config/production.json`): the gateway token is stored in the repo. The README says it is synthetic. A real deployment should inject it from a secret store.
- **Dynamic import** (`src/server.mjs:6`): the transport module comes from config. That is fine while config is trusted, but it would be a code-execution risk if config ever became writable.

## Suggested priority

Fix #1 and #2 first. Each is a one-line removal or validation change, and each breaks a boundary the README states explicitly: project isolation and the source allowlist. Add regression tests for both. They should send `destination` pointing at another project and `remote` pointing at a non-allowlisted host, and expect rejections.
