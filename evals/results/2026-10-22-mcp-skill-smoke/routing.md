# BRACE skill discovery routing check

Scope: selection based only on the YAML `name` and `description` fields of the four supplied skills. No skill bodies, research, execution, or effectiveness assessment were used.

| # | Request | Select | Reason |
|---|---|---|---|
| 1 | Audit this .mcp.json for leaked secrets and unpinned launch commands. | `brace-mcp-review` | Explicit `.mcp.json` review and MCP client configuration security audit. |
| 2 | Review my agent against the full BRACE checklist, including its MCP gateway. | `brace-review` | The full 53-item agent checklist is the controlling scope; the MCP gateway is part of that review. |
| 3 | Write isolated negative tests for the issuer and audience findings in this MCP report. | `brace-tests` | Requests test evidence following security findings; the requested deliverable is tests, rather than another audit. |
| 4 | Record these drill results and draft the R05 exception for governance. | `brace-record` | Both recording evidence and drafting an exception are explicit triggers. |
| 5 | Help build a new weather MCP server. | None | Implementation of a new server is outside the described audit, evidence-test, and governance-record workflows. |
| 6 | Does this SDK upgrade actually fix my MCP security concerns? | `brace-mcp-review` | Assessing whether a change remediates MCP security gaps fits the review scope and advisory-remediation trigger. |
| 7 | Run a BRACE production readiness review. | `brace-review` | A readiness review most closely matches preparing an agent for BRACE sign-off and reviewing the checklist. |
| 8 | Explain MCP transport basics. | None | General protocol education does not request an audit, tests, or a BRACE record. |
| 9 | Check whether our gateway can be bypassed via CLI tools. | `brace-mcp-review` | Gateway boundary security is explicit in this description. This selection implies review findings; it does not authorize exploit execution. |
| 10 | Install an MCP server from npm. | None | Installation is outside these descriptions; the MCP review explicitly does not launch servers. |

## Ambiguities and overlaps

- **Full-agent versus MCP-specific review (#2, #9):** `brace-review` broadly covers agent security, while `brace-mcp-review` explicitly covers gateways. A full-checklist request selects the former; a gateway-boundary request selects the latter. Neither description explicitly states this precedence, so selection could vary.
- **Tests following an MCP report (#3):** `brace-tests` broadly promises tests for BRACE evidence, but its explicit follow-up examples name only `brace-review` and its ratings. An MCP report without a stated BRACE mapping is less clearly covered. It remains the best match for the requested test-writing deliverable; discovery confidence is lower than for #1 or #4.
- **SDK remediation without a named advisory (#6):** `brace-mcp-review` explicitly mentions advisory remediation, while the request says only security concerns. Its general MCP security-gap scope supports the selection, although an SDK upgrade unrelated to those gaps would require more context.
- **Production readiness versus release check (#7):** `brace-review` covers preparing for sign-off, while `brace-record` includes running the BRACE release check. The word “review” favors `brace-review`; a request to evaluate an existing `.brace/` record against the release check could instead select `brace-record`. The descriptions do not make this boundary explicit.
- **Active bypass testing (#9):** The request could imply executing bypass attempts. `brace-mcp-review` is discoverable for boundary review, but its description excludes running exploits. A request explicitly demanding executable evidence would lean toward `brace-tests`; the current wording does not demand that deliverable.

## Conclusion

Expected routing: `brace-mcp-review` for 1, 6, and 9; `brace-review` for 2 and 7; `brace-tests` for 3; `brace-record` for 4; none for 5, 8, and 10.

The MCP description distinguishes audits from construction, installation, and education. The main discovery weaknesses are handoff to test generation and the distinction between a readiness review and a release-record check. This check does not establish whether any skill executes correctly or produces effective security findings.
