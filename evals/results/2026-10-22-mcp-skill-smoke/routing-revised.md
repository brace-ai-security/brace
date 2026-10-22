# BRACE skill discovery routing recheck

Scope: selection based only on current YAML `name` and `description` frontmatter for `brace-review`, `brace-tests`, and `brace-record`, plus the previously observed unchanged `brace-mcp-review` description. No bodies, research, execution, or repository edits. The original report is preserved.

| # | Request | Select | Reason |
|---|---|---|---|
| 1 | Audit this .mcp.json for leaked secrets and unpinned launch commands. | `brace-mcp-review` | Explicit MCP client-configuration security audit; the general reviewer now expressly delegates MCP-only audits. |
| 2 | Review my agent against the full BRACE checklist, including its MCP gateway. | `brace-review` | Entire-agent review against all BRACE items is explicit; the gateway remains within that full scope. |
| 3 | Write isolated negative tests for the issuer and audience findings in this MCP report. | `brace-tests` | Negative tests and findings from `brace-mcp-review` are now explicit triggers. Writing tests does not itself authorize execution. |
| 4 | Record these drill results and draft the R05 exception for governance. | `brace-record` | Recording evidence and drafting risk acceptances are explicit responsibilities. |
| 5 | Help build a new weather MCP server. | None | New server implementation is outside all four descriptions. |
| 6 | Does this SDK upgrade actually fix my MCP security concerns? | `brace-mcp-review` | Reviewing MCP security gaps and advisory remediation best matches assessing the upgrade's claimed fix. |
| 7 | Run a BRACE production readiness review. | `brace-review` | Readiness reviews are now an explicit trigger. Record maintenance is explicitly not a code audit. |
| 8 | Explain MCP transport basics. | None | General education does not request an audit, tests, or assessment-record work. |
| 9 | Check whether our gateway can be bypassed via CLI tools. | `brace-mcp-review` | Gateway-boundary security review is explicit; the request does not explicitly ask to write or execute tests. |
| 10 | Install an MCP server from npm. | None | Installation is outside the four workflows; the MCP reviewer does not launch servers. |

## Remaining ambiguities

- **Boundary review versus runtime proof (#9):** “Check whether” may mean code/configuration review or executable bypass testing. `brace-mcp-review` is the best single selection for the stated gateway-security question, but it excludes exploits. An explicit request to write controlled bypass tests would select `brace-tests`; running them needs authorization consistent with its description.
- **Upgrade verification method (#6):** The MCP reviewer fits the security-remediation question. The description alone does not establish whether the user expects static inspection, advisory comparison, or runtime regression evidence. An explicit negative-test deliverable would select `brace-tests`.
- **Mapped-item scope (#3):** `brace-tests` now explicitly accepts MCP-review findings, resolving the earlier source-report ambiguity. It produces evidence for BRACE item IDs, so an unmapped external report may still require identifying the relevant mapping before authoring tests. That is execution context, not a competing discovery route.

## Conclusion

Selections remain `brace-mcp-review` for 1, 6, and 9; `brace-review` for 2 and 7; `brace-tests` for 3; `brace-record` for 4; none for 5, 8, and 10.

The revised descriptions make the full-agent/MCP-only boundary, MCP-report-to-tests handoff, and readiness-review/existing-record-check boundary explicit. The remaining uncertainty is mainly whether requests #6 and #9 intend review findings or active test evidence. This is a discovery check only; no effectiveness qualification was performed.
