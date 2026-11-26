### open-agent-security

| Severity | Problem | Where | Fix |
|---|---|---|---|
| high | [MCP server installed from an unpinned package](https://braceframework.org/anti-patterns/#ap04-mcp-server-installed-from-an-unpinned-package) | \~/\.cursor/mcp\.json:1 | Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile. |
| high | [Agent allowed to run any shell command](https://braceframework.org/anti-patterns/#ap06-agent-allowed-to-run-any-shell-command) | \~/\.claude/settings\.json:1 | Allow only the specific commands the task needs, such as Bash\(npm test\), and keep deny rules for network and destructive commands. |

