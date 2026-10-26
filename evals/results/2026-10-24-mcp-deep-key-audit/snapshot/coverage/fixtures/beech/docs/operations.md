# Local operation

The source tree contains the entire request dispatcher. There is no HTTP server,
reverse proxy, network ACL, database RLS, or external policy engine in this bundle.
The MCP-shaped registry is called directly by a host adapter with a session token.
The host adapter is assumed to forward the authenticated token and original object;
it does not authorize resource identifiers or rewrite arguments.

Use `service.bootstrap.build()` with its default settings to obtain the registry.
The returned tools are immediately callable via `Registry.invoke`. Startup imports
seed records into process memory. A restart resets all changes and audit events.
No environment variables enable additional registration or change authorization.

Audit events contain a subject, action, count and request ID. Record bodies and
session tokens are not written to the audit queue. Queue overflow drops the oldest
event. Operators must collect events before shutdown if retention is required.

Only the local profile is supplied. Production credential provisioning, network
transport, persistence, log shipping, and rate limiting remain outside this sample.
Those unknown deployments must not be assumed to repair supplied access checks.
All identities, tokens and records in the seed are synthetic demonstration data.
