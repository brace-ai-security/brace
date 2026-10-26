# Local host client

service.launch.build_host loads local service and host settings and a tool catalog.
It keeps one registry across all local host sessions. open(token) returns an opaque
session handle. tools(handle) returns discovery metadata. invoke(handle, packet)
accepts {id, tool, arguments}; a packet cannot supply a replacement credential.
The saved credential is authenticated again for each invocation. batch executes
one to eight packets serially and returns each result or generic typed error.
This local JSON-compatible packet API does not implement MCP wire negotiation.

history(handle, after, limit) returns the current subject's journal metadata in
its tenant. Journal fields contain argument names, never argument values or result
bodies. Shared subject credentials see that subject's history. Session expiration
and close remove the transport handle; they do not cancel owned application jobs
or undo completed operations. shutdown clears handles and stops further invokes.
Rebuilding the host discards its registry and all local application state.
