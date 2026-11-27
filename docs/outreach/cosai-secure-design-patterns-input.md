# Input to CoSAI's Secure Design Patterns for Agentic Systems: Agent Identity and the Harness Pattern

**Contributor:** The BRACE Project
**Date:** July 2026
**For:** Coalition for Secure AI (CoSAI, under OASIS) — Secure Design Patterns for Agentic Systems workstream; Agentic Identity and Access Management work; MCP Security taxonomy.
**License:** Offered under Creative Commons Attribution 4.0 (CC BY 4.0).

---

## Why this input

CoSAI's *Secure Design Patterns for Agentic Systems* workstream and the *Agentic Identity and Access Management* research are addressing exactly the problems where BRACE has the most concrete, in-production material to offer: **how an autonomous agent gets an identity distinct from its user**, and **the harness pattern that keeps a fallible model from taking an irreversible action on its own**.

BRACE is a vendor-neutral, openly-licensed synthesis of in-production agent-security practice. It is offered as input and prior art — designed to compose with CoSAI's Agentic IAM and MCP Security work, not to replace it. It is not yet validated against a control group; take, adapt, or critique any part.

## Framing: an agent is a runtime configuration

An autonomous agent is not a piece of code; it is a runtime configuration of infrastructure — container, harness, system prompt, tool surface, memory, identity, egress. The weights are largely fixed and shared; the security-relevant variation is how they are wired into a running system. Design patterns for agentic systems should therefore attach to the *configuration*, and the unit of identity and attribution should be the running deployment.

## Pattern 1 — Agent identity, separate from the launching user (for the Agentic IAM work)

When an agent acts, the access-control and audit systems must distinguish "the agent did this" from "the user did this." Collapsing the two destroys attribution and forces over-broad grants. Two concrete recommendations:

**A user-launched agent carries its own identity**, scoped to its own deployment, distinct from the human who started it.

**A minimal set of six identity fields on every agent action:**

1. **Accountable party** — who is answerable for the agent's behavior.
2. **Operational owner** — who runs it day to day.
3. **Tenant** — the customer/organizational boundary it operates within.
4. **Agent-type-id** — a **content hash** over container, harness, system prompt, model, and configuration. Two deployments with the same agent-type-id are, by construction, the same agent; any configuration change changes the id.
5. **Agent-instance-id** — this particular running instance.
6. **Trace context** — standard distributed-tracing context tying actions together across services.

The **content-hashed agent-type-id** is the field we most encourage the Agentic IAM work to adopt: it makes "what exactly was running" a cryptographically verifiable fact rather than a typed label, which is the precondition for both drift detection and credible attribution in machine-speed, agent-spawns-agent environments.

## Pattern 2 — The harness: model proposes, harness disposes

The highest-value design pattern we can offer: the model may *propose* an irreversible action, but a **harness** — code, not the model — decides whether it executes. The harness operates default-deny (the agent gets only what it is explicitly granted), intercepts destructive verbs, and applies the hard limits itself rather than delegating them to another model. A checker model may *narrow* what auto-clears within a limit; it can never *authorize* above it. This pattern is what contains prompt injection and over-broad tool grants regardless of whether the model was fooled.

## Pattern 3 — Tool mediation and the gateway (for the MCP Security work)

Every tool — MCP or otherwise — is both a capability and an untrusted input channel: its output can carry instructions aimed at the model (indirect prompt injection), and its description is text the model reads. Two patterns follow, complementary to CoSAI's MCP Security taxonomy:

- **Route every tool call through a single gateway** that scopes, logs, and can deny each call (deny-except-gateway).
- **Treat all tool/API output and tool descriptions as untrusted** — scan for instruction-like content, quarantine responses as clearly-delimited data, and carry a trust tier so untrusted content can't drive a money-moving decision. Containment (the harness gate, scoped egress) backs this up when detection misses.

## Supporting patterns and observability

Container isolation and resource bounds; capability-scoped access per deployment; memory governance (memory is an injection surface — validate on write, trust-tier on read); a tested kill switch scoped to a deployment and its sub-agents. And three observability primitives, ideally expressed as an open telemetry convention: identity fields on every action, context-size logging, and **sub-agent / parent-prompt provenance** — so the full execution graph of an agent-spawns-agent system is reconstructable after the fact.

## What we can bring to the workstream

- The six-field identity model and content-hashed agent-type-id, developed with the Agentic IAM authors.
- The harness and tool-gateway patterns as documented secure design patterns, with a **runnable reference** (an enterprise agent built naive then hardened one pattern at a time, with tests that assert each pattern actually contains the attack, including indirect injection through MCP-style tool output).

## Reference

> The BRACE Project (2026). *BRACE: A Unified Security Framework for Autonomous AI Agents.* https://braceframework.org

BRACE is vendor-neutral, openly licensed (CC BY 4.0), and designed to compose with — not replace — CoSAI, NIST AI RMF, OWASP, CSA, and MITRE ATLAS. We would welcome the opportunity to contribute further.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
