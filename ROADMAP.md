# BRACE roadmap

Nothing here is fixed. The community's needs set the priorities. Open an issue to add to this list or reorder it. Each item tracks an open issue. Look for the `rfc`, `help wanted`, and `vendor-mapping` labels.

## Now

- **OpenTelemetry guidance** — ask the GenAI SIG to clarify how to record an agent content hash and a single agent run with existing attributes. BRACE defines no custom attributes. The GenAI conventions themselves are still in Development.
- **Vendor worksheet evidence** — sourced, tested evidence for Amazon Bedrock AgentCore, Microsoft Entra Agent ID, and others (help wanted).
- **Reference implementation** — the Tier 1 controls built on a popular open-source agent stack, emitting the OpenTelemetry attributes.
- **Incident mapping** — collect public incident reports and map each one to the controls that would have prevented or contained it. No such collection exists yet.

## Next

- A **controls-layer companion to the OWASP Top 10 for Agentic Applications** (proposal in `docs/outreach/`).
- **Expanded threat mappings** — the [MITRE ATLAS mapping](mappings/mitre-atlas.md) is published (ATLAS v2026.10); keep it current with new ATLAS releases. The [OWASP Agentic Top 10](mappings/owasp-agentic-top-10.md) and [OWASP MCP Top 10](mappings/owasp-mcp-top-10.md) mappings are published; recheck the MCP mapping when that list leaves beta. Still planned: a mapping to Google DeepMind's [TRAIT&R](https://arxiv.org/abs/2607.13087) taxonomy of tactics a misaligned agent could use.
- **Compliance mappings** — mappings to the [NIST AI RMF](mappings/nist-ai-rmf.md) and [ISO/IEC 42001](mappings/iso-iec-42001.md) are published. The ISO mapping uses only public control titles; check it against the full standard. Still planned: SOC 2 and [ISO/IEC 27001](https://www.iso.org/standard/27001).

## Later / not planned for now

These stay on the list but are not being worked on. Each needs adopter demand or a real implementation to learn from first.

- **Sequence-pattern baselines for C7 (Behavioral)** (RFC): a portable spec for multi-step attacks made of individually allowed actions. Why later: it needs detection data from real deployments, and there is none to base a spec on.
- **agent-type-id hashing spec** (RFC): the exact inputs to hash, and behavior when a hosted model changes without notice. Why later: the current identity fields and OpenTelemetry guidance are enough for adopters; a hashing spec should follow a reference implementation.
- **Scoring / aggregation model** for the self-assessment. Why later: a single score invites false comfort, and the per-item scores and gates already serve reviewers.

## How to help

Pick anything above, or open a new issue. The most useful contributions now are the **reference implementation**, **vendor evidence** and **incident mapping**. They turn the framework from a document into something teams can adopt.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
