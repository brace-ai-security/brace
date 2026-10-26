# Host interface

The host loads the configured factory, keeps one returned registry for its
lifetime, and calls call(tool, token, arguments, request_id). Arguments are JSON-
compatible values. Every call supplies its own credential, even when a host
retains a session. The credential table is immutable for a local instance except
for disabled IDs. Credential scopes bound each token's delegation, including
when two credentials identify the same subject.

The registry is an in-process MCP-shaped tool component. No MCP wire transport,
SDK, proxy, browser, network listener or external policy service is supplied.
The host must not replace the original caller credential with a service token.
Typed errors cross this interface; their network representation is not supplied.
