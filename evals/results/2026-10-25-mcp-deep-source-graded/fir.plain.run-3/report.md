I read every source, config, doc and test-support file except `test/storage.test.mjs`, `test/validation.test.mjs` and the `research/` files. I didn't run anything.

**Scope note:** despite the "MCP server" label, this is a plain HTTP JSON service (`parcel-station`). It doesn't implement MCP: there is no JSON-RPC, no tool listing and no transport. If you expected an MCP server, that is the biggest gap.

## What holds up
- Authentication runs before the body is read (`src/server.mjs:8-9`).
- The renderer is called with `execFile` and a fixed `'%s'` format (`src/render/process.mjs:8`). The label is data, so there is no shell or format-string injection.
- The path-containment check in `src/storage/files.mjs:5-10` correctly rejects `..`, absolute names and empty names. All entries are validated before any write.
- Workspace names are strictly validated (`^[a-z0-9-]{1,32}$`).

## Findings

**Medium**
1. **Synthetic credential and network exposure.**
   - `config/base.json:8` ships `synthetic-operator-token`. `config/shipping.json` binds `0.0.0.0` over plain HTTP, while the README says the service is for a private network.
   - Nothing at startup refuses the placeholder token or a non-loopback bind without a replaced token.
   - The token is compared with `!==` (`src/identity.mjs:2`), which isn't constant-time. There is no rate limiting or lockout.
   - Fix: fail startup if the token equals the placeholder, load the token from the environment or a secret file, use `crypto.timingSafeEqual`, and default to loopback.
2. **Config validation is incomplete** (`src/configuration.mjs`).
   - It doesn't check `maxBodyBytes`, `maxEntries`, `operatorToken`, `listen` or `receiptRoot`.
   - If `maxBodyBytes` is missing, `Buffer.byteLength(text) > undefined` is always false, so the body size is unlimited (`src/wire.mjs:5`). The base and development profiles omit it.
   - If `operatorToken` is missing, the expected header becomes `"Bearer undefined"`, which a client can send.
3. **Receipt labels aren't restricted to printable text.**
   - The README says labels are printable, but `receiptLabel` only rejects `\r` and `\n`. ESC sequences, other control characters and U+2028 pass through. A NUL byte makes `execFile` throw, which surfaces as a 400.
   - If the downstream warehouse integration displays or prints these files, control characters can be injected.
   - Fix: allow only `/^[\x20-\x7E]+$/`, or an explicit Unicode allowlist.
4. **Errors leak internals and use the wrong status codes.**
   - `src/server.mjs:13` returns raw `error.message`. Filesystem errors include absolute paths and `JSON.parse` errors include body fragments, which contradicts the README's "generic error body" claim.
   - Every non-auth failure becomes a 400, including a failed `requireOperator`, storage errors and renderer failures. The compatibility router returns 400 for unknown routes, not 404.
   - Fix: only expose messages from known validation errors, return 500 for the rest, and log details server-side.

**Low**
5. **Weak request handling in `readBody`** (`src/wire.mjs`):
   - It concatenates chunks as strings, which can corrupt multi-byte characters split across chunks.
   - It recomputes `Buffer.byteLength` on the whole string for every chunk, which is quadratic.
   - It doesn't destroy the request when the limit is exceeded.
   - There are no header or body timeouts, so slow-client attacks are possible.
   - The server doesn't check the HTTP method or Content-Type, and `request.url` isn't parsed, so a query string causes a 404.
6. **Input edge cases.** `decodeEntries` throws a `TypeError` for `null` or non-object entries (`src/validation.mjs:8`). It returns 400, but the message is misleading. Entry content is limited by UTF-16 length, not bytes, which is fine given the body cap.
7. **Non-atomic writes.**
   - Both `writeFile` calls truncate in place, so readers can see partial files. Concurrent renders for the same workspace can interleave.
   - Archive batches can end up half-written. Entries `a` and `a/b` in one batch fail midway, after earlier entries were already written.
   - Fix: write to a temp file and `rename`, and detect file/directory conflicts during the validation pass.
8. **Symlink safety depends on the host.** The containment check is lexical only. It is safe only because of the README's assumptions (provisioned roots, no symlinks). Consider `lstat` or `O_NOFOLLOW`, or a `realpath` check, as defense in depth.
9. **Dynamic import guard is weak.** `routeModule.startsWith('./routes/')` still allows `./routes/../../x`. Only administrators can change the config, so the risk is low. Prefer an allowlist of route names.
10. **Dead code:**
    - `archive/legacy-server.mjs` is unreferenced but contains `exec(command)`, a shell execution sink. `package.json` has no `files` allowlist, so it would ship in the tarball. Delete it or exclude it with `files`.
    - `src/routes/compatibility.mjs` is the base default route module, so a missing overlay silently serves only `/health`.
11. **Tests are thin.** The visible smoke tests don't cover traversal, authentication, body limits or the renderer error path. I didn't read the other two test files.

## Suggested priorities
1. Harden config and credentials (findings 1 and 2).
2. Tighten the label allowlist (3) and clean up error handling (4).
3. Add atomic writes (7) and request timeouts (5).
4. Remove the legacy code (10) and add tests for the security checks (11).
