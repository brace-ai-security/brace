I found three real problems in `service/routes.mjs`, plus a few smaller ones. I only read the code and didn't run anything.

## Findings

**1. An authenticated request can crash the process (high)**
- `sessions` is a plain `{}` (`routes.mjs:5`). The lookup `sessions[req.headers['mcp-session-id']]` (lines 17 and 22) also finds inherited keys.
- A header such as `mcp-session-id: constructor` or `toString` returns a truthy `Object.prototype` member, so the `!session` check passes. `session.handleRequest` is then `undefined`, and the call throws a `TypeError`.
- The handlers are `async`, and Express 4.22.2 doesn't catch rejected promises from them. The README says Node 20 runs with default unhandled-rejection behavior and the app has no hooks, so the process exits.
- Anyone holding the gateway key can do this. The same crash happens if the trusted `handleRequest` ever rejects, for example on a client abort or a malformed request.
- **Fix:** use a `Map`, or `Object.create(null)` plus `Object.hasOwn`. Wrap each handler body in `try/catch`, and send a 500 only if `!res.headersSent`. Also check that the session ID is a string.

**2. Sessions are never removed (medium)**
- `DELETE /mcp` forwards to the transport but never deletes the entry from `sessions`. Nothing else expires entries either.
- `POST /mcp/init` has no cap or rate limit, so memory grows without bound. Each entry holds a transport object.
- **Fix:** on a successful DELETE, call `sessions.delete(id)`. Also add a transport close hook, an idle TTL, and a maximum session count.

**3. There is no `POST /mcp` route (functional, medium)**
- Only `POST /mcp/init`, `GET /mcp` and `DELETE /mcp` are registered. Client-to-server JSON-RPC messages have no route. If this is meant to be a Streamable HTTP MCP endpoint, it can't receive requests.
- No body parser is mounted either. That is fine if `handleRequest` reads the raw stream, but it should be confirmed.
- Either add the POST handler with the same session lookup, or document that the transport handles messages some other way.

**4. The bearer check isn't constant-time (low)**
- `req.headers.authorization !== \`Bearer ${secret}\`` (line 7) is a plain string comparison, which leaks timing information in principle.
- With a single trusted principal and a high-entropy secret, the risk is small. It is still cheap to fix with `crypto.timingSafeEqual` on equal-length hashes of both values.

**5. Minor issues**
- The 401 response has no `WWW-Authenticate` header.
- There is no failed-auth rate limiting. The README puts ingress policy under the host.
- The session lookup is copied into two handlers. Pull it into a helper so the fix for item 1 lives in one place.
- `GATEWAY_KEY` is read once at registration. That is fine, but rotating the key needs a restart.

## Out of scope
The README assigns these to the host, so I didn't assess them:
- `createTransport` internals
- the secret store
- audit logging
- framing limits
- process supervision

Session IDs are random UUIDs and are only correlation handles behind the auth gate, so I don't count their guessability as an issue.
