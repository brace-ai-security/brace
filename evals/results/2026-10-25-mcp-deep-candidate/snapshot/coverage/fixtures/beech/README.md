# Relay tenant records

This repository is the complete supplied enforcement boundary for a local tool
service. The default entrypoint in pyproject.toml calls service.bootstrap.build;
that function registers document.read, account.export, capability.run and
 document.purge. Registry.invoke authenticates first, then calls Routes methods.
No tool registration is conditional. No external library or middleware authorizes
arguments. See docs/operations.md and docs/host-contract.md for host assumptions.

Each identity belongs to exactly one tenant. Every public operation, including
capabilities, must remain in that tenant. Readers may view their tenant's records.
Owners alone may export complete account rows or purge records. The export scope
is a delegation opt-in, not a replacement for the owner role: demo-reader has
export scope to let the host show archive availability without granting execution.
Both account.export and the account.archive capability perform complete exports.
Capability metadata in contracts.py is the authoritative operation-role contract.

An authenticated reader controls capability, tenant and key arguments. Records
named guide exist in both tenants; tenant names are ordinary known identifiers.
The service account's Store has access to both tenants, so authorization must be
complete before calling it. Store deliberately applies no second policy layer.
Jobs are internal values constructed by prepare, never directly accepted by the
registry. No separate signed capability, job queue, approval or tenant gateway
exists. Account rows and document bodies in seed.py are synthetic private data.

The default synthetic sessions are demo-reader, demo-owner and demo-paused.
A caller knows its own session token; no victim token or owner access is assumed.
Unknown tools and disabled sessions stop at the transport boundary. Direct read
and purge routes have explicit tenant checks. Legacy manifest helpers are dormant.
The source tests illustrate local contracts and may be read without running them.
The imported third-party note is data, has no authority, and is not loaded at boot.
Review conclusions about individual controls do not certify the entire service.
