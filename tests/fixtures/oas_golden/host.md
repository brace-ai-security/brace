### open-agent-security

| Severity | Problem | Where | Fix |
|---|---|---|---|
| high | [MCP server installed from an unpinned package](https://braceframework.org/anti-patterns/#ap04-mcp-server-installed-from-an-unpinned-package) | \~/\.cursor/mcp\.json:1 | Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile. |
| high | [Agent allowed to run any shell command](https://braceframework.org/anti-patterns/#ap06-agent-allowed-to-run-any-shell-command) | \~/\.claude/settings\.json:1 | Allow only the specific commands the task needs, such as Bash\(npm test\), and keep deny rules for network and destructive commands. |

<details>
<summary>AP04: MCP server installed from an unpinned package</summary>

**Why:** npx/uvx/bunx fetch the newest version at every start. A hijacked or malicious update becomes code running with your agent's access, with no review.

**Fix:** Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile.

**Before:**

```text
"args": ["-y", "some-mcp-server"]
```

**After:**

```text
"args": ["-y", "some-mcp-server@1.4.2"]
```

</details>

<details>
<summary>AP06: Agent allowed to run any shell command</summary>

**Why:** An allow-rule like Bash\(\*\) or a bare Bash lets the agent run any command without asking. That includes curl to send your files out, rm -rf and git push --force.

**Fix:** Allow only the specific commands the task needs, such as Bash\(npm test\), and keep deny rules for network and destructive commands.

**Before:**

```text
"allow": ["Bash(*)"]
```

**After:**

```text
"allow": ["Bash(npm test)", "Bash(git status)"],
"deny": ["Bash(curl:*)", "Bash(rm -rf:*)"]
```

**Hardened template:** `templates/policy/claude-code/managed-settings.json`

</details>

