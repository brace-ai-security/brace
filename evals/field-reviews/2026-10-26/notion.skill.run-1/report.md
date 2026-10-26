Reading is done and I'm writing up the findings now. I've covered the HTTP/stdio entrypoints, the proxy and HTTP client, the lockfile pins, the Dockerfile and CI, and the bundled advisory records. I did not run or write anything. The report is below rather than saved as `mcp-review.md`, because this session can't write files.

# BRACE MCP review: makenotion/notion-mcp-server

This is a focused MCP review. It is not the full 53-item assessment. It issues no security pass, certification or release verdict.

## 1. Scope and inventory

- **Target:** commit `730ae781ba28beeaf0865025a3f2ed4c25ea2387`, package `@notionhq/notion-mcp-server` 2.5.2, review date 2026-10-26.
- **Component:** self-hosted server only. It proxies a bundled OpenAPI spec (`scripts/notion-openapi.json`) to the Notion API. The hosted Notion service and any MCP host or client are not supplied.
- **Transports:**
  - stdio (default).
  - Streamable HTTP via `--transport http`, using Express 4 and a per-session `StreamableHTTPServerTransport`.
  - Negotiated protocol revision: unknown (SDK 1.29.0 negotiates it, and no runtime trace was supplied).
  - Operating systems: not stated; the Dockerfile is Linux (`node:20-slim`).
  - Extensions: none enabled. The server declares only `capabilities: { tools: {} }` (`proxy.ts:140`).
- **Resolved versions** (`package-lock.json`):

  | Package | Declared | Resolved |
  |---|---|---|
  | `@modelcontextprotocol/sdk` | `^1.29.0` | **1.29.0** |
  | express | `^4.21.2` | 4.22.2 |
  | axios | `^1.8.4` | 1.18.0 |
  | `@hono/node-server` | override `^2.0.5` | 2.0.11 |

- **Credentials:**
  - Notion token from `NOTION_TOKEN` or `OPENAPI_MCP_HEADERS`.
  - HTTP gateway bearer from `--auth-token`, `AUTH_TOKEN`, or an auto-generated value written to `os.tmpdir()/.notion-mcp-auth-token-<pid>`.
  - Optional per-session Notion token via the `Notion-Token` header, when `--enable-token-passthrough` or `ENABLE_TOKEN_PASSTHROUGH=true` is set.
- **Entrypoints:** `scripts/start-server.ts` (stdio branch, `POST/GET/DELETE /mcp`, `GET /health`) and `src/init-server.ts`.
- **Tools** (23 operationIds in the bundled spec, each exposed as a tool through `ListTools`). All are enabled, with no allowlist or read-only mode.
  - Reads: `get-user`, `get-users`, `get-self`, `retrieve-a-block`, `get-block-children`, `retrieve-a-page`, `retrieve-a-page-property`, `retrieve-a-comment`, `retrieve-a-data-source`, `retrieve-a-database`, `list-data-source-templates`, `retrieve-page-markdown`.
  - Read-like POSTs: `post-search`, `query-data-source`.
  - Writes: `patch-block-children`, `update-a-block`, `delete-a-block`, `patch-page`, `post-page`, `create-a-comment`, `update-a-data-source`, `create-a-data-source`, `move-page`, `update-page-markdown`.
- **Launch:** the Dockerfile runs `ENTRYPOINT ["notion-mcp-server"]` on a floating `node:20-slim` tag with no digest and no `USER` directive, so it runs as root. `docker-compose.yml` publishes no ports and passes no environment.

## 2. Sources

All advisory records come from `research/sources.json`, which is a supplied record of earlier research. They were retrieved 2026-10-26T10:13:35Z. **None were rechecked in this session** (no lookup was available). That retrieval date is distinct from the publication dates below and from this review's date.

| ID | Source | Authority | Published / updated |
|---|---|---|---|
| S1 | [GHSA-f897-62hf-6gxq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq) | Maintainer advisory. Affected `sdk >=1.10.0 <1.30.1`, fixed 1.30.1. | 2026-10-15 / 2026-10-15 |
| S2 | [GHSA-46jr-4wx8-v453](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-46jr-4wx8-v453) | Maintainer advisory. Affected `sdk >=1.3.0 <1.32.0`, fixed 1.32.0. | 2026-10-15 / 2026-10-19 |
| S3 | [GHSA-jm63-cq47-j5jp](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-jm63-cq47-j5jp) | Maintainer advisory. Only the `@modelcontextprotocol/server` 2.0.0–<2.3.0 package is listed. | 2026-10-15 / 2026-10-19 |
| S4 | [GHSA-rvq5-wwqv-78pq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq), [GHSA-22jm-h49p-29qw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-22jm-h49p-29qw), [GHSA-6qxp-vccf-f47h](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h), [GHSA-6prh-2h8m-c8cw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw) | Maintainer advisories, assessed for relevance in section 3. | 2026-09-30 to 2026-10-05 |
| S5 | [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) | Guidance, via `control-map.md`. | Date not recorded in the files read |
| S6 | [OWASP SSRF](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html), [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | Guidance. | Unknown |

The notion-mcp-server advisory collection recorded 0 published entries (`sources.json`, query at 2026-10-26T10:13:34Z). That means no published entries in that collection and nothing more.

## 3. Findings, ordered by impact

### F1. Resolved SDK 1.29.0 predates the HTTP exhaustion fixes, and no mitigation is configured (BRACE B07, R01, E06)
- **Evidence:** `package-lock.json` resolves `@modelcontextprotocol/sdk` to 1.29.0. S1 lists `>=1.10.0 <1.30.1` as affected (body size and batch length). S2 lists `>=1.3.0 <1.32.0` as affected (validation memory exhaustion), and says an upgrade alone is insufficient: `maxToolInputElements` must also be set.
- **Reachable path:** `start-server.ts:120` `app.post('/mcp')` passes `req.body` to `transport.handleRequest`. The code configures no `maxToolInputElements` or batch limit.
- **Extent and prerequisites:**
  - Only the HTTP transport is affected. The advisories exclude stdio.
  - With auth enabled, the attacker needs the gateway bearer.
  - With `--unsafe-disable-auth`, any host that passes the Host/Origin checks can send the requests.
- **Partial mitigation:**
  - `app.use(express.json())` (`start-server.ts:43`) applies Express's default body limit, which is 100kb as I recall from library behavior and have not verified here. That limits body size but not element count or batch length.
  - The `express.json()` middleware is registered before `authenticateToken`, so JSON parsing runs on unauthenticated requests. That is bounded by the same limit.
- **Remediation:**
  - Update the lockfile to a fixed SDK (S1 says 1.30.1, S2 says 1.32.0).
  - Set `maxToolInputElements` as S2 describes.
  - Set an explicit `express.json({ limit })`.
  - Confirm the settings at runtime.
- **Limit:** whether 1.29.0 behaves as the advisories describe was not tested.

### F2. Predictable auto-generated token file is written without exclusive creation (BRACE B03, E12)
- **Evidence:** `start-server.ts:52-53`:
  ```
  authTokenFilePath = path.join(os.tmpdir(), `.notion-mcp-auth-token-${process.pid}`)
  fs.writeFileSync(authTokenFilePath, authToken, { mode: 0o600 })
  ```
- **Mechanism, from Node semantics and not tested:**
  - The path is predictable from the pid.
  - `mode` applies only when the file is newly created.
  - `writeFileSync` follows symlinks and overwrites an existing file.
  - A co-resident local user could pre-create that path, or plant a symlink there, and read the token or redirect the write.
- **Prerequisites:** a shared, multi-user host, HTTP transport, and no `--auth-token` or `AUTH_TOKEN`.
- **Remediation:** use `fs.mkdtemp` plus the `wx` flag, or print the token once to a protected channel.
- **Status:** README describes this mode as "only for development", which narrows exposure.

### F3. Gateway bearer check is weak in construction (BRACE B02, B03)
- **Evidence:** `start-server.ts:61` uses `authHeader.split(' ')[1]`, which accepts any scheme word. `start-server.ts:75` uses `token !== authToken`, a non-constant-time comparison. Missing and invalid tokens return distinct codes (401 vs 403).
- **Extent:** a single shared static secret with no audience, expiry, rotation or per-client identity. The MCP protocol makes authorization optional, but BRACE expects it for protected access. This is a design limit, not an exploit. The timing leak is practically hard to exploit and is not demonstrated.
- **Remediation:** `crypto.timingSafeEqual` on equal-length digests, and enforce the `Bearer` scheme. The README shows `--auth-token` on the command line, which exposes the secret in the process list.

### F4. Sessions are bound to a session ID only, not to a caller, and the lookup is shared (BRACE E06, R04)
- **Evidence:** `start-server.ts:126-128`, `216-236`. `transports[sessionId]` is looked up after only the shared-bearer check, and nothing records which caller created the session.
- **Mechanism:**
  - Under one shared bearer, all holders are the same principal, so there is no cross-user path inside the supplied design.
  - With passthrough enabled, the session's Notion token is fixed at initialize (`start-server.ts:149,183`). A second client that learns the session ID could use the first client's Notion authority.
  - With `--unsafe-disable-auth`, the session ID is the only gate.
  - The session ID is a `randomUUID`.
- **Also note:** the server and proxy are created per session, so S3 (shared-instance leak) does not apply as written. S3's affected package, `@modelcontextprotocol/server` 2.x, is not installed here, and I did not test the 1.29.0 transport for the same flaw. Status is `needs_evidence`, not a confirmed gap.

### F5. Every Notion write and delete tool is exposed with no server-side approval or filtering (BRACE B01, B05, B06)
- **Evidence:** `proxy.ts:164-190` lists all 23 operations. Non-GET operations get `destructiveHint: true` and GET operations get `readOnlyHint: true`. `proxy.ts:196-240` executes any listed operation with no approval, allowlist or argument policy.
- **Extent:**
  - Annotations are hints, not authorization policy (see `control-map.md`).
  - `post-search` and `query-data-source` are reads but are labelled destructive, because the hint keys off the HTTP verb.
  - The effective limit is the Notion integration token's scope. The README advises read-only integration capabilities, which is the operator's control.
  - Approval behavior belongs to the MCP host, which was not supplied (unknown).
- **Remediation:** add an optional read-only or allowlist mode, and a distinct hint for read-like POSTs.

### F6. Notion page content returns to the model as untrusted text (BRACE E04, R01–R03)
- **Evidence:** `proxy.ts:214-220` returns `JSON.stringify(response.data)` with no marking or filtering.
- **Extent:**
  - Anyone who can edit pages the integration can read has a write path into model context. Prompt injection is therefore plausible by policy.
  - The mitigation is the host's and the operator's: integration scope, and approval of write tools.
  - Server-side sanitization is not a standard control here, so this is a risk note and not a server defect.

### F7. Latent local file read in the HTTP client's multipart path (BRACE B09, B11)
- **Evidence:** `http-client.ts:104-141` calls `fs.createReadStream(filePath)` on a tool-supplied string. There is no path allowlist, canonicalization or size cap.
- **Reachability:**
  - It triggers only for operations whose multipart schema has `string/binary` properties (`file-upload.ts:8-40`).
  - A search of `scripts/notion-openapi.json` found no `multipart` or `binary` matches, so the bundled spec does not reach this path.
  - The spec path is fixed relative to the script (`start-server.ts:28`).
- **Status:** `likely_pass` for the shipped configuration; it becomes a gap if the spec gains file-upload operations or a different spec is supplied. The tests in `client/__tests__/http-client-upload.test.ts` exercise this path, and I did not execute them.

### F8. Smaller observations
- `BASE_URL` (`start-server.ts:30`, `init-server.ts:31-33`) replaces the API base while the Notion bearer header is still sent. An operator who sets it would send the token to that host (B03, B09).
- `GET /health` is unauthenticated and returns the port and transport (low).
- DNS-rebinding Host/Origin protection is enabled only when auth is disabled (`server-options.ts:130`). With auth enabled it relies on the bearer.
- There is no TLS. Binding `--host 0.0.0.0` sends the bearer in clear text over the network.
- `deserializeValue` has a bounded depth for string unwrapping, but recursion on decoded structures has no explicit depth cap. Impact is limited by the body limit. Status is `needs_evidence`.
- The proxy does not validate tool arguments against `inputSchema` before `executeOperation`. Path parameters and query keys pass through `openapi-client-axios`. Traversal-like values would still be authorized by the same Notion token. `needs_evidence`.
- The Dockerfile uses a floating base tag, no digest and runs as root. `npm ci --ignore-scripts` is a good practice.

## 4. Coverage table

| Boundary / check | Status | Evidence | Owner |
|---|---|---|---|
| Inventory and ownership | `likely_pass` | Section 1 | Maintainer |
| Launch and supply chain | `needs_evidence` | Dockerfile floating tag; CI actions pinned by SHA; publish uses `--provenance --ignore-scripts` (workflow grep lines only) | Maintainer / operator |
| Gateway authentication (HTTP) | `gap` (hardening) | F3 | Operator / maintainer |
| Token file | `gap` | F2 | Maintainer |
| Delegated authority / passthrough | `needs_evidence` | F4; prefix-only token shape check (`token.ts:39-48`) | Maintainer |
| OAuth / issuer / audience / redirect advisories (S4) | `na_candidate` | No SDK OAuth client or server-auth code found in the files read; the server uses its own bearer; no `redirectPolicy` or tasks usage. Absence is from reading only the files listed in section 6. | Maintainer |
| Business authorization | `needs_evidence` | F5; host approval unknown | MCP host / operator |
| Tool metadata integrity | `likely_pass` | Tool definitions are generated from the fixed bundled spec | Maintainer |
| Returned content | `needs_evidence` | F6 | Host / operator |
| Network and egress | `needs_evidence` | Fixed Notion base URL; `BASE_URL` override (F8) | Operator |
| State isolation | `needs_evidence` | Per-session server and transport; F4 | Maintainer |
| Resource limits | `gap` | F1 | Maintainer |
| File access | `likely_pass` for the shipped spec | F7 | Maintainer |
| Stop and recovery | `needs_evidence` | Session close deletes the transport (`start-server.ts:177`); no worker or queue was found | Maintainer |
| Audit and logging | `needs_evidence` | Token is redacted (`token.ts:120`); error logs omit bodies; no audit log of tool calls or approvals | Maintainer / operator |
| stdio local boundary | `needs_evidence` | Inherits environment and user authority; no sandbox in repo | Host / operator |

## 5. Controls supported in code

- A loopback default bind (`server-options.ts:3`).
- Bearer authentication on `/mcp` routes by default.
- Opt-in token passthrough, off by default.
- Notion token shape check and redacted logging.
- Dedicated `Notion-Token` header, so the gateway secret is not reused as a Notion token unless auth is disabled.
- Unsafe auth only through an explicitly named flag, with warnings.
- Host/Origin protection when auth is disabled.
- Per-session proxy and server construction.
- Pinned workflow actions and provenance on publish.

## 6. Unreviewed scope

I did not read these, so they are unreviewed:
- `openapi/parser.ts`
- `auth/*` (including `template.ts`)
- `scripts/build-cli.js`
- `client/polyfill-headers.ts`
- Test files and snapshots (not executed).
- README sections beyond the first 60 grep matches.
- `RELEASING.md`
- The workflow files (seen only through grep lines).
- `CLAUDE.md`

Also not reviewed: axios, express and openapi-client-axios advisories (the bundled advisory index does not cover them), the hosted Notion service, and the MCP host.

## 7. Proposed controlled tests

Run these only in a disposable environment, with fake Notion tokens.

| Test | Allowed | Denied | Owner |
|---|---|---|---|
| Oversized batch / high-element-count `tools/call` against HTTP with a fixed SDK and `maxToolInputElements` set | Normal call succeeds | Oversized request is rejected without memory growth | Maintainer |
| Two OS users, auto-generated token, pre-created file or symlink at the pid path | Owner reads their token | Second user cannot read it or redirect the write | Maintainer |
| Wrong scheme word, wrong token, missing token | Correct `Bearer` token | Rejected | Maintainer |
| Session-ID replay from a second client with passthrough on | Creator can use the session | Second caller is rejected, or the gap is confirmed | Maintainer |
| Read-only Notion integration token with write tools called through the host | Reads work | Writes fail at Notion, and the host asks for approval | Operator / host |
| Page containing instruction-like text, read through the host | Task completes | No unapproved write or exfiltration | Host owner |
| Spec with a multipart binary field, `filePath` set to a path outside the intended directory | Intended upload path | Out-of-scope path is refused | Maintainer |

No findings above are confirmed by execution. Static reasoning about a denial or an exposure is not a runtime result. Final deployment decisions belong to accountable people, with gradual rollout, bounded exposure, stop conditions and tested recovery.
