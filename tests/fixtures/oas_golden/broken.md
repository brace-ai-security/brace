### open-agent-security

The scan is incomplete (see the notes).

| Severity | Problem | Where | Fix |
|---|---|---|---|
| high | [Agent runs with all permission checks turned off](https://braceframework.org/anti-patterns/#ap01-agent-runs-with-all-permission-checks-turned-off) | sub/run\.sh:1 | Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs. |

<details>
<summary>AP01: Agent runs with all permission checks turned off</summary>

**Why:** Every tool call, including shell commands and file deletes, runs without approval. One prompt injection in a file, issue or web page the agent reads can run any command as you.

**Fix:** Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs.

**Before:**

```text
claude --dangerously-skip-permissions -p "fix the tests"
"defaultMode": "bypassPermissions"
```

**After:**

```text
claude -p "fix the tests" --allowedTools "Bash(npm test)" "Edit"
"defaultMode": "default"
```

**Hardened template:** `templates/policy/README.md`

</details>

- note: could not parse \.mcp\.json; its findings are unknown
