# Contribution to CSA Agentic AI Research: An Operator-Testable Control Layer for the Agentic Control Plane

**Contributor:** The BRACE Project
**Date:** July 2026
**For:** Cloud Security Alliance — AI Safety / AI Controls working groups; peer review of *Securing the Agentic Control Plane*, *Operationalizing the Agentic Control Plane: Integrating the Agentic Trust Framework*, and related agentic work.
**License:** This contribution and the framework it references are offered under Creative Commons Attribution 4.0 (CC BY 4.0).

---

## Why this contribution

CSA's Agentic Trust Framework (ATF) and the Agentic Control Plane work define *what* a secure agentic deployment must achieve across five pillars — Identity, Behavior, Data Governance, Segmentation, and Incident Response — and the Tool Gateway establishes the deny-except-gateway egress pattern. What operators still ask for, repeatedly, is the layer just below that: the concrete, individually-testable controls they configure and verify on a *running* agent to satisfy those pillars.

BRACE is a vendor-neutral, openly-licensed synthesis of in-production agent-security practice that sits at exactly that altitude. It is offered here as prior art and peer-review input — designed to *operationalize* ATF, not to compete with it. BRACE is not yet validated against a control group; take, adapt, critique, or discard any part of it.

## The framing BRACE adds: an agent is a runtime configuration

An autonomous agent is not a piece of code. It is a runtime configuration of infrastructure — a container, a harness, a system prompt, a tool surface, a memory store, an identity, and a network egress path. The weights are largely fixed and shared; the security-relevant variation lives in how they are wired into a running system. This is why controls belong at *agent-deployment granularity*, and why the unit of assessment is the running configuration, not "the application."

It splits the threat space cleanly: **hijacked/misused** agents are contained by constraining the configuration (tool scope, egress, destructive-action gating) and by attribution; **misaligned** agents are detected by observing behavior over time. The control plane needs both — perimeter hardening alone does not address the misaligned case.

## Mapping BRACE controls to the ATF five pillars

BRACE proposes controls that are each independently testable on a deployed agent. They line up under the ATF pillars as follows:

| ATF pillar | BRACE controls that operationalize it |
|---|---|
| **Identity** | Agent identity separate from the launching user; six required identity fields; a **content-hashed agent-type-id** (hash over container + harness + system prompt + model + config) |
| **Behavior** | The **harness** (model proposes, harness disposes; default-deny; destructive-verb interception); behavioral monitoring for drift/misalignment; tested kill switch |
| **Data Governance** | Data classification at the boundary; memory governance (write-validation + trust-on-read, since memory is an injection surface); retrieval/corpus trust tiers |
| **Segmentation** | Capability-scoped API access per deployment (not per user/org); container isolation; default-deny egress — the Tool-Gateway pattern made per-tool testable |
| **Incident Response** | Full-execution-graph audit trail; kill switch; the observability primitives below |

The one addition we most encourage the control-plane work to adopt is the **content-hashed agent-type-id**. It turns "what exactly was running" into a cryptographically verifiable fact rather than a typed label: two deployments with the same type-id are, by construction, the same agent, and any config change changes the id. That is the primitive that makes drift detection and after-the-fact attribution possible.

## Observability primitives (cheap to emit, high forensic value)

Controls you cannot observe are controls you cannot assess. We recommend three primitives, ideally expressed as an open telemetry convention (e.g., OpenTelemetry attributes) so conformance is portable across vendors:

- **T1 — Identity fields** on every agent action (the six fields above).
- **T2 — Context-size logging** over time — a near-free leading indicator of injection, memory bloat, and runaway loops.
- **T3 — Sub-agent / parent-prompt provenance** — record who launched whom, with what prompt; multi-agent systems are otherwise unauditable.

Together these support treating the **execution graph**, not the single log line, as the unit of auditability for multi-agent deployments.

## Adoption order and conformance

Operators cannot adopt everything at once. BRACE proposes a tiered order the control-plane work could use to define conformance levels:

- **Tier 1 — prevent damage, establish attribution:** harness, capability-scoped access, kill switch, audit trail, identity fields.
- **Tier 2 — harden the substrate:** architecture, container, data controls, context-size logging.
- **Tier 3 — active detection:** behavioral monitoring, memory controls, sub-agent provenance.

Paired with a **sign-off gate** (an accountable party attests the required controls for the tier are present and functioning before production) — a familiar, auditable change-management pattern that yields an artifact an assessor can check.

## What we can bring to the working group

- The BRACE↔ATF mapping above, developed further with the pillar leads.
- A **runnable reference implementation**: an enterprise agent ("Butler") built naive and hardened one control at a time, with each control as a diffable change and a test suite that asserts the control actually contains the attack (prompt injection, over-privileged tools, cross-tenant leakage, indirect injection via tool output). Useful as concrete evidence for "testable on a running agent."
- Peer-review commentary on the in-flight *Securing the Agentic Control Plane* and *Integrating the ATF* documents.

## Reference

> The BRACE Project (2026). *BRACE: A Unified Security Framework for Autonomous AI Agents.* https://braceframework.org

BRACE is vendor-neutral, openly licensed (CC BY 4.0), and designed to compose with — not replace — CSA ATF/MAESTRO, NIST AI RMF, OWASP, and MITRE ATLAS. We would welcome the opportunity to contribute further.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
