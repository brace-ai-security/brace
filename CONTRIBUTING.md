# Contributing to BRACE

BRACE (Build-time, Run-time, Agent, Configuration, Ecosystem) is a vendor-neutral technical control framework for autonomous AI agents. Contributions are welcome. This guide explains how to propose changes and what kinds of contributions are most useful.

## Scope

BRACE is a **technical control framework**, not a governance or compliance framework. It names concrete, testable controls for deploying agents safely — it does not define organizational policy, risk appetite, or audit programs.

BRACE **composes with** OWASP, NIST, and MITRE; it does not replace them. The OWASP Top 10 for Agentic Applications and MITRE ATLAS describe threats; the NIST AI RMF describes governance; BRACE describes the control layer in between. Contributions that strengthen these mappings are especially valuable. Contributions that turn BRACE into a governance or compliance standard are out of scope.

## Propose a change to a control

The nine controls (C1 Architecture, C2 Capability-scoped API access, C3 Container, C4 Harness, C5 Data, C6 Memory, C7 Behavioral, C8 Kill Switch, C9 Audit Trail) are the core of the framework, so changes go through two steps:

1. **Open an issue** describing the change and why it matters. State which control is affected, what the current text says, and what you propose instead. Discussion happens on the issue.
2. **Open a pull request** once there is rough agreement on the issue. Reference the issue number. Keep the diff focused on the one control.

This two-step flow keeps control changes deliberate. Please do not open a PR that rewrites a control without a prior issue.

## Identifier and linking style

BRACE uses separate namespaces for checklist items (`B05`, `R01`, `A03`, `C01`, `E06`), release gates (`G1`–`G3`), controls (`C1`–`C9`), and observability requirements (`Obs-T1`–`Obs-T3`). Treat these as stable identifiers: do not renumber them merely because the presentation order changes. In particular, `C01` is a Configuration checklist item, while `C1` is the Architecture control.

When using an identifier defined by another organization, link the identifier itself to its authoritative definition on first use in each document or self-contained section. Examples include [ASI01](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), [RFC 7009](https://www.rfc-editor.org/info/rfc7009/), and [ISO/IEC 42001](https://www.iso.org/standard/81230.html). Prefer the standards body, publisher, or official registry over a secondary explanation. Do not format an external identifier as though it were part of a BRACE namespace.

## Report a real-world incident

BRACE is grounded in things that have actually happened to deployed agents. If you know of a real incident, please add it to the corpus by opening an issue using this template:

```
**What happened:** A short, factual description of the incident.
**Which control applies:** Which BRACE control (C1–C9) or observability
  requirement (T1–T3) would have prevented or contained it, and how.
**Source link:** A public, durable link — a writeup, advisory, postmortem,
  or news report. First-hand reports are welcome; please say so.
```

Keep it factual. We are building a corpus, not a blog.

## Map a vendor product to controls

The vendor worksheet describes the evidence needed to assess support for BRACE controls. To add or correct an entry, open a PR (or an issue, if you'd rather discuss first) with:

- The vendor and product name.
- The control(s) (C1–C9) it addresses.
- A one-line note on *how* it addresses each, with a link to the product's documentation.

Mappings must be vendor-neutral in spirit: we map what a product does, we do not endorse it. Please disclose any affiliation with a vendor you are mapping.

## Suggest OpenTelemetry attribute refinements

The three observability requirements (T1 identity fields, T2 context-size logging, T3 sub-agent and parent-prompt provenance) are expressed as proposed OpenTelemetry attributes so that conformance is portable across vendors. To refine them, open an issue with:

- The attribute name(s) you'd change, add, or remove.
- How it aligns with OpenTelemetry semantic-convention practice.
- What it lets an operator observe that the current set does not.

Alignment with existing OpenTelemetry conventions is preferred over inventing new shapes.

## Licensing

By contributing, you agree that your contribution is accepted under **Creative Commons Attribution 4.0 (CC BY 4.0)**, the same license as the rest of the project. You retain attribution; the work stays openly reusable.

## Status

For context: BRACE is a synthesis of agent-security practice already in production. It has not yet been validated against a control group. Contributions that move it toward validation — real incidents, real mappings, real-world deployment experience — are the most valuable kind.

The current requirements are in the [sign-off checklist](CHECKLIST.md). See the [source review](SOURCE-REVIEW.md) for supporting evidence and its limits.

## Code of conduct

Be kind and assume good faith. We're here to make agent deployments safer, which is a shared goal. Critique ideas, not people; keep discussion concrete; help newcomers. Behavior that makes the project unwelcoming isn't tolerated.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
