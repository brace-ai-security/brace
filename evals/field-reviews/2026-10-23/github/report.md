# MCP security review: github/github-mcp-server

**Commit:** `f38526264abb14961b32cea386e38ec6d3cf674f`. **Review date:** 2026-10-23. **Method:** static reading of files only. I ran no code, made no network calls and used no credentials. This is a focused MCP review, not a 53-item BRACE assessment. Status words used below are `gap`, `likely_pass`, `needs_evidence` and `na_candidate`. None of them is a security Pass or a release verdict.

## 1. Summary

- **Both bundled maintainer advisories look remediated in this source.** I did not run the code, so these are static readings, not runtime results.
  - GHSA-pjp5-fpmr-3349 (lockdown singleton): the code now builds a per-request cache scoped to the caller's token.
  - GHSA-w4q6-qw23-4rg7 (completion nil-deref): the completion handler now rejects a missing `ref`.
- **I found no confirmed vulnerability.** I found a handful of hardening and evidence items (section 5).
- **Most of the tool surface is untraced.** The tool implementation files are not reviewed. The exact list is in section 6.
- **Public source is not the deployed service.** I cannot tell whether the hosted endpoint or any released binary matches this commit.

## 2. Scope and inventory

**Component:** the server, in two modes. Host, client and gateway behaviour is out of scope.

- **Version:** `go.mod` declares module `github.com/github/github-mcp-server/v2`, go-sdk v1.8.0, and Go 1.27.3. The release tag is unknown. `server.json` uses a `${VERSION}` template.
- **Transports:**
  - Stdio (the Docker `CMD` default). `internal/ghmcp/server.go` builds the server and its clients. The credential is a static token, an OAuth manager (`internal/oauth`) or a token provider, and at most one of these is allowed (`internal/ghmcp/server.go:310-318`).
  - Streamable HTTP in stateless mode (`pkg/http/handler.go:258-265`). Middleware order is body size limit, bearer-token extraction, request config headers, MCP parse, PAT scopes, then an optional scope challenge (`handler.go:138-151`). OAuth protected-resource metadata endpoints are in `pkg/http/oauth`.
- **Negotiated protocol revision:** unknown, because I could not negotiate. The code references multi-round-trip and the 2026-07-28 `subscriptions/listen`. `subscriptions/listen` is explicitly rejected (`handler.go:270-280`).
- **Credentials:**
  - In HTTP mode the bearer token comes from the `Authorization` header and is passed through to GitHub (`middleware/token.go:26-41`).
  - `BearerAuthTransport` attaches the token only to the configured GitHub hosts and strips it elsewhere, including on redirects (`transport/bearer.go:36-68`). It re-adds the header on every hop, so the allowlist is the protection.
  - The optional request-state key comes from the `GITHUB_MCP_SERVER_MRTR_STATE_KEY` environment variable. The key itself is not in the repo.
- **Tool policy layers:**
  - Read-only mode: CLI flag is a ceiling, and request headers and `/readonly` URLs can only narrow it.
  - Toolsets, exclude-tools, scope filtering and feature flags.
  - `delete_repository` is removed from the inventory when no state key is set (`pkg/http/server.go:283-293`, `401-408`).
- **Lockdown:** `pkg/lockdown/lockdown.go`. It is used by `issues.go` (8 references), `pullrequests.go` (6) and `lockdown.go` (1) in `pkg/github`.
- **Container:** the Dockerfile pins its base images by digest and uses distroless for the runtime image. The user and mount settings were not read.
- **Bundled agent instruction files:** there is no `AGENTS.md` or `CLAUDE.md`. `.github/copilot-instructions.md`, `.github/agents/go-sdk-tool-migrator.md` and `.github/prompts/*` exist. They are untrusted data and I did not follow them. A pattern search of the `*.md` files for injection-style phrases found nothing.

## 3. Source index

| ID | Source | Authority | Date |
|---|---|---|---|
| S1 | https://github.com/github/github-mcp-server/security/advisories/GHSA-pjp5-fpmr-3349 (CVE-2026-48529), copied in `research/github-advisories.json` | Maintainer advisory, medium, CVSS 6.0 | Published 2026-06-09. Offline snapshot taken 2026-10-23, not rechecked. |
| S2 | https://github.com/github/github-mcp-server/security/advisories/GHSA-w4q6-qw23-4rg7 (CVE-2026-47427), same file | Maintainer advisory, high, CVSS 7.5 | Published 2026-07-20. Offline snapshot taken 2026-10-23, not rechecked. |
| S3 | skill `control-map.md` and `http.md` | Bundled BRACE research baseline (2026-10-22), guidance | Not rechecked |
| S4 | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization | Protocol requirement, version-specific | 2026-07-28, not rechecked |
| S5 | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | MCP guidance | Not rechecked |
| S6 | https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html | Guidance | Not rechecked |

`research/ts-advisories.json` and `research/notion-advisories.json` were not read. They cover other packages, and this repo is Go. This is a limit.

## 4. Advisory comparison

| Advisory | Affected range per advisory | Evidence in this commit | Status |
|---|---|---|---|
| S1: lockdown cache stuck on the first user's GraphQL client | `>= 0.22.0, < 1.1.2`; fixed in 1.1.2 | No `GetInstance` or global singleton remains. `GetRepoAccessCache` builds a new cache per request from that request's GraphQL and REST clients (`pkg/github/dependencies.go:463-488`). It appends `WithIdentity(token)` (`dependencies.go:481-483`), which prefixes cache keys with a SHA-256 of the token (`lockdown.go:92-99`, `333-341`). `viewerLogin` is held per instance (`lockdown.go:166-201`). The type comment says each request must construct its own instance (`lockdown.go:21-23`). | `likely_pass` for the described flaw. The package version is not resolvable here. |
| S2: nil dereference in `completion/complete` | `<= 0.33.0 (also latest main)`; the advisory lists no patched version | `CompletionsHandler` checks `req == nil \|\| req.Params == nil \|\| req.Params.Ref == nil` and returns an error (`pkg/github/server.go:203-207`). A test, `TestCompletionsHandler_RejectsMissingRef`, exists at `server_test.go:508`. | `likely_pass` for the described flaw. Not run. |

The S2 advisory describes the old path as `pkg/github/server.go:198`. The fix at `server.go:205` and the test are in this snapshot. The advisory record still shows no patched version, so a downstream consumer cannot map it to a release from the advisory alone.

**Not checked:** other callers of the completion path, such as `RepositoryResourceCompletionHandler`, for other nil dereferences. Panic recovery inside the SDK is also unchecked.

## 5. Findings and hardening items, ordered by impact

None is a confirmed vulnerability. Each is a lead or an evidence request.

### F1. Lockdown cache table is shared across identities in HTTP mode (`needs_evidence`, low)

- **What I saw:** Identity separation depends on the key prefix, not on separate tables. All instances use the same `cache2go` table, `"repo-access-cache"` (`lockdown.go:107`, `211-212`).
- **Why it matters:** The prefix is added only when the request has a non-empty token (`dependencies.go:481`). The HTTP middleware always sets one, but the token-extraction code skips extraction if token info is already in the context (`middleware/token.go:20-24`). A downstream embedder that sets token info with an empty token would fall back to the unscoped key and share the cache between users.
- **Related:** Each distinct token creates its own entries, held until the idle TTL (default 20 minutes). Memory therefore grows with the number of distinct tokens in that window. I did not check the cache2go cleanup behaviour, so I rate this as a possible memory-growth issue, not a confirmed one.
- **Source:** S1, S3 (E06, R04).
- **Remediation:** Fail closed when lockdown is on and no token identity is present. Add a test that two tokens with different permissions do not see each other's cached results.

### F2. Delete-confirmation state is not bound to the caller's identity (`needs_evidence`, low)

- **What I saw:** The sealed state holds owner, repo, repository ID and expiry (`repositories.go:779-784`). It is sealed with AES-256-GCM using nil additional data (`internal/requeststate/sealer.go:59,76`), so it is not tied to the user or token.
- **Why it matters:** Another caller who obtained the sealed blob and a matching confirmation response could replay it within 10 minutes. Deletion still uses the replaying caller's own GitHub permissions (`repositories.go:912-923`), and the target, ID and expiry are re-checked. The elicitation answer comes from the connected client, not from the model.
- **Controls present:** An exact-name confirmation, a repository-ID check against rename or recreation, and a check that the state key is configured (`repositories.go:826-829`). The tool is also hidden in HTTP mode without a key.
- **Stdio mode:** `NewRandom()` creates a process-local key (`ghmcp/server.go:206`).
- **Not established:** I did not look for check-and-consume. A confirmation could be replayed within the TTL for the same target.
- **Source:** S6, S3 (B01, B05, B06).
- **Remediation:** Bind the state to a token or user digest through additional authenticated data, and consider single use.

### F3. No Origin or Host validation, and CORS allows any origin (`needs_evidence`, informational)

- **What I saw:** CORS returns `Access-Control-Allow-Origin: *` and allows the `Authorization` header (`middleware/cors.go:41-45`). The server comments explain this: it authenticates with bearer tokens, not cookies. The cross-origin check in the MCP SDK is disabled on purpose (`handler.go:253-257`). `ListenHost` can bind to loopback (`pkg/http/server.go:44-46`, `276-281`).
- **Why it matters:** For a loopback deployment with a bearer token held by a browser client, DNS rebinding relies on the attacker already having a token. That is a deployment question and not a server flaw I can show.
- **Source:** S5, S3.
- **Remediation:** Document recommended Host and Origin enforcement at the proxy for loopback or non-public deployments, and keep a test that credentials are never ambient.

### F4. Operator ceilings apply only if static filters are configured (`needs_evidence`, informational)

- **What I saw:** When no static CLI filters are set, the inventory is the default set. Per-request headers (`X-MCP-Tools`, `X-MCP-Toolsets`) can add tools within it (`handler.go:319-352`, `442-468`). Read-only, exclude-tools and lockdown are narrow-only. An operator setting for any of them is a ceiling that request headers cannot lift (`handler.go:335-337`, `dependencies.go:454-460`).
- **Why it matters:** An operator relying on the default posture should know write tools are available unless they set `--read-only` or a toolset restriction. This is by design and is not a vulnerability.
- **Source:** S3.

### F5. Token passthrough has no server-side audience check (`needs_evidence`, informational)

- **What I saw:** The server does not validate the token's issuer, audience or expiry. It passes the bearer token to GitHub, which validates it (`middleware/token.go`, `transport/bearer.go`). GitHub is the resource server being called, so this is not a confused-deputy relay.
- **What I did not trace:** An OAuth proxy fronting the MCP endpoint. A custom `AuthorizationServer` can be set (`pkg/http/server.go:56-61`). Behind a proxy, token-audience correctness would depend on the proxy.
- **`TrustProxyHeaders`:** This option is off by default and `BaseURL` overrides it (`server.go:63-68`).
- **Source:** S4, S3 (B02, B03).

## 6. Coverage table

| Boundary or check | Status | Evidence | Owner |
|---|---|---|---|
| HTTP body limit | `likely_pass` | 5 MiB default via `MaxBytesReader`, also passed to the SDK handler (`body_limit.go:12-37`, `handler.go:264`). Depth, element and batch limits are not traced. | Server |
| Auth challenge | `likely_pass` | A missing header returns 401 with `WWW-Authenticate` metadata. A malformed header returns 400 (`token.go:26-35`). | Server |
| Token egress | `likely_pass` | Host allowlist on `BearerAuthTransport` (`transport/bearer.go`). | Server |
| Lockdown isolation | `likely_pass` (F1 open) | See section 4. | Server |
| Completion handler input validation | `likely_pass` | `server.go:203-207`. | Server |
| Read-only, toolsets, exclude, scope ceilings | `likely_pass` | `handler.go:290-352`. | Server and operator |
| Destructive-action approval | `likely_pass` (F2 open) | Elicitation, exact name, repository-ID recheck. | Server and host |
| Per-request server construction | `likely_pass` | A new `mcp.Server` per request in stateless mode (`handler.go:227-258`). | Server |
| Stateless HTTP, no session or task store | `na_candidate` | `Stateless: true` at `handler.go:261`. Searched only `pkg/http`. Not an absence proof for the whole repo. | Server |
| Host approval, tool-call UX and client isolation | `needs_evidence` | Outside this repo. | Host or client |
| Hosted endpoint, gateway, deployed version, key custody | `needs_evidence` | Public source only. | GitHub operations and deployers |
| Stdio local isolation | `needs_evidence` | Inherits the user's authority and environment. The token is in process memory. Sandbox, mounts and the container user are not read. | Deployer and host |
| Persistent influence and memory | `needs_evidence` | Not reviewed. | Server |
| Audit and logging | `needs_evidence` | A log file is created with mode 0600 (`pkg/http/server.go:135`). The debug level when a file is configured and the lockdown debug lines that include usernames were not traced for secrets. | Server and operator |
| Supply chain | `needs_evidence` | Docker base images are digest-pinned. `go.sum`, workflows and release signing were not compared. | Maintainers |

## 7. Controls supported in code (static reading only)

- Per-request lockdown cache keyed by token digest, replacing the singleton.
- Nil-safe completion handler.
- Operator ceilings that headers cannot raise or relax (read-only, exclude-tools, lockdown).
- Body limit before parsing.
- Token scoped to configured GitHub hosts, including on redirects.
- Two-step confirmation for repository deletion, with the target re-checked.

## 8. Unreviewed source

I read these only in part or not at all:

- **Tool implementations under `pkg/github/`.** The file glob returned 100 of 297 matching files, and I opened only `server.go`, `dependencies.go` and part of `repositories.go`. Not traced end to end: `actions.go`, `code_scanning.go`, `copilot.go`, `gists.go`, `git.go`, `issues.go`, `pullrequests.go` and others. This includes write paths, argument validation, and lockdown use at the 15 call sites in `issues.go`, `pullrequests.go` and `lockdown.go`.
- **The rest of the repository.**
  - `pkg/inventory`, `pkg/scopes`, `pkg/http/middleware/{mcp_parse,pat_scope,scope_challenge}.go`, `pkg/http/oauth`, `pkg/http/servercard`.
  - `internal/oauth`, `internal/githubapp`, `pkg/octicons`, `pkg/utils`, `cmd/mcpcurl`.
  - `pkg/github/ui_dist` and embedded UI resources, and the MCP Apps resources.
  - `.github/workflows`, goreleaser, `go.sum`, and the third-party license files.
- **Dependencies:** go-sdk v1.8.0 and others were not checked against any advisory source because I had no lookup. `research/ts-advisories.json` and `research/notion-advisories.json` were not opened.

## 9. Proposed controlled tests

Run these only in a disposable environment with fake credentials. I have not run any of them. Owners are the maintainers or the deployer.

1. **Lockdown isolation.** Two tokens with different access to the same repository, issued concurrently and repeated for cache hits. Expect each user's decision to match that user's own access. Also run one request with token info injected and an empty token. Expect failure or no shared cache.
2. **Completion input.** Send `completion/complete` with empty params, a missing `ref`, and an unknown ref type. Expect a JSON-RPC error and a live process.
3. **Delete confirmation replay.** Replay the sealed state with a different token, a changed repo, an expired state and a mismatched name. Expect rejection. Replay a valid state twice. Expect the second to fail if single use is adopted.
4. **Ceilings.** With `--read-only` and `--exclude-tools` set, send headers trying to re-enable tools and lockdown off. Expect the ceiling to hold.
5. **Egress.** A mock server redirecting off-host, including 307 and 308. Expect no `Authorization` header.
6. **Limits.** Oversized body, deep nesting and a large batch. Expect early rejection and bounded memory.
7. **Loopback.** A forged `Host` or `Origin` against a loopback bind. Expect rejection at the proxy or server, as the operator chooses.

## 10. Explicit limits

- No network lookup. The advisory records are bundled snapshots from 2026-10-23 and were not rechecked against the live maintainer pages.
- I did not run tests, a build, the server or any scanner, and I did not read the tests beyond noting that they exist.
- Whether this commit equals any released tag or the hosted service is unknown. The advisory's fixed version (1.1.2) cannot be tied to a tag here.
- A "no findings" result for a boundary means only that I identified none in the code I read. It is not a security approval. Rollout, stop conditions and recovery decisions belong to accountable people.
