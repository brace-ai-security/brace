# HTTP, OAuth and gateway review

Use for server HTTP handlers, remote clients and gateways. Record the negotiated
revision; [official versioning](https://modelcontextprotocol.io/specification/versioning)
identified 2026-07-28 on 2026-10-22. Recheck before claiming a newer/current version.
Protocol authorization is optional; BRACE requires authorization for protected access.

## Follow the request and credentials

1. Locate every handler and middleware path, including OAuth endpoints, health/debug
   routes, subscriptions, background work and dynamic/wrapper calls. Distinguish
   public third-party backends from internal gateway-only services; private networks
   and mTLS are a deployment pattern, not universal protocol requirements.
2. Trace Origin/Host checks, request version/metadata parsing and limits through
   [Streamable HTTP](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http).
   For matching protocol revisions, compare routing/authorization headers with the
   body; check ambiguity/error handling before dispatch. Do not project newer
   header/session rules onto older negotiated revisions.
3. Trace OAuth discovery, exact issuer binding, saved registrations, redirect policy,
   PKCE/resource indicators and token verification. Confirm actual issuer, audience,
   expiry and scopes at each protected resource. A validated signature is not an
   audience check. Inspect custom headers and 307/308 bodies as well as Authorization.
4. Separate gateway frontend credentials from backend credentials and their audiences.
   A backend needs its own supported authorized credentials, not passthrough of a
   frontend token. Distinguish workload identity from explicitly delegated user/system
   authority. Neither identity nor broad OAuth scopes establish the approved business task.
5. Trace effective operation/resource/tenant/argument authorization after adapters,
   auth hooks and path normalization. Review missing claims, errors and outage
   branches, raw API paths and code/CLI alternatives for the same policy.
6. Inspect per-request/server/transport construction, shared mutable state, cache keys,
   task ownership and revocation propagation. Shared JSON-RPC IDs are correlation,
   not client identity. Cache hits and resumed tasks need current authorization.
7. Trace body/batch/element limits before parsing and expensive validation. Inspect
   remote schema references and helper fetches for network/file I/O, timeouts and
   re-resolution. Network boundaries must cover decoders and token counters too.

## Proposed evidence

For each relevant boundary, specify one valid request and concrete denial cases:
wrong issuer/audience/tenant, forged metadata, alternate route, cross-origin redirect,
concurrent client-ID collision, cache/handle reuse, oversized batch, unavailable
authorizer/auditor and blocked egress. Record who can run these against disposable
fixtures. A middleware declaration or HTTP 401 without checking destination state
does not establish deployment effectiveness.

Use [advisories.md](advisories.md) to check package-specific fixes and settings.
Sender constraint, token exchange and centralized IdP extensions apply only where
supported/adopted; do not invent issuer capabilities or classify their absence as
a universal MCP protocol violation.
