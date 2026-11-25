# BRACE and the OWASP Top 10 for Agentic Applications

This page maps each risk in the [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) to BRACE controls (C1–C9) and items in the [BRACE sign-off checklist](../CHECKLIST.md). The list comes from the OWASP GenAI Security Project. Its resource page gives a release date of 9 December 2025. The IDs and names below were copied from the [official list page](https://genai.owasp.org/top-10-for-agentic-applications-2026/) on 2026-11-24.

## How to read this mapping
- **Direct** — passing the listed BRACE items prevents the risk or contains its damage in a deployed agent.
- **Partial** — the listed items reduce the risk or help detect it, but some of it is left to other work.
- **Out of scope** — BRACE doesn't address it; the row says why in a few words.

Item IDs refer to the [checklist](../CHECKLIST.md), most relevant first. An item counts only when its result is Pass. Passing an item is not proof that a risk is gone. Test it with the [verification recipes](../CHECKLIST-VERIFICATION.md).

## Summary

| Coverage | Risks |
|---|---|
| Direct | 4 |
| Partial | 6 |
| Out of scope | 0 |
| **Total** | **10** |

## Mapping

| OWASP ID | Risk | Coverage | BRACE controls | BRACE items | How BRACE addresses it |
|---|---|---|---|---|---|
| [ASI01](https://genai.owasp.org/agentic-applications-2026/asi01-agent-goal-hijack/) | Agent Goal Hijack | Partial | C5, C4, C7 | R02, R01, B05, B06, R09, B12 | BRACE assumes some injections will work. R02 tests that a hijacked goal still can't cause harm, and B05 and B06 stop destructive actions without approval. It can't stop the model from being steered in the first place. |
| [ASI02](https://genai.owasp.org/agentic-applications-2026/asi02-tool-misuse-and-exploitation/) | Tool Misuse and Exploitation | Direct | C4, C5 | B01, B05, B07, E06, E04, E05, R09 | The harness allows only needed tools and arguments, sets budgets, and blocks destructive calls. The gateway enforces the same rules at the boundary. R09 catches misuse spread across allowed steps. |
| [ASI03](https://genai.owasp.org/agentic-applications-2026/asi03-identity-and-privilege-abuse/) | Identity and Privilege Abuse | Direct | C2 | A01, B02, B03, B04, E08, A04, E06 | Each agent has its own identity and short-lived, narrow tokens. E08 stops delegated authority from growing as it passes between agents. B04 can cut off the agent without cutting off its user. |
| [ASI04](https://genai.owasp.org/agentic-applications-2026/asi04-agentic-supply-chain-vulnerabilities/) | Agentic Supply Chain Vulnerabilities | Direct | C3, C5 | E02, E03, E05, B10, C05, C01, E04 | Dependencies, images, models, and tools are vetted, pinned, and listed in the release manifest. Tools are re-checked each time they load, so a changed tool is caught. |
| [ASI05](https://genai.owasp.org/agentic-applications-2026/asi05-unexpected-code-execution-rce/) | Unexpected Code Execution (RCE) | Direct | C3, C1, C4 | B11, B08, B09, B01, B05, R01 | Code runs in a minimal, isolated runtime, with a stronger sandbox for untrusted code. Network limits keep a breakout from reaching much. BRACE does not find bugs in the code itself. |
| [ASI06](https://genai.owasp.org/agentic-applications-2026/asi06-memory-context-poisoning/) | Memory & Context Poisoning | Partial | C6, C5 | R05, R06, R04, R02 | Memory is split by tenant and agent, writes are checked, and each entry records where it came from. R05 and R06 are Detection items, required only at higher stakes. Checks on writes can't spot every poisoned fact. |
| [ASI07](https://genai.owasp.org/agentic-applications-2026/asi07-insecure-inter-agent-communication/) | Insecure Inter-Agent Communication | Partial | C2, C5, C9 | E07, E06, A04, E10, E08 | Messages from peer agents are treated as untrusted and sent through an authenticating gateway, and the audit trail follows calls across services. BRACE does not set a message protocol, encryption, or replay rules. |
| [ASI08](https://genai.owasp.org/agentic-applications-2026/asi08-cascading-failures/) | Cascading Failures | Partial | C8, C4, C7 | E09, B07, R11, R12, E12, C07 | Budgets cap runaway work, and a tested kill switch stops an agent and all its sub-agents in a safe state. Fleet response and rollback limit spread. BRACE does not test how errors flow through a whole multi-agent system. |
| [ASI09](https://genai.owasp.org/agentic-applications-2026/asi09-human-agent-trust-exploitation/) | Human-Agent Trust Exploitation | Partial | C4 | B06, B05 | Approvals show the reviewer the exact action, so a persuasive summary can't hide it. BRACE does not measure over-trust, social engineering of users, or how the agent presents itself. |
| [ASI10](https://genai.owasp.org/agentic-applications-2026/asi10-rogue-agents/) | Rogue Agents | Partial | C7, C8, C1–C9 | R10, R08, R09, R11, E09, C03, C04, A05 | BRACE watches for misaligned behavior and drift, and can stop a rogue agent and its sub-agents. Isolation and least privilege limit the damage. R08–R10 are Detection items, and no check proves an agent is aligned. |

## Gaps

- **Steering the model.** BRACE limits what a hijacked or rogue agent can do. It does not stop the model from being misled (ASI01, ASI10).
- **Inter-agent protocol security.** BRACE has no rule for message signing, encryption, or replay protection between agents (ASI07).
- **System-wide failure testing.** BRACE stops and rolls back agents but does not test how one fault spreads through many agents (ASI08).
- **Human factors.** BRACE does not cover user training, over-reliance, or deceptive agent output beyond the approval screen (ASI09).
- **Detection items.** Several rows depend on Detection items (R05, R06, R08–R10, E12). These are required only at higher stakes and autonomy ratings. At lower ratings those rows give less protection.

## Limits

- This mapping is BRACE's judgment. OWASP has not reviewed or endorsed it.
- Each OWASP risk covers many attack paths. "Direct" means BRACE addresses the main paths for one deployed agent. It does not mean every example in the OWASP text is blocked.
- Only items with a Pass result count. A Gap, an accepted risk, or an N/A gives no coverage.
- The OWASP mitigation lists for each risk are not mapped one by one.
- Recheck this mapping when OWASP publishes a new edition. Last checked 2026-11-24.

---
*Part of [BRACE](../README.md), a security framework for autonomous AI agents. CC BY 4.0.*
