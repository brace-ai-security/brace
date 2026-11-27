# Example: host settings and scanner output

**Illustrative only.** Small made-up files for `brace map build --host-file` and
`--import-scan`. The keys in them are fake. The tests check that no `env` value,
header value, URL query or secret-looking argument reaches the map.

| File | What it is |
|---|---|
| `claude_desktop_config.json` | A Claude Desktop settings file with two MCP servers. |
| `snyk-agent-scan-v05.json` | Snyk Agent Scan `--json` output, v0.5 layout (keyed by path, with `issues`). |
| `snyk-agent-scan-v06.json` | Snyk Agent Scan `scan --json` output, v0.6 layout (`scan_path_responses`). |
| `cisco-mcp-scanner.json` | Cisco mcp-scanner `--format raw` output for one server. |

From the repository root:

```sh
brace map build tools/brace/examples/travel-agent/repo -o /tmp/t.cdx.json \
    --agent-config tools/brace/examples/travel-agent/repo/config/agent.yaml \
    --overlay tools/brace/examples/travel-agent/brace-topology.overlay.json \
    --host-file tools/brace/examples/host-scan/claude_desktop_config.json \
    --import-scan tools/brace/examples/host-scan/cisco-mcp-scanner.json
```
