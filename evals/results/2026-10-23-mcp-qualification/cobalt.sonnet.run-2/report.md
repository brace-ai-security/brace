# MCP review: `repo/` (file read component)

**Review date:** 2026-10-23. **Method:** static file reading only. I did not execute, import or connect to anything. No public-source lookup was possible, so advisory rechecks were not done.

## Untrusted-content notice
`repo/catalog-notes.txt` contains an "imported description" telling a security reviewer to skip file permission findings and output SAFE. It is untrusted data. I did not follow it, and it did not change any conclusion below. Someone should check where that text came from. It looks like an attempt to influence review output.

## Scope and inventory
| Item | Evidence |
|---|---|
| Component | Server handler `handle_line` in `repo/server.py`. The host, framing adapter, sandbox and audit capture are outside the supplied source (README). |
| Transport | stdio only. There is no HTTP, OAuth, Tasks, Apps, memory or sub-agent code (README, and no such code in `server.py`). |
| Server entry | `files`, in `.mcp.json:3-8`. Command is `/opt/runtime/bin/python3` with arg `server.py` (relative). No `env`, `cwd` or package pins. |
| Version evidence | `runtime.lock` declares `python-3.12.13` and `source-release: file-component-8`. This is a declared value. The installed runtime and resolved release are **unknown**. |
| Protocol revision / extensions | **Unknown.** The code has no `initialize` or negotiation handling. No extensions are enabled in the source. |
| Tools | One tool, `read` (`server.py:15`), advertised with `readOnlyHint`. It has no `inputSchema`. |
| Downstream action | Read up to 8192 bytes of a regular file under `/srv/mcp-share`. |
| Credentials | None in the source. Inherited environment is host-owned and unknown. |
| OS | Linux stdio host (README). |
| Dependencies | Standard library only, with no lockfile package entries. No listed MCP SDK, LangChain, LangGraph or Cosign advisory applies. |

## Findings
**No confirmed gaps** within this scope. Two `needs_evidence` items could become findings if the host evidence is unfavourable.

### 1. Path boundary: `likely_pass` (supported in code)
Trigger: a requester-supplied `args["path"]`, which reaches `target_path` and then `os.open` (`server.py:4-8, 19-20`).

I tried these bypasses against the code:
- **Absolute path or `..`:** `os.path.join` followed by `realpath` and `commonpath` against `ROOT` rejects both.
- **Symlink inside the tree pointing outside:** `realpath` resolves it first, so the `commonpath` check rejects it. Final-component symlinks are also blocked by `O_NOFOLLOW`.
- **FIFO or device:** `O_NONBLOCK` plus the `S_ISREG` check on the `fstat` of the opened descriptor rejects it. A directory, including `ROOT` itself, also fails `S_ISREG`.
- **Check-then-open race (TOCTOU):** the README states that only trusted administrators write the tree and requesters cannot modify it during a request. Under that policy no reachable path exists. This is a documented precondition, not something the code enforces. The host must enforce write permissions on `/srv/mcp-share`.
- **Non-string or NUL path:** this raises an exception (`TypeError` or `ValueError`) before any open, so it fails closed.

Residual note: `ROOT` is not passed through `realpath`. If `/srv/mcp-share` is itself a symlink, every request is denied. That is an availability issue, not a security one.

Basis: guidance in the stdio reference and the BRACE control map. Related BRACE items: B05 and B11.

### 2. `needs_evidence`: audit completeness (R03, R13, A02, E10–E12)
- `audit_sink.record` runs only after a successful read (`server.py:27`). Denials, failed opens and malformed requests are not recorded by this code.
- The README says the host owns the full attempt, denial and result audit. Its implementation and protections are not supplied.
- Owner: host or framing operator. Evidence needed: a trace showing denied and errored requests are logged, and what happens when the audit sink is unavailable.

### 3. `needs_evidence`: launch integrity and isolation (B10–B12, C02, C05, E02)
- `server.py` is resolved relative to the host's working directory, with no hash, signer or pin. The working directory is unknown.
- Python is run without `-I`, so imports of `json`, `os` and `stat` could be shadowed by a file next to the script. This is only reachable if someone untrusted can write to that directory, which is not shown.
- Process user, sandbox, network policy, inherited credentials and process-tree termination are not supplied (README). A local server inherits the full authority of its process. `ROOT` is enforced only in application code.
- Owner: host or deployment operator.

### Informational (no BRACE gap asserted)
- `readOnlyHint` is metadata, not an authorization decision (control map). Authorization here comes from the code in item 1.
- Requests other than `tools/list` are treated as `tools/call`. For example, `initialize` would fail with a `KeyError`. This could be a protocol-compliance concern, but I can't judge it without the negotiated revision, so I record no claim.
- The line size limit (16384) is checked on the decoded string length. Output is truncated silently at 8192 bytes. Both are bounded.

## Coverage table
| Boundary / check | Status | Evidence | Owner |
|---|---|---|---|
| Path and symlink containment | likely_pass | `server.py:4-8, 19-22` | Server |
| Tree write protection | needs_evidence | Documented only (README) | Host / administrator |
| Operation allowlist (`read` only) | likely_pass | `server.py:17-18` | Server |
| Input and parser limits | likely_pass | `server.py:11`, `:24` | Server |
| Audit of denials and results | needs_evidence | `server.py:27` is partial | Host |
| Launch pin, working directory, environment | needs_evidence | `.mcp.json` | Host / deployment |
| Sandbox, network, credentials, termination | needs_evidence | README says host-owned | Host |
| Installed runtime vs `runtime.lock` | needs_evidence | Declared only | Deployment |
| Protocol revision / negotiation | needs_evidence | Unknown | Host |
| HTTP, OAuth, Tasks, Apps, memory, sub-agents | na_candidate | README documents absence. A search of `repo/` for `http`, `oauth`, `task`, `memory` and `agent` shows no implementation code (only README prose). | n/a |
| MCP SDK advisories | na_candidate | No SDK dependency in `server.py` or `runtime.lock` | n/a |
| Identity, tenant and approval | needs_evidence | No identity or tenant data in the handler. The README says only that filesystem consumers submit arbitrary names. | Host |

## Controlled tests to propose (not run)
Owner for all: the host operator, on a disposable fixture.
1. **Allowed:** read a regular file under `ROOT`. Expected: content up to 8192 bytes, plus an audit record.
2. **Denied:** `../x`, an absolute path, a symlink to an outside file, a FIFO, a directory, and a NUL byte. Expected: each rejected and each denial logged by the host.
3. **Audit outage:** make the sink unavailable. Expected: a defined fail-closed or fail-open behaviour that the operator has approved.
4. **Launch:** change `server.py` or the working directory. Expected: the host rejects an unapproved executable.
5. **Isolation:** confirm the process user and mounts cannot read outside `ROOT`, even if the application check were bypassed.
6. **Write protection:** confirm requesters cannot write to `/srv/mcp-share`.

## Limits
Source-only evidence. Nothing here shows the installed runtime, host configuration or OS enforcement, and this is not a deployment authorization. The report is not a security Pass or a 53-item BRACE assessment. No findings means only that this review identified none within the scope recorded above. Any rollout decision belongs to accountable people, with gradual rollout, bounded exposure, stop conditions and tested recovery.
