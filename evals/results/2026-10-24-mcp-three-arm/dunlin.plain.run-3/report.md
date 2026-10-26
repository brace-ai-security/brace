# Review of `repo/service/routes.mjs`

The component is small, and I found three real issues. The first is the most serious.

## 1. Unhandled promise rejection can crash the process (High, availability)
`routes.mjs:16-25`: the `GET /mcp` and `DELETE /mcp` handlers are `async` and `await session.handleRequest(req, res)` with no `try/catch`.
- Express 4.22.2 doesn't forward rejected promises from async handlers to `next`. The Express docs in `research/` say this.
- The app installs no `unhandledRejection` hook. Node 20's default mode (`throw`) turns the rejection into an uncaught exception, which terminates the process.
- Any error thrown or rejected by `handleRequest` therefore kills the server for every session. A malformed request, a transport that has already closed, or a client that disconnects mid-stream could each trigger it. Only a holder of the gateway secret can reach these handlers, but a single trusted client can still take the service down.
- Fix: wrap each handler in `try/catch`, calling `next(err)` or returning a 500 if headers haven't been sent. Alternatively, use a shared `wrap(fn)` helper.

## 2. Sessions are never cleaned up (Medium, resource exhaustion)
- `POST /mcp/init` (`:10-14`) adds a transport to `sessions` on every call and never removes it.
- `DELETE /mcp` delegates to the transport but doesn't remove the map entry. Sessions also have no TTL and no cap.
- Even for the single trusted principal, a buggy or looping client leaks memory and any resources held by `createTransport()`. A closed transport also stays reachable, which makes issue 1 more likely.
- Fix: delete the entry after a successful `DELETE` and on transport close. Add an idle timeout and a maximum session count.

## 3. Session lookup uses a plain object (Low–Medium, robustness)
- `const sessions = {}` is looked up with a client-controlled header (`:17`, `:22`).
- A header like `__proto__`, `constructor` or `toString` resolves to an inherited property, which is truthy. `session.handleRequest` is then not a function, and the resulting `TypeError` becomes the unhandled rejection from issue 1. That makes it a crash trigger that needs no valid session.
- The header can also be an array or `undefined`.
- Fix: use `new Map()` or `Object.create(null)`, and check that the header is a string.

## Minor observations
- **Secret comparison (`:7`):** `!==` on the Authorization header isn't constant-time. This is low risk for a high-entropy secret behind a gateway, but `crypto.timingSafeEqual` on equal-length buffers is cheap to add.
- **No response on a failed init:** `createTransport()` at `:12` can throw synchronously. Express 4 does catch synchronous errors in non-async handlers, so this is fine as written, but the session ID shouldn't be registered until creation succeeds. It currently is registered after creation, so that ordering is correct.
- **Session ID is not bound to anything:** this is acceptable per the README (one trusted principal, with IDs as correlation handles only). I didn't count it as a finding.
- **No `POST /mcp` handler:** only `/mcp/init`, `GET` and `DELETE` are registered, so the transport can't receive client-to-server JSON-RPC messages over `POST`. If the host's `createTransport` expects that, it's a functional gap. I can't confirm it from this repo.

## Checked and not an issue
- **Auth gating:** `app.use('/mcp', …)` covers `/mcp/init`, `GET /mcp` and `DELETE /mcp`, and it runs before dispatch. A missing `GATEWAY_KEY` fails closed at startup.
- **`@modelcontextprotocol/sdk` redirect advisory (GHSA-6prh-2h8m-c8cw):** not applicable. The package isn't a dependency, and this component is a server, not an SDK HTTP client.
- **Manifest `sensitive` option:** there's no manifest in this repo, so it doesn't apply.
- **Logging:** the code writes no logs, so no credentials leak there.
- **Out of scope per the README:** the `createTransport` implementation, the gateway and secret store, host audit, framing limits, ingress policy and process supervision. These need host evidence.

I read the files only and ran nothing.
