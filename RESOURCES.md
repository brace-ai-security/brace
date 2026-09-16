# BRACE Resources

Resources for implementing BRACE’s controls. Use the standards and threat models to understand risks, reference designs to explore implementation approaches, and software components to build and test your controls.

Each entry notes the BRACE concern it most relates to: **Build-time · Run-time · Agent · Config · Ecosystem · Observability · Governance**.

> Source review: 2026-09-16. See [scope, findings, and verification limits](SOURCE-REVIEW.md). **Listing is not endorsement**, and this space moves fast — verify status before relying on anything. The website version of this list lives at <https://braceframework.org/resources/>. Know something we should add? [Suggest a resource](https://github.com/brace-ai-security/brace/issues/new?template=get-listed.yml).

---

## Standards & threat models

Use these references to understand threats and governance requirements alongside BRACE’s deployment checks.

### Agentic threat catalogs

| Resource | What it is | BRACE |
|---|---|---|
| [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | The flagship ranked risk list (ASI01–ASI10) for autonomous agents — the closest external analog to BRACE's scope. | Agent · Run-time · Ecosystem |
| [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) | The ten most critical LLM-app risks; the industry baseline. | Run-time · Build-time |
| [OWASP Multi-Agentic System Threat Modeling Guide](https://genai.owasp.org/resource/multi-agentic-system-threat-modeling-guide-v1-0/) | Applies the agentic threat taxonomy to multi-agent systems. | Ecosystem · Agent |
| [MITRE ATLAS](https://atlas.mitre.org/) | ATT&CK-style knowledge base of real adversary techniques against AI systems, now including agentic techniques. | Run-time · Ecosystem |
| [CSA MAESTRO](https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro) | Seven-layer threat-modeling method for agentic systems. | Governance · Ecosystem |
| [OWASP AIVSS](https://aivss.owasp.org/) | An AI Vulnerability Scoring System extending CVSS with agentic amplifiers. *Pre-1.0.* | Agent · Run-time |

### Governance frameworks & regulation

| Resource | What it is | BRACE |
|---|---|---|
| [NIST AI RMF (AI 100-1)](https://www.nist.gov/itl/ai-risk-management-framework) | The de facto U.S. governance baseline — Govern, Map, Measure, Manage. | Governance · Config |
| [NIST Generative AI Profile (AI 600-1)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | GenAI-specific companion to the AI RMF — 12 risk categories. | Run-time · Governance |
| [ISO/IEC 42001:2023](https://www.iso.org/standard/42001) | The first certifiable AI management-system standard. *Paywalled.* | Governance · Config |
| [ISO/IEC 23894:2023](https://www.iso.org/standard/77304.html) | AI-specific risk-management guidance. *Paywalled.* | Governance |
| [EU AI Act (Reg. 2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | Official text of Regulation (EU) 2024/1689. Consult the regulation and applicable guidance for obligations and implementation dates. | Governance · Agent |
| [Google Secure AI Framework (SAIF)](https://saif.google/) | Google security guidance and risk-assessment resources, including agent security. Vendor-authored guidance complements deployment-specific verification. | Agent · Build-time · Run-time |

### Government & multi-stakeholder guidance

| Resource | What it is | BRACE |
|---|---|---|
| [Careful Adoption of Agentic AI Services](https://www.cisa.gov/news-events/news/cisa-us-and-international-partners-release-guide-secure-adoption-agentic-ai) | CISA and international partners announce guidance for secure agentic-AI adoption. Use it as supporting risk guidance; BRACE priorities and item mappings are BRACE interpretations. | All concerns |
| [NIST CAISI — AI Agent Standards Initiative](https://www.nist.gov/caisi/ai-agent-standards-initiative) | The first U.S. program dedicated to agentic-AI standards. *Mostly drafts; track it.* | Agent · Ecosystem |
| [Coalition for Secure AI (CoSAI)](https://www.coalitionforsecureai.org/) | Open collaboration publishing AI security guidance and work on agent identity, delegation, and sandboxing. Consult each publication for its scope and maturity. | Agent · Ecosystem · Build-time |

## Reference implementations & conformance specs

Concrete blueprints — one way to actually build a control. BRACE defines what to enforce and in what order; these show how.

| Resource | What it is | BRACE |
|---|---|---|
| [OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/) | Middleware hooks and portable runtime policy enforcement; listed September 1, 2026. Verify framework coverage and implementation maturity. | Run-time · Ecosystem |
| [Microsoft Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) | MIT-licensed governance toolkit with draft specifications and conformance requirements. The pinned MCP gateway specification is a design reference; its existence does not establish that a deployed implementation passes the requirements. | Ecosystem · Build-time · Agent · Config |
| [Anthropic — Trustworthy agents in practice](https://www.anthropic.com/research/trustworthy-agents) | Explains model, harness, tools, and environment responsibilities and five governance principles. This article is guidance, not evidence that every managed deployment supplies a particular identity or containment feature. | Config · Build-time · Run-time |

## Managed platforms

Commercial runtimes that ship some controls out of the box. For per-control vendor coverage, see [VENDOR-MATRIX.md](VENDOR-MATRIX.md).

| Resource | What it is | BRACE |
|---|---|---|
| [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) | Managed agent services. Verify runtime isolation, identity, gateway, policy, memory, and observability against the exact service configuration and current technical documentation; this listing is not a BRACE coverage rating. | Build-time · Agent · Run-time · Ecosystem |
| [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id) | Agent identity and security framework with blueprints and agent identities. Verify credential issuance, delegated scope, revocation, and telemetry for your deployment. | Agent |
| [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) | Managed agent runtime and tool integration platform. Identity, networking, and tool controls depend on the chosen deployment and configuration; verify each applicable checklist item. | Agent · Ecosystem · Run-time |
| [Google Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini-enterprise-agent-platform) | Google agent development and deployment platform. Use service-specific documentation and deployment tests to establish isolation, authorization, and observability coverage. | Build-time · Ecosystem |
| [OpenAI Agent Builder](https://developers.openai.com/api/docs/guides/agent-builder) | Visual workflow builder with versioned publishing. Scheduled shutdown: November 30, 2026; ChatKit remains available according to the official guide. | Ecosystem · Run-time |

## Open-source building blocks

The primitives you assemble BRACE-level controls from.

### Identity & attribution → Agent

| Resource | What it is |
|---|---|
| [SPIFFE / SPIRE](https://spiffe.io/) | CNCF-graduated workload identity — short-lived cryptographic SVIDs, no long-lived secrets. |
| [IETF draft — AI Agent Authentication and Authorization](https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/) | An evolving Internet-Draft on agent authentication and authorization, not an adopted RFC. This link does not independently substantiate other agent-passport or identity proposals. |

### Authorization → Config / Agent / Ecosystem

| Resource | What it is |
|---|---|
| [Cedar](https://github.com/cedar-policy/cedar) | Authorization policy language, engine, and validator for fine-grained access decisions. Correct policy, identity inputs, and enforcement placement remain deployment responsibilities. |
| [OpenFGA](https://github.com/openfga/openfga) | CNCF relationship-based (Zanzibar-style) authorization — fits agent delegation chains. |
| [Open Policy Agent (OPA)](https://github.com/open-policy-agent/opa) | CNCF-graduated general-purpose policy engine (Rego). |

### Observability → the three BRACE observability requirements

| Resource | What it is |
|---|---|
| [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai) | GenAI conventions have moved to a dedicated repository. Agent spans include agent IDs, versions, and model references; these do not automatically supply BRACE content hashes, per-run identity, or complete audit coverage. Agent conventions remain in Development. |
| [Langfuse](https://github.com/langfuse/langfuse) | Open-source LLM/agent tracing, evals, prompt management; ingests OTel GenAI. |
| [Arize Phoenix](https://github.com/Arize-ai/phoenix) | Self-hostable AI tracing and evaluation platform with OpenTelemetry-based instrumentation. Verify license terms for the version/components used and test required audit coverage. |
| [OpenLLMetry (Traceloop)](https://github.com/traceloop/openllmetry) | OpenTelemetry-native, non-intrusive instrumentation for LLM apps. |
| [Helicone](https://github.com/Helicone/helicone) | Open-source LLM observability plus a Rust AI gateway. |

### Sandboxing & isolation → Build-time

| Resource | What it is |
|---|---|
| [Firecracker](https://github.com/firecracker-microvm/firecracker) | Lightweight virtual machine monitor using KVM for microVM isolation. Runtime configuration and the surrounding host/network remain part of the security boundary. |
| [gVisor](https://github.com/google/gvisor) | Google's user-space application kernel — stronger than namespaces, lighter than a VM. |
| [E2B](https://github.com/e2b-dev/E2B) | SDKs and infrastructure for cloud sandboxes running generated code. Verify the actual provider isolation, network policy, lifecycle, and access controls for your deployment. |
| [Daytona — legacy public repository](https://github.com/daytonaio/daytona) | The linked repository says it is no longer maintained and that core development moved to a private codebase in June 2026. Do not treat this repository as a maintained security component; evaluate the current service separately. |
| [Modal Sandboxes](https://modal.com/docs/guide/sandbox) | Managed sandbox execution. Check the chosen sandbox type, network settings, and provider isolation documentation; configuration and visibility limits belong in the assessment. |

### Guardrails & runtime defense → Run-time

| Resource | What it is |
|---|---|
| [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) | NVIDIA's programmable input/output rails — content safety, jailbreak detection, topic control, PII. |
| [Guardrails AI](https://github.com/guardrails-ai/guardrails) | Input/output validation framework. The repository announces migration to standard PyPI validator packages and discontinuation of hosted remote inferencing, with a planned August 25, 2026 cutoff. Check migration guidance for the version you deploy. |
| [Llama Guard / Prompt Guard](https://github.com/meta-llama/PurpleLlama) | Meta's classifier models for content safety and injection/jailbreak detection. |
| [LLM Guard — archived](https://github.com/protectai/llm-guard) | The repository and associated models are archived and no longer actively maintained. Retain as historical reference; evaluate a maintained alternative before adopting it as a production control. |

### Red-team & testing → verify your Run-time defenses

| Resource | What it is |
|---|---|
| [garak](https://github.com/NVIDIA/garak) | LLM vulnerability scanner with probes for injection, leakage, jailbreaks, and other failures. Passing its probes does not establish complete attack coverage. |
| [PyRIT](https://github.com/microsoft/PyRIT) | Microsoft's red-team orchestration framework for multi-turn adversarial attacks. |
| [ModelScan](https://github.com/protectai/modelscan) | Scans serialized model files for unsafe code / serialization attacks before load. |

### MCP & tool supply-chain security → Ecosystem

| Resource | What it is |
|---|---|
| [Snyk Agent Scan](https://github.com/snyk/agent-scan) | Scanner for agent components, MCP servers, and skills. The repository warns that raw CLI output fields and risk labels are experimental; avoid relying on that output as a stable production interface. |
| [Cisco MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner) | Discovers MCP tools and scans descriptions/schemas with YARA rules. |
| [Agentic Radar](https://github.com/splx-ai/agentic-radar) | Static scanner for agentic workflows — maps tools, detects MCP servers, surfaces vulnerabilities. |

### Memory, signing & incident knowledge

| Resource | What it is |
|---|---|
| [Mem0](https://github.com/mem0ai/mem0) | Memory infrastructure with user, session, and agent state. Verify actual isolation, write validation, and per-entry provenance; a memory API alone does not establish these controls. |
| [Sigstore / cosign](https://github.com/sigstore/cosign) | Keyless artifact/container signing with a transparency log — provenance for signed agent builds. |
| [SLSA](https://slsa.dev/) | Supply-chain framework for build provenance and artifact integrity. Verify the applicable track/version and provenance policy; a signature alone does not establish all build guarantees. |
| [AI Incident Database (AIID)](https://incidentdatabase.ai/) | A long-running index of real-world AI harms — the threat priors behind "what actually goes wrong." |
| [AI Vulnerability Database (AVID)](https://avidml.org/) | An open knowledge base of GPAI/agent failure modes. |

## Commercial security products

Notable commercial offerings, clearly flagged. Several pioneered techniques now common across the field.

| Resource | What it is | BRACE |
|---|---|---|
| [Lakera Guard](https://www.lakera.ai/) · [Gandalf](https://gandalf.lakera.ai/) | Runtime prompt-injection/threat detection (now part of Check Point). **Gandalf** is a free prompt-injection game worth trying. | Run-time |
| [Cisco AI Defense](https://www.cisco.com/site/us/en/products/security/ai-defense/index.html) | End-to-end model/app/agent/MCP protection (ex–Robust Intelligence); its [MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner) is open source. | Run-time · Ecosystem |

---

*Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.*
