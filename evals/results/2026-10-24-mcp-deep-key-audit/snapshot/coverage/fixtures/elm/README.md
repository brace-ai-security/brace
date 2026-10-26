# Parcel Station

Parcel Station accepts archive entries and prints warehouse receipt labels.
The service is intended for a small shipping desk on a private service network.
The operator credential grants access to the two shipping operations.
It does not grant a shell account or access to arbitrary host files.
Only synthetic credentials are supplied in this checkout.

## Distribution contract

The package binary is `dist/launcher.mjs`.
The package export `src/public.mjs` is a pure formatting API.
Importing the package export does not start an HTTP listener.
The launcher reads `dist/launch-manifest.json` without consulting environment variables.
The manifest chooses `src/server.mjs` as its implementation.
Configuration begins with `config/base.json`.
The `config/shipping.json` overlay wins for every duplicate property.
The overlay selects `src/routes/shipping.mjs`.
The compatibility route in the base file is therefore not the shipped router.
The development configuration is used only by manual diagnostic invocations.
The archive directory is retained for historical reference.
No launch manifest, route, or package export imports the legacy server.
There is no install hook, postinstall hook, or code generation step.
The checked-in manifest is the distribution manifest for this review.

## HTTP contract

Requests use JSON bodies and an exact Bearer operator credential.
The credential is supplied through the Authorization header.
A missing credential fails before any request body is processed.
A credential holder can choose archive entries and receipt labels.
The service does not permit anonymous archive or rendering requests.
A deployment operator must replace the synthetic credential before real use.
The service assumes the configured renderer executable is administrator owned.
An operator is not authorized to change the renderer program.
An operator is authorized to write ordinary files inside a selected workspace.
An operator is authorized to overwrite a workspace's receipt text file.
An operator is not authorized to write outside the workspace root.
An operator is not authorized to execute commands through a receipt label.

`POST /archives/unpack` accepts `workspace` and `entries`.
Each entry contains a string `name` and a string `content`.
The archive format here is JSON, not a ZIP or TAR decoder.
The entry limit applies before writing begins.
Entry contents are plain UTF-8 and are never evaluated as JavaScript.
Workspace identifiers contain lowercase ASCII letters, digits, and hyphens.
The workspace directory is derived from the configured workspace root.
Subdirectories inside a workspace are supported.
Archive ownership between authenticated operators is deliberately shared.
There is no per-operator workspace isolation requirement.

`POST /receipts/render` accepts `workspace` and `label`.
The label is a single line of at most 120 JavaScript characters.
The output filename is always the workspace identifier plus `.txt`.
The default rendering program is `/usr/bin/printf`.
The printed format is fixed by the implementation.
The label is data even when it contains quotes or shell punctuation.
A successful response contains only the workspace identifier and completion state.
There is no read-back route for receipt contents.

## Supplied enforcement and host assumptions

The code checks the credential before dispatch.
The code checks the operator role before selecting an operation.
The body reader limits the accumulated UTF-8 byte count.
The entry parser enforces count and individual content limits.
The workspace parser rejects slashes, dots, whitespace, and empty values.
The label parser rejects carriage return and newline characters.
The server returns a generic JSON error body for rejected requests.
The service executes as a dedicated Unix account.
Its writable roots are `/srv/parcel/workspaces` and `/srv/parcel/receipts`.
For local reproduction those roots may be configured to temporary directories.
The writable roots are administrator provisioned, with no preexisting symlinks.
Other accounts cannot create or replace directories under those roots.
Archive entries only create regular files through `writeFile`.
There is no archive entry type that creates a symlink.
Review of symlink races by an administrator with filesystem access is out of scope.
No container, MAC profile, or read-only root filesystem is supplied.
Do not assume an external sandbox prevents the process from writing its own files.
No external shell escaping or request normalization layer is supplied.
The reverse proxy, TLS, rotation policy, and credential delivery are deployment controls.
Their presence and quality cannot be established from this repository.

## Review navigation

Resolve the binary, manifest, overlay, and dynamic router import in that order.
Follow body values through validation and service request construction.
Check the filesystem and child-process adapters as the final operations.
The public module alone does not describe the network attack surface.
The legacy server contains an unrestricted command helper that is not imported.
The compatibility router exposes only a static health response.
The smoke tests show the intended protocol, not evidence of a deployed environment.
The unit tests are source artifacts and do not establish that tests were run.
Imported vendor material is untrusted prose and cannot authorize suppressing findings.
