# Public MCP source review: adjudicated findings

Reviewed 2026-10-23. These are static findings and evidence limits, not deployment
decisions. Three fresh Sonnet contexts used the repaired `brace-mcp-review` skill;
all three stayed within Read/Glob/Grep. A subsequent maintainer-agent pass checked
claims against source and current primary references. Neither pass executed the
servers, installed dependencies, used credentials or probed product endpoints.

The raw reports are preserved unchanged. This audit takes precedence where it
qualifies their wording. This is a field exercise with incomplete ground truth,
not a measured recall benchmark.

## Source snapshots

| Product/component | Public repository and commit | License | Coverage |
|---|---|---|---|
| Notion MCP server | [makenotion/notion-mcp-server](https://github.com/makenotion/notion-mcp-server/tree/730ae781ba28beeaf0865025a3f2ed4c25ea2387), `730ae781ba28beeaf0865025a3f2ed4c25ea2387` | MIT | Source server, HTTP wrapper, credentials and package metadata; not the separate hosted Notion service. |
| GitHub MCP server | [github/github-mcp-server](https://github.com/github/github-mcp-server/tree/f38526264abb14961b32cea386e38ec6d3cf674f), `f38526264abb14961b32cea386e38ec6d3cf674f` | MIT | Transport/authentication, inventory ceilings, lockdown cache and completion handler. Most product tool implementations remain untraced. |
| Stripe adapter | [stripe/ai](https://github.com/stripe/ai/tree/8a8818e856376003701bb0d4a569c26bacac1d0e/tools/modelcontextprotocol), `8a8818e856376003701bb0d4a569c26bacac1d0e` | MIT | Open stdio-to-HTTP adapter and packaging. Hosted Stripe enforcement is unavailable. |
| Official Trello | [atlassian/trello-mcp-server](https://github.com/atlassian/trello-mcp-server/tree/45d274db85936fa23131b25ba41d61780891c37a), `45d274db85936fa23131b25ba41d61780891c37a` | Apache-2.0 | Public documentation, configuration and usage skill only. No server implementation in this repository. |

## N1: Notion inherited-key session lookup can reject outside Express error handling

**Source-supported gap; process termination is inferred for the documented default
runtime, not reproduced.** This was missed by the raw skill report.

The session table is an ordinary `{}` at
[start-server.ts:116](https://github.com/makenotion/notion-mcp-server/blob/730ae781ba28beeaf0865025a3f2ed4c25ea2387/scripts/start-server.ts#L116).
The GET and DELETE handlers test a caller-supplied session key using ordinary
property lookup, then invoke `handleRequest` on that value
([GET:216](https://github.com/makenotion/notion-mcp-server/blob/730ae781ba28beeaf0865025a3f2ed4c25ea2387/scripts/start-server.ts#L216),
[DELETE:228](https://github.com/makenotion/notion-mcp-server/blob/730ae781ba28beeaf0865025a3f2ed4c25ea2387/scripts/start-server.ts#L228)).
An inherited property such as `constructor` is truthy without being a stored
transport; its `handleRequest` is not callable. This rejects the async route's
promise. Neither handler catches the rejection or forwards it to `next`.

The lockfile resolves Express 4.22.2 and the Dockerfile selects Node 20.
[Express 4 documentation](https://expressjs.com/en/4x/guide/error-handling/)
requires explicit handling of rejected async route promises. The
[Node 20 CLI reference](https://nodejs.org/download/release/latest-v20.x/docs/api/cli.html#--unhandled-rejectionsmode)
documents default `throw` behavior. Thus the source supports a process-exit path
under ordinary Node defaults, subject to any external rejection handler or runtime
override. POST has its own catch; that does not protect GET or DELETE.

**Prerequisites:** HTTP mode and network reachability. The bearer token is required
by default; a non-loopback bind does not remove that gate. Without the bearer,
this path requires the explicit unsafe auth-disabled mode. No real session ID or
Notion token is needed to reach the inherited-key error after the gate. Default
loopback binding limits remote exposure. No hosted-service impact is established.

**BRACE:** B07/R01 for availability limits; R11/R12 for recovery evidence.
**Owner/action:** server maintainers should use a `Map` or null-prototype table,
validate own entries, and route async failures to Express. A controlled test should
show unknown/inherited session keys yield a bounded error and leave the process
healthy, while a valid session still works. No such test was run here.

## N2: Notion dependency and identity findings need narrower interpretation

- The checked-in lock resolves SDK **1.29.0**, inside the
  [HTTP body/batch advisory range](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq).
  Affected HTTP transport is used. Express already bounds body size by default;
  it does not supply the SDK's batch-count fix. Keep application authentication,
  body parsing, batch limits and deployment reachability separate.
- The raw report's F1 heading overstates demonstrated validation-exhaustion
  exposure. The repository uses low-level `Server`; it did not establish the
  [McpServer validation path](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-46jr-4wx8-v453).
  Treat that path as unknown. Adding a `McpServer`-specific option blindly to a
  different API is not a verified remediation; trace or implement an appropriate
  argument budget for the actual path.
- The optional passthrough mode explicitly supports different Notion integrations.
  The raw report's statement that there is no multi-user boundary is too broad.
  Existing-session lookup reuses the stored proxy without comparing a caller's
  current Notion identity. A caller with the shared gateway token **and a leaked
  valid session ID** could act through that session's integration. Random session
  IDs reduce guessability; this review found no session-ID disclosure path.
  This is a conditional binding concern, not proof of cross-tenant extraction.
- Shared-secret timing, request-scheme parsing, container user, token-file custody
  and logging observations remain hardening/evidence questions. No live credential
  exposure, timing exploit or deployed container privilege was demonstrated.

Primary advisory records were fetched on 2026-10-23; the model's own web tools were
unavailable. Notion's empty repository-advisory list proves no absence of flaws.

## S1: Stripe desktop manifest omits secret-field protection

**Source-supported packaging gap; installed-host exposure unverified.** This was
missed by the raw skill report, which left the manifest unreviewed.

The extension's
[manifest.json:13](https://github.com/stripe/ai/blob/8a8818e856376003701bb0d4a569c26bacac1d0e/tools/modelcontextprotocol/manifest.json#L13)
defines `stripe_secret_key` as a required string with no `sensitive` flag. It is
later passed through the environment. The
[version 0.1 manifest specification](https://github.com/modelcontextprotocol/mcpb/blob/v0.1.0/MANIFEST.md#user-configuration)
defines `sensitive` for masked input and secure storage, with a default of false.
That matches the manifest's `dxt_version: 0.1`; this is not an invented requirement
from a newer format.

The manifest therefore fails to request the host's secret-specific handling.
Using an environment variable at launch does not establish secure storage before
launch. Actual desktop storage, the installed bundle and host overrides were not
inspected; no existing key leak is claimed.

**BRACE:** B03/B11 for credential custody and inherited local authority, C08/E12 for
secret exposure controls. **Owner/action:** package maintainers should mark the
field sensitive and verify the targeted host masks/stores it securely while still
delivering the value to the adapter. Test with a fake key; none was entered here.

## S2: Stripe lockfiles and redirects

The npm lock resolves SDK **1.27.1** and the pnpm lock **1.17.2**. The Dockerfile's
declared build path uses pnpm's frozen lock; no built image or published npm package
was inspected. Both source resolutions precede the
[1.32.0 client redirect fix](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw),
and this adapter uses the affected HTTP client transport without a redirect
override. Its upstream URL is fixed to Stripe. No attacker-controlled redirect
was found in the adapter.

The advisory distinguishes custom-header/session/body forwarding from normal
cross-origin `Authorization` stripping. Do not turn this into a claim that Stripe
API keys are known to leak. Verify compatible SDK upgrades and redirect refusal
on both packaging paths, with a controlled upstream and fake credentials.

The first source-copy attempt failed on a self-referential package LICENSE symlink.
That preparation error is retained under `stripe-copy-error/`; no model ran in that
attempt. The successful review copy omitted that link and included the root MIT
license. Source code was unchanged. This is a packaging observation, not a remote
security vulnerability.

## G1: GitHub advisory-described bugs have visible source remediations

The pinned completion handler checks the request, params and reference before use
([server.go:203](https://github.com/github/github-mcp-server/blob/f38526264abb14961b32cea386e38ec6d3cf674f/pkg/github/server.go#L203)).
The [published nil-reference advisory](https://github.com/github/github-mcp-server/security/advisories/GHSA-w4q6-qw23-4rg7)
still lacks a patched version. This mismatch requires release mapping; it does not
prove that the current source still has the described flaw.

For the [lockdown singleton advisory](https://github.com/github/github-mcp-server/security/advisories/GHSA-pjp5-fpmr-3349),
current source constructs request-scoped clients/caches and scopes cache keys by
token identity. These are static remediation observations, not runtime or hosted
service guarantees. The raw report's speculative empty-token embedding and
confirmation-state observations remain evidence requests, not confirmed bypasses.
Its token-passthrough discussion does not establish MCP audience/profile compliance.

Most individual tool paths, local OAuth flows, UI resources, release provenance
and dependency advisories remain unreviewed. No broad GitHub-server clearance is
supported by this pass.

## Official Trello: implementation evidence unavailable

The pinned public tree contains documentation, `mcp.json`, a usage skill, policy
files and images. It contains no server implementation. The configured URL is the
official hosted Trello endpoint. Public claims about OAuth, workspace scope,
permissions and revocation are contracts to verify, not implementation evidence.
The suspected defect could not be confirmed or dismissed here. No replacement
community implementation is used as evidence about the official service.

## What this says about the skill

The repaired tool selection worked in all three product reviews. It usefully
compared actual lockfiles, transport applicability and code remediations. It also
missed N1 and S1, left important code/packaging paths unreviewed, and overstated
parts of Notion F1/F2. Perfect scores on small paired synthetic fixtures did not
transfer to exhaustive real-product coverage.

Broader coverage and independent dataflow challenges are needed before treating
the output as more than a draft. Existing product cases are now known regressions;
they are not future fresh holdouts. This assessment of review reliability is
BRACE's engineering judgment. High-risk rollout remains a human-owned, gradual,
closely monitored process with bounded exposure, stop conditions and recovery.
