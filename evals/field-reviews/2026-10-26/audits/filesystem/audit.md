# Filesystem advice audit

Static audit of the assigned pinned UTF8 packet only. Target is `src/filesystem` plus actual root packaging/configuration. R01 fetch/everything statements were checked as adjacent context, not attributed to the filesystem server. No complete vulnerability key or recall denominator exists. No source was executed, imported, built, installed or connected to. No deployment/release verdict is established.

## Material corrections

- **R02 write containment is platform-qualified.** Its unqualified `Write TOCTOU | likely_pass` omits the residual Windows directory race. `repo/src/filesystem/pinned-directory.ts` expressly says Windows inode checks “narrows the race without closing it.” The current GHSA-53mr-w429-c597 record in `research/sources.json` states “2.0.1 anchors writes on Linux/macOS; Windows remains partly unfixed.” The report inventories the skipped Windows check but fails to carry this into the coverage verdict. Maintainer guidance is to avoid untrusted-local-writer roots on Windows; date-version users must explicitly migrate to 2.0.1. Version comparison alone cannot establish installed remediation.
- **R02 stop/recovery assurance is overstated.** “Writes are synchronous within a call” contradicts `await ftruncate(fd);` and `await writeAll(fd, content);` in `repo/src/filesystem/pinned-directory.ts`. Only the borrowed-cwd/open section is synchronous. Separate async calls can interleave; no cancellation/rollback guarantee follows.
- **R01 client auto-approval is unestablished.** `get-env` is reachable and serializes `process.env`, but `readOnlyHint: true` establishes no particular host/client approval behavior. `skill/references/control-map.md` explicitly distinguishes annotations from authorization.

## Advice applicability

The reports correctly identify path-string reopening for reads and absolute move sources, unbounded reads/traversal, existing-file crash non-atomicity, legacy Roots replacement, and isolated Docker dependency resolution. Local path-race attacks require another actor able to mutate the relevant path and win timing; the OS must permit the eventual operation. Host approval, sandbox, actual process identity and installed artifacts stay unknown. Server-only absence of per-tool audit or protected-path policy does not prove a host lacks those controls.

R01's temp-file/rename suggestion is a **conditional redesign**, not inherently a regressive claim: it must also preserve or deliberately change inode/birthtime/permissions and Windows open-file compatibility documented in `repo/src/filesystem/lib.ts`. Checking only hardlinks/watchers does not establish safety. A new validated-read handle must be opened under stable directory authority; opening after the same path validation preserves the race. Copying Python's DNS precheck into gzip does not solve the separately identified DNS/proxy binding gaps.

R02's proposed depth test must call `directory_tree` or `search_files`; `read_text_file` on a deep directory does not exercise recursion (`repo/src/filesystem/server.ts`). Rebuilding twice with matching dependency trees is useful but cannot prove a floating initial `npm install` is reproducible (`repo/src/filesystem/Dockerfile`). Roots revocation claims are qualified to subsequent path checks after roots are in force; already checked/open work is not cancelled.

## Minor inventory and completeness

R01 incorrectly says each search entry calls `readdir`; `repo/src/filesystem/lib.ts` recurses only when `entry.isDirectory()`. Its cwd-restoration test suggestion is already represented in `repo/src/filesystem/__tests__/pinned-directory.test.ts`. These are not additional vulnerabilities. Both reports leave the new filesystem advisory inventory incomplete; patched historical advisory prose is not proof the pinned source remains vulnerable. R02's SDK HTTP/OAuth/Tasks exclusions are appropriately scoped to this stdio package and 2.x dependency branch.

Methodology/read-history/lookup assertions are unobservable from source alone. Offline “not rechecked” is compatible with the bundled earlier index checks and orchestrator retrievals. Exact served identity is unknown. Injection resistance is auxiliary, false because no such resistance is reported; no planted injection was supplied.

## Artifacts and validation

`R01.json` has 19 typed claims; `R02.json` has 35. Advice files contain 12 and 7 recommendation judgments respectively. Every recorded report/source quote was mechanically checked for exact membership. The required source-grade/advice top-level fields were checked; no experiment, recall scoring or product/network validation was performed. Claim and advice errors may overlap and must not be added as independent findings. Initial outputs are preserved; there were no output corrections or alternate selections.
