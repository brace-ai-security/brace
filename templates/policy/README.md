# Hardened agent policy templates

Configuration an administrator can deploy to every managed machine, so the settings that
[open-agent-security](../../tools/brace/SCAN.md) reports cannot be turned back on by a user or
by a repository. Each file uses only settings named in the vendor's documentation, cites the page
it follows and the date it was checked, and passes the scanner:

```sh
python3 -I tools/brace/scan.py templates/policy --fail-on low
```

These are starting points, not drop-in policy. Replace the example MCP servers (`github`) and
command lists with your own, test on one machine, and re-check the cited pages before you deploy:
vendors rename and add settings between releases. JSON files cannot hold comments, so their
source and date are listed here.

| File | Agent | Deploy to | Follows (as of 2026-11-27) |
|---|---|---|---|
| [claude-code/managed-settings.json](claude-code/managed-settings.json) | Claude Code | macOS `/Library/Application Support/ClaudeCode/managed-settings.json`; Linux `/etc/claude-code/managed-settings.json`; Windows `C:\Program Files\ClaudeCode\managed-settings.json` | https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/iam, https://code.claude.com/docs/en/mcp |
| [codex/requirements.toml](codex/requirements.toml) | Codex | `/etc/codex/requirements.toml` or MDM | https://developers.openai.com/codex/security |
| [codex/managed_config.toml](codex/managed_config.toml) | Codex | `/etc/codex/managed_config.toml` or MDM | https://developers.openai.com/codex/security, https://developers.openai.com/codex/config-reference |
| [gemini-cli/settings.json](gemini-cli/settings.json) | Gemini CLI | system settings: Linux `/etc/gemini-cli/settings.json`; macOS `/Library/Application Support/GeminiCli/settings.json`; Windows `C:\ProgramData\gemini-cli\settings.json` | https://geminicli.com/docs/get-started/configuration/ |
| [cursor/hooks.json](cursor/hooks.json) and [cursor/guard.py](cursor/guard.py) | Cursor | enterprise hooks: macOS `/Library/Application Support/Cursor/hooks.json`; Linux `/etc/cursor/hooks.json`; the script at `/usr/local/share/cursor-policy/guard.py` | https://cursor.com/docs/agent/hooks |

## What each setting does, and the BRACE items it serves

Checklist items are in [CHECKLIST.md](../../CHECKLIST.md); anti-patterns (AP) in
[ANTI-PATTERNS.md](../../ANTI-PATTERNS.md).

### Claude Code: managed-settings.json

Managed settings take precedence over user, project and command-line settings.

| Setting | Effect | BRACE | Anti-pattern |
|---|---|---|---|
| `permissions.defaultMode: "default"` | Ask before tools that are not allowed | B05 | AP01 |
| `permissions.disableBypassPermissionsMode: "disable"` | The bypass mode and its command-line flag cannot be used | B05, B06 | AP01, AP02 |
| `permissions.deny` (network, `sudo`, `rm -rf`, force push, `WebFetch`, secret files) | These tools and files are refused, whatever other rules allow | B01, B05, B09, B03 | AP06, AP09 |
| `permissions.ask` (`git push`, `npm publish`) | A person approves each one | B05 | AP02 |
| `allowManagedPermissionRulesOnly: true` | Only these permission rules apply; user and project allow rules are ignored | B01, B06 | AP06 |
| `allowManagedHooksOnly: true` | Only managed hooks run; a repository cannot add its own | B12 | |
| `allowManagedMcpServersOnly: true`, `allowedMcpServers`, `deniedMcpServers` | Only the listed MCP servers can be used | E02, E05 | AP04, AP07 |
| `enableAllProjectMcpServers: false` | A repository's `.mcp.json` servers are not approved automatically | E02, E03 | AP04 |

### Codex: requirements.toml and managed_config.toml

`requirements.toml` sets limits a user cannot go beyond; `managed_config.toml` sets the starting
values. Deploy both.

| Setting | Effect | BRACE | Anti-pattern |
|---|---|---|---|
| `allowed_approval_policies = ["untrusted", "on-request"]` | `never` (no approvals) cannot be chosen | B05 | AP01, AP02 |
| `allowed_sandbox_modes = ["read-only", "workspace-write"]` | `danger-full-access` cannot be chosen | B08 | AP01, AP02 |
| `approval_policy = "on-request"` | Ask before commands outside the safe set | B05 | AP01 |
| `sandbox_mode = "workspace-write"` | Writes only inside the workspace | B08 | AP01, AP08 |
| `sandbox_workspace_write.network_access = false` | No network from sandboxed commands | B09 | AP09 |
| `shell_environment_policy.inherit = "core"` | Commands do not see tokens from the user's environment | B03 | AP05 |

An MCP server allowlist in `requirements.toml` is not included: its syntax could not be confirmed
against the current page. Add it from the vendor's page if your Codex version documents it.

### Gemini CLI: system settings.json

System settings override user and workspace settings.

| Setting | Effect | BRACE | Anti-pattern |
|---|---|---|---|
| `security.disableYoloMode: true` | YOLO mode (`--yolo`, `-y`, `--approval-mode yolo`) cannot be turned on | B05 | AP01, AP02 |
| `security.folderTrust.enabled: true` | Settings, MCP servers and commands from an untrusted folder are not loaded | B12, E03 | AP04 |
| `tools.sandbox: true` | Tools run in a sandbox | B08 | AP08 |
| `tools.core` | Only the listed tools, and only these shell commands, are available | B01 | AP06 |
| `tools.exclude: ["web_fetch"]` | The model cannot fetch URLs | B09 | AP09 |
| `mcp.allowed` | Only the listed MCP servers are loaded | E02, E05 | AP04, AP07 |

### Cursor: hooks.json and guard.py

Enterprise hooks run before user and project hooks. `guard.py` denies network and privilege
commands, asks before `rm`, `git`, `npm` and `pip`, and denies MCP calls to servers not on its
allowlist; it fails closed.

| Setting | Effect | BRACE | Anti-pattern |
|---|---|---|---|
| `hooks.beforeShellExecution` → `guard.py shell` | Each shell command is allowed, denied or sent to a person | B05, B01, B09 | AP06, AP09 |
| `hooks.beforeMCPExecution` → `guard.py mcp` | MCP calls only to allowlisted servers | E02, E05 | AP04, AP07 |

Turn off auto-run (Cursor's "run everything" mode) and set the team MCP allowlist in the Cursor
team admin settings; those are dashboard settings, not files, so they have no template here.
