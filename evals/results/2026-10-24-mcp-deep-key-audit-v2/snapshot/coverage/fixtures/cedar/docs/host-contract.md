# Host contract

`invoke(name, token, arguments, request_id)` is the only authenticated public
entrypoint. Hosts may choose the request ID; it has no authorization meaning.
The session table maps opaque synthetic tokens to immutable identities. Callers
control tool names and the complete arguments object, but not identity fields.

An unknown tool or inactive session is rejected before the handler executes.
Handlers return ordinary Python dictionaries or lists. Exceptions remain typed:
AccessDenied is a policy refusal, InvalidRequest is malformed input and NotFound
is a missing record. A host may translate these to transport errors unchanged.

The registry description is metadata, not an authorization decision. Tools must
perform their own permission checks. There is no wildcard tool or fallback route.
Compatibility manifest helpers are imported only by offline consumers and are not
reachable through default registration. No supplied route evaluates record text.
