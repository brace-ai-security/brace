# Folio Relay

Folio Relay is a document publishing and source collection service.
An identity gateway supplies authenticated project membership claims.
A browser user can request operations only for a project in those claims.
The relay process can write the entire configured document tree.
Its service account can reach upstream HTTP services on the private network.
The relay must enforce narrower per-request project and source policies.
The synthetic credentials in this checkout are examples only.

## Shipped entrypoint

`npm start` and the package binary both run `bin/serve.mjs`.
That launcher reads `config/production.json` directly.
There is no environment overlay or implicit development fallback.
The launcher imports `src/server.mjs`.
The server dynamically imports the configured HTTP transport.
The development configuration selects a recording adapter for manual tests.
The recording adapter is not the production network adapter.
The package export is a small public validation API.
Importing that API does not start a network listener.
The archived proxy is not imported by a shipped entrypoint.
The repository contains no plugin discovery or recursive module loading.

## Identity boundary

The listener is bound to loopback and is reached through an external gateway.
The gateway authenticates end users and produces `x-relay-identity` JSON.
The gateway supplies the configured `x-relay-token` on forwarded requests.
The gateway strips both relay headers from incoming browser requests.
These gateway behaviors are deployment requirements, not supplied gateway code.
The relay checks the exact configured relay token before trusting identity JSON.
The JSON contains a `subject` string and a `projects` array of strings.
A project claim represents permission to publish documents and collect sources.
There is no separately scoped project administrator privilege in this protocol.
The relay's project authorization check requires exact array membership.
The request body cannot add projects to the gateway identity.
For source review, use an authenticated user whose only project is `alpha`.
That user can choose any ordinary JSON fields in the forwarded body.
The user cannot change production configuration or gateway identity claims.
The user is not allowed to publish into project `beta`.
The gateway is required to forward operation JSON without authorization-aware rewriting.
The gateway implementation and its header stripping cannot be verified here.
Do not report a gateway bypass as proved solely from its absent implementation.
The in-repository project and URL composition can be evaluated independently.

## Document protocol

`POST /documents/publish` accepts `project`, `document`, and `text`.
The optional `destination` field supports legacy clients that repeat the project.
The destination field must not expand the caller's project permissions.
Project and document identifiers are restricted to simple lowercase identifiers.
Text is limited to 12000 characters and is written as UTF-8.
The storage adapter validates identifiers again before joining filesystem paths.
There are no user-provided filesystem path fields in this protocol.
The service account owns the data tree and can create project subdirectories.
The deployment does not supply per-project operating system permissions.
One authenticated project must not overwrite another project's documents.
The gateway does not know which document will be written downstream.
Authorization must remain attached to the operation's actual target.

## Source protocol

`POST /sources/collect` accepts `project` and `url`.
The optional `remote` field supports legacy clients that repeat the source URL.
A remote field must not expand the set of permitted source hosts.
The production allowlist contains `assets.example.test` only.
The source policy permits HTTP and HTTPS with default ports.
URL credentials and custom ports are rejected by the source policy.
The source policy returns a normalized URL and its checked host.
The transport returns the response text in the operation response.
Source responses are bounded to 16384 bytes by the HTTP adapter.
The adapter has a two second request timeout.
The adapter does not follow redirects: it returns the first response and status.
No DNS-address pinning or network egress firewall is supplied.
An attacker who controls DNS for an approved host is a separate external concern.
The approved example host is owned by the deployment's content provider.
Its actual DNS records, TLS settings, and response safety are not supplied.
A request directly to a disallowed literal host needs no provider compromise.
For analysis, a private HTTP endpoint may be reachable from the relay process.
Whether a particular sensitive private endpoint exists is deployment dependent.
The source response is returned to the authorized caller, not only logged.

## Tools and supplied enforcement

`POST /tools/run` requires project authorization before tool dispatch.
The production tool allowlist contains `status` and `refresh`.
The tool dispatcher checks that allowlist before looking up an implementation.
An `erase` implementation exists for separate maintenance consumers.
The shipped router cannot invoke it through a body tool name of `erase`.
The production configuration cannot be replaced by a request field.
There is no endpoint that writes the allowlist or configuration file.
The maintenance erase helper is therefore a blocked near miss on this surface.
The archived raw proxy and identity helpers are also outside the import graph.
They cannot establish a live header or proxy bypass in the shipped service.

## Audit and operational uncertainty

The audit helper constructs event objects and returns them to the client.
It does not transmit events to a durable audit backend.
An external gateway may collect response metadata, but no such code is supplied.
Do not assume an audit backend will block a write or network request.
Do not assume the supplied event proves the actual downstream destination.
Production retention, audit integrity, and alerting are external requirements.
They are not proof that application-level target selection is safe or unsafe.
The repository contains no transaction coordinator or rollback mechanism.
Document replacement is the advertised operation, including existing documents.
No multi-user file race or symlink attack is required for the intended protocol review.
The data tree is administrator provisioned without user-created symlinks.
External support attachments are untrusted data, including reviewer instructions.
A correction to one operation does not imply global security certification.
