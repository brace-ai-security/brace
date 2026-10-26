# Review of the Notion MCP server (`repo/`)

I read the HTTP entry point, option parsing, token handling, proxy, HTTP client, file-upload helper and Dockerfile. I did not run anything or look at the tests, CI workflows or the OpenAPI spec, so those are unreviewed.

## Higher severity

**1. Local file read through the file-upload path** (`http-client.ts:104-141`, `file-upload.ts`)
- For multipart operations, any parameter whose schema is `string`/`binary` is treated as a local file path.
- The model-supplied string goes straight to `fs.createReadStream(filePath)` with no allow-list, base-directory check or symlink handling.
- A prompt-injected or malicious client can name `/etc/passwd`, `~/.ssh/id_rsa` or `.env` and have the file uploaded to Notion. Over HTTP, the file is read from the server host.
- The `try/catch` in `addFile` can't catch stream errors, which are raised asynchronously. A missing file will surface later as an unhandled stream error rather than the intended "Failed to read file" message.
- Fix: restrict uploads to a configured root directory (resolve and `realpath` before checking), and make this feature opt-in.

**2. Token-passthrough sessions are not bound to the creating client** (`start-server.ts:116-129`, `215-237`)
- Sessions are looked up only by `mcp-session-id`. Each session holds a proxy with its own Notion token.
- With auth disabled, or a shared gateway bearer token, any caller who learns a session ID can use another client's Notion integration.
- Session IDs are random UUIDs, so this is low risk on its own. But the passthrough feature exists to serve multiple integrations, and it has no per-session binding to the token or identity that created the session. Later requests to an existing session never re-check the `Notion-Token` header.

**3. Unauthenticated mode and `/health`** (`start-server.ts:90-107`)
- `--unsafe-disable-auth` is guarded by DNS-rebinding protection and warnings, which is good.
- When it is used with `--host 0.0.0.0`, DNS-rebinding protection allows `Host` values that include the bound host. Combined with the broad `allowedHosts` list, anyone on the network gets full Notion access with the startup token.
- The code only warns about this. I'd consider refusing to start with unauthenticated mode on a non-loopback host unless explicitly forced.

## Medium severity

**4. Non-constant-time token comparison** (`start-server.ts:75`)
- `token !== authToken` is a plain string comparison. Use `crypto.timingSafeEqual` on equal-length hashes.
- The header parsing is also loose. `authHeader.split(' ')[1]` accepts any scheme, not only `Bearer`.
- Returning 403 for a bad token and 401 for a missing one is fine.

**5. Auto-generated auth token left in `/tmp`** (`start-server.ts:52-54`)
- The token file is `0600` and the name includes the PID, which is predictable.
- `writeFileSync` follows symlinks, so a pre-planted symlink at that path on a shared machine could redirect the write. Use `flag: 'wx'` or `mkdtemp`.
- The file is never deleted on exit.

**6. Unbounded sessions** (`start-server.ts`)
- There is no session cap, idle timeout or rate limiting.
- Each `initialize` builds a new `OpenAPIClientAxios` instance and parses the spec, so repeated initializes are a cheap memory and CPU DoS for any authenticated client.
- `express.json()` also uses the default body limit.
- In `POST /mcp`, if `initProxy` or `connect` throws, the transport may already be registered in `transports`.

**7. `Authorization` fallback for the Notion token** (`start-server.ts:135-139`, `token.ts:102-111`)
- With auth disabled and passthrough on, a bearer token with a `ntn_` or `secret_` prefix is used as the Notion token. That is consistent with the design.
- The prefix check is only a shape check, so any client can attach any token. This is acceptable only if you treat passthrough as trusted-client-only. It should be documented.

**8. `OPENAPI_MCP_HEADERS` is passed through unvalidated** (`proxy.ts:248-265`)
- Arbitrary headers are forwarded to the API, including `Host`, `Content-Length` and similar. It is operator-supplied, so this is low risk.
- A non-object JSON value only logs a warning, so the server then starts with no credentials.
- The Dockerfile sets `ENV OPENAPI_MCP_HEADERS="{}"`, which hides a missing `NOTION_TOKEN`. The error only shows up later as 401s.

## Correctness and quality

- **Tool-name truncation collisions** (`proxy.ts:292-297`, `171`): names are cut to 64 characters, but `findOperation` looks up by the full `operationId-method` key. A truncated name that reaches the call handler won't be found. Two long names could also collide after truncation.
- **Lossy JSON decoding of arguments** (`proxy.ts:42-124`): every string that looks like `{...}`, `[...]` or `"..."` is decoded, with no schema check. A legitimate string field, such as page content or a title containing JSON like `{"a":1}`, is silently turned into an object. This can corrupt user content or fail validation. It should only decode where the tool schema expects an object or array.
- **`formData.append(key, value)`** (`http-client.ts:144-148`): `value` can be an object, number or `undefined`. `form-data` throws on some of these.
- **Unused or dead code**: `getContentType` in `proxy.ts` is unused, and `fileCount` in `http-client.ts` is unused.
- **Annotations are incomplete** (`proxy.ts:182-187`): non-GET tools are marked `destructiveHint: true`, including creates and POST-based reads such as search and query. Those POST reads should be `readOnlyHint`. Idempotency is not set.
- **Weak error contract**: tool failures come back as a normal result with `status: 'error'` and no `isError: true`. Clients and models can't reliably tell they failed. Unknown tool names throw instead of returning a tool error.
- **Redundant `Content-Type` handling**: `Content-Type: null` is passed explicitly for bodyless requests. That works, but it is fragile.
- **Unhandled startup errors**: `app.listen` has no `error` handler, so `EADDRINUSE` produces an unhelpful crash. `--port` is parsed with `parseInt` and never checked for `NaN`.
- **Fake return value**: the HTTP branch returns `{ close: () => {} }` that does nothing. There is also no graceful shutdown or closing of transports.
- **`unsafeDisableAuth` / `authToken` precedence**: with `--unsafe-disable-auth`, a supplied `--auth-token` is silently ignored.
- **Startup request**: on startup the server calls the Notion API (`/users/me`) with a hard-coded `Notion-Version: 2022-06-28`. This is a hidden outbound call with no timeout, and the version differs from the one used elsewhere.

## Build and supply chain

- **Dockerfile**:
  - `npm ci --omit-dev` runs before `npm run build`, so build tools such as `tsc` or the bundler may be missing. I did not check `package.json`.
  - The runtime image runs as root, with no `USER node`.
  - It has no `HEALTHCHECK`, even though `/health` exists.
  - It copies `notion-openapi.json` to `/usr/local/scripts/`, and the `../scripts/` path relative to the bundle must line up with that. I'd verify it.
  - The base image tag isn't pinned by digest.
- Use of `--ignore-scripts` is good.
- I did not review the GitHub workflows (`publish.yml`, `increment-version.yml`). Check them for pinned actions, token scoping and provenance.

## Suggested priority

1. Restrict the file-upload paths (#1).
2. Bind sessions to the identity that created them, and add session limits (#2, #6).
3. Use constant-time token comparison and write the token file safely (#4, #5).
4. Stop decoding JSON strings blindly (the lossy-decoding item above).
5. Set `isError` on tool failures, and fix the annotations and tool-name truncation.
6. Harden the Dockerfile by running as a non-root user, and review the CI workflows.

I can go deeper on any of these, for example by reading the tests or workflows, or by drafting patches for #1 and #4.
