# BRACE Resources

Resources for putting BRACE’s controls in place. Use the standards and threat models to understand risks. Use the reference designs to see ways to build. Use the software components to build and test your controls.

Each entry is tagged with the BRACE concern it most relates to: **Build-time · Run-time · Agent · Config · Ecosystem · Observability · Governance**. Status flags: **Open source · Commercial · Free · Emerging · Deprecating** (or **Unmaintained repository**).

> Source review: 2026-09-16; sources rechecked 2026-09-30. See [scope, findings, and verification limits](SOURCE-REVIEW.md). **Listing is not endorsement.** This field changes fast, so check an entry’s status before you rely on it. The website version of this list is at <https://braceframework.org/resources/>. Know something we should add? [Suggest a resource](https://github.com/brace-ai-security/brace/issues/new?template=get-listed.yml).

---

## Standards & threat models

Use these references to understand threats and governance requirements alongside BRACE’s deployment checks.

### Agentic threat catalogs

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | The flagship ranked risk list ([ASI01–ASI10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)) for autonomous agents — goal misalignment, tool misuse, delegated trust, memory, emergent autonomy. The closest outside match to BRACE's scope. | Agent · Run-time · Ecosystem | Free |
| [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) | The ten most critical LLM-app risks — prompt injection, excessive agency, supply chain, output handling, system-prompt leakage. The industry baseline. | Run-time · Build-time | Free |
| [OWASP Multi-Agentic System Threat Modeling Guide](https://genai.owasp.org/resource/multi-agentic-system-threat-modeling-guide-v1-0/) | Applies the agentic threat taxonomy to multi-agent systems, built around the MAESTRO layered method. | Ecosystem · Agent | Free |
| [MITRE ATLAS](https://atlas.mitre.org/) | The ATT&CK-style knowledge base of real adversary techniques against AI systems — now with agentic techniques (tool misuse, memory manipulation, orchestration attacks) and case studies. | Run-time · Ecosystem | Free |
| [CSA MAESTRO](https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro) | Cloud Security Alliance's seven-layer threat-modeling method for agentic systems; adopted within OWASP's MAS guide. | Governance · Ecosystem | Free |
| [OWASP AIVSS](https://aivss.owasp.org/) | An AI Vulnerability Scoring System extending CVSS with agentic amplifiers (autonomy, tool scope, multi-agent interaction) to quantify agent vulnerabilities. *Pre-1.0 (v0.8). The site plans v1.0 for the end of 2026; the method may still change.* | Agent · Run-time | Free · Emerging |

### Governance frameworks & regulation

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [NIST AI Risk Management Framework (AI 100-1)](https://www.nist.gov/itl/ai-risk-management-framework) | The de facto U.S. governance baseline — Govern, Map, Measure, Manage. BRACE sits underneath as the technical control layer. | Governance · Config | Free |
| [NIST Generative AI Profile (AI 600-1)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | GenAI-specific companion to the AI RMF — 12 risk categories including prompt injection, info-sec, and value-chain accountability. | Run-time · Governance | Free |
| [ISO/IEC 42001:2023](https://www.iso.org/standard/81230.html) | The first certifiable AI management-system standard — policy, roles, controls, audit, continual improvement. | Governance · Config | Paywalled |
| [ISO/IEC 23894:2023](https://www.iso.org/standard/77304.html) | AI-specific risk-management guidance that can support an [ISO/IEC 42001](https://www.iso.org/standard/81230.html) management system. | Governance | Paywalled |
| [EU AI Act (Reg. 2024/1689)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | Official text of Regulation (EU) 2024/1689. Consult the regulation and applicable guidance for obligations and implementation dates. | Governance · Agent | Free |
| [Google Secure AI Framework (SAIF)](https://saif.google/) | Google security guidance and risk-assessment resources, including agent security. Vendor-authored guidance complements deployment-specific verification. | Agent · Build-time · Run-time | Free |

### Government & multi-stakeholder guidance

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Careful Adoption of Agentic AI Services](https://www.cisa.gov/resources-tools/resources/careful-adoption-agentic-ai-services) | Joint guidance from CISA and international partners on adopting agentic AI safely. Use it as supporting risk guidance. BRACE’s priorities and item mappings are BRACE’s own reading of it. | Build-time · Config · Run-time · Ecosystem · Agent | Free |
| [NIST CAISI — AI Agent Standards Initiative](https://www.nist.gov/caisi/ai-agent-standards-initiative) | NIST’s program for agentic-AI interoperability and security standards. Its output so far is mostly requests for information and early drafts. Track it and expect change. | Agent · Ecosystem | Free · Emerging |
| [Coalition for Secure AI (CoSAI)](https://www.coalitionforsecureai.org/) | Open collaboration publishing AI security guidance and work on agent identity, delegation, and sandboxing. Consult each publication for its scope and maturity. | Agent · Ecosystem · Build-time | Free |

## Reference implementations & conformance specs

Concrete blueprints — one way to actually build a control. BRACE defines what to enforce and in what order; these show how.

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/) | Runtime middleware hooks and portable policy enforcement for agent frameworks. OWASP listed it in September 2026. Check how mature it is and whether it covers your framework. | Run-time · Ecosystem |  |
| [Microsoft Agent Governance Toolkit](https://github.com/microsoft/agent-governance-toolkit) | MIT-licensed governance toolkit with draft specifications and conformance requirements. Its MCP gateway specification is still a Draft and is a design reference. A written spec does not show that any deployed implementation meets it. | Ecosystem · Build-time · Agent · Config | Open source |
| [Anthropic — Trustworthy agents in practice](https://www.anthropic.com/research/trustworthy-agents) | Explains how duties split across the model, harness, tools, and environment, and sets out five governance principles. It is guidance. It does not show that a managed deployment has any given identity or containment feature. | Config · Build-time · Run-time | Free |

## Human-in-the-loop & platform controls

Companion frameworks and platform docs for human approval, guardrails, and oversight — where "high-risk actions need a human" actually gets built.

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [LoopRails](https://looprails.dev/) | An open, vendor-neutral human-in-the-loop framework for AI agents: which actions need review, how much oversight each needs, and how to keep approvals from becoming rubber stamps (Grade-Guard-Show-Prove, the RAIL checklist). | Build-time · Run-time | Free |
| [n8n — human-in-the-loop for AI tool calls](https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/) | Official doc for gating an agent's tool calls behind human approval: the reviewer sees the tool and parameters, approves or denies, and the agent is told the result. | Run-time · Agent | Free |
| [n8n — Guardrails node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.guardrails/) | A purpose-built node to check and sanitize LLM input and output — prompt-injection detection, text sanitization, and a custom system message. | Run-time · Agent | Free |
| [n8n — error handling & error workflows](https://docs.n8n.io/flow-logic/error-handling/) | Error workflows, the Error Trigger node, and Stop-And-Error for deliberate failure — reliability and escalation primitives for agent workflows. | Run-time | Free |
| [n8n — RBAC & external secrets](https://docs.n8n.io/user-management/rbac/) | Project-scoped roles over workflows and credentials, plus [external secrets](https://docs.n8n.io/external-secrets/) from 1Password, AWS/Azure/GCP, and HashiCorp Vault. | Config | Free |
| [n8n — 15 best practices for deploying AI agents in production](https://blog.n8n.io/best-practices-for-deploying-ai-agents-in-production/) | A substantive operational checklist spanning secrets, guardrails, audit logging, human-in-the-loop, escalation and timeouts, and per-node error handling. | Build-time · Run-time · Config | Free |

## Managed platforms

Commercial runtimes that ship some controls out of the box. For per-control evidence requirements, see the [vendor worksheet](VENDOR-MATRIX.md).

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) | Managed agent services. Check runtime isolation, identity, gateway, policy, memory, and observability against your exact service setup and the current technical docs. This listing is not a BRACE coverage rating. | Build-time · Agent · Run-time · Ecosystem | Commercial |
| [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id) | Identity and security for agents, using agent blueprints and agent identities. Check credential issuance, delegated scope, revocation, and telemetry for your deployment. | Agent | Commercial |
| [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) | Managed agent runtime and tool integration platform. Identity, networking, and tool controls depend on the deployment and settings you choose. Check each applicable checklist item. | Agent · Ecosystem · Run-time | Commercial |
| [Google Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini-enterprise-agent-platform) | Google’s platform for building and deploying agents. Use the service’s own docs and your deployment tests to show isolation, authorization, and observability coverage. *Renamed several times (formerly Vertex AI Agent Engine and Agentspace). Check current product names.* | Build-time · Ecosystem | Commercial |
| [OpenAI Agent Builder](https://developers.openai.com/api/docs/guides/agent-builder) | Visual agent workflow builder with versioned workflow publishing. OpenAI is deprecating it. Evaluate any workflow and its tools against the checklist, and plan a migration. *The official guide says Agent Builder shuts down on November 30, 2026, and that ChatKit remains available.* | Ecosystem · Run-time | Commercial · Deprecating |

## Open-source building blocks

The primitives you assemble BRACE-level controls from.

### Identity & attribution → Agent

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [SPIFFE / SPIRE](https://spiffe.io/) | CNCF-graduated workload identity — short-lived cryptographic SVIDs so agents authenticate without long-lived secrets. The foundation an agent identity chains from. | Agent · Observability | Open source |
| [IETF WIMSE draft — AI Identity Management System](https://datatracker.ietf.org/doc/draft-ietf-wimse-aims/) | A working-group Internet-Draft on agent identity, authentication, and authorization, not an RFC. It replaced draft-klrc-aiagent-auth in September 2026. This link does not independently substantiate other agent-passport or identity proposals. | Agent | Free · Emerging |

### Authorization → Config / Agent / Ecosystem

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Cedar](https://github.com/cedar-policy/cedar) | Authorization policy language, engine, and validator for fine-grained access decisions. Correct policy, identity inputs, and enforcement placement remain deployment responsibilities. | Config · Ecosystem | Open source |
| [OpenFGA](https://github.com/openfga/openfga) | CNCF relationship-based (Zanzibar-style) authorization — well suited to agent delegation chains and "who can act on whose behalf." | Agent · Config | Open source |
| [Open Policy Agent (OPA)](https://github.com/open-policy-agent/opa) | The CNCF-graduated general-purpose policy engine (Rego) for decoupled, context-aware authorization across gateways and tool calls. | Config · Run-time | Open source |

### Observability → the three BRACE observability requirements

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai) | The GenAI conventions now live in their own repository, semantic-conventions-genai. Status: Development. Agent spans include agent IDs, versions, and model references. They do not supply BRACE content hashes, per-run identity, or full audit coverage. BRACE’s proposed attributes are tracked in [issue #334](https://github.com/open-telemetry/semantic-conventions-genai/issues/334). | Observability · Agent | Open source |
| [Langfuse](https://github.com/langfuse/langfuse) | Open-source LLM and agent tracing, evals, and prompt management. Accepts OpenTelemetry GenAI data. (Custom license: MIT core plus commercial enterprise edition.) | Observability · Ecosystem | Open source |
| [Arize Phoenix](https://github.com/Arize-ai/phoenix) | Self-hostable AI tracing and evaluation platform with OpenTelemetry-based instrumentation. Check the license terms for the version and parts you use, and test the audit coverage you need. | Observability · Run-time | Open source |
| [OpenLLMetry (Traceloop)](https://github.com/traceloop/openllmetry) | OpenTelemetry-native instrumentation for LLM apps that needs few code changes. Exports to any OpenTelemetry backend. | Observability | Open source |
| [Helicone](https://github.com/Helicone/helicone) | Open-source LLM observability plus an AI gateway that captures cost, latency, and traces. A gateway is one place to log context size and audit tool calls. | Observability · Config | Open source |

### Sandboxing & isolation → Build-time

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Firecracker](https://github.com/firecracker-microvm/firecracker) | Lightweight virtual machine monitor that uses KVM for microVM isolation. Its settings and the host and network around it are still part of the security boundary. | Build-time | Open source |
| [gVisor](https://github.com/google/gvisor) | Google's user-space application kernel — stronger than container namespaces, lighter than a VM. Powers several agent-sandbox offerings. | Build-time | Open source |
| [E2B](https://github.com/e2b-dev/E2B) | SDKs and infrastructure for cloud sandboxes that run generated code. Check the provider’s actual isolation, network policy, lifecycle, and access controls for your deployment. | Build-time · Run-time | Open source |
| [Daytona — legacy public repository](https://github.com/daytonaio/daytona) | The linked repository says it is no longer maintained. Core development moved to a private codebase in June 2026. Don’t treat this repository as a maintained security component. Evaluate the current service on its own. | Build-time · Config | Unmaintained repository |
| [Modal Sandboxes](https://modal.com/docs/guide/sandbox) | Managed sandbox execution. Check the sandbox type you choose, its network settings, and the provider’s isolation docs. Record setup and visibility limits in your assessment. | Build-time · Config | Commercial |

### Guardrails & runtime defense → Run-time

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) | NVIDIA's programmable input/output rails — content safety, jailbreak detection, topic control, PII — for LLM/agent apps. | Run-time | Open source |
| [Guardrails AI](https://github.com/guardrails-ai/guardrails) | Input and output validation framework. Validators moved to standard PyPI packages, and hosted remote inferencing was discontinued, with a planned cutoff of August 25, 2026 (now passed). Follow the migration guide for the version you deploy. | Run-time | Open source |
| [Llama Guard / Prompt Guard](https://github.com/meta-llama/PurpleLlama) | Meta's classifier models: Llama Guard 4 for input/output content safety, Prompt Guard 2 for injection/jailbreak detection. (Llama community license.) | Run-time | Open source |
| [LLM Guard — archived](https://github.com/protectai/llm-guard) | The repository and its models are archived and no longer maintained. Keep it as a historical reference. Choose a maintained alternative for a production control. | Run-time | Unmaintained repository |

### Red-team & testing → verify your Run-time defenses

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [garak](https://github.com/NVIDIA/garak) | LLM vulnerability scanner with probes for injection, leakage, jailbreaks, and other failures. Passing its probes does not prove full attack coverage. | Run-time | Open source |
| [PyRIT](https://github.com/microsoft/PyRIT) | Microsoft's red-team orchestration framework — automates multi-turn adversarial attacks against models and agents. | Run-time | Open source |
| [ModelScan](https://github.com/protectai/modelscan) | Scans serialized model files (pickle, H5, SavedModel) for unsafe code / serialization attacks before load. | Ecosystem · Build-time | Open source |

### MCP & tool supply-chain security → Ecosystem

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Snyk Agent Scan](https://github.com/snyk/agent-scan) | Scanner for agent components, MCP servers, and skills. The repository warns that raw CLI output fields and risk labels are experimental, and that the v0.5.x CLI line is planned for deprecation. Don’t build production workflows on that output. | Ecosystem | Open source |
| [Cisco MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner) | Discovers MCP tools and scans descriptions/schemas with YARA rules for injection, tool poisoning, credential harvesting, and code execution. | Ecosystem | Open source |
| [Agentic Radar](https://github.com/splx-ai/agentic-radar) | Static scanner for agentic workflows (LangGraph, CrewAI, OpenAI Agents). Maps tools, detects MCP servers, and reports known vulnerabilities. No commits since November 2025; check maintenance status before you adopt it. | Ecosystem · Run-time | Open source |

### Memory, signing & incident knowledge

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Mem0](https://github.com/mem0ai/mem0) | Memory infrastructure with user, session, and agent state. Check actual isolation, write checks, and per-entry provenance. A memory API alone does not provide these controls. | Run-time | Open source |
| [Sigstore / cosign](https://github.com/sigstore/cosign) | Keyless artifact/container signing via OIDC identity and a transparency log — verifiable provenance for signed agent builds without long-lived keys. | Build-time · Ecosystem | Open source |
| [SLSA](https://slsa.dev/) | Supply-chain framework for build provenance and artifact integrity. Check which track and version apply, and your provenance policy. A signature alone does not give every build guarantee. | Build-time | Open source |
| [AI Incident Database (AIID)](https://incidentdatabase.ai/) | A long-running index of real-world AI harms (5,000+ reports) — the threat priors behind "what actually goes wrong." | Ecosystem | Free |
| [AI Vulnerability Database (AVID)](https://avidml.org/) | An open knowledge base of GPAI/agent failure modes — supply-chain CVEs, red-team results, and crowdsourced agent failures. | Ecosystem | Open source |

## Commercial security products

Notable commercial offerings, clearly flagged. Several pioneered techniques now common across the field.

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [Lakera Guard](https://www.lakera.ai/) · [Gandalf](https://gandalf.lakera.ai/) | Runtime prompt-injection/threat-detection API (now part of Check Point). **Gandalf** is a free public prompt-injection game for learning how injection works. | Run-time | Commercial · Gandalf free |
| [Cisco AI Defense](https://www.cisco.com/site/us/en/products/security/ai-defense/index.html) | End-to-end model/app/agent/MCP protection (ex–Robust Intelligence) — AI firewall, runtime protection, algorithmic red teaming, MCP catalog. Its [MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner) is open source. | Run-time · Ecosystem | Commercial |

## Companion projects

Related open work on building AI-augmented software safely and measurably — by the same author.

| Resource | What it is | BRACE | Status |
|---|---|---|---|
| [LoopRails](https://looprails.dev/) | A human-in-the-loop framework for AI agents: which actions need review, and how to keep approvals from becoming rubber stamps. (Also linked under Human-in-the-loop, above.) | Human oversight | Free |
| [Cost Per Accepted Change](https://costperacceptedchange.org/) | A metric for the true cost of AI-augmented delivery: (model + infra + engineering + review + rework) ÷ changes that reached production and stayed. | Delivery cost | Free |

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
