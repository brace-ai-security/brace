# BRACE and the OWASP MCP Top 10

This page maps each risk in the [OWASP MCP Top 10](https://owasp.org/www-project-mcp-top-10/) to BRACE controls (C1–C9) and items in the [BRACE sign-off checklist](../CHECKLIST.md). It uses the 2025 edition (IDs MCP01:2025 to MCP10:2025), as published in the [project repository](https://github.com/OWASP/www-project-mcp-top-10) (latest commit 29 July 2026, `165fe0f`). The IDs and names were checked on 2026-11-24.

**Status: not final.** The project roadmap says it is in "Phase 3 – Beta Release and Pilot Testing". The owasp.org page labels it a Production Project, but its own roadmap says the list is still in beta. Item names may change.

## How to read this mapping
- **Direct** — passing the listed BRACE items prevents the risk or contains its damage in a deployed agent.
- **Partial** — the listed items reduce the risk or help detect it, but some of it is left to other work.
- **Out of scope** — BRACE doesn't address it; the row says why in a few words.

Item IDs refer to the [checklist](../CHECKLIST.md), most relevant first. An item counts only when its result is Pass. Passing an item is not proof that a risk is gone. Test it with the [verification recipes](../CHECKLIST-VERIFICATION.md). The [MCP gateway guide](https://braceframework.org/guides/mcp-gateway/) shows how many of these items apply to MCP.

## Summary

| Coverage | Risks |
|---|---|
| Direct | 6 |
| Partial | 4 |
| Out of scope | 0 |
| **Total** | **10** |

## Mapping

| OWASP ID | Risk | Coverage | BRACE controls | BRACE items | How BRACE addresses it |
|---|---|---|---|---|---|
| MCP01:2025 | Token Mismanagement & Secret Exposure | Direct | C2, C5, C9 | B03, B02, R03, E11, B12 | Tokens are short-lived, narrow, and kept out of config. R03 keeps secrets out of outputs and logs, and E11 protects shared evidence. |
| MCP02:2025 | Privilege Escalation via Scope Creep | Direct | C2, C4 | B02, B01, E08, C02, C04, E06 | Each token has only the scopes the task needs. Scope changes go through change review (C02), and drift checks (C04) catch permissions that grow over time. |
| MCP03:2025 | Tool Poisoning | Direct | C5 | E04, E03, E05, R01, R02 | Tool descriptions are inspected, re-checked on every load, and namespaced. Tool output is treated as untrusted input. |
| MCP04:2025 | Software Supply Chain Attacks & Dependency Tampering | Direct | C3, C5 | E02, B10, C05, C01, E03 | MCP servers and their packages are vetted, pinned, and listed in the release manifest. Changes trigger review and re-tests. |
| MCP05:2025 | Command Injection & Execution | Partial | C3, C4, C5 | R01, B11, B01, B05, B08 | Input is checked at each boundary, and tools run in a minimal, isolated runtime. BRACE does not review the MCP server's own code for injection bugs. That is the server author's job. |
| MCP06:2025 | Intent Flow Subversion | Partial | C5, C4 | R02, R01, B05, B06, R09 | BRACE assumes some injected context will work. R02 tests that harm is still blocked, and B05 and B06 stop destructive actions. It can't stop the model from being steered. |
| MCP07:2025 | Insufficient Authentication & Authorization | Direct | C2, C1 | E06, A01, B02, E05, E07, A04 | Every MCP call passes an authenticating gateway that checks the agent's own identity and scopes. Servers and peers are verified. |
| MCP08:2025 | Lack of Audit and Telemetry | Direct | C9, C7 | R13, E10, A04, C08, R08, E11 | Every tool call, decision, and result is recorded, across service boundaries, in a record the agent can't change. |
| MCP09:2025 | Shadow MCP Servers | Partial | C1, C4 | E06, B09, C01, E01, B01 | The gateway and egress allowlist block calls to MCP servers that aren't approved, and the manifest lists approved ones. BRACE checks one agent at a time. It does not search the organization for unknown servers. |
| MCP10:2025 | Context Injection & Over-Sharing | Partial | C6, C5 | R05, R03, B02, R04, R06 | Memory is split by tenant, agent type, and instance, and outputs are checked for leaks. R05 and R06 are Detection items. BRACE has no rule for trimming what context is sent to each tool. |

## Gaps

- **Server code quality.** BRACE contains the damage from a buggy MCP server but does not test the server's code (MCP05).
- **Steering the model.** BRACE limits what injected context can make the agent do. It does not stop the model from being misled (MCP06).
- **Finding unknown servers.** BRACE blocks unapproved servers for a reviewed agent. Finding MCP servers that no one has reported is organization-wide work (MCP09).
- **Context minimization.** BRACE isolates memory but does not limit how much context is shared with each tool call (MCP10).
- **Detection items.** MCP10 relies partly on Detection items (R05, R06), which are required only at higher stakes and autonomy ratings.

## Limits

- This mapping is BRACE's judgment. OWASP has not reviewed or endorsed it.
- The OWASP list is in beta. Recheck this mapping when OWASP publishes a final or new edition. Last checked 2026-11-24.
- The project's sources disagree on the name of MCP06. The repository's index page and item file call it "Intent Flow Subversion". The README and the owasp.org list heading call it "Prompt Injection via Contextual Payloads". This page uses the index page name.
- Only items with a Pass result count. A Gap, an accepted risk, or an N/A gives no coverage.

---
*Part of [BRACE](../README.md), a security framework for autonomous AI agents. CC BY 4.0.*
