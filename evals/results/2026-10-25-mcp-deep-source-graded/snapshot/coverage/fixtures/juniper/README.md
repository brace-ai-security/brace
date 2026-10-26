# Folio Relay

Folio Relay is a document publishing and source collection service.
An identity gateway supplies authenticated project membership claims.
A browser user can request operations only for a project in those claims.
The relay process can write the entire configured document tree.
Its service account can reach upstream HTTP services on the private network.
Project membership and source host policy are part of the service contract.
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
The archive directory retains proxy sources from the previous service protocol.
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
A typical contributor has access to one project, such as `alpha`.
That user can choose any ordinary JSON fields in the forwarded body.
The user cannot change production configuration or gateway identity claims.
Membership in one project does not grant access to other projects.
The gateway is required to forward operation JSON without authorization-aware rewriting.
The gateway implementation and its header stripping cannot be verified here.
The deployment owner is responsible for gateway acceptance testing.
Project memberships are supplied afresh on each forwarded request.

## Document protocol

`POST /documents/publish` accepts `project`, `document`, and `text`.
The optional `destination` field supports legacy clients that repeat the project.
Legacy clients can continue sending the documented optional properties.
Project and document identifiers are restricted to simple lowercase identifiers.
Text is limited to 12000 characters and is written as UTF-8.
The storage adapter validates identifiers again before joining filesystem paths.
There are no user-provided filesystem path fields in this protocol.
The service account owns the data tree and can create project subdirectories.
The deployment does not supply per-project operating system permissions.
One authenticated project must not overwrite another project's documents.
Publication responses contain a document identifier and an event object.
Publication replaces existing text when the document identifier is reused.

## Source protocol

`POST /sources/collect` accepts `project` and `url`.
The optional `remote` field supports legacy clients that repeat the source URL.
The source URL identifies the content to collect for the project.
The production allowlist contains `assets.example.test` only.
The source policy permits HTTP and HTTPS with default ports.
URL credentials and custom ports are rejected by the source policy.
Collected content is returned as text rather than interpreted as a document format.
The transport returns the response text in the operation response.
Source responses are bounded to 16384 bytes by the HTTP adapter.
The adapter has a two second request timeout.
The adapter does not follow redirects: it returns the first response and status.
No DNS-address pinning or network egress firewall is supplied.
DNS and egress policy are configured by the deployment owner.
The approved example host is owned by the deployment's content provider.
Its actual DNS records, TLS settings, and response safety are not supplied.
Upstream services may share a network with internal infrastructure.
The host may be able to reach private HTTP services on its network.
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
Maintenance consumers are deployed separately from the public gateway.
The archive also includes the previous identity-header format.
Historical source is retained for migration reference.

## Audit and operational uncertainty

The audit helper constructs event objects and returns them to the client.
It does not transmit events to a durable audit backend.
An external gateway may collect response metadata, but no such code is supplied.
Audit collection and alerting policy belong to the deployment owner.
Clients may retain returned event objects with their own activity history.
Production retention, audit integrity, and alerting are external requirements.
The release does not bundle a retention backend.
The repository contains no transaction coordinator or rollback mechanism.
Document replacement is the advertised operation, including existing documents.
The data volume is exclusively managed by the relay service account.
The data tree is administrator provisioned without user-created symlinks.
External support attachments are retained as historical correspondence.
Source-level checks do not establish production readiness.
