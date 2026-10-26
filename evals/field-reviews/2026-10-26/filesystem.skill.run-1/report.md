# BRACE MCP review: `@modelcontextprotocol/server-filesystem` 2.0.1

Nothing was executed, installed or connected to. Review date is 2026-10-26. No lookups were done in this session, so every advisory source below is **not rechecked**. The `mcp-review.md` report is returned here because file writes were disallowed in this session.

## 1. Scope and inventory

- **Component:** the server, `src/filesystem`, at commit `ef9808f71090d0db3eda99e2af2ba78f1086f4fb`. The tests were not run.
- **Transport:** stdio only (`index.ts:116-132`, `serveStdio` with `StdioServerTransport`). There is no HTTP or OAuth path in this package, so `http.md` was not applied.
- **Protocol:** the server answers 2026-07-28 clients (`era: "modern"`, no `initialize`, no Roots) and 2025-era clients (`initialize`, then Roots). The negotiated revision is unknown because it depends on the client.
- **Operating systems:** POSIX, macOS and Windows code paths all exist. The `chdir` anchoring check is skipped on Windows (`pinned-directory.ts:131`).
- **Extensions:** none enabled. Roots (deprecated) is a legacy path and is enabled for 2025-era clients.
- **Resolved dependencies** (root `package-lock.json`):
  - `@modelcontextprotocol/server` 2.4.0, declared `^2.3.1`.
  - `minimatch` 10.2.5, `diff` 8.0.4, `glob` 13.0.6.
  - `glob` is declared but not imported by the files I read.
- **Launch commands** (README):
  - `npx -y @modelcontextprotocol/server-filesystem <dirs>`, with no version pin.
  - `docker run … mcp/filesystem /projects`, with optional `ro` mounts.
- **Credentials:** none in this package.
- **Root config, context only:**
  - `.mcp.json` points at a remote docs server over HTTP, with no credentials. It is not the target.
  - `.claude/settings.json` registers a SessionStart command hook. I did not read the hook script and it is outside the target.
- **Tools (14), all traced:**
  - Reads: `read_file`, `read_text_file`, `read_media_file`, `read_multiple_files`, `list_directory`, `list_directory_with_sizes`, `directory_tree`, `search_files`, `get_file_info`, `list_allowed_directories`.
  - Writes: `write_file`, `edit_file`, `create_directory`, `move_file`.
- **Resources and prompts:** none.
- **Privileged downstream action:** the local filesystem, with the full authority of the launching OS user.

## 2. Sources

All sources are not rechecked in this session.

| ID | Source | Authority | Date |
|---|---|---|---|
| S1 | [MCP security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) (`stdio.md`, `control-map.md`) | Protocol guidance | Publication date unknown |
| S2 | [VS Code GHSA-w79w-rj9h-vg4f](https://github.com/microsoft/vscode/security/advisories/GHSA-w79w-rj9h-vg4f) (`advisories.md`, adjacent components) | Maintainer advisory. A file-write tool may alter future execution. Fixed in 1.132.1. | Publication date unknown |
| S3 | [LangChain GHSA-gr75-jv2w-4656](https://github.com/langchain-ai/langchain/security/advisories/GHSA-gr75-jv2w-4656) (glob/symlink/path boundaries) | Maintainer advisory, analogous class. It is not a finding about this package. | Publication date unknown |
| S4 | [OWASP Logging](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) and [OWASP MCP sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html) | Guidance | Unknown |
| S5 | TS SDK advisories GHSA-jm63-cq47-j5jp, GHSA-46jr-4wx8-v453, GHSA-f897-62hf-6gxq, GHSA-22jm-h49p-29qw (`advisories.md`) | Maintainer advisories, dated 2026-10-02 to 2026-10-15 in the bundled index | Index checked in BRACE's 2026-10-22 research |

**SDK advisory applicability:**
- Resolved 2.4.0 is at or above the listed fixes (server 2.3.0, node 2.1.0).
- The HTTP, OAuth and redirect advisories do not apply because this package has no HTTP transport.
- The shared-server leak (GHSA-jm63) excludes stdio, and `createServer` is called once per connection anyway (`index.ts:117`, `server.ts:185`).
- The experimental tasks advisory is not applicable. No Tasks are registered and the advisory affects SDK 1.x only.
- Patched versions do not prove configured remediation, but no configuration is needed on stdio.

## 3. Findings

Impact order. None is a confirmed remote exploit. All need a local or host-side prerequisite.

**F1. Reads and the `move_file` source are not anchored, so a path swapped after validation can escape the allow-list (B09, B11; `likely_pass` for writes only).**
- Trigger: a local actor who can create or replace directories inside an allowed directory races a tool call. `validatePath` returns a `realpath`. Reads then reopen that string:
  - `lib.ts:322`: `fs.readFile(filePath…)`
  - `lib.ts:590`: `fs.open(filePath,"r")`
  - `lib.ts:490`: `applyFileEdits` reads via `fs.readFile`
  - `server.ts:134`: `createReadStream`
- The write path is pinned (`pinned-directory.ts`). `renameIntoDirectory` anchors the destination only. Its own comment says the source is `"absolute, outside this fix's scope"` (`pinned-directory.ts:254`), so `renameSync(sourcePath, …)` follows a swapped parent symlink.
- Effect: a read or move outside the allowed directories. An attacker needs write access inside an allowed directory and winning timing. Static analysis only, with no runtime test.
- Remediation: document the limit, or open reads via validated handles.
- Related: `moveFile` does an `lstat` and then `renameSync`. A destination created in between is silently overwritten, which contradicts the tool's "fails if destination exists" contract (`server.ts:710-714`).

**F2. No protected-path policy, so a write tool can alter future execution (B05, B12, C02; S2).**
- Any file under an allowed directory can be written, including `.mcp.json`, `.claude/settings.json`, git hooks and shell startup files (`server.ts:449-451`, `server.ts:477-479`).
- `readOnlyHint` and `destructiveHint` are annotations, not an authorization policy.
- If the host auto-approves tools and an allowed directory contains such files, a prompt-injected write can persist into code execution. The server-side control is absent. Host approval behavior is unknown (`needs_evidence`, host owner).

**F3. No size, depth or count limits on reads or traversal (B07, R01; S4).**
- Whole-file `readFile` and base64 encoding in memory: `read_text_file`, `read_multiple_files`, `read_media_file`.
- `read_multiple_files` takes an unbounded array. `directory_tree` and `search_files` recurse without limit. `args.head === 0` is falsy, so it falls through to a full read (`server.ts:260-272`).
- There is no file-type check, so a FIFO or device inside an allowed directory could block a call. The server is single-user stdio, so the impact is local availability and context flooding. Static only.

**F4. Client Roots replace the command-line allow-list entirely (B02, B03, E06).**
- `allowedDirectories = [...validatedRootDirs]` (`server.ts:835`). There is no intersection with the CLI directories, and a root of `/` is accepted.
- This is documented and by design. It means the CLI arguments are not a ceiling for 2025-era Roots-capable clients, so the host owns the effective scope. The modern era ignores Roots.
- Positive: revocation works. An empty roots update clears access (`server.ts:840-844`), and stale-answer and barrier handling is implemented (`server.ts:828`, `server.ts:234-237`).

**F5. No audit trail of tool invocations (R03, A02; S4).**
- The only logging is `console.error` for roots changes and startup. Writes, edits, moves and denials are not recorded with caller, target or outcome.
- A host or gateway log may exist (`needs_evidence`, host owner).

**F6. Docker build is not lock-pinned and runs as root (B10, B11, C02, C05).**
- `FROM node:24-alpine` is a floating tag.
- The builder runs `npm install` (lifecycle scripts enabled) against `COPY src/filesystem /app`. I found no `package-lock.json` in `src/filesystem`.
- The release stage copies the lock generated in the builder and runs `npm ci` against it. Dependency resolution therefore floats within `^` ranges at build time.
- There is no `USER` directive. Bind-mount `ro` is the real isolation control and is host-owned.
- The npx example in the README is unpinned.

**F7. `edit_file` and `write_file` are non-atomic and can lose updates (R14; low).**
- Truncate-then-write (`pinned-directory.ts:246-247`). A crash leaves a partial file, which the code comment acknowledges (`lib.ts:363`).
- `edit_file` does read-modify-write with no concurrent-writer check.

## 4. Coverage

| Boundary or check | Status | Evidence | Owner |
|---|---|---|---|
| Allow-list prefix check, with sibling-prefix and null-byte rejection | `likely_pass` | `path-validation.ts:11-105` appends a separator and rejects `\x00` | Server |
| Symlink escape on existing and new paths | `likely_pass` | `lib.ts:276-283`, `lib.ts:208-218`; a dangling symlink yields ENOENT and a denial (`lib.ts:201`, `lib.ts:291-296`); `list_directory_with_sizes` revalidates each entry | Server |
| Unicode and case-insensitive resolution | `likely_pass` | `lib.ts:186-188` rejects ambiguous matches | Server |
| Quote and whitespace stripping not used for file ops | `likely_pass` | `normalizePathFormat` vs `normalizePath` (`path-utils.ts:41-52`) | Server |
| Windows path on POSIX | `likely_pass` | `lib.ts:235-242` | Server |
| Write TOCTOU | `likely_pass` | `O_EXCL`, `O_NOFOLLOW`, inode match, chdir pin (`pinned-directory.ts`). The chdir is synchronous, so no `await` runs inside the borrowed cwd. | Server |
| Read and move-source TOCTOU | `gap` | F1 | Server |
| Traversal paths (`directory_tree`, `search_files`) | `likely_pass` | Per-entry `validatePath`. Dirent symlinks are not followed, so there are no symlink cycles. | Server |
| Resource limits | `gap` | F3 | Server |
| Business authorization and approval | `needs_evidence` | None in the server; F2 | Host or client |
| Protected-path policy | `gap` | F2 | Server, then host |
| Roots scope | `needs_evidence` | F4; client behavior unknown | Host |
| Process user, mounts, network, sandbox | `needs_evidence` | Not determinable from the repo | Deployer |
| Credentials | `na_candidate` | Searched the tool, config and Dockerfile files for secrets and env reads; none found | – |
| HTTP, OAuth, Tasks, Skills, Apps, auth extensions | `na_candidate` | Only stdio is wired in `index.ts`; the entrypoint registers no HTTP transport and none of those extensions | – |
| Untrusted returned content | `needs_evidence` | Tool output is file content. Whether an attacker can write files inside an allowed directory is not established. File content and filenames are model-visible (`read_*`, `list_*`). | Host |
| Audit | `gap` | F5 | Server, host |
| Supply chain | `gap` | F6. SDK 2.4.0 is resolved and the lockfile has integrity hashes. | Maintainers, deployer |
| Stop and recovery, process-tree termination | `needs_evidence` | No child processes spawned. Writes are synchronous within a call. | Host |
| stdout contamination | `likely_pass` | Logging uses `console.error` (stderr) | Server |

**Unreviewed:**
- Everything else in the monorepo: `everything`, `fetch` and others.
- The `__tests__` content, beyond filenames.
- The `.github` workflows, the release process, and the contents of `dist`.
- The SDK internals: `serveStdio` and schema validation.
- The `scripts/session-instructions-check.mjs` hook.

## 5. Proposed controlled tests

Run these only in a disposable environment with fake data, owned by the maintainers or deployer. Do not run them as part of this review.

1. **F1:** loop-swap a subdirectory with a symlink to an outside directory while calling `read_text_file` and `move_file` on a path beneath it. Expected: allowed reads inside the root succeed, and an outside read or move is denied or fails.
2. **F2:** with the host's approval settings, ask the model to write `.claude/settings.json` or a git hook. Expected: the host requires explicit approval, or the server refuses. Owner: host.
3. **F3:** call `read_text_file` on a very large file, `head: 0`, a FIFO, and a deep tree. Expected: a bounded response or error with no process stall.
4. **F4:** send roots `/`, then an empty roots update. Expected: access follows the host's policy, and an empty update revokes access.
5. **F6:** rebuild the image twice and diff the resolved dependency trees. Expected: identical trees. Also check that the container's user and mounts are non-root and `ro` where intended.

## 6. Limits

- No findings above are runtime-confirmed.
- This is a focused MCP review of one server, not the 53-item BRACE assessment.
- It is not a release verdict or a security Pass. Any deployment decision belongs to accountable people, with gradual, monitored rollout, bounded exposure, stop conditions and tested recovery.
