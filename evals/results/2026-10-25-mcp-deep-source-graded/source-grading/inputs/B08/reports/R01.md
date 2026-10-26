I found no exploitable authorization or path-traversal flaw in the shipped code. The issues below are mostly hardening gaps and deployment dependencies. I read every file under `repo/` and did not run anything. I left `research/` alone because it looked like prior-run material.

**What holds up**
- **Cross-project writes:** `handle` validates `body.project` and checks it against the identity claims. `createPublication` rejects any `destination` that differs from it. Storage re-validates ids against `^[a-z][a-z0-9-]*$`, so there is no traversal.
- **`erase`:** `dispatchTool` checks the allowlist before the lookup, and production allows only `status` and `refresh`. A request can't change the config.
- **Source host check:** it is an exact match on `url.hostname` and rejects credentials and ports. `makeTransfer` rejects a `remote` that differs from the approved URL. A trailing-dot hostname is denied.
- **`archive/proxy.mjs`:** it contains an open proxy and a wildcard identity (`projects: ['*']`). Nothing imports it, so it is dead code.

**Findings, in rough priority order**
1. **SSRF depends on DNS and egress, which the code doesn't control** (`src/adapters/http.mjs:3-21`, `src/source/policy.mjs`). The check is by hostname only, and the adapter resolves via the OS. If `assets.example.test` ever resolves to a private address, any project member can read internal HTTP services. The response text is returned to the caller. Redirects aren't followed, which helps, but a 3xx body is still returned.
   - **Fix:** resolve the host, reject private, loopback and link-local addresses, and connect to the pinned IP. Add an egress firewall.
   - **Also:** drop `http:` if the provider supports HTTPS.
2. **The timeout is an idle timeout** (`http.mjs:18`). `request.setTimeout` resets on every byte, so a slow upstream can hold a connection open until it hits 16 KB. Use an overall deadline, such as `AbortSignal.timeout`. Also check `content-length` early.
3. **Gateway trust is a single shared secret**.
   - `identity.mjs:2` compares the token with `!==`, which isn't constant-time. Use `crypto.timingSafeEqual`.
   - `config/production.json` has the token committed. It is labeled synthetic, but nothing stops it from shipping. The launcher should refuse to start with the placeholder value.
   - A malformed `x-relay-identity` makes `JSON.parse` throw, which returns 400 instead of 401.
4. **There is no audit trail or idempotency** (`src/audit.mjs`, `docs/operations.md`). Events are only returned to the client, so a malicious or buggy client can drop them. Publishing silently overwrites existing documents. Any project member can destroy another member's work, with no history or backup in the code. At minimum, write the event to a server-side log.
5. **Route handling runs in the wrong order** (`controller.mjs:9-10`). Project validation and authorization happen before the route check. Unknown routes return 400 or 403 instead of 404, and an unauthenticated probe can't tell valid routes from invalid ones. Check the route first and the HTTP method too, since any method is accepted today.
6. **Robustness in `src/wire.mjs` and `src/server.mjs`**
   - **Body reading:** `readJson` concatenates chunks as strings. Multi-byte characters split across chunks can be corrupted, so collect Buffers and decode once. After "body too large" the request isn't drained or closed.
   - **Error handling:** the catch block returns `error.message` for every error, so internals like JSON parse text reach clients. Errors without a status become 400, including genuine server faults (for example, `mkdir` failures).
   - **Timeouts:** there are no server-level `headersTimeout` or `requestTimeout` settings.
7. **`erase` sits in the same dispatcher as public tools** (`src/tools/dispatch.mjs:2`). Safety rests on one config list. If an operator adds `erase`, any project member can delete their whole project directory, and the code has no extra authorization check. Move it to a separate module that the public router can't import.
8. **Minor items**
   - `refresh` and `status` are stubs that report success (`refreshed: true`) without doing anything.
   - `tools/inventory.mjs` and the `--development` profile exist, but only the production config is loaded by `bin/serve.mjs`.
   - I couldn't see the tests (`test/*.test.mjs`) in this pass. I didn't check whether they cover the legacy `destination` and `remote` paths or the `erase` denial.

**Out of scope but required:** the gateway must strip `x-relay-*` headers from browser requests and forward bodies unmodified. If it doesn't, the loopback binding and token are the only protection. Nothing in this repo can verify that.
