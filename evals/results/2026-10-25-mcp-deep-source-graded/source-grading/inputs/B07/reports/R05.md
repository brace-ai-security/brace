I found two high-severity authorization and SSRF bugs in the request path. I read the `src/`, `config/`, and `bin/` code and the README. I didn't open the tests, `archive/`, `tools/`, `docs/`, `notes/` or `research/`, and I ran nothing.

## High severity

**1. Cross-project overwrite through `destination`** (`src/controller.mjs:9-15`, `src/publication/plan.mjs:2-4`, `src/publication/commit.mjs:4`)
- `handle` authorizes only `body.project`.
- `createPublication` then accepts a separate `body.destination`. It checks the format but never checks membership.
- `publish` writes to `plan.destination`.
- A user with access only to `alpha` can send `{project:"alpha", destination:"beta", document:"x", text:"..."}`. That overwrites `beta/x.txt`.
- The README says one project must not overwrite another's documents, so this breaks the stated contract.
- The audit event records `plan.project` (`alpha`), so it also hides the real target.
- **Fix:** drop `destination`, or reject it unless it equals `project`. If it must stay, call `authorizeProject(actor, destination)`. Write to the authorized project value only.

**2. SSRF through `remote`, which bypasses the host allowlist** (`src/source/transfer.mjs:2-3`, `src/source/collect.mjs:4-5`)
- `inspectSource` validates `body.url` against the allowlist.
- `makeTransfer` then uses `String(options.remote)` in preference to the approved URL.
- `collectSource` fetches `transfer.url`, so the allowlist, port, and credential checks never apply to the URL actually fetched.
- Any project member can send `{project:"alpha", url:"http://assets.example.test/", remote:"http://169.254.169.254/..."}`. The relay fetches that URL, and the README says its service account can reach the private network.
- The response text is returned to the caller, so this is a full-read SSRF.
- **Fix:** ignore `remote`, or require it to equal `approved.url`. Always fetch `approved.url`. Re-validate inside the transport as defense in depth.

## Medium and low severity

- **No egress controls:** DNS is not pinned and there is no egress firewall. The allowlisted host can resolve to or rebind to an internal address, and the README acknowledges this. Resolve the host once, reject private, loopback, and link-local ranges, and connect to the vetted IP. Also enforce egress at the network layer.
- **Audit is not durable:** `eventFor` events are only returned to the client. Nothing is recorded server-side, so the two bugs above would leave no trace. Write events to a server-side log or audit sink. I didn't read `audit.mjs` itself.
- **Gateway trust:** security depends on an external gateway stripping `x-relay-*` headers.
  - `src/identity.mjs:2` compares the token with `!==`, which isn't constant-time. Use `crypto.timingSafeEqual`.
  - The token sits in the committed `config/production.json`. Load it from a secret store.
  - A malformed identity header gives a 400 rather than a 401.
- **Server hardening:**
  - `src/server.mjs` doesn't check the HTTP method.
  - It matches `request.url` exactly, so a query string causes a 404.
  - It returns raw `error.message` text to clients.
  - It sets no request timeouts.
  - `readJson` sizes the body by string length rather than raw bytes, but it does cap the size.
- **HTTP adapter:** `src/adapters/http.mjs` doesn't re-check the allowlist. The 2-second timeout is an idle-socket timeout, so a slow trickle of data can run longer than 2 seconds. It also lets the server see `http:` URLs, which allows plaintext fetches.
- **`erase` is dangerous but currently unreachable:** it runs `rm -r` with no authorization of its own. The allowlist check in `src/tools/dispatch.mjs` is the only barrier. Move it out of the public module so adding `erase` to config can't expose it.
- **Concurrency:** writes are not atomic. Concurrent publishes to the same document can interleave, and a crash can leave a partial file. Write to a temp file and rename it.

The path-traversal protections look sound. The identifier regexes forbid `/` and `.`, and the storage layer validates them again. The tool allowlist check runs before the lookup, and `Object.hasOwn` guards the lookup.

I can draft patches for the two high-severity bugs and add regression tests if you want them.
