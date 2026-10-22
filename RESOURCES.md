# BRACE Resources

Resources for putting BRACE’s controls in place. Use the standards and threat models to understand risks. Use the reference designs to see ways to build. Use the software components to build and test your controls.

Each entry is tagged with the BRACE concern it most relates to: **Build-time · Run-time · Agent · Config · Ecosystem · Observability · Governance**. Status flags: **Open source · Commercial · Free · Emerging · Deprecating** (or **Unmaintained repository**).

> Source review: 2026-09-16; sources rechecked 2026-09-30; MCP references updated 2026-10-16; all 53 recommendations re-researched 2026-10-22 (BRACE 2.0.1). See [scope, findings, and verification limits](SOURCE-REVIEW.md). **Listing is not endorsement.** This field changes fast, so check an entry’s status before you rely on it. The website version of this list is at <https://braceframework.org/resources/>. Know something we should add? [Suggest a resource](https://github.com/brace-ai-security/brace/issues/new?template=get-listed.yml).

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
| [NIST CAISI — AI Agent Standards Initiative](https://www.nist.gov/caisi/ai-agent-standards-initiative) | NIST’s program for agentic-AI interoperability and security standards. Published RFI/comment summaries and draft project work inform it; they are not a final agent-security standard. Track its current publications and maturity. | Agent · Ecosystem | Free · Emerging |
| [Coalition for Secure AI (CoSAI)](https://www.coalitionforsecureai.org/) | Open collaboration publishing AI security guidance and work on agent identity, delegation, and sandboxing. Consult each publication for its scope and maturity. | Agent · Ecosystem · Build-time | Free |

## Security reference refresh: 2026-10-22

Re-researched all 53 recommendations for BRACE **2.0.1**. The [dated review](RESEARCH-2026-10-22.md) records per-item assessments, precise package ranges, required configuration/migration and evidence limits. Dates below are publication dates unless labeled otherwise. Advisories predating October 16 are historical omissions discovered now. Fixed versions address the named issue, not every vulnerability. None establishes that a BRACE deployment is affected without checking its dependencies and exposed features.

High-risk reports describe evidence, gaps and unknowns without a BRACE release verdict. Accountable people own any gradual, closely monitored rollout. Proposed technical refinements remain discussion inputs.

| Primary reference | Date | Relevance and limits |
|---|---|---|
| [ASD/ACSC: Agentic AI harnesses](https://www.cyber.gov.au/advisory/agentic-ai-harnesses) | 2026-09-11 | Harness, context, connector and update-path controls. Government guidance; historical addition. |
| [Joint Careful adoption guidance: coauthor full text](https://www.cyber.gov.au/publication/careful-adoption-of-agentic-ai-services) | 2026-05-01 | Rechecked: recommends low-risk, non-sensitive tasks; does not endorse high-risk deployment. |
| [CERT-In CIAD-2026-0049](https://www.cert-in.org.in/s2cMainServlet?VLCODE=CIAD-2026-0049&pageid=PUBVLNOTES02) | 2026-10-15 | Task-scope violations, credential reuse, live monitoring and independent stopping; government advisory. |
| [UK AISI unsanctioned cyber-evaluation incident](https://www.aisi.gov.uk/blog/incident-report-unsanctioned-agent-behaviour-during-cyber-testing) | Incident 2026-07-28; publication unconfirmed | Permissive evaluation, cyber filters disabled; allowed internet use, not sandbox escape. |
| [NIST AI 800-5: agent-security RFI response analysis](https://www.nist.gov/publications/summary-analysis-responses-request-information-regarding-security-considerations-ai) | 2026-05-18 | Stakeholder-response analysis, not a final agent-security standard. |
| [NCCoE identity and authorization comment summary](https://pages.nist.gov/nccoe-ai-identity/summary-of-comments.html) | Announced 2026-09-29 | Stable trust anchors, ephemeral credentials and task authority; feedback, not certification. |
| [Agent Security Requirements draft -02](https://datatracker.ietf.org/doc/draft-ni-a2a-ai-agent-security-requirements/02/) | 2026-10-21 | Individual Internet-Draft; work in progress, no IETF endorsement. |
| [Microsoft: Securing the agentic insider](https://blogs.microsoft.com/blog/2026/10/19/securing-the-agentic-insider/) | 2026-10-19 | Contemporary vendor position on containment; guardian-model effectiveness is not independently established. |
| [MCP TS shared-server isolation: GHSA-jm63-cq47-j5jp](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-jm63-cq47-j5jp) | 2026-10-15 | Server 2.3.0 plus factory/lifecycle changes; HTTP client isolation. |
| [MCP TS validation exhaustion: GHSA-46jr-4wx8-v453](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-46jr-4wx8-v453) | 2026-10-15 | SDK 1.32.0/server 2.3.0; explicitly enable maxToolInputElements and body limits. |
| [MCP TS body/batch exhaustion: GHSA-f897-62hf-6gxq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq) | 2026-10-15 | Body and batch limits; fixes differ across sdk/server/node/hono packages. |
| [MCP TS issuer binding: GHSA-6qxp-vccf-f47h](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h) | 2026-09-30 | Upgrade, expectedIssuer and saved-registration binding/cleanup; assess credential exposure. |
| [MCP TS audience validation: GHSA-rvq5-wwqv-78pq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq) | 2026-10-05 | Enable expectedResource and verified AuthInfo.resource, or enforce audience in custom verifier. |
| [MCP TS redirects: GHSA-6prh-2h8m-c8cw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw) | 2026-10-02 | Custom headers/request bodies crossing origins; issue-specific SDK/client fixes. |
| [MCP TS experimental tasks: GHSA-22jm-h49p-29qw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-22jm-h49p-29qw) | 2026-10-02 | Old shared taskStore isolation; distinct from redesigned protocol Tasks. |
| [MCP Python issuer binding: GHSA-qx49-fqc8-xw99](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-qx49-fqc8-xw99) | 2026-09-28 | mcp 1.30.0/2.2.0 plus issuer configuration and stored-registration cleanup. |
| [MCP Python audiences: GHSA-w4fh-qvv9-3v23](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-w4fh-qvv9-3v23) | 2026-10-05 | Enable resource validation and verified AccessToken.resource after upgrading. |
| [MCP Python schema resolution: GHSA-rwrf-2pqf-9j8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-rwrf-2pqf-9j8j) | 2026-09-28 | Remote output-schema references trigger I/O; SSRF/stalling, not proven file exfiltration. |
| [MCP Python redirects: GHSA-5h93-6whr-6q8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-5h93-6whr-6q8j) | 2026-10-02 | Cross-origin custom headers and bodies; final endpoints and redirect policy matter. |
| [MCP Python body exhaustion: GHSA-fmmv-w9g8-j3gc](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-fmmv-w9g8-j3gc) | 2026-09-30 | Unauthenticated request-body allocation; verify parser/proxy limits too. |
| [Splunk MCP SVD-2026-1004](https://advisory.splunk.com/advisories/SVD-2026-1004) | 2026-10-07 | Tool administrator changes token destination; victim execution also required. Fixed 1.2.1. |
| [vLLM image dispatch: GHSA-h3rc-j82p-2c3h](https://github.com/vllm-project/vllm/security/advisories/GHSA-h3rc-j82p-2c3h) | 2026-10-20 | EPS mislabeled PNG; conditional Ghostscript RCE. Issue fix 0.32.0; prerequisites matter. |
| [vLLM audio OOM: GHSA-8397-8qf6-f2gm](https://github.com/vllm-project/vllm/security/advisories/GHSA-8397-8qf6-f2gm) | 2026-10-20 | Phi-4 multimodal GPU exhaustion within default audio bounds; fixed 0.32.0. |
| [vLLM token validation: GHSA-q97c-p368-75c4](https://github.com/vllm-project/vllm/security/advisories/GHSA-q97c-p368-75c4) | 2026-10-20 | Out-of-range token IDs can crash shared engines; fixed 0.32.0. |
| [vLLM CORS/no-auth: GHSA-vvpg-rrww-wpmh](https://github.com/vllm-project/vllm/security/advisories/GHSA-vvpg-rrww-wpmh) | 2026-10-20 | Browser access to local/internal unauthenticated endpoints; fixed 0.32.0, configure access controls. |
| [Cosign legacy blob bundles: GHSA-fx35-mq7g-6g98](https://github.com/sigstore/cosign/security/advisories/GHSA-fx35-mq7g-6g98) | 2026-08-06 | Fixed 2.6.5/3.1.3; OCI verification and modern protobuf bundles explicitly unaffected. |
| [VS Code lifecycle hooks: GHSA-w79w-rj9h-vg4f](https://github.com/microsoft/vscode/security/advisories/GHSA-w79w-rj9h-vg4f) | 2026-08-11 | Injected custom-agent hooks execute later; fixed 1.132.1. |
| [LangChain filesystem boundary: GHSA-gr75-jv2w-4656](https://github.com/langchain-ai/langchain/security/advisories/GHSA-gr75-jv2w-4656) | 2026-06-12 | Glob, symlink and path-resolution bypasses; package-specific fixes. |
| [LangChain constructor loading: GHSA-pjwx-r37v-7724](https://github.com/langchain-ai/langchain/security/advisories/GHSA-pjwx-r37v-7724) | 2026-05-05 | Structured-object reconstruction is executable under affected APIs; not arbitrary pickle loading. |
| [LangChain image token counting: GHSA-r7w7-9xr2-qq2r](https://github.com/langchain-ai/langchain/security/advisories/GHSA-r7w7-9xr2-qq2r) | 2026-04-16 | DNS rebinding in helper fetches; blind probing, not demonstrated image exfiltration. |
| [runc rootfs setup: GHSA-xjvp-4fhw-gc47](https://github.com/opencontainers/runc/security/advisories/GHSA-xjvp-4fhw-gc47) | 2026-06-13 | Orchestrator-dependent host integrity issue; advisory explicitly excludes Docker exploitation. |
| [PyTorch weights-only: GHSA-53q9-r3pm-6pq6](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6) | 2025-04-17 | Historical RCE fixed 2.6.0; clean scans and weights-only remain bounded defenses. |
| [LangGraph namespace collision: GHSA-6hmw-9432-67qq](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-6hmw-9432-67qq) | 2026-10-21 | Postgres 3.1.3/SQLite 3.1.2, checkpoint 4.3.0; batch/async namespace isolation. |
| [LangGraph deploy token logs: GHSA-8prr-f582-jqq3](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-8prr-f582-jqq3) | 2026-10-19 | Local verbose deploy exposed temporary registry tokens; CLI fix 0.4.32. |
| [LangGraph streaming paths: GHSA-3fx2-cqw9-xr3c](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-3fx2-cqw9-xr3c) | 2026-10-07 | Authenticated GET path confusion; SDK 0.4.6/langgraph 1.2.14, not arbitrary-host writes. |
| [LangGraph auth-hook rewriting: GHSA-4hm6-w6qq-w73v](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-4hm6-w6qq-w73v) | 2026-09-28 | JS/TS namespace transformations lost before Store access; API fix 0.15.0. |
| [LangGraph checkpoint revival: GHSA-fjqc-hq36-qh5p](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-fjqc-hq36-qh5p) | 2026-05-22 | Checkpoint fix 4.1.1; requires unauthorized store writes, defense-in-depth advisory. |
| [Self-Propagating Misalignment](https://arxiv.org/abs/2610.04083) | 2026-10-02 | Induced laboratory persistence through memory and files; not spontaneous deployment prevalence. |
| [Anthropic self-replication experiments](https://www.anthropic.com/research/self-replicating-ai) | 2026-10-12 | Simplified lab experiments; scope kill claims to governed assets and credentials. |
| [Microsoft: Guarding AI memory](https://www.microsoft.com/en-us/security/blog/2026/06/22/guarding-ai-memory/) | 2026-06-22 | Delayed cross-session influence; vendor-authored guidance, not independent certification. |
| [MemSecBench](https://arxiv.org/abs/2607.27080) | 2026-07-29 | Evaluate persistence, downstream behavior and selective cleanup separately; preprint. |
| [Utility Under Attack](https://arxiv.org/abs/2608.21230) | 2026-08-21 | Factual memory poisoning and utility tradeoffs; evaluated defenses, not universal rankings. |
| [Skills over MCP](https://modelcontextprotocol.io/extensions/skills/overview) | Checked 2026-10-22; publication unconfirmed | Optional extension: origin, activation, manifest/file integrity and cache approval boundaries. |
| [OWASP RAG Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/RAG_Security_Cheat_Sheet.html) | Living guidance; checked 2026-10-22 | Chunk/cache permissions, source provenance, revocation and safe audit collection. |
| [OWASP Secure AI Model Ops](https://cheatsheetseries.owasp.org/cheatsheets/Secure_AI_Model_Ops_Cheat_Sheet.html) | Living guidance; checked 2026-10-22 | Model lifecycle, deployment, drift and operational security practices. |
| [OWASP Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html) | Living guidance; checked 2026-10-22 | Dependency/build/update provenance and lifecycle controls; no deployment certification. |
| [CycloneDX ML-BOM](https://cyclonedx.org/capabilities/mlbom/) | Living specification documentation; checked 2026-10-22 | Represent model, dataset and configuration provenance; a BOM is not authentication. |

## MCP security: specifications, deployment practice, and research

MCP sources checked 2026-10-16. Protocol requirements, optional extensions, industry profiles, deployment reports and experimental defenses have different authority. No resource listing certifies a gateway or deployment. Benchmark results depend on their models, versions and attacker assumptions; no combined production attack rate is claimed.

### Protocol and authorization specifications

| Reference | Scope and limits | Evidence type |
|---|---|---|
| [MCP authorization, 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization) | Protocol requirements for protected HTTP access: discovery, resource indicators, issuer validation and audience-bound access tokens. Authorization is optional in MCP itself; BRACE requires it for protected tools. | Specification |
| [MCP Streamable HTTP, 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) | Transport requirements, Origin validation, and matching request metadata headers to the body. Check the negotiated version before applying legacy session rules. | Specification |
| [MCP security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) | Official guidance on confused deputies, token passthrough, SSRF, local process risks and scope minimization. A separate backend needs its own authorized credentials. | Official guidance |
| [RFC 9700: OAuth security best current practice](https://www.rfc-editor.org/rfc/rfc9700.html) | OAuth security baseline for grants, redirect handling, token protection and deployment threat models. | IETF BCP |
| [RFC 8693: OAuth token exchange](https://www.rfc-editor.org/rfc/rfc8693.html) | Standardized exchange where supported. Distinguishes original subject, current actor and prior actor history; prior nested actors grant no extra authority. | IETF RFC |
| [MCP Enterprise-Managed Authorization](https://modelcontextprotocol.io/extensions/auth/enterprise-managed-authorization) | Stable optional extension for enterprise IdP-managed access. Requires compatible clients, servers and identity infrastructure; not a guarantee of immediate revocation of existing tokens. | Stable extension |
| [MCP OAuth Client Credentials](https://modelcontextprotocol.io/extensions/auth/oauth-client-credentials) | Draft optional extension for machine-to-machine access. Client authentication and resource access tokens are distinct; confirm support and draft version before deployment. | Draft extension |
| [MCP Apps security model](https://apps.extensions.modelcontextprotocol.io/api/documents/overview.html) | Host-rendered UI adds iframe sandbox, CSP, bridge-message and UI-triggered tool-call boundaries. A remote gateway cannot enforce every host-side control. | Extension documentation |

### Deployment guidance and architecture reports

| Reference | Scope and limits | Evidence type |
|---|---|---|
| [CoSAI MCP Security v2.0](https://www.coalitionforsecureai.org/mcp-security-version-2-0-from-threat-taxonomy-to-a-model-you-can-actually-audit-against/) | August 2026 update with deployment-specific assurance profiles and explicit state/extension controls. These profiles supplement the protocol; choosing a topology does not establish assurance. | Industry guidance |
| [OWASP MCP Top 10](https://owasp.org/projects/mcp-top-10) | MCP risk taxonomy covering credential handling, privilege escalation, poisoning, supply chain, injection, authorization and telemetry; not a gateway certification. | Threat taxonomy |
| [OWASP secure MCP server development](https://genai.owasp.org/resource/a-practical-guide-for-secure-mcp-server-development/) | February 2026 development guidance covering identity, access control, validation, isolation and hardened deployment. Interpret version-specific session advice against the protocol actually deployed. | Industry guidance |
| [OWASP using third-party MCP servers](https://genai.owasp.org/resource/cheatsheet-a-practical-guide-for-securely-using-third-party-mcp-servers-1-0/) | Guidance for evaluating and operating external integrations, including supply-chain and tool/content risks. | Industry guidance |
| [Uber: Solving the Identity Crisis for AI Agents](https://www.uber.com/us/en/blog/solving-the-agent-identity-crisis/) | May 2026 report on verified agent/workload binding and short-lived per-hop credentials preserving delegation context. Its customized exchange is not itself an MCP standard. | Deployment report |
| [Uber: Designing MCP Gateway](https://www.uber.com/us/en/blog/designing-mcp-gateway/) | October 2026 report on registry/control and proxy/data planes, disabled-by-default tools, owner-approved changes and gateway-routed CLI calls. Reported deployment practices, not independently verified security results. | Deployment report |
| [Microsoft Agent Governance Toolkit gateway design](https://developer.microsoft.com/blog/securing-mcp-a-control-plane-for-agent-tool-execution/) | Project-specific interception, policy and inspection architecture. Its gateway specification is a design reference, not a universal MCP conformance standard. | Implementation reference |
| [agentgateway: backend token exchange](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/token-exchange/standard/) | Implementation documentation for backend-scoped RFC 8693 exchange. Verify issuer support, TLS, audience, resource and scope settings in the deployed configuration. | Implementation reference |
| [Docker MCP Gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/) | Container-backed server lifecycle, routing and credential management. Verify actual permissions and network policy; gateway presence alone does not establish poisoning resistance. | Implementation reference |

### Research and evaluation

| Reference | Scope and limits | Evidence type |
|---|---|---|
| [MCPTox](https://arxiv.org/abs/2508.14925) | Benchmark of poisoned tool metadata on real MCP servers/tools. Use its attack cases to test behavior before tool invocation, not as a production compromise-rate estimate. | Benchmark |
| [MCP-SafetyBench](https://arxiv.org/abs/2512.15163) | Multi-step and cross-server attack evaluation across five domains. Model, server, version and attacker assumptions matter when transferring results. | Benchmark |
| [MCP Security Bench](https://arxiv.org/abs/2510.15994) | Real-tool attack harness measuring security alongside successful task completion. Useful for checking defenses that otherwise block legitimate work. | Benchmark |
| [MCPXKIT](https://arxiv.org/abs/2508.12538) | Attack taxonomy, unified toolkit and empirical analysis spanning MCP components. Consult the evaluated version and attacker assumptions. | Research |
| [MCPZoo and scanner reliability](https://arxiv.org/abs/2607.11086) | Runtime-server study finding scanner disagreement, false positives and missed vulnerabilities in its evaluated sample. Metadata-only alerts and clean scans need concrete validation. | Research |
| [MCP Pitfall Lab](https://arxiv.org/abs/2604.21477) | Combines supply-chain artifacts, hardening cases and runtime traces; cross-tool forwarding and image-mediated leakage need dataflow evidence beyond metadata. | Research |
| [AEGIS: cross-domain resource abuse](https://arxiv.org/abs/2608.20481) | Research on mapping tool invocations to enforceable resource policies. A proposed defense architecture, not a protocol requirement or proof of general effectiveness. | Research |
| [Enterprise MCP authentication architecture](https://arxiv.org/abs/2608.10760) | Explores heterogeneous authentication, identity delegation and interactive-user versus automated-agent personas. Separate its proposed architecture from interoperable protocol requirements. | Research |
| [MCP landscape and threat survey](https://arxiv.org/abs/2503.23278) | Lifecycle threat analysis spanning creation, deployment, operation and maintenance. Older protocol-specific conclusions need comparison with 2026-07-28. | Survey |

### Original attack and vulnerability disclosures

| Reference | Scope and limits | Evidence type |
|---|---|---|
| [Invariant: MCP tool poisoning](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks) | Original demonstrations of malicious tool descriptions, cross-tool influence and changes after approval. Metadata can affect an agent before the poisoned tool executes. | Attack demonstration |
| [Invariant: GitHub toxic flow](https://invariantlabs.ai/blog/mcp-github-vulnerability) | Demonstrates an injected public issue steering authorized tools toward private-data disclosure. Authentication does not establish that a tool sequence serves the approved task. | Attack demonstration |
| [Trail of Bits MCP research](https://blog.trailofbits.com/categories/mcp/) | Original reports on pre-invocation injection, conversation theft, deceptive terminal rendering and insecure credential storage. | Security research |
| [JFrog: mcp-remote CVE-2025-6514](https://research.jfrog.com/vulnerabilities/mcp-remote-command-injection-rce-jfsa-2025-001290844/) | Historical command-injection disclosure in authorization-endpoint handling. Shows why client adapters and discovery are part of the executable attack surface. | Vulnerability disclosure |
| [Pillar: Deadbugz MCP supply-chain campaign](https://www.pillar.security/blog/deadbugz-currently-active-mcp-supply-chain-campaign) | Researcher-reported campaign distributing malicious MCP installation configuration through pull requests. Review configuration and launch commands as executable supply-chain inputs. | Incident report |

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
| [Snyk Agent Scan](https://github.com/snyk/agent-scan) | Scanner for agent components, MCP servers, and skills. The repository warns that raw CLI output fields and risk labels are experimental, and that the v0.5.x CLI line is planned for deprecation. Don’t build production workflows on that output. Scanning executes configured stdio commands and sends configured remote credentials: contain untrusted configurations before scanning. | Ecosystem | Open source |
| [Cisco MCP Scanner](https://github.com/cisco-ai-defense/mcp-scanner) | Discovers MCP tools and scans descriptions/schemas with YARA rules for injection, tool poisoning, credential harvesting, and code execution. | Ecosystem | Open source |
| [Agentic Radar](https://github.com/splx-ai/agentic-radar) | Static scanner for agentic workflows (LangGraph, CrewAI, OpenAI Agents). Maps tools, detects MCP servers, and reports known vulnerabilities. Verify current maintenance and advisory status before adoption; this review did not re-establish the last-commit date. | Ecosystem · Run-time | Open source |

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
