I've read the in-scope files, the lockfiles and the advisory snapshots. Next I'll write the report, which needs no more tool calls.

# MCP review: `@stripe/mcp` stdio-to-HTTP adapter

Review date: 2026-10-23. Method: static file reading only. I ran no code, installed nothing and made no network calls. Nothing here is a security Pass, certification or release verdict.

## 1. Scope and inventory

| Item | Value | Evidence |
|---|---|---|
| Component | Local stdio-to-Streamable-HTTP forwarder. It is an MCP server toward the host and an MCP client toward `https://mcp.stripe.com`. | `src/index.ts:3-4,14,32-41` |
| Package and commit | `@stripe/mcp` 0.3.3, commit 8a8818e | `package.json:3` |
| Transports | Inbound: `StdioServerTransport`. Outbound: `StreamableHTTPClientTransport` to a hardcoded URL. | `src/index.ts:32,40-43` |
| Credential source | `--api-key=` argument or `STRIPE_SECRET_KEY`. It is sent as `Authorization: Bearer` on every upstream request. Optional `Stripe-Account` header. | `src/cli.ts:25,38,72-85` |
| Key checks | Must start with `sk_` or `rk_`. A warning is printed for `sk_`. `Stripe-Account` must start with `acct_`. | `src/cli.ts:49-70` |
| Tools, resources, prompts | None defined locally. Everything is forwarded unmodified. The tool set comes from the hosted server, which was not supplied. | `src/index.ts:46-87` |
| Declared SDK range | `@modelcontextprotocol/sdk ^1.17.1` | `package.json:28` |
| Resolved SDK, npm lock | 1.27.1 | `package-lock.json:2065-2067` |
| Resolved SDK, pnpm lock | 1.17.2 | `pnpm-lock.yaml:811,3815` |
| Which lock builds the image | The Dockerfile runs `pnpm install --frozen-lockfile`, so the image resolves 1.17.2. I did not check which lockfile the npm publish pipeline uses. | `Dockerfile:10` |
| Other resolved npm-lock packages | `express` 5.2.1, `hono` 4.12.9, `@hono/node-server` 1.19.11, `eventsource` 3.0.7, `zod` 3.25.76, `cross-spawn` 7.0.6. These are SDK-server dependencies that this adapter does not use. | `package-lock.json` |
| Container | `node:22-alpine` pinned by digest. Runs as non-root `user`. The build installs `typescript` and `pnpm` unpinned from npm with `npm install -g`. | `Dockerfile:4-13` |
| OAuth | None. The adapter sets no `authProvider`. The README mentions OAuth only for the Gemini CLI path. | `src/index.ts:40-43` |
| Protocol revision | Not determinable from this repo, because negotiation happens inside the SDK. Recorded as unknown. | n/a |
| Extensions, Tasks, Skills, Apps | Not implemented locally. Messages pass through opaquely. | `src/index.ts:46-87` |
| Hidden files | `repo/.*` returned nothing. In the package directory: `.dxtignore`, `.gitignore`, `.node-version`, `.prettierrc`. I did not read these. No `AGENTS.md` or `CLAUDE.md` was found at the root or in the package directory. | Glob results |

I did not find any instruction-like content in the files I read, so there was nothing to refuse or report.

## 2. Source index

All advisory records come from `research/*.json`, retrieved 2026-10-23. I did not recheck them online.

| ID | Source | URL | Authority | Date |
|---|---|---|---|---|
| S1 | TS SDK GHSA-6prh-2h8m-c8cw, cross-origin redirects | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw | Maintainer advisory | 2026-10-02 |
| S2 | TS SDK GHSA-6qxp-vccf-f47h, OAuth issuer binding | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h | Maintainer advisory | 2026-09-30 |
| S3 | TS SDK GHSA-cqwc-fm46-7fff, UriTemplate ReDoS (<1.25.2) | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-cqwc-fm46-7fff | Maintainer advisory | 2026-01-07 |
| S4 | TS SDK GHSA-345p-7cg4-v4c7, shared server leak (1.10.0–1.25.3) | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-345p-7cg4-v4c7 | Maintainer advisory | 2026-02-04 |
| S5 | TS SDK GHSA-w48q-cv73-mx4w, DNS rebinding (<1.24.0) | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-w48q-cv73-mx4w | Maintainer advisory | 2025-12-02 |
| S6 | TS SDK server advisories: GHSA-f897-62hf-6gxq (2026-10-15), GHSA-46jr-4wx8-v453 (2026-10-15), GHSA-rvq5-wwqv-78pq (2026-10-05), GHSA-22jm-h49p-29qw (2026-10-02), GHSA-jm63-cq47-j5jp (2026-10-15) | https://github.com/modelcontextprotocol/typescript-sdk/security/advisories (the `html_url`s are in the bundled JSON) | Maintainer advisories | dates as listed |
| S7 | MCP security guidance | https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | Guidance | Bundled review date 2026-10-22 |
| S8 | MCP authorization spec | https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization | Protocol requirements, version-specific | Bundled review date 2026-10-22 |
| S9 | OWASP Logging Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | Guidance | Bundled review date 2026-10-22 |
| S10 | OWASP Supply Chain Security Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html | Guidance | Bundled review date 2026-10-22 |
| S11 | Streamable HTTP transport spec | https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http | Protocol requirements, version-specific | Bundled review date 2026-10-22 |

The other two research files are not usable evidence. `research/github-advisories.json` covers `github/github-mcp-server`, which is not a component here. `research/notion-advisories.json` is `[]`, and an empty list proves nothing. `research/ts-advisories.json` was truncated in my view at about 48 KB of 73 KB. I extracted the remaining records with Grep, which covered ranges, patched versions and dates, but I did not read their full text.

## 3. Findings (ordered by impact)

### F1. SDK client below 1.32.0 follows cross-origin redirects, so custom headers could be re-sent. Status: `needs_evidence`, low to medium impact.

- **Sources:** S1, with S7 and S11 as context. BRACE IDs: B03, B09, E06, E12.
- **Trigger and dataflow:**
  - `main()` builds `StreamableHTTPClientTransport(new URL('https://mcp.stripe.com'), {requestInit: {headers}})` (`src/index.ts:40-43`).
  - `headers` holds `Authorization: Bearer <key>`, `User-Agent` and an optional `Stripe-Account` (`src/cli.ts:76-83`).
  - Neither `fetch` nor `redirectPolicy` is overridden.
  - Both resolved SDK versions, 1.27.1 and 1.17.2, are below the 1.32.0 fix. The advisory says redirects went to any origin and re-sent custom headers, and on 307/308 also the body.
- **Mitigating facts:**
  - The advisory states that current runtimes' `fetch` already drops `Authorization` across origins. The `engines` field allows Node >=18, and the Dockerfile uses Node 22. I did not verify the behaviour for each Node version.
  - The attacker prerequisite is that `mcp.stripe.com`, or something on the path to it, returns a cross-origin redirect. The URL is hardcoded with no user-controlled endpoint, so I found no reachable attacker-controlled redirect in this repo.
  - What could actually leak is the `Stripe-Account` header, the `mcp-session-id` and, on 307/308, the JSON-RPC body (which can contain tool arguments and data). That is not the key itself, assuming `fetch` strips `Authorization`.
- **Not established:** that the hosted service ever redirects. The hosted server was not supplied. This is a static finding, not a runtime result.
- **Remediation (owner: Stripe package maintainers):**
  - Raise the SDK pin to 1.32.0 or later, in both lockfiles.
  - Pass a `fetch` that sets `redirect: 'error'`, which is the advisory's workaround.
  - Do not set `redirectPolicy: 'follow'`.
- **Evidence requested:** the lockfile actually used for the published npm artifact and the Docker image. This request resolves to S1 (2026-10-02).

### F2. Two lockfiles resolve very different SDK versions, and the declared range is a floor only. Status: `gap` (hygiene), medium.

- **Evidence:** `^1.17.1` in `package.json:28`. The npm lock resolves 1.27.1 and the pnpm lock resolves 1.17.2. The Dockerfile builds from the pnpm lock.
- **Why it matters:** the Docker image is on SDK 1.17.2. That version is also in the range for S3 (<1.25.2) and S1.
  - S3 concerns UriTemplate ReDoS. This adapter never constructs a `UriTemplate`, so I found no reachable path. Reachability inside the SDK client was not traced.
  - S4 (<=1.25.3) and S5 (<1.24.0) affect SDK servers over HTTP and DNS rebinding on localhost HTTP servers. The adapter uses only stdio plus an HTTP client, so I classified them as not applicable. Evidence: `src/index.ts:3-4`, with no use of `express` or `StreamableHTTPServerTransport`.
  - Besides what is cited in this report, the pnpm lock was only spot-checked, so I did not cross-check its other packages against advisories.
- **BRACE:** B10, C05, E02. **Sources:** S3, S1, S10 (guidance).
- **Remediation:** keep one lockfile as the source of truth. Make the Docker and npm builds use the same resolution and raise it to the patched SDK. Pinning alone does not fix known flaws.

### F3. The Stripe key is passed on the command line, and the README recommends it. Status: `needs_evidence`, medium.

- **Evidence:**
  - `README.md:15,34,47` put `--api-key=STRIPE_SECRET_KEY` in argv.
  - `src/cli.ts:25-26` parses it from argv.
  - argv is typically visible to other local processes, in shell history and in host config files.
  - The `sk_` warning (`src/cli.ts:56-63`) is only advice. An unrestricted secret key is accepted.
- **Mitigating facts:** the environment-variable path exists (`src/cli.ts:38`). The README tells users to use restricted keys (`README.md:23`). Authority is delegated to the key's restrictions, which Stripe's hosted side enforces, and I could not see that.
- **Unknowns:**
  - Which host stores the config, and who can read it. The owner is the host and the user.
  - Whether the hosted server enforces RAK scopes per tool.
- **BRACE:** B02–B04 (identity and delegated authority), B11. **Sources:** S7, S10. These are guidance, not protocol requirements. The MCP spec's OAuth requirements (S8) don't apply to stdio.
- **Remediation:**
  - Prefer the environment variable in documented examples.
  - Consider rejecting `sk_` keys by default behind an explicit opt-in.
  - Keep the guidance on restricted keys.

### F4. Error and diagnostic output may expose request details. Status: `needs_evidence`, low.

- **Evidence:** `console.error(red('HTTP transport error:'), error)` at `src/index.ts:55`, and `console.error(red('Error forwarding message to server:'), error)` at `src/index.ts:85`. The whole error object is logged to stderr.
- **Why I rate it low:** the key is held in `requestInit.headers`. I could not confirm whether SDK error objects embed request headers, because I did not read SDK source. Stderr is separate from the stdout MCP channel, which is correct.
- **BRACE:** C08, R13. **Source:** S9 (guidance).
- **Remediation:** log only the error message and status code. Add a test that asserts the key never appears in any logged output.

### F5. Hosted-side authorization cannot be assessed from this repo. Status: `needs_evidence`.

- **What the adapter does:** forwards everything and filters nothing (`src/index.ts:46-87`). `--tools` is removed with a warning (`src/cli.ts:17-24`), so all tool permission rests on the RAK and on Stripe's hosted server.
- **What I could not verify:** operation, tenant and argument authorization. Approval for consequential actions. Rate and size limits. Whether untrusted tool output reaches the model. For the last two, the adapter does no sanitizing and neither does anything local.
- **BRACE:** B01, B05, B06, E03–E05, R01–R03. **Owners:** Stripe (hosted server) and the MCP host (approval UI).
- **Sources:** S7, S8.

## 4. Behaviours I checked and did not report as gaps

- **Input handling:** the pre-start `initialize` message is only mined for `clientInfo.name` (`src/userAgent.ts:13-25`). That value goes into `User-Agent` only (`buildUserAgent`, `src/userAgent.ts:31-36`).
- **Header injection:** I considered CR/LF in a self-reported client name. Node's `fetch` header validation should reject it, but I could not verify that statically. The consequence would be a failed request, not an authorization bypass. I raised no finding. The proposed test in section 7 covers it.
- **Pre-initialize ordering:** the `initialized` flag is set before `httpTransport.start()` completes. If a second message arrived early, `httpTransport!` could be null, and the error would be caught and logged (`src/index.ts:71-86`). This is robustness only, not a security gap.
- **Start-up failure:** if `start()` throws, the flag is already true, so later messages fail. It is a liveness issue only.
- **Request ID handling:** there is one process per user and one session, so request ID collisions of the kind in GHSA-jm63 (a server-side issue) don't apply. Evidence: `src/index.ts:32-34`.

## 5. Coverage table

| Boundary / check | Status | Evidence | Authority | Owner |
|---|---|---|---|---|
| Inventory, pins, lockfiles (E01, E02, C05) | `gap` for the lockfile mismatch | F2 | S10 | Stripe maintainers |
| Launch command and supply chain (B10–B12, C02) | `needs_evidence`: README uses unpinned `npx -y @stripe/mcp`. The image base is digest-pinned but `typescript` and `pnpm` are installed unpinned. | `README.md:15,34`, `Dockerfile:5` | S10 | Maintainers and users |
| Local process isolation (stdio.md) | `needs_evidence`: the process inherits the user's authority. The container runs non-root, but the README's inspector example mounts `/var/run/docker.sock`. | `Dockerfile:12`, `README.md:92` | S7 | User and host |
| Credential custody (B02–B04) | `needs_evidence` | F3 | S7 | User and host |
| Outbound endpoint and redirect (B03, B09) | `needs_evidence` | F1 | S1 | Maintainers |
| OAuth discovery and issuer binding (B02–B04) | `na_candidate`: no `authProvider`, `withOAuth` or `auth()` call in `src/` (searched). S2 therefore does not apply to this code. | `src/index.ts` | S2, S8 | n/a |
| Server-side HTTP controls: audience, body and batch limits, tasks, shared state (B07, R01, E06) | `na_candidate`: no SDK HTTP server in the adapter. Searched for `McpServer`, `StreamableHTTPServerTransport`, `express`, `taskStore` in `src/index.ts` and `src/cli.ts`. | n/a | S6 | n/a |
| Tool-argument and business authorization (B01, B05, B06) | `needs_evidence`, hosted | F5 | S7 | Stripe and host |
| Tool metadata and output trust (E03–E05, R01–R03) | `needs_evidence`: the adapter passes content through unchanged, so I found no local mitigation. | `src/index.ts:46-52` | S7 | Host and Stripe |
| Tenant isolation (E06, R04) | `likely_pass` locally: one process, one upstream session. Hosted isolation is unknown. | `src/index.ts:32-34` | S7 | Stripe |
| Stop and recovery (R11, R12, E09) | `needs_evidence`: closing either side closes the other (`src/index.ts:58-60,95-97`), which is a cooperative shutdown. No in-process revocation. Revocation is a key rotation in Stripe's Dashboard. | `src/index.ts` | S7 | User and Stripe |
| Audit and logging (C08, R13) | `needs_evidence`: no local audit trail. Error logging is in F4. | F4 | S9 | Maintainers and Stripe |
| Extensions (Tasks, Skills, Apps, auth extensions) | `na_candidate`: no local implementation. Messages are forwarded opaquely, so the host and hosted server own them. | `src/index.ts:46-87` | S7 | Host and Stripe |

## 6. Controls supported in code

- A key-prefix check and a restricted-key recommendation warning (`src/cli.ts:49-64`).
- A `Stripe-Account` prefix check (`src/cli.ts:66-70`).
- A hardcoded upstream URL with no user-supplied endpoint, so there is no SSRF-style endpoint control (`src/index.ts:14`).
- Strict argument parsing that rejects unknown flags (`src/cli.ts:29-32`). One quirk is that `split('=')` truncates a value containing `=`, which is a functional point, not a security one.
- Logging to stderr only, leaving stdout for MCP traffic (`src/index.ts:102`).
- A removed `--tools` flag with a warning, so permission control rests on the RAK (`src/cli.ts:17-24`).
- A Docker image with a digest-pinned base, a lockfile-frozen install and a non-root user (`Dockerfile:4-12`). This is hygiene, not proof of isolation.

## 7. Unreviewed scope and limits

- **Not supplied:** the hosted `mcp.stripe.com` server and its internals, the Stripe API's authorization behaviour, and the Dashboard's RAK enforcement. The public code does not establish the deployed service's behaviour.
- **Not read:** the SDK source in `node_modules`, `build-dxt.js`, `manifest.json`, `server.json`, `tsup.config.ts`, `src/test/index.test.ts`, the four hidden files named above, and the full text of the truncated parts of `ts-advisories.json`. I did not read the repository's other directories beyond the root README and LICENSE (README skimmed, LICENSE not examined). The DXT manifest and `server.json` could define launch configuration for hosts, so they are unreviewed.
- **Not done:** no advisories were rechecked online, and no live behaviour was observed, including whether `fetch` strips headers on redirects. Advisory records are as retrieved 2026-10-23. No dependency tree beyond the SDK was audited against advisories.
- **Host unknowns:** tool approval, sandboxing and config-file permissions belong to the MCP host and the user.
- Having no further findings means only that I found none within this scope.

## 8. Proposed controlled tests

I have not run any of these. Each should run only in a disposable environment with a fake key and a local stub upstream, and the owner decides whether to run them.

| Test | Expected allowed | Expected denied | Owner |
|---|---|---|---|
| T1. Stub HTTPS upstream returns 307 to a different origin (mocked `fetch`). | A same-origin request succeeds. | No custom headers, session ID or body reach the second origin, or the request errors. This matters for F1 on SDK <1.32.0. | Maintainers |
| T2. Build the image and the npm package, then compare resolved SDK versions with the lockfiles. | One consistent patched version. | A version mismatch between the two paths fails CI. | Maintainers |
| T3. Force transport errors and capture stderr. | Messages without secrets. | The fake key never appears in logs (F4). | Maintainers |
| T4. Send `initialize` with a `clientInfo.name` containing CR/LF or a very long string. | A sanitized `User-Agent`. | No header injection and no crash. | Maintainers |
| T5. Use a RAK without write scope and ask for a write tool through the hosted server (needs authorized access). | Reads succeed. | Writes are denied by Stripe, not by the adapter. | Stripe and the account owner |
| T6. Send two messages before `start()` finishes, and make `start()` fail. | A clean error or retry. | No unhandled rejection and no stuck session. | Maintainers |
