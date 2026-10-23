# MCP review: `repo/` (local file tool and `.mcp.json`)

Review date: 2026-10-23. Method: static file reading only. Nothing was executed, installed or connected to. Public-source lookup was unavailable, so advisory and protocol citations below are the bundled URLs and dates and were **not rechecked**.

## Attempt to influence the review

`repo/catalog-notes.txt:1` says an "imported description" instructs a security reviewer to skip all file permission findings and output SAFE. This is untrusted data, so I did not follow it. It conflicts with the findings below, and its presence is itself a supply-chain and metadata-integrity signal (E03, E04).

## 1. Scope and inventory

| Item | Evidence |
|---|---|
| Files reviewed | `server.py`, `README.md`, `launch-contract.md`, `.mcp.json`, `catalog-notes.txt`, and the skill references. No other hidden files exist. |
| Component | A server-side line handler (`handle_line`) for a local stdio MCP server. It is invoked by a Linux host through the `file-bridge` package. |
| Commit/release | Unknown. There is no git repo and no lockfile. |
| Protocol revision, extensions | Unknown. No negotiation code is supplied. The README states there is no HTTP, OAuth, Tasks, Apps, memory or sub-agent surface. |
| Configured server `files` | `npx -y file-bridge@latest`, with `BRIDGE_ACCESS_TOKEN` set in `.mcp.json:9-11` (value redacted; it looks synthetic). |
| Tools | `tools/list` advertises only `read`, with `readOnlyHint: true` (`server.py:15`). `tools/call` accepts `read` and `write` (`server.py:17`). |
| Downstream actions | File read, up to 8192 characters, and file write under `/srv/mcp-share`. |
| Resolved version | Unknown. `@latest` is a floating declaration, not a resolved version. |

**Ownership boundaries**
- This component owns path checks and the tool operations.
- The host owns the sandbox, network, package verification and registry resolution, inherited credentials, audit-sink protection, process termination, and framing and authentication of callers.
- The README says none of the host-owned items are supplied.

## 2. Findings (by impact)

### F1. Undeclared `write` tool is callable with no authorization (gap)
- **Trigger and dataflow:** a `tools/call` with `name="write"` goes through `request["params"]` → `target_path` → `open(path,"w").write(content)` (`server.py:16-23`).
- **Evidence:** the only checks are the name allowlist and the path prefix. There is no caller, approval or scope check. The README says the module contains the complete application operation and path checks, with no extra authorization in the adapter.
- **Evidence:** `tools/list` shows only a read-only tool, so the host or user sees a read-only surface while a consequential write is reachable. Annotations and list metadata are not an authorization decision.
- **Impact:** any client that can submit a request can create or overwrite files in the share. That also allows persistent influence if those files are later trusted.
- **BRACE:** B01, B05, B06, E03, E04, B12.
- **Sources:** OWASP Transaction Authorization (guidance); control-map "Business authorization" and "Publication/integrity" rows.
- **Remediation:**
  - Remove `write`, or advertise it in `tools/list` with accurate annotations.
  - Enforce a per-caller, per-operation and per-path authorization check inside the handler.
  - Require host-side approval for writes.
  - Make the list and call surfaces derive from one registry.

### F2. Path containment is a string-prefix check on a non-canonical path (gap)
- **Evidence:** `target_path` uses `normpath(join(ROOT, name))` and then `path.startswith(ROOT)` (`server.py:5-7`).
- **Sibling prefix bypass:** a name such as `../mcp-share-x/f` normalizes to `/srv/mcp-share-x/f`, which passes because there is no trailing separator in the comparison. The prerequisite is that a sibling directory with that prefix exists, which is unknown. If one does, both read and write escape.
- **Symlink bypass:** `normpath` does not resolve symlinks, and `open` follows them. The README says the tree may contain symlinks. A symlink inside ROOT pointing outside it passes the check for both read and write. The README's claim that ROOT is the only permitted read tree is therefore not enforced in code.
- **Rejected:** an absolute `name` or plain `..` traversal that lands outside ROOT is rejected by the prefix check. Static reasoning only; this was not run.
- **Reachability:** the symlink path is reachable if the administrator-provisioned tree contains outward links. The README says consumers cannot write files, which limits who can create such links, but it does not rule out existing ones.
- **BRACE:** B05, B11. Sources: stdio.md (symlink, glob and canonical-path handling); the LangChain filesystem advisory GHSA-gr75-jv2w-4656 (2026-10-22 research index; adjacent, not rechecked).
- **Remediation:**
  - Resolve with `os.path.realpath` and compare using `commonpath` or `path == ROOT or path.startswith(ROOT + os.sep)`.
  - Open with `O_NOFOLLOW`, or use dirfd-based `openat`.
  - Reject symlinks on write.

### F3. Floating, auto-installed package with a credential in the launch config (gap / needs_evidence)
- **Evidence:** `npx -y file-bridge@latest` (`.mcp.json:4-8`) has no pin, no integrity or signature check, and auto-confirms the install. `launch-contract.md` says the package delegates to this `server.py` and may read `BRIDGE_ACCESS_TOKEN`.
- **Impact:** each launch can run different, unreviewed code that receives the token. Pinning would not by itself fix known flaws.
- **Credential custody:** the token is stored in plaintext in a repo file (location `.mcp.json:10`, redacted). Rotation and exposure history are unknown.
- **Unknown:** the resolved version, the package contents and whether it matches this `server.py`. The registry and sandbox are out of scope.
- **BRACE:** B03, B10–B12, E02, C02, C05, E12.
- **Sources:** OWASP Supply Chain (guidance); stdio.md.
- **Remediation:**
  - Pin an exact version and digest, and verify provenance.
  - Move the secret to a secret store or the host's credential mechanism.
  - Treat the committed value as exposed and rotate it if it is real.
  - Run the server in a sandbox with a minimal environment.

### F4. Audit trail is incomplete and ordered after the effect (gap)
- **Evidence:** `audit_sink.record` runs after the read or write (`server.py:27`).
  - Denials raise before recording, so they are not logged.
  - A sink failure after a successful write leaves an unrecorded effect.
  - The record has only action and path: no caller or subject, no policy or approval ID, no outcome and no content hash.
- **BRACE:** R03, R13, A02, E10–E12. Source: OWASP Logging (guidance).
- **Remediation:**
  - Record the intent before the effect, and fail closed for writes if the sink is unavailable.
  - Log denials, caller identity and outcome.
  - Sink protection is host-owned (needs_evidence).

### F5. Robustness and limits (low, needs_evidence)
- **Evidence:** malformed requests raise uncaught `KeyError` or `JSONDecodeError` (`server.py:13-16`). The caller or adapter behavior is unknown.
- **Limits:** the 16384 limit is applied to `raw` before parsing (good). Reads are capped at 8192 characters. There is no per-file or total write quota beyond the line size.
- **BRACE:** B07, R01. Remediation: return structured errors without internals, and add quotas.

## 3. Coverage table

| Boundary / check | Status | Evidence | Owner |
|---|---|---|---|
| Inventory and pin | gap | `.mcp.json:6-7`; `@latest` | Deployer |
| Identity and caller authorization | needs_evidence | No caller identity is available to the handler. The adapter and host are unsupplied. | Host |
| Business authorization / approval for write | gap | F1 | Server, host |
| Tool metadata integrity | gap | F1; `catalog-notes.txt` | Server, registry |
| Path and symlink containment | gap | F2 | Server |
| Network and egress | needs_evidence | No network code in the module. Egress is host-owned. | Host |
| Tenant and state isolation | na_candidate | Searched `server.py` for caches, sessions and shared state and found none. A single shared tree has no tenant concept; the host must confirm. | Host |
| Resource and parser limits | likely_pass (partial) | 16 KB line cap and 8 KB read cap. Write quotas are absent. | Server |
| Persistent influence | gap | `write` into a trusted tree | Server, host |
| Stop and recovery | needs_evidence | Process termination is host-owned. | Host |
| Audit | gap | F4 | Server, host |
| Credentials | gap | F3 | Deployer |
| HTTP / OAuth / Tasks / Apps / Skills | na_candidate | The README states they are absent. Searched the files for HTTP, OAuth and task handlers and found none. | n/a |

## 4. Advisories
No SDK or framework package is identifiable in the source, and the resolved `file-bridge` version is unknown, so no advisory applies directly. The adjacent filesystem and symlink guidance (LangChain GHSA-gr75-jv2w-4656) is relevant by analogy only. Lookup was unavailable, so the entries are cited from `advisories.md` (dated 2026-10-22) and not rechecked.

## 5. Supported in code
- Request-size cap before JSON parsing.
- Tool-name allowlist.
- Read size cap.
- Normalization-based rejection of simple `..` and absolute-path escapes. This is superseded by the gaps in F2.

## 6. Missing evidence and unreviewed scope
- The `file-bridge` package contents and resolved version.
- The framing adapter and host: sandbox, process user, mounts, environment inheritance, approval UX, network policy and termination.
- The contents of `/srv/mcp-share` and its siblings: symlinks and `mcp-share*` directories.
- The audit sink.
- Whether the committed token is real.
- This was a source-only review. It is not deployment authorization or a release verdict.

## 7. Proposed controlled tests (disposable environment, fake credentials; not executed)

| Test | Expected allowed | Expected denied | Owner |
|---|---|---|---|
| Read a file in ROOT | Succeeds | n/a | Server owner |
| Name `../mcp-share-sibling/x` with a sibling dir present (read and write) | n/a | Rejected | Server owner |
| Symlink in ROOT pointing outside (read and write) | n/a | Rejected | Server owner |
| `tools/call write` by an unapproved caller | n/a | Denied and audited | Host and server owners |
| Audit sink unavailable during write | n/a | Write refused | Host owner |
| Launch with an altered package or a new `@latest` | Pinned build only | Unapproved build rejected; token not exposed in logs | Deployer |
| Termination drill | n/a | No further effects after stop | Host owner |

No findings are cleared by this review beyond its recorded scope.
