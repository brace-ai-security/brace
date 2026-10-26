# Official MCP primary sources — 2026-10-26

Public static research only. Advisory retrieval timestamps are recorded individually in sources.json; repository records were rechecked at 2026-10-26T10:14:28Z. Recheck means the URL was reachable; initial content is preserved. Source commits and runtime dependency applicability must be established separately. Empty advisory lists are not safety evidence.

## Ownership and source scope

- [GitHub official repository](https://api.github.com/repos/github/github-mcp-server): owner github; public implementation. Current main go.mod declares github.com/modelcontextprotocol/go-sdk v1.8.0; historical mcp-go advisories are not automatically applicable.
- [Notion official repository](https://api.github.com/repos/makenotion/notion-mcp-server): owner makenotion; public self-hosted implementation. [Current README](https://raw.githubusercontent.com/makenotion/notion-mcp-server/main/README.md) explicitly says this implementation is no longer actively maintained/supported and is separate from hosted Remote Notion MCP. package.json is 2.5.2 with SDK ^1.29.0; this is a range, not an installed version.
- [Filesystem official reference repository](https://api.github.com/repos/modelcontextprotocol/servers): owner modelcontextprotocol; inspect src/filesystem only. Current package.json is 2.0.1, depends on @modelcontextprotocol/server ^2.3.1; exact snapshot/lockfile must control applicability.
- [Official Trello tree](https://api.github.com/repos/atlassian/trello-mcp-server/git/trees/main?recursive=1): owner atlassian; untruncated main tree 45d274db85936fa23131b25ba41d61780891c37a. It now contains documentation, policy/license, images, client/plugin manifests, and a skill; no server implementation is present. It is no longer literally README-only. Public inspectability of another official implementation remains unknown; do not substitute third-party servers.
- [Atlassian public tree](https://api.github.com/repos/atlassian/atlassian-mcp-server/git/trees/main?recursive=1): docs, plugin manifests, skills and validation scripts; no hosted server implementation in this inspected tree. Trello and Atlassian Rovo are separate remote services in their official repository READMEs.

## Published advisory records

Ranges and patch fields below reproduce maintainer structured records without normalizing date and semantic version schemes. Publication/update timestamps are UTC. Advisory prose may qualify or disagree with the fields; those cases are called out.

### github/github-mcp-server

[Public maintainer collection](https://api.github.com/repos/github/github-mcp-server/security-advisories?per_page=100), retrieved 2026-10-26T10:13:34.559933+00:00: 2 published entries.

- [GHSA-pjp5-fpmr-3349: Lockdown mode singleton in HTTP server causes cross-user GraphQL client confusion](https://github.com/github/github-mcp-server/security/advisories/GHSA-pjp5-fpmr-3349). Published 2026-06-09T09:15:58Z; updated 2026-06-09T09:15:58Z.
  - github.com/github/github-mcp-server: affected `>= 0.22.0, < 1.1.2`; patched `1.1.2`.
  - HTTP deployments using --lockdown-mode share the first authenticated user’s GraphQL client across users. Advisory patch field: 1.1.2.

- [GHSA-w4q6-qw23-4rg7: Nil Pointer Dereference DoS in completion/complete Handler](https://github.com/github/github-mcp-server/security/advisories/GHSA-w4q6-qw23-4rg7). Published 2026-07-20T12:01:42Z; updated 2026-07-20T12:01:42Z.
  - github.com/github/github-mcp-server: affected `<= 0.33.0 (also affects latest main)`; patched ``.
  - Malformed completion/complete input can panic before authentication. Patched-version field is empty; advisory suggests validating params and ref. Its “latest main” wording is historical advisory text, not a verified statement about today’s main.

### makenotion/notion-mcp-server

[Public maintainer collection](https://api.github.com/repos/makenotion/notion-mcp-server/security-advisories?per_page=100), retrieved 2026-10-26T10:13:34.838811+00:00: 0 published entries.
No published entries returned. Unknown: unpublished reports, unfixed defects, hosted implementation, and dependency advisories outside this collection.

### modelcontextprotocol/servers

[Public maintainer collection](https://api.github.com/repos/modelcontextprotocol/servers/security-advisories?per_page=100), retrieved 2026-10-26T10:13:35.440062+00:00: 14 published entries.

- [GHSA-4gxg-m5jx-9j57: Case-variant path bypasses symlink check and allows creating files outside allowed directories in server-filesystem](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-4gxg-m5jx-9j57). Published 2026-10-25T00:18:21Z; updated 2026-10-25T00:18:22Z.
  - @modelcontextprotocol/server-filesystem: affected `= 2026.8.31`; patched `None`.
  - @modelcontextprotocol/server-filesystem: affected `>= 1.0.0, < 2.0.1`; patched `2.0.1`.
  - Case-insensitive filesystems with an escaping symlink can permit creation outside allowed directories through case-varied paths. Explicitly install 2.0.1 when migrating from date-version releases.

- [GHSA-7rgq-gccq-qphx: Path traversal via trailing quote/whitespace in validatePath (Check/Use Mismatch)](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-7rgq-gccq-qphx). Published 2026-10-25T00:18:38Z; updated 2026-10-25T00:18:38Z.
  - @modelcontextprotocol/server-filesystem: affected `>= 2025.8.21, <= 2026.8.31`; patched `None`.
  - @modelcontextprotocol/server-filesystem: affected `>= 1.0.0, < 2.0.1`; patched `2.0.1`.
  - Path normalization and filesystem use differ for trailing quotes/whitespace. Explicitly install 2.0.1 when migrating from date-version releases.

- [GHSA-53mr-w429-c597: Parent-Directory Fallback TOCTOU in @modelcontextprotocol/server-filesystem Permits Arbitrary File Write Outside allowedDirectories](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-53mr-w429-c597). Published 2026-10-25T00:19:21Z; updated 2026-10-25T00:51:09Z.
  - @modelcontextprotocol/server-filesystem: affected `>= 2025.1.14, <= 2026.8.31`; patched `None`.
  - @modelcontextprotocol/server-filesystem: affected `< 2.0.1`; patched `2.0.1`.
  - A separate local process can swap a parent for a symlink after checking it. 2.0.1 anchors writes on Linux/macOS; Windows remains partly unfixed. On Windows avoid allowed directories writable by untrusted local processes/users. Complete fix tracked by issue 5260. Date-version users must explicitly install 2.0.1.

- [GHSA-hhwq-wxfx-cj7g: @modelcontextprotocol/server-filesystem list_directory_with_sizes follows symlinks and leaks outside-directory file metadata](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-hhwq-wxfx-cj7g). Published 2026-10-25T00:19:37Z; updated 2026-10-25T00:19:37Z.
  - @modelcontextprotocol/server-filesystem: affected `>= 2025.7.1, <= 2026.8.31`; patched `None`.
  - @modelcontextprotocol/server-filesystem: affected `>= 1.0.0, < 2.0.1`; patched `2.0.1`.
  - list_directory_with_sizes follows child symlinks and discloses outside-target metadata. Validate children or use lstat without following the target. Date-version users must explicitly install 2.0.1.

- [GHSA-hc55-p739-j48w: Path validation bypass via colliding path prefix](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-hc55-p739-j48w). Published 2025-07-01T18:39:04Z; updated 2025-07-01T18:39:04Z.
  - @modelcontextprotocol/server-filesystem: affected `< 0.6.3, < 2025.3.28`; patched `0.6.3, 2025.7.01`.
  - Colliding directory prefixes can escape allowed paths. Advisory prose recommends 0.6.4 or 2025.7.01; structured patched field says 0.6.3, 2025.7.01. Preserve this discrepancy.

- [GHSA-q66q-fx2p-7w4m: Path validation bypass via symlink handling](https://github.com/modelcontextprotocol/servers/security/advisories/GHSA-q66q-fx2p-7w4m). Published 2025-07-01T18:38:24Z; updated 2025-07-01T18:38:24Z.
  - @modelcontextprotocol/server-filesystem: affected `< 0.6.3, < 2025.3.28`; patched `0.6.3, 2025.7.01`.
  - Symlinks inside allowed directories can reach unintended files. Advisory prose recommends 0.6.4 or 2025.7.01; structured patched field says 0.6.3, 2025.7.01. Preserve this discrepancy.

### modelcontextprotocol/typescript-sdk

[Public maintainer collection](https://api.github.com/repos/modelcontextprotocol/typescript-sdk/security-advisories?per_page=100), retrieved 2026-10-26T10:13:35.940541+00:00: 10 published entries.

- [GHSA-6qxp-vccf-f47h: OAuth client could send credentials to an authorization server chosen by the MCP server](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h). Published 2026-09-30T20:59:40Z; updated 2026-10-02T16:21:20Z.
  - @modelcontextprotocol/sdk: affected `>= 1.12.0, < 1.31.0`; patched `1.31.0`.
  - @modelcontextprotocol/client: affected `>= 2.0.0, < 2.2.0`; patched `2.2.0`.
  - HTTP OAuth clients holding credentials can send them to an authorization server selected by an untrusted MCP server. Servers and stdio clients are excluded. Upgrade; bundled providers still need expectedIssuer, saved credentials need issuer or clearing, and custom providers must preserve issuer. Direct refreshAuthorization/exchangeAuthorization calls and skipIssuerMetadataValidation remain outside the fix.

- [GHSA-rvq5-wwqv-78pq: Server bearer authentication accepted tokens issued for another service](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq). Published 2026-10-05T16:01:06Z; updated 2026-10-19T20:12:07Z.
  - @modelcontextprotocol/sdk: affected `>= 1.6.0, < 1.32.0`; patched `1.32.0`.
  - @modelcontextprotocol/server: affected `>= 2.0.0, < 2.3.0`; patched `2.3.0`.
  - @modelcontextprotocol/express: affected `>= 2.0.0, < 2.0.2`; patched `2.0.2`.
  - @modelcontextprotocol/server-legacy: affected `>= 2.0.0, < 2.3.1`; patched `2.3.1`.
  - HTTP bearer authentication may accept tokens for another audience when the verifier omits audience checks. Upgrading alone does not enable protection: set expectedResource and return AuthInfo.resource from verifyAccessToken; alternatively enforce aud in the verifier.

- [GHSA-22jm-h49p-29qw: Experimental tasks were not tied to the session that created them](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-22jm-h49p-29qw). Published 2026-10-02T20:54:41Z; updated 2026-10-19T19:50:48Z.
  - @modelcontextprotocol/sdk: affected `>= 1.24.0, < 1.32.0`; patched `1.32.0`.
  - Experimental taskStore tasks were not session-bound. Upgrade or remove taskStore or allocate one InMemoryTaskStore per session; 2.x packages excluded.

- [GHSA-jm63-cq47-j5jp: Shared transport or server instances delivered one HTTP client's messages to another](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-jm63-cq47-j5jp). Published 2026-10-15T13:10:24Z; updated 2026-10-19T20:09:41Z.
  - @modelcontextprotocol/server: affected `>= 2.0.0, < 2.3.0`; patched `2.3.0`.
  - Shared HTTP server/transport instances misroute client messages. Upgrade and create one server plus transport per request/session, or provide a server factory to createMcpHandler. stdio excluded.

- [GHSA-6prh-2h8m-c8cw: HTTP client transports and OAuth requests followed cross-origin redirects and re-sent custom headers and request bodies](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw). Published 2026-10-02T20:42:34Z; updated 2026-10-19T20:07:25Z.
  - @modelcontextprotocol/sdk: affected `< 1.32.0`; patched `1.32.0`.
  - @modelcontextprotocol/client: affected `>= 2.0.0, < 2.3.0`; patched `2.3.0`.
  - HTTP client/OAuth redirects may resend custom headers and request bodies across origins. Upgrade and configure final URLs; redirectPolicy follow restores exposure. Refuse redirects as a workaround. stdio excluded.

- [GHSA-46jr-4wx8-v453: One HTTP request within the default size limit could exhaust server memory during validation](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-46jr-4wx8-v453). Published 2026-10-15T13:10:32Z; updated 2026-10-19T20:06:02Z.
  - @modelcontextprotocol/sdk: affected `>= 1.3.0, < 1.32.0`; patched `1.32.0`.
  - @modelcontextprotocol/server: affected `>= 2.0.0, < 2.3.0`; patched `2.3.0`.
  - HTTP validation can exhaust memory within the body size limit. Upgrading alone is insufficient: set maxToolInputElements and reduce maxRequestBodySize or the application body-parser limit. stdio excluded.

- [GHSA-f897-62hf-6gxq: HTTP server transports and handlers did not limit request body size or JSON-RPC batch length](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq). Published 2026-10-15T13:10:21Z; updated 2026-10-15T13:10:21Z.
  - @modelcontextprotocol/sdk: affected `>= 1.10.0, < 1.30.1`; patched `1.30.1`.
  - @modelcontextprotocol/server: affected `>= 2.0.0, < 2.1.0`; patched `2.1.0`.
  - @modelcontextprotocol/node: affected `>= 2.0.0, < 2.1.0`; patched `2.1.0`.
  - @modelcontextprotocol/hono: affected `>= 2.0.0, < 2.0.1`; patched `2.0.1`.
  - HTTP bodies/batches were unbounded. Upgrade every installed affected adapter; patched defaults cap body size at 4 MiB and batches at 100 messages. Reverse-proxy body limits are a workaround; stdio excluded.

- [GHSA-345p-7cg4-v4c7: Sharing server/transport instances can leak cross-client response data](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-345p-7cg4-v4c7). Published 2026-02-04T19:51:03Z; updated 2026-02-09T14:49:03Z.
  - @modelcontextprotocol/sdk: affected `>= 1.10.0, <= 1.25.3`; patched `1.26.0`.
  - Sharing HTTP transport/server instances can leak cross-client messages. Upgrade and isolate one server and transport per request/session; guards convert reuse into errors.

- [GHSA-cqwc-fm46-7fff: Regular Expression Denial of Service (ReDoS) in UriTemplate](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-cqwc-fm46-7fff). Published 2026-01-07T15:50:48Z; updated 2026-01-07T15:50:48Z.
  - @modelcontextprotocol/sdk: affected `<1.25.2`; patched `1.25.2`.
  - Exploded resource URI template patterns allow excessive regex backtracking. Upgrade to 1.25.2 or avoid exploded array patterns and validate incoming URIs.

- [GHSA-w48q-cv73-mx4w: DNS Rebinding Protection Disabled by Default in Model Context Protocol TypeScript SDK for Servers Running on Localhost](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-w48q-cv73-mx4w). Published 2025-12-02T13:48:27Z; updated 2025-12-02T13:48:27Z.
  - @modelcontextprotocol/sdk: affected `< 1.24.0`; patched `1.24.0`.
  - Unauthenticated localhost HTTP servers lacked default DNS rebinding protection. Upgrade; createMcpExpressApp enables protection on localhost, custom Express apps need hostHeaderValidation. stdio excluded.

### modelcontextprotocol/go-sdk

[Public maintainer collection](https://api.github.com/repos/modelcontextprotocol/go-sdk/security-advisories?per_page=100), retrieved 2026-10-26T10:13:36.371455+00:00: 4 published entries.

- [GHSA-xw59-hvm2-8pj6: DNS Rebinding Protection Disabled by Default in Model Context Protocol Go SDK for Servers Running on Localhost](https://github.com/modelcontextprotocol/go-sdk/security/advisories/GHSA-xw59-hvm2-8pj6). Published 2026-03-30T14:42:59Z; updated 2026-03-30T19:59:41Z.
  - github.com/modelcontextprotocol/go-sdk: affected `< 1.4.0`; patched `1.4.0`.
  - Unauthenticated localhost HTTP handlers lacked default DNS rebinding protection. Upgrade to 1.4.0 for automatic localhost protection; stdio excluded.

- [GHSA-89xv-2j6f-qhc8: Cross-Site Tool Execution for HTTP Servers without Authorization in github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk/security/advisories/GHSA-89xv-2j6f-qhc8). Published 2026-03-18T14:55:37Z; updated 2026-03-18T23:36:09Z.
  - github.com/modelcontextprotocol/go-sdk: affected `<= 1.4.0`; patched `1.4.1`.
  - Unauthenticated HTTP handlers accepted browser cross-site POSTs. Upgrade to 1.4.1 for content-type validation and configurable origin verification; requires Go 1.25 or later.

- [GHSA-q382-vc8q-7jhj: Improper handling of null Unicode character when parsing JSON in github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk/security/advisories/GHSA-q382-vc8q-7jhj). Published 2026-03-18T14:55:55Z; updated 2026-03-18T14:55:55Z.
  - github.com/modelcontextprotocol/go-sdk: affected `<= 1.4.0`; patched `1.4.1`.
  - JSON key matching accepted null-suffixed keys. Upgrade SDK to 1.4.1 using segmentio/encoding 0.5.4.

- [GHSA-wvj2-96wp-fq3f: Improper Handling of Case Sensitivity in github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk/security/advisories/GHSA-wvj2-96wp-fq3f). Published 2026-02-25T20:59:39Z; updated 2026-02-25T20:59:39Z.
  - github.com/modelcontextprotocol/go-sdk: affected `< v1.3.1`; patched `v1.3.1`.
  - JSON parsing accepted case variants and Unicode folding, conflicting with exact protocol field names. Upgrade SDK to 1.3.1 for case-sensitive decoding.

### mark3labs/mcp-go

[Public maintainer collection](https://api.github.com/repos/mark3labs/mcp-go/security-advisories?per_page=100), retrieved 2026-10-26T10:13:36.750936+00:00: 1 published entries.

- [GHSA-xf6j-693p-wqxx: mcp-go OAuth client accepts an unvalidated resource from well-known Protected Resource Metadata](https://github.com/mark3labs/mcp-go/security/advisories/GHSA-xf6j-693p-wqxx). Published 2026-10-09T09:02:58Z; updated 2026-10-09T09:02:58Z.
  - github.com/mark3labs/mcp-go: affected `>= 0.48.0, <= 1.2.0`; patched `1.2.1`.
  - OAuth client resource metadata validation advisory is preserved as historical SDK context; root source dependency selection must establish applicability.

### atlassian/trello-mcp-server

[Public maintainer collection](https://api.github.com/repos/atlassian/trello-mcp-server/security-advisories?per_page=100), retrieved 2026-10-26T10:13:37.039231+00:00: 0 published entries.
No published entries returned. Unknown: unpublished reports, unfixed defects, hosted implementation, and dependency advisories outside this collection.

### atlassian/atlassian-mcp-server

[Public maintainer collection](https://api.github.com/repos/atlassian/atlassian-mcp-server/security-advisories?per_page=100), retrieved 2026-10-26T10:13:37.382861+00:00: 0 published entries.
No published entries returned. Unknown: unpublished reports, unfixed defects, hosted implementation, and dependency advisories outside this collection.

## Limits

The packet records 2026-10-26 observations; it does not establish installed/resolved dependency versions, deploy settings, completeness of vulnerability coverage, or runtime exploitability. No server was installed, imported, started, probed or connected. No product account/API data or credentials were accessed. All changes are confined to this research directory.
