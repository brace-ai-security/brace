I found no exploitable vulnerability in the shipped code, only hardening gaps and a few places where the code and README differ. I only read the files; I ran nothing, including the tests. I didn't open `archive/proxy.mjs`, the tests, `docs/`, `notes/` or `research/`. The README says the archive isn't reachable from `bin/serve.mjs`, and I only confirmed that for the files I did read.

## What I checked and found sound
- **Project isolation:** `handle()` validates `body.project` and runs `authorizeProject` before any route logic (`src/controller.mjs:9-10`). `destination` must equal the authorized project (`src/publication/plan.mjs:2`), and the plan then uses `project` itself.
- **Path traversal:** project and document IDs match strict anchored regexes (`src/validation.mjs`) and are checked again in `src/storage/documents.mjs`. No user-supplied path reaches `join` unchecked.
- **Tool dispatch:** the allowlist check runs before the lookup, and `Object.hasOwn` guards the lookup (`src/tools/dispatch.mjs:4-5`). `erase` is unreachable with the production config (`allowedTools` is `status` and `refresh`).
- **Source URL:** it checks protocol, credentials, hostname allowlist and port, and the `remote` field must match the approved URL. The adapter doesn't follow redirects, so a redirect can't point it at another host.

## Findings

**1. SSRF depends on DNS, which the code doesn't control (medium, deployment-dependent).**
- `inspectSource` checks only the hostname string. `retrieve` then resolves it again, and nothing pins or validates the resulting IP (`src/adapters/http.mjs:8`).
- If `assets.example.test` resolves, or is rebound, to a private address, the relay fetches it and returns the body to the caller (`src/source/collect.mjs:6-10`).
- The README admits no pinning or egress firewall exists. Before production, add an egress restriction or a resolve-then-check-then-connect step that rejects private, loopback and link-local addresses.
- Plain `http:` is also allowed for the allowlisted host. That exposes the content to tampering on the network path, and the relay returns it as-is.

**2. The audit trail isn't durable (medium).**
- `eventFor` only builds an object that goes back to the client (`src/audit.mjs`). Nothing is persisted or sent anywhere, so overwrites and source fetches leave no server-side record.
- The event doesn't include `actor.subject`, so even a gateway that logs responses can't tell who acted. Add the subject to the event and write it to a real sink.
- Publication also silently overwrites existing documents with no versioning (`src/storage/documents.mjs:7`). That matches the README, but together with the missing audit trail it can't be undone or traced. Any project member can overwrite any document in that project.

**3. Authentication weaknesses (low to medium).**
- The gateway token is compared with `!==` (`src/identity.mjs:2`), which isn't constant-time. Use `crypto.timingSafeEqual`.
- The token is committed in `config/production.json`. The README says it's synthetic, but the launcher reads this file directly, so a real deployment would put a real secret in the repo. Load it from the environment or a secret store.
- The relay trusts the `x-relay-identity` header whenever the token matches. Everything rests on the gateway stripping those headers, which is unverified. Loopback binding limits this to local processes, and any local process that knows the token can claim any project.
- There's no check that the token is configured. If `gatewayToken` were `undefined`, a request with no token header would pass, because `undefined !== undefined` is false. Fail at startup if it's missing or empty.

**4. Resource and robustness gaps (low).**
- The adapter's `setTimeout(2000)` is an idle-socket timeout, not a total deadline. A slow-drip upstream can hold a request open well past two seconds. The 16 KB cap works.
- `readJson` and `createServer` set no request or header timeouts (`src/wire.mjs`, `src/server.mjs`). Slow-loris is mostly a gateway concern but worth setting.
- `readJson` concatenates chunks as strings with `+=`, so a multi-byte character split across chunks can corrupt text. Use `request.setEncoding('utf8')` or collect Buffers.
- No HTTP method is enforced, and the route is matched on the full `request.url`, so `/tools/run?x=1` returns 404.
- The server never checks the route before project authorization. An unknown route returns 400 or 403 rather than 404, and 404 only appears for authorized projects.
- Several client errors get the wrong status. Malformed identity JSON, bad body JSON and validation errors return 400 by default, and the raw `error.message` goes to the client. That includes `JSON.parse` messages and `source too large`. Upstream failures should map to 502 or 504 with generic text.
- Writes aren't atomic. `writeFile` can leave a truncated document if the process dies mid-write. Write to a temp file and rename it.
- `mkdir` and `writeFile` follow symlinks. The README says the tree has none, so this matters only if that assumption breaks.

**5. Design and maintenance notes.**
- `erase` ships in the same module as the public operations and uses `rm -rf` on a project directory. The allowlist is the only barrier, so a config change enables it for every project member. The README says there is no project-admin privilege. Move `erase` out of the public bundle, or require a separate privilege.
- `tools/inventory.mjs` accepts `--development` and only prints configuration. That's harmless, but it reads config via a relative URL, so it breaks if run from elsewhere.
- `config/development.json` selects the recording adapter. Nothing stops someone launching `serve.mjs` with a dev config swapped in. That's fine as long as production is deployed from the checked-in config.

## Suggested priority
1. Add egress or DNS controls and a private-IP check for source fetches.
2. Add a real audit sink that records the subject.
3. Do the config hardening: validate the token at startup, compare it in constant time, and keep the secret out of the repo.
4. Fix the HTTP hygiene items: error mapping, timeouts, atomic writes and byte-safe body reading.
