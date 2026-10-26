I reviewed `repo/service/routes.mjs`, the only code file, along with the README, `package.json` and `launch.json`. I didn't run anything. I took the README's scope limits as given. `createTransport`, the gateway and secret store, host audit, and framing and ingress limits are outside this review.

## Findings

**1. Sessions are never removed (medium).** `routes.mjs:5,12,21-25`
- Entries are added to the `sessions` Map in `/mcp/init` and never deleted.
- `DELETE /mcp` hands the request to the transport but doesn't call `sessions.delete(id)`. A closed session stays in memory and its ID stays valid.
- There is no TTL, idle timeout or cap on session count. Every `init` call allocates a transport, so memory grows without bound.
- Only the authenticated principal can reach this, so it's a resource leak more than an attack.
- Fix: delete the entry after a successful `DELETE`, add an idle expiry, and cap the number of sessions.

**2. There is no `POST /mcp` route (medium, functional).** `routes.mjs:10-25`
- The only routes are `POST /mcp/init`, `GET /mcp` and `DELETE /mcp`.
- Streamable HTTP MCP sends client JSON-RPC messages as `POST /mcp`, and nothing here handles that.
- Unless the host mounts it elsewhere, clients can't send requests.
- If it is meant to exist, add it with the same session lookup and `route()` wrapper. The README says this repo is the complete implementation of the described paths, so check that this is intentional.

**3. The secret comparison isn't constant-time (low).** `routes.mjs:7`
- `req.headers.authorization !== \`Bearer ${secret}\`` leaks timing information.
- Fix: hash both values and compare them with `crypto.timingSafeEqual`.
- Nothing rate-limits or logs failed auth attempts either. Those may belong to the host, which the README says is out of scope.

**4. Missing or invalid session IDs return 404 (low).** `routes.mjs:17-18,22-23`
- A missing `mcp-session-id` header is a malformed request, so it should return 400. 404 fits only an unknown ID.
- Clients can't tell "you forgot the header" from "your session expired".

**5. Error handling relies on Express defaults (low).**
- The `route()` wrapper correctly forwards async rejections to `next`, so there's no unhandled-rejection risk in these routes.
- No error handler is registered here. Express's default handler prints stack traces unless `NODE_ENV=production`.
- Confirm the host sets `NODE_ENV=production` or registers its own handler.
- `/mcp/init` is synchronous, so Express 4 catches a throw from `createTransport()` and returns a 500. Nothing leaks, but no transport is created either.

**6. Minor points.**
- The `Bearer` scheme match is case-sensitive, which is stricter than RFC 7235 requires. That's acceptable for a single trusted client.
- `GET` and `DELETE` repeat the same session-lookup code. A small `getSession` helper would remove the duplication.
- The code is correct on the following:
  - Auth middleware is mounted on `/mcp`, which covers `/mcp/init` and everything under it.
  - It runs before any dispatch.
  - The app fails closed at startup if `GATEWAY_KEY` is unset.
  - Session IDs come from `randomUUID`.

## Out of scope, needs host evidence
- TLS and ingress policy.
- Request size and framing limits.
- Audit logging.
- Process supervision and restart behavior.
- How `GATEWAY_KEY` is stored and rotated.
- Whether `createTransport` cleans up after itself, which affects finding 1.
