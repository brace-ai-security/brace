# Proposal: a controls layer for the OWASP Top 10 for Agentic Applications

> **Historical outreach draft — source review 2026-09-16:** Do not use its novelty, vendor-coverage, or incident-count claims as current evidence. See [SOURCE-REVIEW.md](../SOURCE-REVIEW.md), the [current checklist](../CHECKLIST.md), and [current telemetry proposal](../otel-conventions.md) before adapting this draft.

**To:** OWASP GenAI Security Project — Agentic Security Initiative
**From:** The BRACE Project
**Re:** Adopting a concrete, testable controls layer that maps to the Agentic Top 10
**License:** the framework referenced here (BRACE) is released under CC BY 4.0 and is offered as open input.

---

## Summary

The OWASP Top 10 for Agentic Applications (2026) is the field's reference list of what can go wrong with autonomous agents. By design, it is a **threat catalog**: it names the ten risks ([ASI01–ASI10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)) and discusses mitigations at a general level. It does not specify a concrete control architecture, and the accompanying threats-and-mitigations material stops short of a testable, build-it checklist.

That leaves a recurring question for the engineers who adopt the list: *given these risks, what exactly do I build, and in what order?*

This proposal suggests publishing a **controls layer** as a companion to the Agentic Top 10 — a set of concrete, vendor-neutral controls, each mapped to the ASI risks it mitigates. I offer **BRACE** (a control framework for autonomous agents, CC BY 4.0) as a ready candidate or starting point. The aim is not to introduce a competing list; it is to give the existing Top 10 an actionable other half.

## The gap this fills

A threat catalog and a control framework answer different questions:

- **The Top 10 answers:** what are the most important risks? (Goal hijack, tool misuse, identity abuse, …)
- **A controls layer answers:** what do I configure, and what do I log, to contain those risks — and which do I do first?

Teams already use the Top 10 to scope risk. The common next step — translating each ASI risk into specific configuration and telemetry — is currently left to each team to reinvent. A shared controls layer would make that step reproducible and reviewable.

## What the controls layer would contain

BRACE organizes the agent's *runtime configuration* — container, harness, system prompt, tool surface, memory, identity, network egress — into **nine controls** and **three observability requirements**:

- **Build-time:** Architecture, Capability-scoped API access, Container, Harness (including destructive-verb interception).
- **Run-time:** Data (input validation), Memory (scoping and provenance), Behavioral (security-anomaly monitoring).
- **Closure:** Kill Switch, Audit Trail.
- **Observability:** required identity fields (T1), context-size logging (T2), sub-agent and parent-prompt provenance (T3).

Each is specified at agent-deployment granularity and is testable (you can check whether a deployment has it).

## Mapping to the Agentic Top 10

| OWASP risk | Primary BRACE controls |
|------------|------------------------|
| [ASI01 Agent Goal Hijack](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Harness (system prompt as a frozen, reviewed artifact); Data (input validation) |
| [ASI02 Tool Misuse and Exploitation](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Harness (tool allowlist, destructive-verb interception); Capability-scoped API access |
| [ASI03 Identity and Privilege Abuse](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Required identity fields (T1); Capability-scoped API access; agent identity separate from the user |
| [ASI04 Agentic Supply Chain Vulnerabilities](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Container (signed, minimal); Harness (tool allowlist); IaC drift detection |
| [ASI05 Unexpected Code Execution (RCE)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Container (minimal, kernel-isolated); Architecture (egress) |
| [ASI06 Memory and Context Poisoning](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Memory (scoping, write validation, provenance); Data |
| [ASI07 Insecure Inter-Agent Communication](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Required identity fields (T1); Sub-agent and parent-prompt provenance (T3) |
| [ASI08 Cascading Failures](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Sub-agent provenance (T3); Kill Switch (recursive to sub-agents) |
| [ASI09 Human-Agent Trust Exploitation](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Harness (system prompt); Behavioral monitoring |
| [ASI10 Rogue Agents](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Behavioral monitoring; Kill Switch; Required identity fields |

Every ASI risk maps to at least two controls; most map to more. The same mapping inverts usefully: for any control a team skips, it names which ASI risks lose their primary mitigation — a ready input to a risk register.

## Why this fits OWASP

- **It composes with the Top 10 rather than competing.** The list stays the canonical risk catalog; the controls layer is the build-and-verify companion many adopters already ask for.
- **It's actionable for engineers.** A sign-off checklist covering all five BRACE aspects, with verification recipes and operational tradeoffs, and a tiered adoption order (ship Tier 1 first) turn the Top 10 from an awareness artifact into a deployment gate.
- **It's vendor-neutral and openly licensed.** BRACE is CC BY 4.0, maps to MITRE ATLAS as well, and names where each cloud and open-source ecosystem currently falls short.

## The ask

One or more of the following, whichever the initiative prefers:

1. **Co-develop a "controls and mitigations" companion** to the Agentic Top 10, using the ASI→control mapping above as a starting point.
2. **Fold the control mappings into the existing threats-and-mitigations document**, so each ASI entry points to concrete, testable controls.
3. **Adopt the sign-off checklist** as a community artifact under OWASP, revised by the working group.

## Honest framing

BRACE is a synthesis of in-production practice, not a validated standard. It is offered as prior art and a concrete starting point — to be revised, renamed, or partly adopted by the OWASP community as the working group sees fit. The goal is a shared, actionable controls layer under the list that already has the field's trust; whose name is on it matters less than that it exists.

---

*Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.*
