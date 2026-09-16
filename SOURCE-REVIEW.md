# Source and practical-accuracy review

**Review date: 2026-09-16.** Scope: the [53-item checklist](CHECKLIST.md), [verification recipes](CHECKLIST-VERIFICATION.md), assessment, guides, resource catalog, vendor worksheet, and telemetry proposal.

## Conclusion and limits

The core control approach is consistent with the primary guidance reviewed, subject to the corrections below. All 53 requirements and their verification recipes were reviewed for practical accuracy using the available documentation. **This is not a deployment test, product certification, or proof that these controls prevent every attack.** Effectiveness must be demonstrated on the actual release using the verification recipes.

The source inventory contained **70 distinct external URLs** before this review. The initial link check successfully retrieved 67 sources (HTTP 200); three blocked access (HTTP 403). A successful response establishes reachability, not accuracy or implementation effectiveness. Relevant primary documentation was then read to check the security claims and catalog descriptions; the inventory states the verification limits for other references. Product source code, all linked subpages, and proprietary service internals were not comprehensively audited.

The nine controls, exact six-field identity schema, decision-time context requirement, top-three selections, and release gates are BRACE design judgments. Sources support related principles; they do not prescribe this exact checklist or validate its ranking. Mappings to standards show related concepts; they do not establish compliance.

## Findings and corrections

| Finding | Correction and practical consequence |
|---|---|
| Revocation is not universally immediate. | B04 now requires a measured revocation time limit appropriate to the potential harm covering existing sessions and self-contained/cached tokens. [RFC 7009](https://www.rfc-editor.org/info/rfc7009/) describes propagation considerations; disabling refresh alone is insufficient. |
| Approval can be replayed or become stale. | B05/B06 now bind authorization to operation, target, and arguments, check relevant state at execution, and test concurrent replay. See [OWASP transaction authorization](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html). |
| Network allowlists and signatures can be overclaimed. | B09 includes redirect/DNS and allowed-service abuse. B10 requires an approved signing identity as well as digest verification. B11 distinguishes sandbox architecture from a few successful denial probes. |
| Input validation is not a complete prompt-injection defense. | R01/R02 retain separate structural validation, treatment of external text as data, and independently enforced action permissions. R03 also covers generated content consumed by interpreters. See [OWASP injection prevention](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html). |
| Context and remote implementation identity can be unobservable. | R07 records counting method and uncertainty. E03 distinguishes metadata hashes from hidden remote implementation changes. Model and training records now identify unavailable details explicitly. |
| Integrity and replay claims need stronger assumptions. | R14 requires independently protected trust state and scoped destination idempotency guarantees, or a manual reconciliation hold. [Stripe’s documented behavior](https://docs.stripe.com/api/idempotent_requests) is a concrete example, not a guarantee for other integrations. |
| An HTTP gateway does not cover every MCP transport. | E06 and the gateway guide distinguish OAuth/HTTP authorization from host/process/sandbox controls for local stdio. See [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization). |
| Existing OpenTelemetry coverage was understated. | Current GenAI conventions already include agent identity/version and agent/tool spans. BRACE’s extra fields are labeled custom proposals; context propagation must be instrumented and verified. [Agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md) remain Development. |
| Framework novelty and vendor rankings were unsupported. | Added [OWASP ACS](https://genai.owasp.org/resource/agent-control-standard-acs/), removed sweeping exclusivity claims, and replaced product checkmarks/rankings with an evidence worksheet. The Microsoft gateway reference is a draft with conformance requirements, not proof of independent conformance testing. |
| Catalog maintenance and lifecycle claims had drifted. | Marked [Daytona](https://github.com/daytonaio/daytona) and [LLM Guard](https://github.com/protectai/llm-guard) repositories as unmaintained; recorded [Guardrails](https://github.com/guardrails-ai/guardrails) migration and [Snyk Agent Scan](https://github.com/snyk/agent-scan) experimental-output limitations. |
| OpenAI lifecycle wording exceeded the source. | [Agent Builder docs](https://developers.openai.com/api/docs/guides/agent-builder) state a November 30, 2026 sunset and that ChatKit continues. Removed the unsupported Evals sunset claim and claims that vendors do not version workflows. |
| A study result was easy to overgeneralize. | The 73.5% debugging/logging figure describes vulnerabilities identified in the [sampled skill study](https://arxiv.org/abs/2604.03070), not all agent vulnerabilities in the wild. |

### Evidence still unavailable

- The previously described standalone BRACE paper and 35+ incident analysis corpus were not available for inspection. They are not counted as verified support; the README now makes that limitation explicit.
- ISO 42001 and ISO 23894 public metadata was inspected, but the full paywalled standards were not. No clause-level completeness or compliance conclusion is claimed.
- Vendor feature coverage, configuration defaults, deployment performance, and security effectiveness require version-specific evidence and testing. The [vendor worksheet](VENDOR-MATRIX.md) records what to request rather than assigning unsupported passes.
- Historical outreach drafts are marked as historical; their novelty statements are not current verified claims.

## Primary control references

References below support the related principle, not every BRACE-specific implementation detail. Drafts and living documentation can change after this review.

- **S1:** [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).
- **S2:** [OWASP Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).
- **S3:** [MCP authorization, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
- **S4:** [MCP draft security best practices](https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices).
- **S5:** [RFC 7009: OAuth token revocation](https://www.rfc-editor.org/info/rfc7009/).
- **S6:** [OWASP Transaction Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html).
- **S7:** [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
- **S8:** [Sigstore verification](https://docs.sigstore.dev/cosign/verifying/verify/).
- **S9:** [SLSA artifact verification](https://slsa.dev/spec/v1.2/verifying-artifacts).
- **S10:** [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/).
- **S11:** [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html).
- **S12:** [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests).
- **S13:** [W3C Trace Context](https://www.w3.org/TR/trace-context/).
- **S14:** [OpenTelemetry GenAI agent spans, Development](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md).
- **S15:** [OWASP Agent Control Standard](https://genai.owasp.org/resource/agent-control-standard-acs/).
- **S16:** [Microsoft MCP Security Gateway draft, pinned revision](https://github.com/microsoft/agent-governance-toolkit/blob/013c7fb44ae589c21488b2746fef9ee44c4f1416/docs/specs/MCP-SECURITY-GATEWAY-1.0.md).
- **S17:** [OpenAI Agent Builder documentation](https://developers.openai.com/api/docs/guides/agent-builder).
- **S18:** [Agent skill vulnerability study](https://arxiv.org/abs/2604.03070).

## Review coverage: all 53 items

Each row records the practical issue checked or clarified. An unchanged item means no design correction was identified in this review; it does not mean an implementation has passed. Use the linked verification guide for procedures and expected evidence.

| Item | Related guidance | Practical review conclusion |
|---|---|---|
| B05 | S1 S6 | Authorize operation, target, and arguments at execution; command-name filtering is insufficient. |
| B02 | S1 S3 | Check destination permissions and tenant isolation with actual issued credentials. |
| B01 | S1 | Inventory every callable path; a model refusing a tool is not enforcement. |
| B03 | S3 S5 | Measure expiry and rotation overlap; do not demand invalidation before an explicitly permitted overlap ends. |
| B04 | S5 | Measure the revocation budget, including cached tokens and existing sessions; refresh-token revocation alone is insufficient. |
| B06 | S6 | Bind approval to the action, check current state, and exercise concurrent replay. |
| B07 | S1 | Include children and in-flight overshoot in a declared budget; no universal safe numerical limit. |
| B08 | S1 S10 | Inspect effective isolation policy as well as probe results; an unavailable endpoint proves little. |
| B09 | S7 | Cover redirects, DNS, IPv6, and unauthorized resources on otherwise allowed services. |
| B10 | S8 S9 | Verify an approved signer and digest; a valid signature is not evidence the artifact is safe. |
| B11 | S10 | Choose isolation for the threat model; ordinary containers and a few access probes do not establish escape resistance. |
| B12 | S1 S9 | Version and review harness/instruction artifacts alongside code and runtime permissions. |
| R11 | S1 | Measure stop time with work in flight; committed external effects require reconciliation. |
| R13 | S11 S13 | Compare audit reconstruction to independent destination state; make unknown outcomes explicit. |
| R01 | S1 S2 | Exercise malformed, oversized, streamed, error, and callback responses at each integration. |
| R02 | S2 | Schema-valid text can still inject instructions; enforce prohibited actions outside the model. |
| R03 | S1 S11 | Test secrets through all output paths and generated content through its downstream interpreter. |
| R04 | S1 S2 | Test ingestion rights, tenant filtering, revocation, derived chunks, and cache propagation. |
| R05 | S1 S2 | Memory is an input boundary; validate writes and scope access across later sessions. |
| R06 | S1 | Retain lineage and test cleanup of derived memory; incomplete lineage limits the cleanup claim. |
| R07 | S14 | BRACE-specific decision-time measurement: report method and uncertainty; usage billing is not necessarily context occupancy. |
| R08 | S1 S11 | Deliver a real test alert to its owner and include a benign control. |
| R09 | S1 | Labeled sequence tests show bounded performance, not detection of every harmful sequence. |
| R10 | S1 | Review observable behavior; test results cannot establish hidden intent or alignment. |
| R12 | S1 S12 | Exercise before/during/after commit; hold ambiguous outcomes with an owner and prevent blind retries. |
| R14 | S8 S11 S12 | Use protected trust state for integrity; replay only within destination idempotency guarantees, otherwise reconcile manually. |
| A01 | S1 S3 | Demonstrate independent agent identity and revocation, not just a label in a user session. |
| A02 | S11 S14 | The exact six fields are a BRACE schema choice; verify completeness on asynchronous and failed actions too. |
| A03 | S9 | Canonical manifest hashing is a BRACE design; opaque model references identify recorded provenance, not invisible weights. |
| A04 | S3 S13 | Trace labels are correlation data, not authentication; derive authoritative identity in a trusted layer. |
| A05 | S1 S11 | Exercise the operator lookup and targeted containment procedure. |
| A06 | S1 S14 | Check nested lineage and authorized retrieval of protected prompts; account for retention and privacy. |
| A07 | S1 S14 | Inventory auxiliary and routing models too; declare provider-hidden details as unknown. |
| C01 | S9 S17 | Manifest must explicitly name model/checkpoint/adapter and training provenance where available; do not invent unavailable provider internals. |
| C03 | S9 | Compare deployment evidence to the manifest; managed aliases limit proof of immutable model identity. |
| C04 | S1 S9 | Exercise drift detection and its response; versioned storage alone does not prove the running state. |
| C02 | S1 S9 | Require review for changes that affect authority, inputs, models, or behavior. |
| C05 | S1 S9 | Explicitly track model, adapter, training-run, and data-reference changes as well as software dependencies. |
| C06 | S1 S2 | Use deployment-specific regression and injection cases; a passing finite suite is bounded evidence. |
| C07 | S1 S9 S12 | Test restart and rollback with state compatibility; a code rollback cannot undo committed external effects. |
| C08 | S11 S14 | Verify retained trace-to-release and prompt references; the exact BRACE join is custom instrumentation. |
| E06 | S3 S4 S16 | Apply HTTP authorization or equivalent local stdio enforcement as appropriate; cover bypass and response paths. |
| E08 | S1 S3 | Exercise privilege escalation through a peer; delegation must not bypass the caller’s authorization. |
| E09 | S1 | Prove the stop reaches remote descendants, queues, credentials, and retries within the chosen budget. |
| E01 | S1 S15 | Assign platform and team responsibilities; an upstream product claim is not implementation evidence. |
| E02 | S1 S8 S9 | Pin observable artifacts, assess maintenance, and record remote implementation limitations. |
| E03 | S4 S16 | Metadata fingerprints detect metadata changes; they cannot attest hidden remote code. |
| E04 | S2 S4 | Scan metadata with a failure policy; scanners have false positives and evasion limits. |
| E05 | S3 S4 | Bind server identity plus tool name; names alone do not establish provenance. |
| E07 | S1 S6 | Authenticate, authorize, validate, and prevent replay of action-bearing peer messages. |
| E10 | S11 S13 S14 | Verify cross-service propagation and protected evidence; standards do not guarantee instrumentation completeness. |
| E11 | S11 | Test retention, access, export, loss detection, and safe behavior when audit capture fails. |
| E12 | S1 S15 | Run a shared-dependency incident drill with affected-instance discovery and accountable responders. |

## Original external-source inventory

This inventory preserves the **pre-review** links, including references replaced during the review. “Retrieved” means a successful HTTP response and a title/content check; it is not a conformance verdict. Core technical conclusions use the primary references and findings above. Additional primary references added during the review appear above rather than changing the original 70-link count.

| Original source | Retrieval and review scope |
|---|---|
| [OWASP AI Vulnerability Scoring System (AIVSS) / OWASP Foundation](https://aivss.owasp.org/) | Retrieved; reference/catalog scope, not deployment verification. |
| [EU Artificial Intelligence Act / Up-to-date developments and analyses of the EU AI Act](https://artificialintelligenceact.eu/) | Retrieved; replaced by official EUR-Lex regulation link; no legal compliance assessment. |
| [2604.03070 How Your Credentials Are Leaked by LLM Agent Skills: An Empirical Study](https://arxiv.org/abs/2604.03070) | Retrieved; study sample and reported statistic checked; generalization narrowed. |
| [MITRE ATLAS™](https://atlas.mitre.org/) | Retrieved; reference/catalog scope, not deployment verification. |
| [AVID](https://avidml.org/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Amazon Bedrock AgentCore - AWS                      x                                           facebook                                           linkedin                                           in](https://aws.amazon.com/bedrock/agentcore/) | Retrieved; reference/catalog scope, not deployment verification. |
| [15 best practices for deploying AI agents in production – n8n Blog](https://blog.n8n.io/best-practices-for-deploying-ai-agents-in-production/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Gemini Enterprise Agent Platform (formerly Vertex AI) / Google Cloud](https://cloud.google.com/products/gemini-enterprise-agent-platform) | Retrieved; reference/catalog scope, not deployment verification. |
| [Agentic AI Threat Modeling Framework: MAESTRO / CSA](https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro) | Retrieved; reference/catalog scope, not deployment verification. |
| [AI FinOps — cost per accepted change & cost per accepted outcomeCost per accepted change formula, rendered as a diagramVerification Triangle — cost vertex highlighted](https://costperacceptedchange.org/) | Retrieved; reference/catalog scope, not deployment verification. |
| [draft-klrc-aiagent-auth-03 - AI Agent Authentication and Authorization](https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Human-in-the-loop for tools / Build / n8n Docsx-twitterdiscordlinkedinyoutube](https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Use external secret stores / Administer / n8n Docsx-twitterdiscordlinkedinyoutube](https://docs.n8n.io/external-secrets/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Handle errors gracefully / Build / n8n Docsx-twitterdiscordlinkedinyoutube](https://docs.n8n.io/flow-logic/error-handling/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Guardrails / Nodes / n8n Docsx-twitterdiscordlinkedinyoutube](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.guardrails/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Set permissions and roles (RBAC) / Administer / n8n Docsx-twitterdiscordlinkedinyoutube](https://docs.n8n.io/user-management/rbac/) | Retrieved; reference/catalog scope, not deployment verification. |
| [What is eval-driven development?](https://evaldrivendevelopment.dev) | Retrieved; reference/catalog scope, not deployment verification. |
| [Lakera – Test your AI hacking skills](https://gandalf.lakera.ai/) | Retrieved; reference/catalog scope, not deployment verification. |
| [LLMRisks Archive - OWASP Gen AI Security Project](https://genai.owasp.org/llm-top-10/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Multi-Agentic system Threat Modeling Guide v1.0 - OWASP Gen AI Security Project](https://genai.owasp.org/resource/multi-agentic-system-threat-modeling-guide-v1-0/) | Retrieved; reference/catalog scope, not deployment verification. |
| [OWASP Top 10 for Agentic Applications for 2026 - OWASP Gen AI Security Project](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - Arize-ai/phoenix: AI Observability & Evaluation · GitHub](https://github.com/Arize-ai/phoenix) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - Helicone/helicone: 🧊 Open source LLM observability platform. One line of code to monitor, evaluate, and experiment. YC W23 🍓 · GitHub](https://github.com/Helicone/helicone) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - NVIDIA-NeMo/Guardrails: NeMo Guardrails is an open-source toolkit for easily adding programmable guardrails to LLM-based conversational systems. · GitHub](https://github.com/NVIDIA-NeMo/Guardrails) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - NVIDIA/garak: the LLM vulnerability scanner · GitHub](https://github.com/NVIDIA/garak) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - cedar-policy/cedar: Implementation of the Cedar Policy Language · GitHub](https://github.com/cedar-policy/cedar) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - cisco-ai-defense/mcp-scanner: Scan MCP servers for potential threats & security findings. · GitHub](https://github.com/cisco-ai-defense/mcp-scanner) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - daytonaio/daytona: Daytona is a Secure and Elastic Infrastructure for Running AI-Generated Code · GitHub](https://github.com/daytonaio/daytona) | Retrieved; README maintenance notice checked; catalog corrected. |
| [GitHub - e2b-dev/E2B: Open-source, secure environment with real-world tools for enterprise-grade agents. · GitHub](https://github.com/e2b-dev/E2B) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - firecracker-microvm/firecracker: Secure and fast microVMs for serverless computing. · GitHub](https://github.com/firecracker-microvm/firecracker) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - google/gvisor: Application Kernel for Containers · GitHub](https://github.com/google/gvisor) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - guardrails-ai/guardrails: Adding guardrails to large language models. · GitHub](https://github.com/guardrails-ai/guardrails) | Retrieved; migration notice checked; catalog corrected. |
| [GitHub - langfuse/langfuse: 🪢 Open source agent evals & observability: Trace, evaluate, and improve LLM applications with one open platform. · GitHub](https://github.com/langfuse/langfuse) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - mem0ai/mem0: The Memory Layer for AI Agents - Drop-in memory infrastructure for AI agents and apps. Context that persists. Built for production. · GitHub](https://github.com/mem0ai/mem0) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - meta-llama/PurpleLlama: Set of tools to assess and improve LLM security. · GitHub](https://github.com/meta-llama/PurpleLlama) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - microsoft/PyRIT: The Python Risk Identification Tool for generative AI (PyRIT) is an open source framework built to empower security professionals and engineers to proactively identify risks ](https://github.com/microsoft/PyRIT) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - microsoft/agent-governance-toolkit: AI Agent Governance Toolkit — Policy enforcement, zero-trust identity, execution sandboxing, and reliability engineering for autonomous AI agents. Covers 1](https://github.com/microsoft/agent-governance-toolkit) | Retrieved; reference/catalog scope, not deployment verification. |
| [agent-governance-toolkit/docs/specs/MCP-SECURITY-GATEWAY-1.0.md at 013c7fb44ae589c21488b2746fef9ee44c4f1416 · microsoft/agent-governance-toolkit · GitHub](https://github.com/microsoft/agent-governance-toolkit/blob/013c7fb44ae589c21488b2746fef9ee44c4f1416/docs/specs/MCP-SECURITY-GATEWAY-1.0.md) | Retrieved; pinned draft specification inspected; no independent conformance claim. |
| [agent-governance-toolkit/docs/specs/MCP-SECURITY-GATEWAY-1.0.md at main · microsoft/agent-governance-toolkit · GitHub](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/specs/MCP-SECURITY-GATEWAY-1.0.md) | Retrieved; pinned draft specification inspected; no independent conformance claim. |
| [GitHub - open-policy-agent/opa: Open Policy Agent (OPA) is an open source, general-purpose policy engine. · GitHub](https://github.com/open-policy-agent/opa) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - openai/openai-guardrails-python: OpenAI Guardrails - Python · GitHub](https://github.com/openai/openai-guardrails-python) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - openfga/openfga: A high performance and flexible authorization/permission engine built for developers and inspired by Google Zanzibar · GitHub](https://github.com/openfga/openfga) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - protectai/llm-guard: The Security Toolkit for LLM Interactions · GitHub](https://github.com/protectai/llm-guard) | Retrieved; archive/maintenance notice checked; catalog corrected. |
| [GitHub - protectai/modelscan: Protection against Model Serialization Attacks · GitHub](https://github.com/protectai/modelscan) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - sigstore/cosign: Code signing and transparency for containers and binaries · GitHub](https://github.com/sigstore/cosign) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - snyk/agent-scan: Security scanner for AI agents, MCP servers and agent skills. · GitHub](https://github.com/snyk/agent-scan) | Retrieved; experimental output warning checked; catalog corrected. |
| [GitHub - splx-ai/agentic-radar: A security scanner for your LLM agentic workflows · GitHub](https://github.com/splx-ai/agentic-radar) | Retrieved; reference/catalog scope, not deployment verification. |
| [GitHub - traceloop/openllmetry: Open-source observability for your GenAI or LLM application, based on OpenTelemetry · GitHub](https://github.com/traceloop/openllmetry) | Retrieved; reference/catalog scope, not deployment verification. |
| [Welcome to the Artificial Intelligence Incident Database](https://incidentdatabase.ai/) | Retrieved; reference/catalog scope, not deployment verification. |
| [What is Microsoft Foundry Agent Service? - Microsoft Foundry / Microsoft Learn](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) | Retrieved; reference/catalog scope, not deployment verification. |
| [What is Microsoft Entra Agent ID? - Microsoft Entra Agent ID / Microsoft Learn](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id) | Retrieved; reference/catalog scope, not deployment verification. |
| [Build AI Agent Loops, with Human-in-the-Loop Guardrails · LoopRails](https://looprails.dev) | Retrieved; reference/catalog scope, not deployment verification. |
| [Build AI Agent Loops, with Human-in-the-Loop Guardrails · LoopRails](https://looprails.dev/) | Retrieved; reference/catalog scope, not deployment verification. |
| [How to Build an AI Kill Switch · LoopRails](https://looprails.dev/article-ai-kill-switch.html) | Retrieved; reference/catalog scope, not deployment verification. |
| [Sandboxes / Modal Docs](https://modal.com/docs/guide/sandbox) | Retrieved; reference/catalog scope, not deployment verification. |
| [https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) | Retrieved; reference/catalog scope, not deployment verification. |
| [https://openai.com/index/introducing-agentkit/](https://openai.com/index/introducing-agentkit/) | Initial retrieval blocked; lifecycle claims checked against official Agent Builder documentation instead. |
| [Moved: Generative AI semantic conventions / OpenTelemetryThe OpenTelemetry Logo](https://opentelemetry.io/docs/specs/semconv/gen-ai/) | Retrieved; reference/catalog scope, not deployment verification. |
| [SAIF: Google's Guide to Secure AI](https://saif.google/) | Retrieved; reference/catalog scope, not deployment verification. |
| [SLSA • Supply-chain Levels for Software Artifacts](https://slsa.dev/) | Retrieved; reference/catalog scope, not deployment verification. |
| [SPIFFE / Secure Production Identity Framework for Everyone](https://spiffe.io/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Trustworthy agents in practice \ Anthropic](https://www.anthropic.com/research/trustworthy-agents) | Retrieved; research guidance distinguished from a managed-product claim. |
| [CISA, US and International Partners Release Guide to Secure Adoption of Agentic AI / CISALock](https://www.cisa.gov/news-events/news/cisa-us-and-international-partners-release-guide-secure-adoption-agentic-ai) | Retrieved; reference/catalog scope, not deployment verification. |
| [Cisco AI Defense and Advanced Threat Prevention - CiscoCisco.com Worldwide](https://www.cisco.com/site/us/en/products/security/ai-defense/index.html) | Retrieved; reference/catalog scope, not deployment verification. |
| [Home - Coalition for Secure AI](https://www.coalitionforsecureai.org/) | Retrieved; reference/catalog scope, not deployment verification. |
| [Just a moment...](https://www.iso.org/standard/42001) | Initial retrieval blocked; public metadata subsequently inspected; full standard not reviewed. |
| [Just a moment...](https://www.iso.org/standard/77304.html) | Initial retrieval blocked; public metadata subsequently inspected; full standard not reviewed. |
| [Lakera: The AI-Native Security Platform to Accelerate GenAI](https://www.lakera.ai/) | Retrieved; reference/catalog scope, not deployment verification. |
| [AI Agent Standards Initiative / NISTLock](https://www.nist.gov/caisi/ai-agent-standards-initiative) | Retrieved; reference/catalog scope, not deployment verification. |
| [AI Risk Management Framework / NISTLock](https://www.nist.gov/itl/ai-risk-management-framework) | Retrieved; reference/catalog scope, not deployment verification. |

## Reverification policy

Repeat source/lifecycle checks when adopting or upgrading a dependency and when a linked draft changes. Repeat applicable checklist tests on the deployed release after security-relevant changes. Retain dated evidence, version identifiers, known visibility limits, and an owner for unresolved gaps; a source’s continued availability does not keep a prior test result current.
