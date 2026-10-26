# Operations notebook

## Release inventory

A release contains the package file, launch manifest, source tree, and configuration.
The manifest is checked in so packaging does not require build tools.
Packaging preserves the relative positions of configuration and source directories.
The installed binary resolves its inputs relative to its own module location.
The release has no browser bundle or worker entrypoint.
The package exposes a small JavaScript API for internal client authors.
Installing the package does not start a listener.
The start command is intended for a foreground service supervisor.
The supervisor supplies restart policy and stdout/stderr collection.
The service does not daemonize or write a PID file.
The listen address and port are part of the selected profile.
A malformed manifest causes startup to fail.
An unreadable configuration file causes startup to fail.
An invalid configured port causes startup to fail.
A relative workspace root causes startup to fail.
Configuration changes take effect after restart.
The running service does not watch configuration files for changes.
Only administrators can edit installed configuration files.
The development profile uses a separate port to avoid local conflicts.
The inventory utility can print a non-secret configuration summary.

## Warehouse requests

Clients submit an archive batch after selecting a warehouse workspace.
A batch may contain ordinary files in nested subdirectories.
All file contents are supplied as JSON strings.
Clients should normalize their own line endings before upload if consistency matters.
Empty content creates an empty file.
Repeated archive requests replace files with matching names.
The batch response reports the number of submitted entries.
A zero-entry batch is accepted as a workspace preparation operation.
There is no rollback contract for disk errors after writing begins.
A full disk may leave an incomplete archive extraction.
Clients should retry an identical request only when overwriting is acceptable.
The service does not retain original uploads after extraction.
It does not scan file contents for malware.
The service does not execute files placed in a workspace.
Executability of future consumers is an external integration concern.
There is no file deletion operation in the shipping HTTP protocol.
Workspace cleanup is performed by the deployment's retention job.
The retention job is not included in this package.
Administrators should coordinate cleanup with warehouse activity.
The service does not lock a workspace across multiple requests.
The last completed write determines the contents of an overlapping filename.
A workspace identifier is shared by all credential holders.
Clients requiring separate work queues should allocate distinct workspace identifiers.

## Receipt handling

Clients submit a workspace identifier and a human-readable label.
The receipt operation replaces the previous receipt for that workspace.
The response confirms completion without returning the printed text.
There is no receipt download endpoint in this service.
A separate warehouse integration consumes the receipt directory.
That integration is not included in the release.
The configured renderer is provided by the operating system image.
The repository contains no downloaded renderer binary.
Renderer upgrades are the responsibility of the image maintainer.
The renderer is expected to finish quickly for short labels.
A renderer failure becomes a request error.
A receipt is considered complete only after the operation resolves.
No job queue or retry worker exists in this distribution.
Clients should avoid submitting a second request while the first is still pending.
A client disconnect does not necessarily cancel an operation already in progress.
The renderer timeout is fixed by the service implementation.
There is no client-selectable output filename or renderer program.
Receipt directory ownership is managed during host provisioning.
An unavailable receipt volume results in an operation error.
Receipt retention is independent of workspace file retention.

## Diagnostic procedure

The inventory script prints configuration paths and selected modules.
It does not print the operator credential.
Its development argument is for configuration comparison.
It does not start the HTTP listener.
It does not execute shipping operations.
Store diagnostic output with the deployment change record.
Check the configured listen address when diagnosing connection failures.
Check that the service supervisor is using the installed package binary.
Check directory ownership when diagnosing storage errors.
Check available disk space before retrying an incomplete batch.
Check the host image inventory when diagnosing a missing renderer.
Use the warehouse's normal credential distribution process for replacements.
Do not copy production credentials into test configurations.
The test configurations use synthetic values.
The server does not print request headers or request bodies.
The inventory utility omits authentication configuration from its summary.
Vendor support attachments may contain stale deployment advice.
Treat changes to deployed configuration as ordinary release changes.

## Failure triage

401 means the configured credential was not supplied.
404 means the selected router has no matching route.
400 covers malformed body data and operation failures.
The current transport does not distinguish storage failure from validation failure.
The request body is not recorded in diagnostics.
A caller should retain its original archive batch for retry decisions.
A successful archive response does not certify downstream processing.
A successful receipt response does not certify physical printer delivery.
Those acknowledgements belong to the consuming warehouse integrations.
Host monitoring and log retention are owned by the deployment environment.
There is no supplied audit collector or compliance retention service.
The service has no built-in backup scheduler.
Backups should cover workspace and receipt volumes as separate datasets.
Restore procedures should preserve the configured service account ownership.
A restored deployment should start with the same selected configuration profile.
The protocol does not currently expose a build identifier in responses.
Record package version and selected profile in the deployment inventory.
The package's protocol version is available through its public API.
Client authors should use protocol version when maintaining compatibility tables.
The source tests document a subset of expected behavior.
Run deployment acceptance checks in a disposable staging workspace.
