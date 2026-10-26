# Relay operations

## Deployment review

Provision a dedicated service account for the relay process.
Provision a document root owned by that account.
Keep the root outside the web server's executable directories.
Replace the synthetic gateway token with deployment configuration.
Bind the relay to the configured loopback address.
Deploy a gateway that strips browser-supplied relay headers.
The gateway must emit project memberships from an authoritative identity source.
Membership expiry is owned by the gateway and directory integration.
No directory client or token renewal implementation exists in this repository.
The relay does not call an identity service during individual operations.
An identity outage policy therefore belongs to the gateway deployment.

## Client operations

Contributors use the gateway to publish documents and collect source material.
The gateway supplies the user's current project memberships.
Clients select a project using the documented lowercase identifier.
Clients receive JSON responses for all supplied operations.
Publication and source collection return an event object on completion.
The tool route returns a small operation-specific status object.
There is no asynchronous polling or background-job identifier.
A successful response applies to the one submitted operation.
A failed operation does not yield a successful event response.
A caller should not treat a response timeout as proof that no write occurred.
No idempotency key is part of the supplied protocol.

## Document recovery

The document adapter writes one UTF-8 file per document identifier.
The file extension is always `.txt`.
The document identifier cannot contain a slash or dot.
The project identifier cannot contain a slash or dot.
The adapter recursively creates the selected project directory.
Document text is stored literally and is not evaluated by the relay.
There is no template engine, Markdown renderer, or browser preview in this service.
Future downstream renderers need their own content handling rules.
Backups and retention are deployment responsibilities.
The supplied code does not implement document history.

## Source collection diagnostics

The recording adapter is useful for inspecting selected URLs without network traffic.
It records the exact value passed to `retrieve`.
It does not emulate DNS, redirects, or TLS validation.
A recording-adapter test cannot prove production network isolation.
The production adapter selects HTTP or HTTPS from the URL protocol.
It rejects other protocols before making a request.
It uses the URL's host and port for the outbound request.
The host resolver is provided by the operating system.
Operational DNS changes take effect according to the host resolver configuration.
Requests carry no gateway token or identity header to the upstream.
The upstream body is returned as text rather than interpreted as JavaScript.
The supplied size and timeout limits apply to retrieval resource use.
Upstream connection failures are returned as operation errors.

## Tool inventory

The status operation returns a static ready state for the project.
The refresh operation returns a synchronous refresh acknowledgement.
Neither launches a command or deletes project data.
The maintenance erase operation removes a project directory recursively.
The production dispatcher denies that operation by name before lookup.
Adding erase to an allowlist would change the public capability boundary.
Such a deployment must have an explicit authorization review.
The request protocol cannot add entries to the configured allowlist.

## External boundaries

The gateway code is not part of the review input.
The content provider code is not part of the review input.
The host resolver and egress policy are not represented as enforcement modules.
The audit collector is not implemented here.
Deployment owners should retain a record of gateway and provider configuration.
Access reviews should cover current project memberships.
Network inventories should include the content provider and internal services.
The service package does not contain the deployment network inventory.
