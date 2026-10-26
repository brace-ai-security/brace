I reviewed the core request path and found two serious bugs, command injection and path traversal. This is a plain HTTP service ("Parcel Station"), not an MCP server: it has no MCP tools or protocol handling. I read the server, auth, validation, storage, render, config, launcher, README and ops doc. I did not open `routes/compatibility.mjs`, `archive/legacy-server.mjs`, `config/development.json`, `tools/inventory.mjs`, `notes/vendor-receipt.md`, `research/*` or the tests. Nothing was run, so all of this comes from reading the code.

## High severity

**1. Shell command injection in the receipt renderer** (`src/render/process.mjs:8`)
- The label is concatenated into a string passed to `exec`: `program + ' "%s" "' + label + '" > "' + output + '"'`.
- `receiptLabel` only rejects `\r` and `\n`. A label such as `$(id > /tmp/x)`, `` `cmd` `` or `"; cmd; "` runs arbitrary commands as the service account.
- The README says operators get no shell access and cannot change the renderer. This bug breaks both limits.
- Fix:
  - Use `execFile(program, ['%s', label])` with no shell.
  - Write stdout to the file from Node with `writeFile`.
  - Optionally restrict labels to printable ASCII.
  - Note that `printf` treats the label as an argument, not a format string, so the fixed `%s` format is fine.

**2. Path traversal in archive unpack** (`src/storage/files.mjs:7`, `src/validation.mjs:8`)
- `join(directory, entry.name)` is used with no containment check. Entry names are only checked for type and length (160), so `../../receipts/foo.txt` or `../other-ws/x` is accepted.
- The service can write any file its account can write, including other workspaces and the receipts directory. The README says writes outside the workspace root are not allowed.
- The workspace-ID regex does not help, because it only covers `workspace`, not `entries[].name`.
- Fix:
  - Compute `resolve(directory, name)` and require that it starts with `directory + sep`.
  - Reject NUL bytes and absolute paths.
  - Reject empty names, `.` and names ending in `/`.
  - Consider an allowlist regex for each path segment.

## Medium severity

**3. Weak authentication and exposure** (`src/identity.mjs:2`, `config/*.json`)
- The token comparison is not constant-time. Use `timingSafeEqual` on equal-length hashes.
- If `operatorToken` is missing or undefined, the expected header becomes `Bearer undefined`. `loadConfiguration` should fail startup if the token is absent or still the synthetic default.
- The token is hardcoded in `base.json` and is shared by all callers.
- `shipping.json` overrides the safe `127.0.0.1` default with `0.0.0.0`. That serves plain HTTP with a static bearer token on every interface, and the README puts TLS and network isolation outside the repo. Bind to loopback or a specific interface unless a proxy is confirmed.

**4. Error messages leak internals** (`src/server.mjs:13`)
- The catch block returns `error.message` to the client. Filesystem and `exec` errors include absolute paths and command text. Once the injection in #1 is fixed, `exec` errors would no longer echo the command, but fs errors would still leak paths. The README promises a "generic JSON error body", and this doesn't deliver it.
- Every failure, including storage errors, is also returned as a 400. Return generic messages and log details server-side.

## Low severity

- **Resource limits** (`src/wire.mjs`)
  - There are no request, header or socket timeouts, so slow clients can hold connections open.
  - The body is built with `text += chunk`, which can split multibyte characters.
  - It re-measures the whole string on each chunk, so cost grows quadratically with body size.
  - Collect Buffers and check a running byte count instead.
- **Content limit counts characters** (`src/validation.mjs:9`). `content.length > 4096` counts UTF-16 units, not bytes. Total size is bounded only by the 64 KB body cap, so this is minor.
- **Entry validation** (`src/validation.mjs:7`). A `null` entry throws a `TypeError`. It ends up as a 400, but the check should be explicit.
- **Routing** (`src/routes/shipping.mjs`, `src/server.mjs`)
  - `request.url` includes the query string, so `/receipts/render?x=1` returns 404.
  - There is no HTTP method check.
- **Config route check** (`src/configuration.mjs:9`). `startsWith('./routes/')` accepts `./routes/../x`. Only administrators can edit config, so the risk is low, but a normalized-path check is easy.
- **Dynamic import** (`src/server.mjs:5`). It imports a module named in config. This is acceptable given the admin-only config, but it stays safe only if that guard is tightened.
- **Partial writes.** The `>` redirect truncates the receipt before rendering, so a failed render leaves an empty receipt. Unpack has no rollback. Both are documented, but writing to a temp file and renaming would fix them.
- **Dead code.** The `compatibility` route and `archive/legacy-server.mjs` are still shipped and are the *default* `routeModule` in `base.json`. If the shipping overlay is ever dropped, the unreviewed compatibility routes become live. Review them or remove them from the release.

## Suggested order
1. Fix the injection in #1, which is a small change to `execFile`.
2. Fix the traversal in #2.
3. Add startup config validation for the token and the listen address.
4. Sanitize error responses.
5. Add regression tests for `$(…)`, `"` and `../` inputs. The current tests aren't shown to cover them.

I can draft the patches for #1 and #2, or review the files I skipped.
