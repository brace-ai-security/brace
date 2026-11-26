# open-agent-security

Find known-dangerous AI agent setups in a repository, in seconds.

```bash
uvx open-agent-security .            # or: pipx run open-agent-security .
uvx open-agent-security . --host     # also check MCP servers configured on this machine
```

It reports, with file and line, why each problem matters and how to fix it:

| ID | Problem |
|---|---|
| AP01 | Agent runs with all permission checks turned off |
| AP02 | Unattended agent in CI with permission checks turned off |
| AP03 | Agent workflow triggered by `pull_request_target` |
| AP04 | MCP server installed from an unpinned package |
| AP05 | Secret written directly in agent configuration |
| AP06 | Agent allowed to run any shell command |
| AP07 | Remote MCP server reached over plain HTTP |
| AP08 | Agent tool container can take over the host |
| AP09 | Lethal combination: untrusted input, private data and a way out (inferred, marked *likely*) |
| AP10 | Agent image not pinned to a digest |

Details and fixes: https://braceframework.org/anti-patterns/

**Safe to run.** Standard library only. It reads files and matches fixed patterns: it
starts no server, runs no model and sends nothing over the network. Secret values are
never printed. `--host` reads only the known MCP config files of Claude Desktop, Claude
Code, Cursor, VS Code, Windsurf and Devin Desktop, and shows paths under your home folder
as `~/`.

**Options:** `--json`, `--sarif FILE` (GitHub code scanning), `--markdown FILE` (job
summary), `--fail-on critical|high|medium|low|none` (default `high`; exit 1 at or above).

**Silencing a reviewed finding:** add `open-agent-security: ignore` in a comment on that line, or
list paths in a `.open-agent-security-ignore` file (glob patterns; a trailing `/` matches a folder).

**Limits.** A clean scan means none of these patterns was found. It is not a security
review and not BRACE compliance. For that, use BRACE Starter
(https://braceframework.org/starter/) or the full sign-off checklist
(https://braceframework.org/checklist/).
