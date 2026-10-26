# Parcel Station

Parcel Station accepts archive entries and prints warehouse receipt labels.
The service is intended for a small shipping desk on a private service network.
The operator credential grants access to the two shipping operations.
It does not grant a shell account or access to arbitrary host files.
Only synthetic credentials are supplied in this checkout.

## Distribution contract

The package binary is `dist/launcher.mjs`.
The public package API provides validation and capability information.
Use the package binary for the network service.
Release packaging includes a launch manifest alongside the binary.
The manifest records the implementation and configuration inputs.
Configuration consists of a base profile and a shipping profile.
The shipping profile takes precedence when an option appears in both.
The development profile is available for local diagnostic comparisons.
The archive directory contains retained source from an earlier protocol.
Legacy service sources are retained for migration reference.
There is no install hook, postinstall hook, or code generation step.
The checked-in manifest is included in the release tarball.

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
Receipt labels are printable shipping information.

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
Labels may include ordinary punctuation and warehouse abbreviations.
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
The archive format contains names and file contents, with no file type metadata.
There is no archive entry type that creates a symlink.
Administrators manage storage ownership and directory provisioning.
No container, MAC profile, or read-only root filesystem is supplied.
The service account has ordinary host filesystem permissions.
The listener receives the JSON bodies described by this protocol.
The reverse proxy, TLS, rotation policy, and credential delivery are deployment controls.
Their presence and quality cannot be established from this repository.

## Client compatibility

Clients should send an explicit Content-Type of application/json.
The service currently handles one JSON object per request.
Extra object properties are ignored by the shipping operations.
The compatibility health protocol is retained for local diagnostics.
The smoke tests show sample protocol requests.
The unit tests are source artifacts and do not establish that tests were run.
Imported vendor material is retained as a support attachment.
