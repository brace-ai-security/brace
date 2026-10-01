# Contributing to BRACE

BRACE (Build-time, Run-time, Agent, Configuration, Ecosystem) is a vendor-neutral set of technical controls for autonomous AI agents. Contributions are welcome. This guide explains how to propose changes and which contributions help most.

## Scope

BRACE is a **technical control framework**, not a governance or compliance framework. It names concrete controls you can test for deploying agents safely. It does not define company policy, risk appetite, or audit programs.

BRACE **works alongside** OWASP, NIST, and MITRE guidance. It does not replace them. The OWASP Top 10 for Agentic Applications and MITRE ATLAS describe threats. The NIST AI RMF describes governance. BRACE describes the control layer in between. Contributions that strengthen these mappings help most. Turning BRACE into a governance or compliance standard is out of scope.

## Propose a change to a control

The nine controls are the core of the framework: C1 Architecture, C2 Capability-scoped API access, C3 Container, C4 Harness, C5 Data, C6 Memory, C7 Behavioral, C8 Kill Switch, and C9 Audit Trail. Changes to them take two steps:

1. **Open an issue** that describes the change and why it matters. Say which control it affects, what the current text says, and what you propose instead. Discussion happens on the issue.
2. **Open a pull request** once there is rough agreement on the issue. Include the issue number. Keep the diff to that one control.

These two steps keep control changes careful. Please don't open a PR that rewrites a control without an issue first.

## Identifier and linking style

BRACE uses separate sets of codes for checklist items (`B05`, `R01`, `A03`, `C01`, `E06`), release gates (`G1`–`G3`; G stands for gate), controls (`C1`–`C9`), and observability requirements (`Obs-T1`–`Obs-T3`). These codes are fixed. Don't renumber them just because the display order changes. Note that `C01` is a Configuration checklist item, while `C1` is the Architecture control.

When you use a code defined by another organization, link the code to its official definition the first time it appears in each document or stand-alone section. Examples include [ASI01](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), [RFC 7009](https://www.rfc-editor.org/info/rfc7009/), and [ISO/IEC 42001](https://www.iso.org/standard/81230.html). Link to the standards body, publisher, or official registry, not a secondary explainer. Don't format an outside code as if it were a BRACE code.

## Report a real-world incident

Real incidents show whether BRACE's controls would have helped. BRACE does not yet keep an incident collection. If you know of a real incident with deployed agents, report it in an issue using this template:

```
**What happened:** A short, factual description of the incident.
**Which control applies:** Which BRACE control (C1–C9) or observability
  requirement (Obs-T1–Obs-T3) would have prevented or contained it, and how.
**Source link:** A public, durable link — a writeup, advisory, postmortem,
  or news report. First-hand reports are welcome; please say so.
```

Keep it factual and link a public source.

## Map a vendor product to controls

The [vendor worksheet](VENDOR-MATRIX.md) lists the evidence needed to judge support for BRACE controls. To add or correct an entry, open a PR (or an issue, if you'd rather discuss first) with:

- The vendor and product name.
- The control(s) (C1–C9) it addresses.
- A one-line note on *how* it addresses each, with a link to the product's documentation. A product feature is not proof that a deployment passes; see the worksheet.

Mappings must stay vendor-neutral. We map what a product does; we don't endorse it. Please disclose any link you have to a vendor you are mapping.

## Suggest OpenTelemetry attribute refinements

The three observability requirements are Obs-T1 (identity fields), Obs-T2 (context-size logging), and Obs-T3 (sub-agent and parent-prompt provenance). BRACE expresses them as [proposed OpenTelemetry attributes](otel-conventions.md), so the same fields work across vendors. The proposal is tracked in [open-telemetry/semantic-conventions-genai#334](https://github.com/open-telemetry/semantic-conventions-genai/issues/334). To refine them, open an issue with:

- The attribute name(s) you'd change, add, or remove.
- How it fits OpenTelemetry semantic-convention practice.
- What it lets an operator see that the current set does not.

Reuse existing OpenTelemetry conventions where you can, rather than inventing new shapes.

## Licensing

By contributing, you agree that your contribution is released under **Creative Commons Attribution 4.0 (CC BY 4.0)**, the same license as the rest of the project. You keep credit, and the work stays open for reuse.

## Status

BRACE pulls together agent-security practice already used in production. It has not yet been tested against a control group. The most valuable contributions move it toward that test: real incidents, real mappings, and real deployment experience.

The current requirements are in the [53-item sign-off checklist](CHECKLIST.md). See the [source review](SOURCE-REVIEW.md) for supporting evidence and its limits.

## Code of conduct

Be kind and assume good faith. We share one goal: safer agent deployments. Critique ideas, not people. Keep discussion concrete. Help newcomers. Behavior that makes the project unwelcoming isn't tolerated.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
