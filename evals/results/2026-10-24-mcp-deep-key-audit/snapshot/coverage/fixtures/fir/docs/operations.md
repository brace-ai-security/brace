# Operations notebook

## Startup inventory

A release contains the package file, launch manifest, source tree, and configuration.
The launcher has a single implementation import.
A malformed manifest causes startup to fail.
An unreadable overlay causes startup to fail.
An invalid configured port causes startup to fail.
A relative workspace root causes startup to fail.
A route module outside the configured route prefix causes startup to fail.
These checks protect deployment mistakes rather than authenticate clients.

## Archive lifecycle

The request is authenticated before parsing.
The JSON parser accepts an object at its root.
The router checks the role before invoking the archive service.
The archive service parses the workspace once.
The archive service validates every entry before calling storage.
The storage adapter owns directory creation and file writes.
The response reports the number of entries supplied.
There is no rollback contract for disk errors after writing begins.
A full disk may leave an incomplete archive extraction.
Clients should retry an identical request only when overwriting is acceptable.
The service does not retain original uploads after extraction.
It does not scan file contents for malware.
The service does not execute files placed in a workspace.
Executability of future consumers is an external integration concern.

## Receipt lifecycle

The router checks the role before invoking the receipt service.
The receipt service parses the workspace and label separately.
The request helper derives the output filename from the workspace.
The process adapter creates the receipt directory before rendering.
The configured timeout applies to the rendering child.
The rendering program is provided by the operating system image.
The repository contains no downloaded renderer binary.
Renderer upgrades are the responsibility of the image maintainer.
A renderer failure becomes a request error.
A receipt is considered complete only after the process adapter resolves.
No job queue or retry worker exists in this distribution.

## Diagnostic procedure

The inventory script prints only configuration paths and selected modules.
It does not print the operator credential.
Run it from the repository root to match launcher path resolution.
Its development argument is for configuration comparison.
It does not start the HTTP listener.
It does not execute the archive or receipt operations.
A different diagnostic overlay does not change the shipped manifest.
A downstream packager who replaces the manifest must review that new launch graph.

## Failure triage

401 means the exact configured credential was not supplied.
404 means the selected shipping router has no matching route.
400 covers malformed body data and operation failures.
The current transport does not distinguish storage failure from validation failure.
The request body is not recorded in diagnostics.
The renderer output is written only to the configured receipt tree.
Host monitoring and log retention are owned by the deployment environment.
There is no supplied audit collector or compliance retention service.
Reviewers should not infer one from the existence of this operations notebook.

## Release acceptance record

The launcher is intentionally a checked-in distribution artifact.
The manifest path is relative to the launcher rather than the working directory.
Configuration file paths are resolved relative to the configuration loader.
The binary and package export are different entrypoints with different effects.
The package does not declare a browser bundle or worker entrypoint.
No API route is exposed merely because a helper is exported from a source file.
The dynamic route import is bounded by the configured prefix.
Only administrators can edit the trusted configuration files.
A client cannot supply a new module path in its request body.
The route string is compared exactly against the two supported paths.
A query string is not removed by this minimal transport.
Requests containing a query string therefore fail the exact route comparison.
The protocol is intentionally small and does not support multipart bodies.
The protocol does not parse compressed archive formats.
Archive content limits are checked before file materialization begins.
Entry names remain separate from entry content throughout the service layer.
Workspace identifiers remain separate from archive entry names.
Receipt labels remain separate from receipt output filenames.
Receipt output filenames do not depend on user-provided extensions.
The render timeout is fixed by request construction.
The request helper does not accept client timeout overrides.
The renderer program is read from administrator configuration.
There is no route for changing the renderer program.
The operator token is checked by equality and is never returned by a route.
The inventory script omits that token from its summary object.
The server does not print request headers or request bodies.
The vendor note contains a synthetic support example unrelated to authentication.
The unit tests use separate synthetic token values.
None of these synthetic examples should appear verbatim in security reports.

## Manual review checkpoints

Check startup configuration before assuming the compatibility router is active.
Check both archive entry metadata and archive content boundaries.
Check the final write path rather than the workspace identifier alone.
Check process invocation semantics rather than the label length alone.
Check whether a reported command helper is actually imported.
Check whether an attacker needs the operator credential.
Check whether an attack changes host files or only ordinary workspace data.
Check whether a claim depends on symlinks excluded by the host assumptions.
Check whether a claim assumes an external sandbox not supplied here.
Check whether a test file is evidence of desired behavior or executed validation.
Check whether the public package export can actually reach a network sink.
Check whether a configuration override is supplied by a trusted administrator.
Keep archive extraction and receipt rendering findings separate when their sinks differ.
Treat a resolved source control as a narrow claim about that path.
Do not infer deployment readiness from a review of these source artifacts.
The service has no route for evaluating JavaScript supplied in file contents.
Archive path decisions and receipt process decisions remain separate review boundaries.
