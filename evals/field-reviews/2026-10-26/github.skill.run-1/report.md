# BRACE MCP review: github/github-mcp-server

Review date: 2026-10-26. Commit `f38526264abb14961b32cea386e38ec6d3cf674f`. Method: static file reading only. I did not run or install anything, and I did not connect to any server. This is a focused MCP review, not a 53-item BRACE assessment. It gives no security Pass and no release verdict.

I did not write `mcp-review.md`, because this session allows no file writes. The report is below.

## 1. Scope and inventory

| Item | Finding |
|---|---|
| Components | MCP server only. It has a stdio mode and a stateless Streamable HTTP mode (`pkg/http`). |
| Transports | stdio (`internal/ghmcp/server.go:309`) and Streamable HTTP (`pkg/http/handler.go:258`). |
| Negotiated protocol revision | Unknown. It is negotiated at runtime by go-sdk, and I did not run it. |
| Enabled extensions | The MRTR / multi-round-trip tool path (`delete_repository`, `server.go:945`). Form and URL elicitation (the OAuth prompter and `delete_repository`). MCP Apps UI metadata is gated by a feature flag. I did not review the Apps host side. |
| SDK | `github.com/modelcontextprotocol/go-sdk v1.8.0` (`go.mod:13`), the declared version. `go.sum` was not cross-checked, so the resolved version is unconfirmed. |
| Credential sources | `GITHUB_PERSONAL_ACCESS_TOKEN`. OAuth login (PKCE or device flow). A GitHub App installation token provider. In HTTP mode, the client's `Authorization` header. |
| Downstream | The GitHub REST, GraphQL, raw and upload endpoints, resolved from `--gh-host`. |
| Entrypoints | `stdio`, `http`, `cmd/mcpcurl` (client helper, unreviewed), `agent-plugin/mcp.json` (points at the hosted `https://api.githubcopilot.com/mcp/`), and the Docker image (`CMD ["stdio"]`). |
| Operations | Toolsets are registered in `pkg/github/*.go`. I traced `delete_repository` in full and sampled the HTTP selection code. The remaining ~299 files are **unreviewed**, including the other write tools (create, merge, push, workflow and Actions tools). Their per-tool enforcement is therefore unknown. |

Ownership:
- **This repository:** tool selection, token forwarding, the OAuth callback and the delete confirmation flow.
- **GitHub API:** the actual authorization decision (PAT, OAuth and App scopes, SSO).
- **Host or client:** human approval UI, whether elicitation reaches a person, sandbox and process isolation.
- **Deployer:** TLS, reverse proxy, and the Host and Origin allowlist.

## 2. Sources

| ID | Source | Authority | Date |
|---|---|---|---|
| S1 | `skill/references/advisories.md` | Bundled index of TS and Python SDK advisories | BRACE 2026-10-22 research. **Not rechecked in this session.** |
| S2 | `skill/references/control-map.md`, `http.md`, `stdio.md` | Guidance and protocol pointers | Same. Not rechecked. |
| S3 | [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) | Guidance | Date from the bundle. Not rechecked. |
| S4 | [RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html) (protected resource metadata, cited in `pkg/http/oauth/oauth.go:1`) | Standard | Publication date unknown. Not rechecked. |
| S5 | [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | Guidance | Not rechecked. |
| S6 | [OWASP Transaction Authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html) | Guidance | Not rechecked. |
| S7 | [MCP Authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Version-specific protocol requirements | Not rechecked. |

Advisory lookup: the bundled index covers only the TypeScript and Python SDKs, Splunk, and adjacent components. **No entry maps to the Go SDK, chi, or go-github.** I recorded no matching advisory. This does not show the dependencies are unaffected, because live lookup was unavailable.

## 3. Findings (ordered by impact)

### F1. `--enable-command-logging` writes full MCP traffic to the log (opt-in) — BRACE R03, A02, E10–E12; S5. Status: gap, low to medium

- **Trigger:** the operator sets `--enable-command-logging` in stdio mode. `IOLogger` then logs every byte read and written:
  - `pkg/log/io.go:35`: `l.logger.Info("[stdin]: received bytes", ..., "data", string(p[:n]))`
  - `pkg/log/io.go:45`: `l.logger.Info("[stdout]: sending bytes", ..., "data", string(p))`
- **Dataflow:** the logged data includes tool arguments and results, such as private repository contents, issue text, code-scanning alerts and Actions logs. The destination is stderr or `--log-file`. The file is created `0600` (`server.go:329`) at Debug level.
- **No redaction or minimization:** I found none in the logging path.
- **HTTP mode:** the field exists in `ServerConfig` but nothing reads it (`Grep`: only `ghmcp/server.go:407` uses the logger). The flag is accepted and does nothing in HTTP mode. This is a documentation mismatch, not a leak.
- **Remediation:** document the flag as exposing private repository data. Add redaction or a payload-size cap, and a warning at startup.
- **Limit:** the logger also records tokens only if the MCP payload contains them. I did not trace that.

### F2. Sealed delete confirmation is not bound to the caller or single-use — BRACE B01, B05, B06; S6. Status: needs_evidence (not a confirmed gap)

The controls are good (see section 4). Two properties are missing:
- **Not bound to caller:** the sealed state holds only `Owner`, `Repo`, `RepositoryID` and `ExpiresAt` (`repositories.go:779-784`). It does not hold the caller or token identity.
- **No check-and-consume:** `Open` verifies the AEAD, and there is no replay record within the 10-minute TTL (`repositories.go:893`).
- **Reachability:** with `GITHUB_MCP_SERVER_MRTR_STATE_KEY` set, all HTTP instances share a key. A state obtained by user A could be presented by user B. B must still have GitHub delete permission, because the call uses B's token (`dependencies.go:329-375`). B must also supply the typed name. I found no privilege gain.
- **Human confirmation:** the `InputResponses` content is supplied by the client. The server only checks that `confirmedName == fullName` (`repositories.go:907-908`). It cannot show a person typed it. That is **host-owned**.
- **Proposed test:** see T2.

### F3. Host-header-derived URLs and an unauthenticated listener default (HTTP deployment) — BRACE B08, B09; S3, S4. Status: needs_evidence, low

- **No Host or Origin validation:** with no `--base-url` and no `--trust-proxy-headers`, the 401 challenge and the metadata URL use `r.Host` (`pkg/http/oauth/oauth.go:222-229`). `sendAuthChallenge` puts that value in `WWW-Authenticate` (`middleware/token.go:54`).
- **Reachability:** a client that can reach the port can choose the advertised `resource_metadata` host in its own response. I did not show a path by which another user receives it.
- **Listener:** `--listen-host` defaults to empty, which binds all interfaces (`server.go:277-279`), over plain `http.Server` with no TLS (`server.go:226-230`).
- **CORS:** `Access-Control-Allow-Origin: *` (`cors.go:41`), justified in code by bearer-only auth. That reasoning holds only while no cookie or ambient credential is accepted. I saw none.
- **Server timeouts:** only `ReadHeaderTimeout` (60s) is set.
- **Owner:** the deployer sets `--base-url`, TLS, and a proxy allowlist.

### F4. Scope-based tool filtering fails open on lookup error (defense in depth only) — B02, B07; S3. Status: likely_pass for enforcement, with a caveat

- **Fail-open path:** in HTTP, if `FetchTokenScopes` errors, `PATScopeFilter` returns the unfiltered builder (`handler.go:488-491`). stdio only logs a warning (`server.go:351`).
- **Why this is not a bypass:** the filter hides tools, and GitHub still enforces the real scopes on each call. Fine-grained PATs and App tokens are not filtered at all (`handler.go:481`), so the GitHub API is the only enforcement for them.

### F5. Build-embedded OAuth client secret — C02, C05, E12. Status: needs_evidence

- `Dockerfile:28-34` injects `OAUTH_CLIENT_SECRET` into the binary via `-ldflags` (`buildinfo.OAuthClientSecret`).
- The code and `main.go:261` call it a public, non-confidential credential. That is reasonable for a distributed client, but anyone can extract it.
- **Recommendation:** keep rotation and abuse-monitoring for that app owner-side.

### F6. Local OAuth callback can be aborted by any local sender (login DoS) — B04, R01. Status: gap, informational

- `callback.go:96-100`: a request with a wrong `state` (or an `error` parameter, `callback.go:86-94`) calls `report(...)` first, so the first result wins (`callback.go:117-122`). The flow then fails and must be restarted.
- **Code theft is not possible:** the state check, PKCE S256 (`flow.go:96`) and loopback binding (`callback.go:45-56`) stop it.
- **Container mode:** it binds `0.0.0.0` (`callback.go:47`) and warns about it (`flow.go:91`).
- The state is compared with `!=`, not constant time. That has negligible impact here.

## 4. Controls supported in code (`likely_pass`, static only)

Static reasoning is not a runtime test. Each item is qualified by the predicate quoted.

- **Token egress scoping (B03, B09):** `BearerAuthTransport` attaches `Authorization` only when the request host matches `AllowedHosts`, and deletes it otherwise (`bearer.go:42-47`). This is applied to REST, GraphQL and raw in both modes. Caveat: it matches host:port from configuration, and I did not test redirects.
- **`delete_repository` confirmation (B01, B05):**
  - Gated: the tool is disabled in HTTP when no state key is set (`server.go:284-287`), and filtered out of the registry by `filterUnavailable` (`handler.go:401-408`).
  - Requires an exact `owner/repo` typed match (`repositories.go:908`).
  - Rejects changed target, expiry, `RepositoryID == 0`, and a changed repository ID at the time of delete (`repositories.go:890-922`).
  - Requires a form-elicitation-capable client and a minimum protocol version (`repositories.go:945-946`).
  - stdio uses `requeststate.NewRandom()` (`server.go:206`), so state does not survive restart.
  - Sealer: AES-256-GCM with a random nonce (`sealer.go:53-61`).
- **Per-request narrowing only (E06):**
  - Read-only, lockdown and exclude headers can only restrict (`request_config.go:23-51`, `dependencies.go:454-460`).
  - Static `--tools`, `--toolsets` and `--exclude-tools` bound what request headers can add (`handler.go:342-344`, `handler.go:314-317`).
- **Per-request server and token (E06):** `mcp.StreamableHTTPOptions{Stateless: true}` (`handler.go:261`), a fresh `RequestDeps.GetClient` per call built from that request's token (`dependencies.go:329-375`). I saw no shared client or token cache in HTTP.
- **Body limits (B07):** `WithMaxBodySize` runs first, with a `MaxBytesReader` and a 5 MiB default (`body_limit.go:12-35`). The same limit is passed to the SDK (`handler.go:264`). No element or batch limit is visible in this repository. That is unknown for go-sdk.
- **OAuth:**
  - PKCE S256, with an unguessable `state` (`flow.go:74-96`).
  - The callback server binds loopback by default.
  - `html/template` escapes the error page (`callback.go:150-157`).
  - A fixed port that cannot bind is fatal, not downgraded (`flow.go:58-60`).
- **Supply chain (C02, C05, B10):**
  - Base images in the Dockerfile are digest-pinned (`Dockerfile:1,10,38`).
  - GitHub Actions are pinned by commit SHA.
  - `cosign` is pinned to v3.1.3. That is a modern release outside the legacy-blob advisory noted in `advisories.md`. The workflow also signs with `--new-bundle-format=false` (legacy `.sig`) plus a native-bundle step.
  - The AI workflows pass `issue_body` to a third-party action (`ai-issue-assessment.yml:24`), with `contents: read` and `issues: write` only. Whether the action treats that body as untrusted is unknown and unreviewed.
- **GitHub App key (C05):** no CLI flag for the private key; a path option is preferred (`main.go:265-268`).

## 5. Coverage table

| Boundary or check | Status | Evidence | Owner |
|---|---|---|---|
| Inventory and pins | likely_pass, qualified | Digest and SHA pins; `go.mod` versions declared but not resolved | Repo |
| Identity and delegated authority | likely_pass | Per-request token to GitHub; no audience check of its own, because GitHub validates the token. Whether that meets MCP resource-binding expectations on the hosted server is unknown | GitHub |
| Business authorization (writes) | partial | `delete_repository` traced; other write tools **unreviewed** | Repo, host |
| Approval binding | needs_evidence | F2; host UI unseen | Host |
| Tool publication and integrity | needs_evidence | Static registry; no signed or hashed tool-definition pin; client-side change detection is host-owned | Host |
| Untrusted returned content | needs_evidence | Lockdown mode and content-window exist (`--content-window-size`); sanitizers (`bluemonday`) in `go.mod`; not traced end to end | Repo |
| Network and egress | likely_pass for token scoping, otherwise partial | `bearer.go`; `--gh-host` is operator-set, and no user-supplied URL fetch was traced | Repo, deployer |
| Client and tenant isolation | likely_pass | Stateless; per-request deps. `schemaCache` is shared but holds schema reflection, not user data | Repo |
| Resource and parser limits | partial | Body only; no batch or element limits seen | Repo, SDK |
| Persistent influence | na_candidate | Searched `memory`, `skill` and `hooks` in server code; none found. Upstream repository instruction files exist (`.github/copilot-instructions.md`) but are untrusted data and unreviewed. Not an MCP-server control | – |
| Stop and recovery | needs_evidence | stdio cancels on signal (`server.go:321`); no Tasks extension seen. Child-process behavior is not applicable (no subprocess launch found) | Host, deployer |
| Audit | partial | F1; no policy or approval IDs in logs; "MCP-specific audit logging" is documented as not yet available (`docs/policies-and-governance.md:153`) | GitHub |
| stdio process isolation | needs_evidence | Server inherits user authority; the Dockerfile uses distroless but no non-root `USER` and no seccomp are declared. This is image-level and unknown at runtime | Host, deployer |

Unreviewed (recorded reason: out of this review's time or budget): the other ~290 `pkg/github` tool files, `pkg/lockdown`, `pkg/inventory`, `pkg/http/middleware/{mcp_parse,pat_scope,scope_challenge}.go`, `pkg/raw`, `internal/githubapp`, `cmd/mcpcurl`, `e2e`, `docs/*` (except one), the remaining workflows, and tests. **A clean result for these cannot be inferred.**

## 6. Proposed controlled tests (not executed; owners listed)

- **T1 (repo owner):** run with fake data and enable command logging. Call a tool that returns a canary string and confirm whether it appears in the log. Expected after fix: redacted or an explicit startup warning.
- **T2 (repo owner):** in a disposable org, obtain a sealed state as user A and replay it as user B (both with delete rights on a throwaway repo). Expected: allowed today; desired: denied unless the caller matches. Also test replay after a first success and a changed repository ID.
- **T3 (deployer):** send a request with a forged `Host` and `X-Forwarded-Host` to the HTTP listener, with and without `--base-url`/`--trust-proxy-headers`. Expected: advertised URLs should come from config only.
- **T4 (repo owner):** make a mock authorizer return 5xx for the scopes lookup and confirm that write tools remain bounded by GitHub's own 403 (not by the filter).
- **T5 (host owner):** confirm the host presents the elicitation to a human and does not auto-fill `repository_name`.
- **T6 (SDK owner):** send an oversized JSON-RPC batch and a deeply nested tool input to the HTTP endpoint in isolation. Expected: rejected before heavy allocation.

## 7. Limits

- No live recheck of any source was possible. All dates are bundle-recorded or unknown.
- The hosted `api.githubcopilot.com` deployment is out of scope. The target metadata says its internals are unknown.
- No finding here is a runtime test result.
- No deployment decision is implied. Any rollout of write tools needs accountable-person sign-off, staged exposure, stop conditions and a recovery test.
