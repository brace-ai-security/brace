# BRACE MCP review: makenotion/notion-mcp-server

**Review date:** 2026-10-23. **Commit:** 730ae781ba28beeaf0865025a3f2ed4c25ea2387 (package 2.5.2).
**Method:** static file review only. I did not run, install or import any code, connect to any server or call any API. Web lookup was unavailable, so every advisory source below is marked **not rechecked**. I did not read `research/ts-advisories.json` in full (the read was truncated). I covered the entries the skill index names (GHSA-6qxp, rvq5, 22jm, jm63, 6prh, 46jr, f897).
**Report destination:** inline, as requested. I wrote no file.

Nothing in the inspected files tried to steer the review. `CLAUDE.md` is ordinary developer guidance, and I treated it as data.

## 1. Scope and inventory

| Item | Finding |
|---|---|
| Component | MCP **server** that wraps the Notion REST API. It generates tools from `scripts/notion-openapi.json` (24 operationIds, listed below). |
| Transports | stdio (default) and Streamable HTTP via Express (`scripts/start-server.ts:35-40`). |
| Negotiated protocol revision | **Unknown.** It is chosen by SDK 1.29.0 at runtime, and negotiation was not observable. |
| Extensions | None enabled. The server declares only `capabilities: { tools: {} }` (`proxy.ts:140`). There are no Tasks, Skills, Apps or auth extensions, and no sampling or roots. |
| Operating systems | Not constrained in the code. The Dockerfile uses `node:20-slim` and CI runs Node 20 and 22 on Linux. |
| Downstream | `https://api.notion.com` (spec `servers[0]`). `BASE_URL` can override it (`start-server.ts:30`, `init-server.ts:31`). |
| Credential sources | `NOTION_TOKEN` or `OPENAPI_MCP_HEADERS` from the environment (`proxy.ts:248-278`). With `--enable-token-passthrough`, a per-session `Notion-Token` header. For HTTP gateway auth, `--auth-token`, `AUTH_TOKEN`, or an auto-generated token written to `$TMPDIR/.notion-mcp-auth-token-<pid>` with mode 0600 (`start-server.ts:49-54`). |
| Tools (24) | **Read:** get-user, get-users, get-self, post-search, get-block-children, retrieve-a-block, retrieve-a-page, retrieve-a-page-property, retrieve-a-comment, query-data-source, retrieve-a-data-source, list-data-source-templates, retrieve-a-database, retrieve-page-markdown. **Write or delete:** patch-block-children, update-a-block, delete-a-block, patch-page, post-page, create-a-comment, update-a-data-source, create-a-data-source, move-page, update-page-markdown. |
| Launch and supply chain | README tells users to run unpinned `npx @notionhq/notion-mcp-server`. The Docker image is `node:20-slim` with no digest. Publishing uses npm provenance with OIDC, `--ignore-scripts`, and SHA-pinned actions. |
| Resolved versions (`package-lock.json`) | `@modelcontextprotocol/sdk` **1.29.0** (declared `^1.29.0`), `@hono/node-server` 2.0.11, `hono` 4.12.32, `express` 4.22.2, `body-parser` 1.20.6, `axios` 1.18.0, `path-to-regexp` 0.1.13, `qs` 6.15.2, `form-data` 4.0.6, `zod` 3.24.1, `multer` 1.4.5-lts.1 (devDependency). |

### Ownership boundaries
- **This repository owns** the HTTP wrapper, the bearer gate, session handling, tool generation, and the Notion HTTP client.
- **The MCP host/client owns** tool approval, human-in-the-loop, and the stdio process sandbox. These are not established here.
- **Notion owns** authorization of each call. Its integration-token capabilities and page sharing are what limit data access. Deployed Notion internals are out of scope.
- **The deployer owns** the network perimeter, TLS, the reverse proxy, container hardening and secret custody.

## 2. Source table

All records were retrieved or bundled on 2026-10-23 and are **not rechecked**, because lookup was unavailable.

| ID | Source | URL | Authority | Date |
|---|---|---|---|---|
| S1 | TS SDK GHSA-f897-62hf-6gxq, body/batch limits | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq | Maintainer advisory | 2026-10-15 |
| S2 | TS SDK GHSA-46jr-4wx8-v453, validation exhaustion | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-46jr-4wx8-v453 | Maintainer advisory | 2026-10-15 |
| S3 | TS SDK GHSA-rvq5-wwqv-78pq, audience | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq | Maintainer advisory | 2026-10-05 |
| S4 | TS SDK GHSA-22jm-h49p-29qw, tasks | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-22jm-h49p-29qw | Maintainer advisory | 2026-10-02 |
| S5 | TS SDK GHSA-6prh-2h8m-c8cw, client redirects | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw | Maintainer advisory | 2026-10-02 |
| S6 | TS SDK GHSA-6qxp-vccf-f47h, issuer binding | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h | Maintainer advisory | 2026-09-30 |
| S7 | TS SDK GHSA-jm63-cq47-j5jp, shared server | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-jm63-cq47-j5jp | Maintainer advisory | 2026-10-15 |
| S8 | MCP security best practices | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | Protocol guidance | bundled review date |
| S9 | MCP Streamable HTTP transport | https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http | Protocol requirements (revision 2026-07-28); the negotiated revision is unknown | 2026-07-28 |
| S10 | OWASP MCP Security Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html | Guidance | bundled review date |
| S11 | OWASP Transaction Authorization | https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html | Guidance | bundled review date |
| S12 | OWASP Logging | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | Guidance | bundled review date |
| S13 | OWASP Software Supply Chain | https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html | Guidance | bundled review date |
| S14 | Snyk Agent Scan | https://github.com/snyk/agent-scan | Tool documentation | bundled review date |
| S15 | BRACE checklist and 2026-10-22 research | https://braceframework.org/CHECKLIST.md | Adopted profile | 2026-10-22 |

Other records in the bundled research:
- **`research/notion-advisories.json`** is `[]`. This is a snapshot, not proof of no vulnerabilities. No Notion-maintained advisory is recorded for this repository.
- **`research/github-advisories.json`** covers `github/github-mcp-server` (Go): GHSA-pjp5-fpmr-3349 and GHSA-w4q6-qw23-4rg7. They concern a different package and do not apply here. This is context only.

## 3. Findings (ordered by impact)

### F1. Resolved SDK 1.29.0 is below every relevant fix; HTTP mode is exposed to the body/batch and validation-exhaustion advisories — `gap` (dependency status); exploitability `needs_evidence`
- **Trigger and dataflow:** a client reaches `POST /mcp`. Express parses the body (`app.use(express.json())`, `start-server.ts:43`). The transport and `McpServer` validation then run inside SDK 1.29.0 (lock lines 594-595).
- **Affected scope:** HTTP transport only. The advisories exclude stdio-only servers (S1, S2).
- **Evidence:**
  - **S1** fixes at SDK 1.30.1 and affects 1.10.0–1.30.0. Resolved 1.29.0 is inside that range. The advisory says `express.json()` does not limit batch length.
  - **S2** fixes at 1.32.0 and affects 1.3.0–1.31.0. The fix adds `maxToolInputElements`, which is off by default. No such option appears in the repository: the server uses the low-level `Server` class (`proxy.ts:140`) and never sets it.
  - The `^1.29.0` range allows a fresh install to resolve a patched version, but this commit's lockfile pins 1.29.0. `package.json` has an `overrides` entry that bumps only `@hono/node-server`, not the SDK.
- **Mitigating factors seen in code:**
  - Default binding is `127.0.0.1` (`server-options.ts:3`).
  - `/mcp` requires a bearer token unless `--unsafe-disable-auth` is set. The advisories say credentials are not needed *unless the application authenticates before the SDK*, and here it does (`start-server.ts:102`). The exposure therefore applies to holders of the bearer token, or to everyone when auth is disabled or the host is bound to `0.0.0.0` without a proxy.
  - Express's body-parser default of about 100 kB limits body size, but not batch length or element counts. Whether the unreachable *low-level `Server`* class is subject to the S2 validation path was not demonstrated.
- **Not demonstrated:** I did not confirm that the S2 allocation path is reachable through `Server.setRequestHandler`, which uses a different validation route from `McpServer.registerTool`. I did not test batch handling at runtime.
- **BRACE:** B07, R01, E06. **Sources:** S1, S2.
- **Remediation:** bump the SDK to ≥1.32.0 and regenerate the lockfile. Set an explicit body limit, for example `express.json({ limit })`. Cap batch size at a reverse proxy or in a pre-dispatch check. Keep HTTP bound to loopback or a private network.

### F2. HTTP authorization is one static shared bearer with non-constant-time comparison and no session-to-principal binding — `needs_evidence` / hardening, not a confirmed exploit
- **Evidence:**
  - `token !== authToken` is a plain string comparison (`start-server.ts:75`).
  - The header is parsed with `authHeader.split(' ')[1]` (`:61`) and is not checked for the `Bearer` scheme.
  - There is no throttling or lockout.
  - A request supplying a bad token gets 403 and a missing token 401. This lets a caller tell the two cases apart.
  - Sessions are keyed only by `mcp-session-id`. Any holder of the shared token and a session ID can use that session (`:126`, `:216-237`).
  - Session IDs come from `randomUUID()`.
  - There is no cap or idle timeout on the `transports` map. Sessions are removed only on close (`:177-181`).
- **Why this is not a confirmed gap:**
  - Over network timing, string comparison is generally impractical to exploit.
  - A single shared secret, so no multi-user isolation boundary exists to violate.
  - Session IDs are unguessable per the code.
- **BRACE:** B02, B04, E06 (no per-client identity; the audience concept does not apply to a static token). **Sources:** S8, S10.
- **Remediation:** use `crypto.timingSafeEqual` after a length check, enforce the `Bearer` scheme, cap sessions and add an idle expiry, and rate-limit failed authorizations. Prefer one OAuth-style identity per client if multi-user use is intended.

### F3. Optional token passthrough lets a connecting client choose which Notion identity the session acts as; the binding is held for the session lifetime — `needs_evidence`
- **Trigger:** the deployer enables `--enable-token-passthrough` or `ENABLE_TOKEN_PASSTHROUGH=true` (default off, `server-options.ts:28`). A client then sends `Notion-Token` on `initialize`.
- **Evidence:**
  - The header must match the `ntn_` or `secret_` prefix and a length of 8–300 (`token.ts:27-48`).
  - The token is passed to `initProxy` and fixed for that proxy (`start-server.ts:133-183`).
  - Logging uses `redactToken` (`:150`, `token.ts:120`).
  - `Authorization` is only used as a Notion-token fallback when gateway auth is disabled (`:138`). With auth enabled, the gateway bearer and the Notion token stay separate. This is good.
  - A gateway-authenticated client can therefore operate with any Notion token it holds. Notion authorizes the actual calls, so the server does not widen authority.
- **Residual issues:**
  - The shared gateway secret still does not tell different callers apart, so the audit trail cannot attribute actions to a person.
  - The server has no allowlist of which Notion workspaces or integrations a client may use.
  - `unsafe-disable-auth` plus passthrough makes the endpoint a keyless relay. DNS-rebinding protection covers browsers only, not a non-browser client on the same network.
- **BRACE:** B02–B04, E08, E06. **Sources:** S8, S10.
- **Remediation:** if multi-tenant use is intended, put per-client authentication in front, log a client-identity field, and document that passthrough should not be combined with `--unsafe-disable-auth`.

### F4. DNS-rebinding and Origin protection is enabled only when authentication is disabled — `likely_pass` for the unauthenticated case; `needs_evidence` for the authenticated case
- **Evidence:** `getDnsRebindingProtectionOptions` returns options only when `transport === 'http'` and `unsafeDisableAuth` is true (`server-options.ts:127-139`). It allows `localhost`, `127.0.0.1`, `[::1]` and the configured host, with matching origins.
- **Notes:**
  - With auth enabled, a browser cannot present the bearer unless it holds it. Origin or Host checks are not applied, but the secret gates access.
  - The allowed-host list contains the configured bind host. If `--host 0.0.0.0` is used, the literal `0.0.0.0` is allowed. A real reverse-proxy hostname would not be, so legitimate access through a proxy name is blocked when auth is off.
  - `/health` is unauthenticated and returns the port and a timestamp (`start-server.ts:91-98`). This is low information, but it makes the service discoverable.
- **BRACE:** B08, B09. **Sources:** S8, S9 (Origin validation).
- **Remediation:** apply Host and Origin validation in both modes. Keep `/health` minimal, or put it behind the same gate when exposed.

### F5. All write and delete tools are exposed with no server-side approval or scope policy; annotations are advisory — `needs_evidence` (host owns approval)
- **Evidence:**
  - Write tools exist: `delete-a-block`, `patch-page`, `update-a-data-source`, `move-page`, `update-page-markdown` and others (see the inventory).
  - `ListTools` marks GET operations `readOnlyHint` and everything else `destructiveHint` (`proxy.ts:175-187`).
  - There is no tool allowlist, read-only mode, or per-operation gate in the repository. Authority is whatever the Notion integration token can do.
  - Arguments are forwarded after JSON-string deserialization (`proxy.ts:42-124`). That function bounds JSON-decode passes to 3 (`MAX_UNWRAP_DEPTH`) but not total size or depth.
- **Why this is not a gap by itself:** the server's job is to proxy Notion, and Notion enforces page sharing. Approval belongs to the MCP host and the operator's integration scope.
- **BRACE:** B01, B05, B06, E06. **Sources:** S10, S11.
- **Remediation:** add an optional environment or flag to restrict the tool set (for example read-only), and document least-privilege integration scopes. The host should require approval for destructive tools. The skill's guidance is that server read-only annotations are not an authorization policy.

### F6. Untrusted Notion content is returned verbatim to the model; no sanitization or provenance marking — `needs_evidence`
- **Evidence:** responses are passed back as `JSON.stringify(response.data)` in a `text` content block (`proxy.ts:214-221`). Tool descriptions come from the repository's own spec, not from remote data, so tool-metadata poisoning from Notion is not a path here. Page, comment and database content is third-party-controlled and is returned unmodified.
- **Scope:** this is the normal prompt-injection surface for any content connector. Outcomes depend on the host and model.
- **BRACE:** E04, R01–R03. **Sources:** S8, S10.
- **Remediation:** host-side handling is the main control. Optionally label results as untrusted data, and test with benign valid-shaped injection fixtures.

### F7. Error paths: tool errors return Notion's structured response to the model; logging is metadata-only — `likely_pass`
- **Evidence:** `console.error` logs only the status and message (`proxy.ts:223-225`, `http-client.ts:235-238`). The token is not logged and passthrough tokens are redacted. In HTTP mode logs go to stdout and stderr.
- **Caveat:** in stdio mode, stdout is the protocol channel. The code uses `console.error` for errors. The HTTP-startup `console.log` lines are on the HTTP path only. I did not examine `bin/cli.mjs` or the esbuild bundle (`scripts/build-cli.js`), so stdout contamination in the built CLI is `needs_evidence`.
- **Gap noted:** there is no structured audit record (client, tool, target, outcome) and no request-level ID. This is a `needs_evidence` item against R03, R13 and A02. Source S12.

### F8. Local file-upload read path is latent: arbitrary local path read exists in code but no operation in the current spec triggers it — `na_candidate` (conditional)
- **Evidence:** `prepareFileUpload` opens `fs.createReadStream(filePath)` for any parameter whose multipart schema is `string/binary` (`http-client.ts:104-151`, `file-upload.ts:8-40`). It has no path allowlist, canonicalization or symlink handling.
- **Absence search:** I grepped `scripts/notion-openapi.json` for `multipart/form-data` and `"format": "binary"` and found no matches. None of the 24 operations reach this path today.
- **Risk if the spec gains an upload operation:** a tool call could upload any file the process can read to Notion. This matters most for stdio, where the server inherits the user's full authority.
- **BRACE:** B05, B09, B11. **Sources:** S8 (local server guidance), S10.
- **Remediation:** before adding file-upload operations, restrict to an allowed directory, canonicalize and reject symlinks, and cap size. The test suite exercises the path in `__tests__` (not executed by me).

### F9. Redirect, issuer and audience advisories (S3, S5, S6) — `na_candidate` for the server; the HTTP client path to Notion is `needs_evidence`
- **Evidence and absence search:**
  - S3 (audience): grepped `src` and `scripts` for `requireBearerAuth`, `verifyAccessToken`, `OAuth`. This server does not use SDK OAuth resource-server helpers. It uses a static bearer, so S3 does not apply. That also means there is **no audience validation** because there is no token issuer (see F2).
  - S5/S6 (client OAuth and redirects): these affect SDK *client* transports and OAuth client functions. The server imports only server-side SDK modules.
  - Outbound Notion calls use axios, not the SDK. `BASE_URL` can redirect all traffic and the bearer token to any host, which is a deployer-controlled setting.
- **Not examined:** axios redirect handling for custom headers to a different origin. Notion's API does not normally redirect. Treat as `needs_evidence`.
- **BRACE:** B03, B09. **Sources:** S3, S5, S6.

### F10. Shared-server and Tasks advisories (S4, S7) — `na_candidate`
- **Evidence:** S7 affects `@modelcontextprotocol/server` 2.x. This repository uses `@modelcontextprotocol/sdk` 1.29.0, which S7 excludes (1.26+). In HTTP mode a **new `MCPProxy`/`Server` and transport are created per session** (`start-server.ts:167-184`). That is the fresh-server pattern S7 recommends.
- S4 affects the experimental `taskStore`. Grepped `src` and `scripts` for `taskStore`: no usage. The server declares only `tools`.
- Note that sessions, not requests, are the isolation unit. Within a session, concurrent calls share state. That is expected.
- **BRACE:** E06, R04, E09. **Sources:** S4, S7.

### F11. Supply chain and container posture — mixed
- **`likely_pass`:**
  - CI and publish actions are pinned by SHA.
  - Publishing uses npm provenance with OIDC and `--ignore-scripts`, and the workflow permissions are scoped.
  - The Dockerfile uses `npm ci --ignore-scripts`. The lockfile is committed.
- **`gap` or `needs_evidence`:**
  - README encourages unpinned `npx @notionhq/notion-mcp-server`, so each launch runs whatever is latest, with the user's full authority and environment (S13, S14).
  - The Docker base image is not pinned by digest.
  - The Dockerfile sets no `USER`, so the container runs as root.
  - `ENV OPENAPI_MCP_HEADERS="{}"` is a harmless placeholder. Real tokens must be injected at runtime, and the compose file passes none. Secret custody is the deployer's.
  - The Dockerfile runs `npm ci --omit-dev` and then `npm run build`, which needs `tsc` from a devDependency. Whether the build succeeds as written was not checked and is a reliability, not a security, question.
  - `npm audit` data was not available, so transitive vulnerabilities (express 4.22.2, axios 1.18.0, hono 4.12.32) are `needs_evidence`.
  - The auto-generated auth token is written to the shared temp dir with mode 0600. The filename includes the PID, which is predictable but not secret. It is not cleaned up on exit.
- **BRACE:** B10–B12, C02, C05, E02. **Sources:** S13, S14.
- **Remediation:** document a pinned version for `npx`, pin the image digest, add `USER node`, delete the token file on shutdown, and run `npm audit` in CI.

### F12. Stop and recovery
- **`needs_evidence`:** the server has no cancellation, task, or kill-switch mechanism. Session close removes the transport from the map. Revocation means revoking the Notion token or restarting the process. In-flight Notion writes cannot be recalled. The `readOnlyHint`/`destructiveHint` annotations do not change this.
- **BRACE:** R11, R12, R14. **Sources:** S10.

## 4. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Inventory, pins | `needs_evidence` | Lockfile shows SDK 1.29.0 (F1); `npx` unpinned (F11) | S13 | Maintainer, deployer |
| Launch and supply chain | mixed | F11 | S13, S14 | Maintainer, deployer |
| Identity, delegated authority (HTTP) | `needs_evidence` | F2, F3 | S8 | Maintainer, deployer |
| Identity (stdio) | `needs_evidence` | Process inherits the user's authority; no server-side identity | S8 | Host, user |
| Business authorization, approval | `needs_evidence` | F5 | S11 | Host, operator |
| Publication, integrity (tool definitions) | `likely_pass` | Tool metadata is static from the in-repo spec; no remote discovery. Hash pinning or update review for the spec is not implemented | S10 | Maintainer |
| Untrusted metadata, returned content | `needs_evidence` | F6 | S8, S10 | Host |
| Network, egress | `needs_evidence` | Fixed Notion base URL; `BASE_URL` override (F9); no outbound allowlist enforcement | S8 | Deployer |
| Origin / Host protection | partial | F4 | S9 | Maintainer |
| Client and tenant isolation | `likely_pass` (per-session server, F10); `needs_evidence` for passthrough (F3) | `start-server.ts:116-184` | S7 | Maintainer |
| Resource, parser limits | `gap` (dependency), `needs_evidence` (reachability) | F1 | S1, S2 | Maintainer |
| Persistent influence | `na_candidate` | Searched `src` and `scripts` for memory/cache/skill/hook writes: none. Only the token file is written | S10 | Maintainer |
| Stop and recovery | `needs_evidence` | F12 | S10 | Operator |
| Audit, incident response | `needs_evidence` | F7 | S12 | Maintainer, deployer |
| Local file access (upload path) | `na_candidate` today | F8 | S8 | Maintainer |
| Extensions (Tasks, Skills, Apps, auth) | `na_candidate` | `capabilities: { tools: {} }` only | S4 | Maintainer |
| Legacy paths (HTTP+SSE, sessions) | session-based Streamable HTTP is enabled; HTTP+SSE not found | Grepped `SSEServerTransport`: none | S9 | Maintainer |

## 5. Controls supported in code
- Loopback default bind (`server-options.ts:3`).
- Bearer authentication required on `/mcp` by default, with an unsafe flag that prints warnings, including for non-loopback binds (`:103-125`).
- Auto-generated 32-byte random token written to a mode-0600 file instead of being logged.
- DNS-rebinding and Origin checks when auth is off.
- Fresh server and transport per session. Unguessable session IDs.
- Per-operation `Notion-Version` pinned from the spec, not user-controlled (`http-client.ts:88-102`).
- Passthrough tokens are shape-checked and redacted in logs. They are not mined from `Authorization` when gateway auth is on.
- Bounded JSON-unwrap passes (`proxy.ts:80`).
- Publish workflow: provenance, SHA-pinned actions, `--ignore-scripts`.

## 6. Missing evidence and unreviewed scope
Unreviewed source or runtime evidence:
- **Source not read:**
  - `src/openapi-mcp-server/openapi/parser.ts` (schema conversion and `$ref` handling)
  - `auth/*` (template and types)
  - `src/openapi-mcp-server/index.ts`
  - `scripts/build-cli.js` and `bin/cli.mjs`
  - `.github/workflows/increment-version.yml`
  - `RELEASING.md`
  - all `__tests__` files
  - the Notion spec's operation-level schemas (only operationIds and `multipart`/`binary` markers were searched)
  - the rest of the README configuration sections
- **Hidden files:** I did not run the `repo/.*` hidden-file Glob specified in the skill beyond the root listing. Only `.dockerignore` and `.gitignore` were visible in the root listing. `.github/*` was read as noted above.
- **Dependency tree:** I did not audit transitive packages. `research/ts-advisories.json` was only partly read.
- **Not available:** the negotiated protocol revision, the deployed Notion service, the host's approval behavior, the actual runtime configuration, network topology, and any live advisory recheck.
- **Public code is not the deployed service.** Notion's own hosted MCP is a separate product and was not assessed.

## 7. Proposed controlled tests (do not run without owner approval; use disposable fixtures and fake tokens)

| Test | Allowed | Denied / expected | Owner |
|---|---|---|---|
| After SDK upgrade: oversized body, a batch over the cap, and a deeply nested tool argument against HTTP | Normal call succeeds | 413 or 400 or a bounded error; the process stays healthy | Maintainer |
| Wrong, missing and malformed `Authorization` (for example no `Bearer` prefix) | Correct token works | 401 or 403; no session created | Maintainer |
| Session ID reuse from a second client with the same shared token; many idle sessions | Documented behavior | Session count capped; idle sessions expire | Maintainer |
| Passthrough: invalid, prefix-less and oversized `Notion-Token`; gateway token placed in the Notion header | Valid test token works | 401; no cross-use of the gateway secret | Maintainer |
| Auth-disabled mode with a foreign `Host` or `Origin` header | Loopback `Host` works | 403 on mismatch | Maintainer |
| Spec gains an upload operation: path outside an allowed directory, symlink, `/etc` file | File inside the allowed dir works | Rejected before open | Maintainer |
| Stdio: run under a sandbox with no network except Notion | Notion calls work | Other egress blocked; stdout carries only protocol frames | Deployer, host |
| Read-only integration token used for `delete-a-block` | Reads succeed | Notion rejects the write | Operator (Notion workspace) |
| Kill and restart drill with an in-flight write | Process stops | No further effects after revocation of the integration token | Operator |

## 8. Summary
- **Highest-value item:** F1. The lockfile resolves `@modelcontextprotocol/sdk` 1.29.0, below the S1 (1.30.1) and S2 (1.32.0) fixes, and HTTP mode uses that SDK. The S2 fix also needs an explicit `maxToolInputElements` setting, which is absent. Exploitability depends on the bearer gate and on whether the low-level `Server` path hits the affected validation, which I did not demonstrate. S3–S7 are not applicable to this server as built.
- **Hardening candidates:** F2 (static shared bearer, plain comparison, unbounded sessions), F3 (passthrough audit identity), F4 (Origin/Host only when auth is off), F5 (no tool restriction mode) and F11 (unpinned `npx`, root container).
- **No security Pass, certification or deployment verdict is given.** This is a focused MCP review, not the 53-item BRACE assessment. No findings beyond those listed were identified within the recorded scope, and every advisory record is dated and **not rechecked**.
