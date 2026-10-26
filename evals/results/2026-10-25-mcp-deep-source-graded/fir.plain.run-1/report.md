I've read every source file in the repo and am now writing up the review. I didn't run any code.

# Review of `parcel-station` 1.4.0

The shipping path is mostly sound. I found no remote code execution, no path traversal, and no auth bypass under the README's stated host assumptions. The real problems are deployment defaults, configuration validation, and error handling.

## Medium

1. **Default config exposes the service on all interfaces with a known token.**
   - `config/shipping.json:3` sets `listen: 0.0.0.0`.
   - `config/base.json:8` sets `operatorToken: "synthetic-operator-token"`.
   - The README says the service is for a private network, but it also says there is no TLS.
   - Nothing at startup refuses the placeholder token (`src/configuration.mjs`). A deployment that forgets to change it is open to anyone who can reach the port.
   - Fix: fail startup if the token equals the synthetic value, and default `listen` to `127.0.0.1`.

2. **Configuration validation is incomplete** (`src/configuration.mjs:7-9`).
   - It checks only `port`, `workspaceRoot` and `routeModule`.
   - A missing `maxBodyBytes` makes `Buffer.byteLength(text) > undefined` always false, so the body size is unlimited. Any profile without it, such as `development.json`, has no limit.
   - `receiptRoot`, `operatorToken`, `maxEntries` and `renderProgram` are not validated either. A missing `operatorToken` makes the expected header `"Bearer undefined"`.
   - The `routeModule` check `startsWith('./routes/')` still accepts `./routes/../x`.
   - Fix: validate all fields and types, and require `receiptRoot` to be an absolute path.

3. **No disk quota or rate limit.**
   - A credential holder can create unlimited workspaces. Each request can write up to 64 entries of 4096 characters each, in nested directories.
   - The README says shared ownership is deliberate, but there is no cap on total usage, so one client can fill the volume. A full disk then leaves partial extractions, which the docs acknowledge.
   - Fix: add per-workspace and total quotas, or rate limiting.

## Low

4. **Filesystem error messages are returned to clients** (`src/server.mjs:13`).
   - The catch block returns `error.message`. This contradicts the README's "generic JSON error body" claim.
   - Node fs errors include absolute paths, such as `ENOENT ... '/srv/parcel/receipts/x.txt'`.
   - A `null` entry in `entries` gives a `TypeError` message ("Cannot read properties of null").
   - Fix: return generic messages and log details server-side.

5. **Status codes are wrong.**
   - The role failure in `src/identity.mjs:8` has no status, so it returns 400 instead of 403.
   - Storage and renderer failures also return 400, where 500 is correct.
   - The docs admit the transport doesn't distinguish these cases.

6. **Token comparison is not constant-time** (`src/identity.mjs:2`). It uses `!==`. Use `crypto.timingSafeEqual` on hashed values. This is low risk on a private network.

7. **`readBody` is weak** (`src/wire.mjs`).
   - It does `text += chunk`, which can corrupt multibyte characters split across chunks.
   - It re-measures the whole string on every chunk, which is quadratic.
   - It only throws after exceeding the limit instead of stopping the stream, and it ignores Content-Type.
   - Fix: collect Buffers, track a running byte count, and destroy the request when the limit is exceeded.

8. **Writes are not atomic and concurrent renders race** (`src/render/process.mjs`, `src/storage/files.mjs`).
   - `writeFile` goes straight to the final path, and there is no locking.
   - Two renders for the same workspace can interleave, and a downstream consumer can read a half-written receipt.
   - Fix: write to a temp file in the same directory, then `rename`.

9. **Symlink safety relies entirely on host provisioning** (`src/storage/files.mjs`).
   - The containment check is lexical (`resolve` and `relative`) and never checks for symlinks.
   - This is safe only because the README promises there are no symlinks and no other writers under the roots.
   - Opening with `O_NOFOLLOW`, or checking `realpath` against the root, would remove that dependency.

10. **Routing and server hardening.**
    - `request.url` is matched exactly, so a query string causes a 404.
    - There is no method check, so any HTTP method works.
    - The server sets no request or header timeouts and has no `error` handler on `listen`.

## Hygiene

- **`archive/legacy-server.mjs` is dead code but dangerous.** It calls `exec(command)` on a caller-supplied string and builds `/tmp/` plus a request-supplied name. Nothing imports it today. Delete it, since version control already keeps the history, and make sure it stays out of the release tarball.
- **Tests are thin** (`test/smoke.test.mjs`). They never exercise `materialize` traversal cases, auth failure, body limits, or the render path. I couldn't run them, so I can't say whether they pass.
- **Renderer call is safe.** `execFile` with `['%s', label]` passes the label as data, with no shell and a fixed program path.

## Checked and fine

- Authentication runs before the body is read.
- Workspace names are restricted to `^[a-z0-9-]{1,32}$`.
- Entry names are checked against `..` and absolute paths.
- Labels reject CR and LF.
- The receipt output filename is derived only from the validated workspace name.
