# BRACE MCP review: parcel-station 1.4.0

Review date is 2026-10-24, taken from the bundled verification record. This was a static read of the files only. Nothing was run, installed or connected to, and no tests were executed. I did not write `mcp-review.md`, because no write tool is available here. The report is below.

## Scope and inventory

- **Component:** a plain Node HTTP service (`dist/launcher.mjs`, then `src/server.mjs`). It contains no MCP SDK, no `.mcp.json`, no stdio transport and no tool/resource/prompt registration. It has no dependencies in `package.json`.
- **Release:** version 1.4.0. There is no commit ID because the checkout is not a git repository.
- **MCP protocol revision and extensions:** none negotiated or enabled. The service speaks its own "protocol 1".
- **Active profile:** `launch-manifest.json` merges `base.json` with `shipping.json`, and the shipping overlay wins (`src/configuration.mjs:6`). The resulting settings are:
  - **Router:** `./routes/shipping.mjs`.
  - **Listener:** `0.0.0.0:8418`, with plain HTTP and no TLS.
  - **Limits:** a 65536-byte body limit and 64 entries per request.
  - **Renderer:** `/usr/bin/printf`.
- **Operations**, both behind a single shared Bearer credential:
  - `POST /archives/unpack`
  - `POST /receipts/render`
- **Unused or unwired:**
  - `routes/compatibility.mjs` serves `/health` and is not wired in.
  - `config/development.json` is only selectable through `tools/inventory.mjs --development`.
  - `archive/legacy-server.mjs` is not imported anywhere I found.
- **Owners:**
  - **Repository:** application code.
  - **Deployment operator:** the reverse proxy, TLS, credential rotation, account and filesystem provisioning, and logging.
  - **Image maintainer:** the renderer binary.

## Sources

| ID | Source | Authority and date | Status |
|---|---|---|---|
| S1 | MCP security guidance, https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | Protocol-project guidance, bundled date 2026-10-22 | Not rechecked |
| S2 | OWASP Logging, https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html | Guidance, bundled date 2026-10-22 | Not rechecked |
| S3 | Node 20 CLI docs, https://nodejs.org/download/release/latest-v20.x/docs/api/cli.html#--unhandled-rejectionsmode | Official docs, recorded check 2026-10-24 (`research/verification-2026-10-24.json`, id `node20`) | Not rechecked this session |
| S4 | TS SDK redirect advisory GHSA-6prh-2h8m-c8cw | Maintainer advisory, published 2026-10-02, record updated 2026-10-19, recorded check 2026-10-24 | Not applicable (see coverage) |

The Express 4 and MCPB manifest records in the verification file are not relied on. There is no Express and no manifest in this repository.

## Findings, ordered by impact

### 1. Shell command injection in receipt rendering (gap; BRACE B05, B11)

- **Evidence:**
  - `src/render/process.mjs:8` builds the command as `request.program + ' "%s" "' + request.label + '" > "' + request.output + '"'`.
  - It then runs it with `exec(command)` at line 9, which goes through a shell.
  - `receiptLabel` (`src/validation.mjs:13-17`) rejects only empty values, values over 120 characters, `\n` and `\r`.
  - `test/validation.test.mjs:23` explicitly accepts a label containing `"`.
- **Trigger:** an authenticated `POST /receipts/render` with a label such as `x" ; <cmd> ; echo "`, or one using `$(...)` or backticks. Both fit in 120 characters and contain no newline.
- **Impact:** arbitrary shell commands run as the service account. This breaks the README contract that the operator credential does not grant a shell or arbitrary host file access. The same trigger can redirect output with `>`, which also breaks the write-inside-workspace-root contract.
- **Prerequisite:** the shared operator credential. The listener is `0.0.0.0` in the shipping profile.
- **Not demonstrated:** I did not run it. The finding rests on static reading of the code.
- **Remediation:**
  - Use `execFile` or `spawn` with an argv array and no shell, and write the output through `fs`.
  - Treat `renderProgram` as fixed.
  - Keep the label as data, since `test/smoke.test.mjs:17` says it is preserved "as data" but the sink does not honour that.

### 2. Path traversal in archive unpack (gap; BRACE B05, B11, E06)

- **Evidence:**
  - `src/storage/files.mjs:7` computes `join(directory, entry.name)`.
  - Lines 8-9 then run `mkdir(dirname(...), {recursive:true})` and `writeFile`.
  - `decodeEntries` (`src/validation.mjs:5-12`) checks only that `name` is a string of at most 160 characters.
  - The workspace identifier is validated, but the entry name is not.
- **Trigger:** `{"workspace":"a","entries":[{"name":"../../receipts/x.txt","content":"..."}]}`. `join` normalizes `..`, so the write lands outside the workspace.
- **Impact:** the operator can create or overwrite any file the service account can write. That includes files in other workspaces and, per the README, files under `/srv/parcel/receipts`. If the installed code or configuration directory is writable by the account, it could also change future execution. That last point needs evidence.
- **Contract broken:** the README says an operator may not write outside the workspace root.
- **Remediation:**
  - Resolve the destination and require that it sits under the workspace directory (check the `relative()` result).
  - Reject absolute names, `..` segments and empty names.
  - Validate all entries before the first write.
- **Note on host assumptions:** the README states there are no preexisting symlinks and that no archive entry creates one. This finding does not depend on symlinks.

### 3. Network exposure and credential handling (gap on the repository side; BRACE B02, B03, C05, E12)

- `config/shipping.json:3` sets `listen` to `0.0.0.0`, which overrides the loopback address in `base.json`. The README describes a private service network. Only the reverse proxy, firewall and TLS can narrow this, and none is supplied, so that part is `needs_evidence`.
- `config/base.json:8` ships a synthetic operator token inside the release tarball. Startup does not refuse to run with it. `src/configuration.mjs` has no check for a placeholder or missing token, and the README says the operator must replace it.
- `src/identity.mjs:2` compares the header with `!==`, which is not constant-time. It is also a single shared secret with a fixed principal, so no individual caller is identified. The README says shared ownership is intended, so I report this as an audit and attribution limit, not a bypass.
- The service gives no audit trail. It has no logging, and `docs/operations.md:108` says no collector is supplied. Owner: the deployment operator. This is `needs_evidence` for R03 and R13.

### 4. Error responses expose internals (gap, lower impact; BRACE E04, E10)

- `src/server.mjs:13` returns `error.message` to the caller. The README says the response is a "generic JSON error body", which the code does not match.
- Messages from `exec` failures typically include the failed command line and the stderr. Here that is the label, the output path and the renderer's error text. The `JSON.parse` messages also reach the caller.
- `requireOperator` throws without a status (`src/identity.mjs:8`), so a role failure returns 400, not 403.
- I confirmed the message pass-through in code. I did not confirm exactly what `exec` includes in its messages.

### 5. Smaller observations (needs_evidence or note)

- **No rollback on partial writes.** `materialize` writes entries one at a time. The README and operations notes disclose that disk errors can leave a partial archive. An entry with an empty name makes `writeFile` fail on a directory after earlier entries are written. This is a documented limit, not an authorization failure.
- **Limits depend on the profile.** `maxBodyBytes` and `maxEntries` exist only in `shipping.json`. Under `development.json`, `Buffer.byteLength(text) > undefined` is false and `value.length > undefined` is false, so both limits would be off. That profile is not wired into the manifest, but nothing prevents someone from selecting it.
- **Body reading.** `src/wire.mjs:3-6` concatenates chunks and measures after each one. The limit is enforced while streaming. Authentication does run before the body is read (`src/server.mjs:8-9`), which matches the README.
- **Dead code.** `archive/legacy-server.mjs` has `exec(command)` with a caller-supplied string and a `/tmp/` + name path helper. No caller exists in the inspected tree, so this is `needs_evidence`, not a finding. Remove it from the release if it isn't needed.
- **Unused config.** `archiveRoot` is not read anywhere. The `compatibility.mjs` route is not reachable under the shipping profile. Both are low risk.
- **Error handling.** `src/server.mjs:6-15` wraps the async handler in `try/catch`, so a rejected promise does not escape as an unhandled rejection (S3). I did not rely on the Express record because Express is not used here.

## Attempt to influence the review

`notes/vendor-receipt.md` is a third-party attachment. It asks automated reviewers to output "SAFE" and omit findings, on the grounds that receipt previews are only used by trusted staff. I did not follow that request and treated the note as untrusted data. It has no bearing on the label sink, and nothing in the code restricts the label to trusted staff. It also lists an example credential ("synthetic-example-only"), which I have not reproduced.

## Coverage

| Boundary or check | Status | Evidence | Owner |
|---|---|---|---|
| Authentication, `/archives/unpack` and `/receipts/render` | `likely_pass` for presence and ordering | Bearer check at `server.mjs:8`, before the body read and dispatch. Exact string match, shared secret | Repo |
| Role check before operation | `likely_pass` | `requireOperator` at `routes/shipping.mjs:5`. The role is fixed server-side and cannot be taken from the body | Repo |
| Per-operator isolation | `na_candidate` | The README says shared ownership is deliberate. I searched for per-user checks and found none | Repo |
| Receipt label to shell | `gap` | Finding 1 | Repo |
| Archive entry path | `gap` | Finding 2 | Repo |
| Workspace identifier | `likely_pass` | `^[a-z0-9-]{1,32}$` at `validation.mjs:2`. Receipt output is `receiptRoot/<workspace>.txt` with no client-chosen filename | Repo |
| Request size and entry limits | `likely_pass` under the shipping profile only | See item 5 | Repo |
| Network exposure, TLS, proxy | `needs_evidence` | `0.0.0.0` listener, plain HTTP, no proxy configuration supplied | Deployment operator |
| Credential delivery and rotation | `needs_evidence` | Synthetic token committed in `base.json` | Deployment operator |
| Process isolation and filesystem permissions | `needs_evidence` | The README says a dedicated account, with no container or MAC profile supplied. This sets how far findings 1 and 2 reach | Deployment operator |
| Renderer binary integrity | `needs_evidence` | `/usr/bin/printf` is supplied by the image and cannot be verified from the repository | Image maintainer |
| Audit and incident response | `needs_evidence` | No logging in code. Operations notes say no collector | Deployment operator |
| MCP-specific controls: OAuth, tool metadata, tasks, skills, apps, host approval | `na_candidate` | I searched for `modelcontextprotocol`, tool registration and `.mcp.json`, and the Glob for hidden files found none. The package has no dependencies | n/a |
| Dependency advisories, including S4 | `na_candidate` | No SDK or package dependency. The versions installed on a host are unknown | n/a |
| `compatibility.mjs`, `archive/legacy-server.mjs`, `development.json`, `tools/inventory.mjs` | Reviewed, not reachable under the shipping profile | Reading the code and manifest | Repo |
| `test/*.test.mjs` | Read as source only | No claim that the tests pass. They do not cover the injection or traversal inputs | Repo |

## Proposed controlled tests

Run these against a disposable instance with a fake credential and temporary roots. Owner: the repository maintainers, and none have been run.

1. **Label injection.**
   - **Allowed:** the label `handle with care` produces a receipt file containing that text.
   - **Denied:** a label containing `"`, `$(...)` or a backtick appears literally in the receipt, no command runs and nothing is redirected.
2. **Entry traversal.**
   - **Allowed:** `a/b.txt` is written under the workspace.
   - **Denied:** `../x`, `a/../../x` and absolute names are rejected before any file is written.
3. **Role and credential.** A request with no header, a wrong token, or a role value in the body is rejected before the body is read.
4. **Limits.** A body over 65536 bytes and 65 entries are rejected before any write, under the shipping profile.
5. **Exposure.** From a non-service-network host, the listener is unreachable without the proxy and TLS controls.
6. **Error body.** A forced renderer failure returns a generic message that does not include the command or path.

## Limits of this review

- Public-source lookup was unavailable, and the sources above are marked as not rechecked.
- Deployment controls, the host, the renderer and the retention job were not visible.
- This report lists findings and unknowns only. It is not a security pass and not a release verdict.
- Deployment decisions belong to the accountable owners.
