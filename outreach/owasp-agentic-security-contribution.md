# Contribution to the OWASP Agentic Security Initiative: A Detect / Contain / Trace Control Layer for the Top 10 for Agentic Applications

**Contributor:** The BRACE Project
**Date:** July 2026
**For:** OWASP GenAI Security Project — Agentic Security Initiative (Top 10 for Agentic Applications, Agentic Security Solutions Landscape, reference applications).
**License:** Offered under Creative Commons Attribution 4.0 (CC BY 4.0).

---

## Why this contribution

The *OWASP Top 10 for Agentic Applications (2026)* is the field's reference catalog of agentic risks (ASI01–ASI10). A risk catalog answers "what can go wrong." The question operators ask next is "what do I build, and how do I prove it works" — the concrete, testable control layer that **detects, contains, and traces** each of those risks on a running agent.

BRACE is a vendor-neutral, openly-licensed synthesis of in-production agent-security practice pitched at exactly that layer. It is offered as a contribution to the Agentic Security Initiative — designed to *compose with* the Top 10, mapping controls onto ASI01–ASI10, not to restate the risks. BRACE is not yet validated against a control group; take, adapt, or critique any part.

## The framing: an agent is a runtime configuration

An autonomous agent is not a piece of code — it is a runtime configuration of infrastructure (container, harness, system prompt, tool surface, memory, identity, egress). The weights are largely fixed; the security-relevant variation is how they are wired into a running system. Two failure classes follow: **hijacked/misused** agents (contained by constraining the configuration and by attribution) and **misaligned** agents (detected by observing behavior over time). The Top 10 spans both; a control layer should too.

## What BRACE contributes: detect / contain / trace per risk

BRACE maps to ASI01–ASI10 and, for each risk, names the controls that do three distinct jobs:

- **Detect** — an event fires when the attack is attempted (e.g., instruction-like content in tool/API output is flagged; a blocked destructive action raises an event).
- **Contain** — the harm is bounded even if detection misses it (destructive-action gate; capability-scoped tools; default-deny egress; channel separation / quarantine of untrusted content; trust tiers on retrieval and memory).
- **Trace** — every action carries identity, so the attempt is attributable and reviewable after the fact (six identity fields + a content-hashed agent-type-id).

The core controls (each independently testable on a deployed agent): **architecture**, **capability-scoped API access**, **container isolation**, **harness** (model proposes, harness disposes; default-deny; destructive-verb interception), **data** controls, **memory** governance (memory is an injection surface), **behavioral** monitoring, **kill switch**, and **audit trail** — plus three observability primitives: identity fields on every action, context-size logging, and sub-agent/parent-prompt provenance.

The single primitive we most encourage the Initiative to promote is the **content-hashed agent-type-id** (a hash over container + harness + system prompt + model + config). It makes "what exactly was running" a verifiable fact and is what turns detection events into attributable, reviewable evidence.

## A candidate reference application

The Initiative already ships a reference app (the FinBot CTF). BRACE comes with a comparable, openly-licensed artifact the Initiative is welcome to use: **"Butler,"** an enterprise customer-operations agent built deliberately naive and then hardened one control at a time. It includes:

- a suite that stages **each OWASP agentic vector** against the agent and shows the detect / contain / trace evidence it produces;
- live exploit probes (the same attack succeeds without the controls and is contained with them) — an unauthorized refund via prompt injection, a cross-tenant data dump via an over-privileged tool, indirect prompt injection via a poisoned tool/API response;
- ports of the controls onto multiple agent frameworks (LangChain/LangGraph, plus minimalist and enterprise SDKs), demonstrating the controls are framework-portable — potentially useful for the *Agentic Security Solutions Landscape*.

## What we can bring to the working group

- The BRACE↔ASI01–ASI10 mapping (the "contain each risk" control layer), developed with the Initiative.
- The runnable per-vector detect/contain/trace examples as candidate reference material.
- Review input on future Top 10 updates and Solutions-Landscape entries.

## Reference

> The BRACE Project (2026). *BRACE: A Unified Security Framework for Autonomous AI Agents.* https://braceframework.org

BRACE is vendor-neutral, openly licensed (CC BY 4.0), and designed to compose with — not replace — OWASP, NIST AI RMF, CSA, and MITRE ATLAS. We would welcome the opportunity to contribute further.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
