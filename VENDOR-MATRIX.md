# BRACE Vendor Coverage Matrix — evidence worksheet

**Reviewed:** 2026-09-16. See the [source review](SOURCE-REVIEW.md).

This matrix identifies evidence to request for each BRACE control. Product availability is not evidence that the control is enabled, correctly configured, or complete in your deployment. The previous blanket vendor checkmarks and claims that no vendor implements particular capabilities were not supported by a current, reproducible comparison and have been removed.

Use the [53-item checklist](CHECKLIST.md), its [verification recipes](CHECKLIST-VERIFICATION.md), and the [self-assessment](SELF-ASSESSMENT.md) to evaluate the exact product version, plan, region, and configuration. Record **demonstrated**, **partial**, **not demonstrated**, or **not applicable with rationale** for each deployment; these are evidence outcomes, not vendor rankings.

## Per-control evidence matrix

| BRACE control | Checklist items | Evidence required from vendor and deployment owner |
|---|---|---|
| C1 — Architecture | B08–B09; E06 | Effective network routes, tenant isolation, egress and SSRF controls, and bypass-test results. A managed service label does not establish its boundary. |
| C2 — Capability-scoped access | B02–B04; A01; E07–E08 | Actual grants, resource/audience restrictions, delegation scope, and measured revocation time including existing sessions. |
| C3 — Container | B10–B11; E02 | Artifact provenance, approved signer verification, runtime isolation design, and customer/provider responsibility split. Managed infrastructure may limit direct inspection. |
| C4 — Harness | B01; B05–B07; B12; E08 | Versioned policies, operation/argument enforcement, approval replay tests, hard limits, and all alternate execution paths. |
| C5 — Data | R01–R04; E03–E07 | Boundary validation, generated-output handling, retrieval permissions, metadata checks, and containment when injection detection misses. |
| C6 — Memory | R04–R06 | Scope enforcement, source/writer lineage, revocation, cleanup, and derived-memory/cache behavior. |
| C7 — Behavioral | R08–R10; A07; E12 | Documented detection claims, measured misses/false alarms, checker identities, and responder exercises. |
| C8 — Kill switch | R11–R12; E09 | Measured stop budget across descendants, sessions, queues, and disconnected workers; reconciliation for committed effects. |
| C9 — Audit trail | R13–R14; E10–E11 | Correlated action/outcome records, protected retention, independent integrity verification, and ambiguous-result/replay handling. |
| Obs-T1 — Six identity fields | A01–A05; C03; E10 | Accountable party, operational owner, tenant, type hash, instance ID, and trace context. Correlation fields alone do not authenticate an agent. |
| Obs-T2 — Context size | R07; R09; C08 | Decision-time token occupancy with measurement method, estimation limits, and explicit unknowns. Billing usage alone may be insufficient. |
| Obs-T3 — Parent/prompt provenance | A06; C08 | Parent-child trace or links and the parent-passed prompt or protected reference, with verified propagation and access controls. |

Configuration items C01–C08 apply across this matrix, including model and owned-training provenance. A vendor may provide only part of an item; name who implements and verifies the rest. No product listing changes the checklist's G1/G2/G3 rules.

## Candidate platforms and components

These are discovery links, not conformance awards. The resource catalog provides a broader [component list](RESOURCES.md).

| Source | What to investigate |
|---|---|
| [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) | Runtime, identity, gateway, memory, and observability capabilities for the particular service configuration. |
| [Google Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini-enterprise-agent-platform) | Runtime and tool boundaries, model/deployment versions, and tenant isolation in the chosen service. |
| [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) | Agent lifecycle, tool integration, identity, network controls, and telemetry. |
| [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id) | Issuance, scoping, delegated authority, and independent revocation for agent identities. |
| [OpenAI Agent Builder](https://developers.openai.com/api/docs/guides/agent-builder) | Workflow versioning and tool controls. The official guide schedules shutdown for November 30, 2026 and says ChatKit remains available. |
| [Anthropic trustworthy-agents guidance](https://www.anthropic.com/research/trustworthy-agents) | Model/harness/tool/environment responsibilities. This guidance is not proof of a specific managed-product feature. |
| [OpenTelemetry GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai) | Existing agent/model attributes and tracing instrumentation; verify BRACE-specific additions and audit completeness separately. |

## Reference designs and standards

[OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/) defines portable runtime control hooks. It complements BRACE's deployment review; verify framework support and maturity before relying on a particular integration.

The Microsoft Agent Governance Toolkit's pinned [MCP Security Gateway 1.0 specification](https://github.com/microsoft/agent-governance-toolkit/blob/013c7fb44ae589c21488b2746fef9ee44c4f1416/docs/specs/MCP-SECURITY-GATEWAY-1.0.md) explicitly labels itself **Draft**. It describes interception, scanning, authentication, fingerprinting, audit, and conformance requirements. Those requirements are not evidence of independently verified implementation conformance. Run the applicable tests against the actual implementation.

A gateway circuit breaker does not by itself stop remote child agents. A description/schema fingerprint does not identify hidden remote implementation changes. HMAC authentication does not provide all six BRACE identity fields. Verify those boundaries separately rather than mapping one feature to an entire control.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
