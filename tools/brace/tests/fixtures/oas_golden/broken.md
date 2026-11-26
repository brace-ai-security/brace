### open-agent-security

| Severity | Problem | Where | Fix |
|---|---|---|---|
| high | [Agent runs with all permission checks turned off](https://braceframework.org/anti-patterns/#ap01-agent-runs-with-all-permission-checks-turned-off) | sub/run\.sh:1 | Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs. |

- note: could not parse \.mcp\.json; its findings are unknown
