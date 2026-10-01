# BRACE Vendor Coverage Matrix — evidence worksheet

**Reviewed:** 2026-09-16; sources rechecked 2026-09-30. See the [source review](SOURCE-REVIEW.md).

Use this worksheet to ask for, and record, evidence for each BRACE control. A product having a feature does not prove the control is turned on, set up correctly, or complete in your deployment. This worksheet does not rank vendors or give them checkmarks. Those claims would need a current comparison that others can repeat.

Use the [53-item checklist](CHECKLIST.md), its [verification recipes](CHECKLIST-VERIFICATION.md), and the [self-assessment](SELF-ASSESSMENT.md). Test the exact product version, plan, region, and configuration you will use. For each deployment, record **demonstrated**, **partial**, **not demonstrated**, or **not applicable, with a reason**. These are evidence results, not vendor rankings.

## Per-control evidence matrix

| BRACE control | Checklist items | Evidence required from vendor and deployment owner |
|---|---|---|
| C1 — Architecture | B08–B09; E06 | Actual network routes, tenant isolation, egress and SSRF controls, and bypass test results. Calling a service "managed" does not prove where its boundary is. |
| C2 — Capability-scoped access | B02–B04; A01; E05–E08 | Actual grants, resource and audience limits, delegation scope, and measured revocation time, including open sessions. |
| C3 — Container | B10–B11; E02 | Build provenance, checks against an approved signer, runtime isolation design, and the split of duties between customer and provider. Managed infrastructure may limit what you can inspect directly. |
| C4 — Harness | B01; B05–B07; B12; E06; E08 | Versioned policies, enforcement on operation and arguments, approval replay tests, hard limits, and every other path that can run the same action. |
| C5 — Data | R01–R04; E02–E07 | Input checks at each boundary, handling of generated output, retrieval permissions, tool metadata checks, and containment when injection detection misses. |
| C6 — Memory | R04–R06 | Scope enforcement, records of each entry's source and writer, revocation, cleanup, and how summaries and caches are handled. |
| C7 — Behavioral | R08–R10; A07; E12 | Written detection claims, measured misses and false alarms, identities of checker models, and responder drills. |
| C8 — Kill switch | R11–R12; A05; E09; E12 | Measured stop time across sub-agents, streams, queues, and disconnected workers. Reconciliation for effects that already happened. |
| C9 — Audit trail | R03; R13–R14; A04–A05; E06; E10–E11 | Linked records of actions and results, protected retention, integrity checks against a separate trust anchor, and handling of unclear results and replays. |
| Obs-T1 — Six identity fields | A01–A05; A07; C01; C03–C04; C08; E10 | Accountable party, operational owner, tenant, type hash, instance ID, and trace context. Fields that only link records do not prove who an agent is. |
| Obs-T2 — Context size | R07; R09; C08 | How full the context was, in tokens, at each decision. Include the counting method, limits of any estimate, and values marked unknown. Billing totals alone may not be enough. |
| Obs-T3 — Parent/prompt provenance | A06; C08 | Parent-child trace links, and the prompt the parent passed (or a protected reference to it). Show that links survive handoffs and that access is controlled. |

E01 and the Configuration items (C01–C08) apply across the whole matrix, including model records and the history of training you run yourself. A vendor may cover only part of an item. Name who builds and checks the rest. No product listing changes the checklist's G1/G2/G3 rules.

## Candidate platforms and components

These links are starting points, not verified ratings. The resource catalog has a longer [component list](RESOURCES.md).

| Source | What to investigate |
|---|---|
| [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) | Runtime, identity, gateway, memory, and observability features for your exact service setup. |
| [Google Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini-enterprise-agent-platform) | Runtime and tool boundaries, model and deployment versions, and tenant isolation in the service you choose. |
| [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) | Agent lifecycle, tool integration, identity, network controls, and telemetry. |
| [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id) | How agent identities are issued and scoped, delegated authority, and revoking an agent without revoking its user. |
| [OpenAI Agent Builder](https://developers.openai.com/api/docs/guides/agent-builder) | Workflow versioning and tool controls. OpenAI is deprecating Agent Builder. The official guide says it shuts down on November 30, 2026, and that ChatKit remains available. Plan a migration before you rely on it. |
| [Anthropic trustworthy-agents guidance](https://www.anthropic.com/research/trustworthy-agents) | How duties split across the model, harness, tools, and environment. This guidance does not prove that any managed product has a given feature. |
| [OpenTelemetry GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai) | Existing agent and model attributes and tracing. Status: Development. BRACE's proposed additions are tracked in [semantic-conventions-genai#334](https://github.com/open-telemetry/semantic-conventions-genai/issues/334). Check BRACE-specific fields and audit coverage separately. |

## Reference designs and standards

[OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/) defines portable runtime control hooks. It works alongside BRACE's deployment review. Check framework support and maturity before you rely on a given integration.

The Microsoft Agent Governance Toolkit's [MCP Security Gateway 1.0 specification](https://github.com/microsoft/agent-governance-toolkit/blob/580344a624530b6e9611e67544519bca3107cd31/docs/specs/MCP-SECURITY-GATEWAY-1.0.md) (pinned revision 580344a, 2026-09-25) labels itself **Draft**. It describes interception, scanning, authentication, fingerprinting, audit, and conformance requirements. Written requirements do not show that any implementation has been independently tested against them. Run the relevant tests on the actual implementation.

A gateway circuit breaker does not, by itself, stop remote child agents. A fingerprint of a tool's description and schema does not catch hidden changes to remote code. HMAC authentication does not supply all six BRACE identity fields. Check each of these limits on its own. Don't map one feature to a whole control.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
