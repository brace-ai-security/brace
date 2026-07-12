# Response to NIST CAISI Request for Information on Securing AI Agent Systems

> **STATUS (2026-07-12): NOT SUBMITTED — RFI CLOSED.** The CAISI RFI (docket NIST-2025-0035)
> closed **2026-03-09** (937 comments received) and was not submitted to in time. This draft is
> retained as source material. It has been retargeted to live channels — see sibling files
> `csa-agentic-control-plane-contribution.md`, `owasp-agentic-security-contribution.md`, and
> `cosai-secure-design-patterns-input.md`. The ongoing successor channel is CAISI's AI Agent
> Standards Initiative + sector listening sessions (caisi-events@nist.gov).

**Respondent:** The BRACE Project
**Date:** [DATE]
**Subject:** Response to the NIST Center for AI Standards and Innovation (CAISI) Request for Information on Securing AI Agent Systems (issued January 2026)
**License:** This response and the framework it references are offered under Creative Commons Attribution 4.0 (CC BY 4.0).

---

## Executive Summary

A standard for securing AI agent systems should specify controls at *agent-deployment granularity* and require a small set of *observability primitives*. Today's most-cited frameworks operate at the wrong altitude for this: the NIST AI Risk Management Framework is governance-level, and OWASP and MITRE ATLAS are threat catalogs. Each is valuable, but none names the concrete, testable control layer that an operator must implement to deploy an agent safely. The gap is the layer in between governance intent and an enumerated threat: the set of controls you can point at, configure, and verify on a running agent. This response offers BRACE — a vendor-neutral, openly licensed synthesis of in-production agent-security practice — as prior art and input toward filling that gap. BRACE is not yet validated against a control group; it is submitted as a starting point, not a finished answer.

---

## 1. Threat Model: An Agent Is a Runtime Configuration

The central observation behind our recommendation is that an autonomous AI agent is not a piece of code. It is a runtime configuration of infrastructure: a container, a harness, a system prompt, a tool surface, a memory store, an identity, and a network egress path. The model weights are largely fixed and shared; the security-relevant variation lives in how those weights are wired into a running system. A standard that treats "the agent" as a monolithic application will miss the surface area that actually matters.

This framing yields a clean split of the threat space into two cases:

- **Hijacked-or-misused agents.** The agent does something it was not intended to do because an attacker (or a careless user) drives it there — for example, through prompt injection delivered via tool output, or through over-broad tool grants exploited by a third party. The agent's behavior is wrong relative to its operator's intent.
- **Misaligned agents.** The agent does something harmful while pursuing what it "believes" to be its assigned objective — a goal-directed failure rather than an external compromise.

These two cases call for different controls. Hijack/misuse is contained primarily by constraining the configuration (tool scope, egress, destructive-action gating) and by attribution. Misalignment is detected primarily by observing behavior over time. A standard should name controls for both and should not assume that perimeter hardening alone addresses the misaligned case.

---

## 2. Recommended Technical Controls

We recommend that the standard enumerate concrete controls rather than stop at outcomes. BRACE proposes nine, organized so that each is independently testable on a deployed agent:

1. **Architecture.** Define the agent's components and trust boundaries explicitly — what is inside the configuration, what it can reach, and where the boundaries sit.
2. **Capability-scoped API access.** Grant tools and API scopes per agent deployment on a least-privilege basis, not per user or per organization.
3. **Container.** Run the agent in an isolated, resource-bounded execution environment.
4. **Harness.** Mediate the agent's actions through a harness that intercepts destructive verbs and operates default-deny — the agent gets only what it is explicitly granted.
5. **Data.** Govern what data the agent can read and write, and classify it at the boundary.
6. **Memory.** Control what persists across runs, how it is written, and how it is trusted on read-back (memory is an injection surface).
7. **Behavioral.** Monitor the agent's actions against expected behavior to surface drift and misalignment.
8. **Kill Switch.** Provide a reliable, fast way to stop a specific agent deployment.
9. **Audit Trail.** Record a complete, replayable record of what the agent did.

These are deliberately stated as controls an auditor could check for, not as principles. We suggest the standard preserve that property: each named control should be something an assessor can confirm is present and functioning.

---

## 3. Identity and Access

Agent identity is foundational and is currently under-specified across the field. Two points deserve standardization.

First, **agent identity must be separate from the launching user.** When an agent acts, the audit and access-control system must be able to distinguish "the agent did this" from "the user did this." Collapsing the two destroys attribution and forces over-broad grants. A user-launched agent should carry its own identity, scoped to its own deployment.

Second, we recommend a **minimal set of six required identity fields** on every agent action:

1. **Accountable party** — the entity answerable for the agent's behavior.
2. **Operational owner** — the team or person running it day to day.
3. **Tenant** — the customer or organizational boundary it operates within.
4. **Agent-type-id** — a content hash computed over the container, harness, system prompt, model, and configuration. Two deployments with the same agent-type-id are, by construction, the same agent; any change to the configuration changes the id. This makes "what exactly was running" a verifiable fact rather than a label someone typed.
5. **Agent-instance-id** — the identity of this particular running instance.
6. **Trace context** — the standard distributed-tracing context that ties actions together across services.

The content-hashed agent-type-id is the field we most encourage the standard to adopt. It turns agent identity into something cryptographically tied to the actual configuration, which is what the threat model in Section 1 says actually matters.

---

## 4. Observability and Auditability

Controls you cannot observe are controls you cannot assess. We recommend the standard require a small, fixed set of observability primitives — three requirements, chosen to be cheap to emit and high in forensic value:

- **T1 — Required identity fields.** Emit the six fields from Section 3 on every agent action.
- **T2 — Context-size logging.** Log the size of the context window in use over time. Context growth is a leading indicator of injected content, memory bloat, and runaway loops, and it is nearly free to record.
- **T3 — Sub-agent and parent-prompt provenance.** When an agent spawns a sub-agent, record the parent-child relationship and the prompt that launched the child. Multi-agent systems are otherwise unauditable.

Together with control 9 (Audit Trail), these support a **full-execution-graph audit trail**: a record from which the entire tree of agent and sub-agent actions — who launched whom, with what prompt, under what identity, against what tools — can be reconstructed after the fact. We suggest the standard treat the execution graph, not the single agent log line, as the unit of auditability for multi-agent deployments.

We also encourage the standard to express these primitives in terms of an open telemetry convention (for example, a set of OpenTelemetry attributes) so that conformance is portable across vendors rather than tied to one platform.

---

## 5. Measurement and Conformance

Operators cannot adopt twenty controls at once, and a standard that demands all-or-nothing conformance will be ignored. We recommend two patterns.

First, a **tiered adoption order** that front-loads the controls with the highest damage-prevention and attribution value. BRACE proposes three tiers:

- **Tier 1 — Prevent damage and establish attribution.** Harness (C4), capability-scoped access (C2), kill switch (C8), audit trail (C9), and required identity fields (T1). This tier alone stops the most common high-severity failures and makes every action attributable.
- **Tier 2 — Harden the substrate.** Architecture (C1), container (C3), data controls (C5), and context-size logging (T2).
- **Tier 3 — Active detection.** Behavioral monitoring (C7), memory controls (C6), and sub-agent/parent-prompt provenance (T3).

A standard can use this ordering to define conformance levels, so that an operator can claim Tier 1 conformance honestly and have a defined path to Tier 2 and Tier 3.

Second, a **sign-off gate** as a conformance pattern: before an agent deployment goes to production, an accountable party signs off that the required controls for its tier are present and functioning. This is a familiar, auditable pattern (it mirrors change-management gates) and it produces an artifact an assessor can check.

---

## 6. What to Avoid

We respectfully urge the standard to avoid stopping at governance language. There is a strong pull, in standards work, toward outcome statements — "agents shall be deployed securely," "organizations shall manage agent risk" — that are unobjectionable and unimplementable. The field already has governance-level guidance (NIST AI RMF) and already has threat catalogs (OWASP Top 10 for Agentic Applications, MITRE ATLAS). What it lacks is the concrete, testable control layer in between. A securing-AI-agents standard that does not name specific controls, specific identity fields, and specific observability primitives will reproduce the existing gap rather than close it.

The corollary: every requirement should be something an assessor can test. If a clause cannot be turned into a check against a running agent, it belongs in governance guidance, not in this standard.

---

## Note on BRACE

BRACE (Build-time, Run-time, Agent, Configuration, Ecosystem) is offered here as input and prior art, not as a proposed standard in itself. It is vendor-neutral and openly licensed (CC BY 4.0). It maps to the OWASP Top 10 for Agentic Applications (ASI01–ASI10) and to MITRE ATLAS, and it is designed to *compose with* — not replace — OWASP, NIST, and MITRE. It is a synthesis of in-production practice and has not yet been independently validated against a control group. CAISI and the community are free to take, adapt, critique, or discard any part of it.

The framework is described in full in:

> The BRACE Project (2026). *BRACE: A Unified Security Framework for Autonomous AI Agents.* https://github.com/brace-ai-security/brace

We would welcome the opportunity to provide further detail on any of the above.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
