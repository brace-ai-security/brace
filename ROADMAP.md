# BRACE roadmap

Nothing here is fixed. The community's needs set the priorities. Open an issue to add to this list or reorder it. Each item tracks an open issue. Look for the `rfc`, `help wanted`, and `vendor-mapping` labels.

## Now

- **Sequence-pattern baselines for C7 (Behavioral)** — a portable spec for detecting multi-step attacks made of actions that are each allowed on their own (RFC).
- **agent-type-id hashing spec** — the exact inputs to hash, and how the ID behaves when a hosted model changes without notice (RFC).
- **OpenTelemetry `agent.*` attributes** — take the proposal through the GenAI SIG ([open-telemetry/semantic-conventions-genai#334](https://github.com/open-telemetry/semantic-conventions-genai/issues/334), open). The GenAI conventions themselves are still in Development.
- **Vendor worksheet evidence** — sourced, tested evidence for Amazon Bedrock AgentCore, Microsoft Entra Agent ID, and others (help wanted).
- **Reference implementation** — the Tier 1 controls built on a popular open-source agent stack, emitting the OpenTelemetry attributes.
- **Incident mapping** — collect public incident reports and map each one to the controls that would have prevented or contained it. No such collection exists yet.

## Next

- A **controls-layer companion to the OWASP Top 10 for Agentic Applications** (proposal in `outreach/`).
- A **scoring / aggregation model** for the self-assessment.
- **Expanded threat mappings** — the [MITRE ATLAS mapping](mappings/mitre-atlas.md) is published (ATLAS v2026.09); keep it current with new ATLAS releases. Still planned: a mapping to Google DeepMind's [TRAIT&R](https://arxiv.org/abs/2607.13087) taxonomy of tactics a misaligned agent could use.
- **Compliance mappings** — mappings to the [NIST AI RMF](mappings/nist-ai-rmf.md) and [ISO/IEC 42001](mappings/iso-iec-42001.md) are published. The ISO mapping uses only public control titles; check it against the full standard. Still planned: SOC 2 and [ISO/IEC 27001](https://www.iso.org/standard/27001).

## How to help

Pick anything above, or open a new issue. The most useful contributions now are the **reference implementation** and **vendor evidence**. They turn the framework from a document into something teams can adopt.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
