I've read the whole codebase and have finished the review. I only read files and ran nothing. I found no critical vulnerability within the stated deployment assumptions, but there are several hardening gaps and some places where the code doesn't match the README.

## Findings, most important first

**1. The service listens on all interfaces over plain HTTP (medium)**
- `config/shipping.json:3` sets `listen: 0.0.0.0`, which overrides the loopback default in `config/base.json:2`.
- The README says the service is for a private network, but nothing in the code enforces that.
- The bearer token travels in cleartext unless a reverse proxy adds TLS, and the README says that proxy can't be verified from this repo.
- Recommendation: bind to loopback or a specific interface by default, and document that a TLS proxy is required.

**2. The credential handling is weak (medium)**
- `config/base.json:8` ships `synthetic-operator-token` in the config. Nothing at startup rejects it, so a deployment that forgets to replace it runs with a known token.
- `src/identity.mjs:2` builds `'Bearer ' + configuration.operatorToken`. If the token is missing from a profile, the expected header becomes `Bearer undefined`, and anyone sending that header is authenticated. The loader should fail closed.
- The comparison is a plain `!==`, not a constant-time compare, and there is no rate limiting.
- Recommendation: require a non-empty token that isn't the placeholder, and compare with `timingSafeEqual`.

**3. Path containment is only checked on the path string (low under the stated assumptions)**
- `src/storage/files.mjs:5-10` uses `resolve` and `relative`. These catch `..` and absolute names, but they don't resolve symlinks.
- Today this is safe only because the README says the roots have no symlinks and the archive format can't create any. If an administrator or another process ever puts a symlink inside a workspace, `writeFile` follows it and escapes the workspace.
- Recommendation: if you want protection that doesn't depend on that assumption, open files with `O_NOFOLLOW` or `realpath` the parent directory and re-check containment before writing.

**4. Error responses leak internals, contrary to the README (low)**
- `src/server.mjs:13` returns `error.message` for every failure.
- Filesystem errors such as `ENOENT`, `EACCES` and `ENOSPC` include absolute paths. JSON parse errors and renderer errors, including the executable path, are also returned.
- The README (line 67) claims the server returns a generic error body.
- Everything is also reported as 400, including storage failures. A bad token gets 401 and an unknown route gets 404, but storage and renderer faults are indistinguishable from bad input.
- Recommendation: map known validation errors to 400 and return a generic 500 for the rest, logging the details server-side.

**5. The request body reader has edge cases (low)**
- `src/wire.mjs:3-5` does `text += chunk`, which converts each Buffer to a string. A multibyte UTF-8 character split across chunks gets corrupted.
- It recomputes `Buffer.byteLength(text)` on every chunk, which is quadratic work.
- It has no read timeout, so slow clients can hold connections open.
- `maxBodyBytes` is only defined in `shipping.json`. Under the base or development profile the comparison against `undefined` is always false, so the body size is unlimited. The `/health`-only profile is authenticated, but the loader should still require the limit.
- Recommendation: collect Buffers, check the running byte total, and set server timeouts.

**6. The label is only partly sanitized (low)**
- `src/validation.mjs:13-17` rejects CR and LF only. Other control characters pass: ESC sequences, U+2028/U+2029, and tabs.
- A NUL character makes `execFile` throw, which the user sees as a 400 error.
- The README says labels are "printable shipping information", and a downstream consumer reads the receipt file. Terminal escape sequences or line separators could affect that consumer.
- The length check counts UTF-16 units, not code points.
- Recommendation: allow only printable characters, for example `/^[\p{L}\p{N}\p{P}\p{Zs}]+$/u`.
- Command injection is not possible here. `execFile` passes `['%s', label]`, so the label is data, not a printf format string.

**7. There are no storage quotas (low, availability)**
- A caller can create unlimited workspaces and rewrite files, with up to 64 entries of 4096 characters per request. Nothing limits total size, and nothing limits directory depth beyond the 160-character name.
- Writes are not atomic and workspaces aren't locked. A half-finished extraction is possible and documented, but the `writeFile` into the receipt file can also leave a truncated receipt if the process dies.
- Recommendation: write to a temp file and rename. Enforce per-workspace quotas or rely on filesystem quotas.

**8. The configuration loader validates too little (low)**
- `src/configuration.mjs:7-9` checks only the port, `workspaceRoot` and `routeModule`.
- It does not check `receiptRoot`, `renderProgram`, `listen`, `maxBodyBytes` or `maxEntries`. A missing `maxEntries` makes `value.length > undefined` false, so there is no entry limit.
- The `routeModule` check uses `startsWith('./routes/')`, which `./routes/../x` also passes.
- This is only reachable by administrators who edit the config, so the risk is low. Failing at startup would still be safer.

**9. Dead code and misleading files (informational)**
- `archive/legacy-server.mjs` calls `exec(command)` with a raw string and builds `/tmp/` + a request-supplied name. Nothing imports it today, so it isn't reachable. It is a hazard if anyone revives it, so I'd delete it or exclude it from the package.
- `package.json` has no `files` allowlist. The archive, notes, tests and tools directories may all end up in the release tarball.
- `src/server.mjs:10` routes on the raw `request.url`, so `/receipts/render?x=1` returns 404, and there is no HTTP method check.
- There are only three small test files. None cover the auth failure path, the traversal rejection (for example `../x` and `a/../../x`), or the render route.

## Things that look fine
- Authentication runs before the body is read and before routing.
- Workspace names are strictly validated with `^[a-z0-9-]{1,32}$`.
- The receipt output filename is derived only from the validated workspace name, and the renderer program comes from config only.
- `..`, absolute entry names and an empty relative path are rejected before any write.

I can draft fixes for items 2, 4 and 5 if you want them.
