# BRACE roadmap

Nothing here is fixed. Priorities are set by what the community needs — open an issue to add to or reorder this list. Items track to open issues (look for the `rfc`, `help wanted`, and `vendor-mapping` labels).

## Now

- **Sequence-pattern baselines for Control 7** — a portable spec for detecting multi-step attacks built from individually-allowed actions (RFC).
- **agent-type-id hashing spec** — canonical inputs and stability under opaque model updates (RFC).
- **OpenTelemetry `agent.*` attributes** — drive the semantic-convention proposal through the GenAI SIG (open-telemetry/semantic-conventions#3816).
- **Vendor matrix coverage** — accurate, sourced mappings for AWS Bedrock AgentCore, Microsoft Entra Agent ID, and others (help wanted).
- **Reference implementation** — Tier 1 controls wired onto a popular open-source agent stack, emitting the OpenTelemetry attributes.
- **Incident corpus** — grow the set of real incidents mapped to controls.

## Next

- A **controls-layer companion to the OWASP Top 10 for Agentic Applications** (proposal in `outreach/`).
- A **scoring / aggregation model** for the self-assessment.
- **Expanded threat mappings** — full MITRE ATLAS coverage, and the misaligned-insider (TRAIT&R) tactics.
- **Compliance mappings** — SOC 2, [ISO/IEC 27001](https://www.iso.org/standard/27001), and [ISO/IEC 42001](https://www.iso.org/standard/81230.html) — once the control set stabilizes.

## How to help

Pick anything above, or open a new issue. The highest-value contributions right now are the **reference implementation** and the **vendor mappings** — they turn the framework from a document into something teams can adopt.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
