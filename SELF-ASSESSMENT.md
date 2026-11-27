# BRACE self-assessment and vendor evaluation

Use this worksheet to score the same **53 items** as the [BRACE sign-off checklist](CHECKLIST.md), across **Build-time, Run-time, Agent, Configuration, and Ecosystem**. The checklist holds the full requirements, the hard parts, fallbacks, and tradeoffs you can accept. The [verification guide](CHECKLIST-VERIFICATION.md) gives each item a test, the result to expect, and the evidence to keep.

Part of the BRACE Project. License: CC BY 4.0.

Scores and completed controls do not establish safety. For how BRACE words results for high-risk and lower-risk deployments, see [How results are worded](TOOLS.md#how-results-are-worded).

## How to use this

Assess a named release and environment. Or ask a vendor to show each requirement working in the setup you would actually use. Read the full checklist item before you score its short label below. Record what the agent team owns and what the platform or vendor owns, separately. Then score the combined evidence for the deployment.

### Scoring and checklist outcomes

| Score | Meaning | Checklist outcome |
|---|---|---|
| **2 — Yes** | The full requirement is in place and shown with evidence. | Pass |
| **1 — Partial** | Evidence shows only part of the requirement, or only part of the deployment. | Gap |
| **0 — No** | The requirement is missing or can't be shown. A claim alone earns no credit. | Gap |
| **N/A** | The feature or exposure doesn't exist, with evidence and an approved reason. | N/A; leave out of the score denominator |

A fallback earns 2 only when you can show it meets the requirement for the setup you assessed. Accepted risk does not turn a Partial or No into a Yes. Label details a provider doesn't share as hidden. Apply the model record and pinning rules in C01 and C05. Score the evidence you have, and never make up missing version details.

### Priority gates

The **Blocker/Required/Detection** labels match the checklist's evidence requirements and lower-risk record gates. They do not authorize high-risk releases. **Obs-T1/Obs-T2/Obs-T3** name observability requirements, not gates.

- **Blocker:** Every applicable item must score 2 to meet this evidence requirement; retain each Partial or No as an open finding.
- **Required:** Every applicable item must score 2, or have a written, approved risk acceptance.
- **Detection:** For high-stakes or high-autonomy deployments, report every applicable score and retain Partial or No as an open finding. For lower-stakes deployments, a Partial or No needs a written, approved risk acceptance.

Rate the deployment's stakes and autonomy before you judge any gaps. Record owners, evidence, N/A approvals, and exceptions in the [checklist records](CHECKLIST.md#evidence-and-exception-record). Using a vendor's service doesn't make its part of a control N/A.

## Assessment worksheet

For each row, ask: **Does this deployment meet the full checklist requirement, and can we show it?** Add a score and a link to the evidence or gap. The short labels help you find each item. Score against its full requirement.

### B — Build-time

**IF YOU DO NOTHING ELSE — TOP 3:** **B05 — Destructive-action interception**; **B02 — Least-privilege access**; **B01 — Minimal tool surface**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#b--build-time) · [Verification recipes](CHECKLIST-VERIFICATION.md#b--build-time)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| B01 | Blocker | C4 | Minimal tool surface | | |
| B02 | Blocker | C2 | Least-privilege access | | |
| B03 | Required | C2 | Credential lifetime and handling | | |
| B04 | Blocker | C2 | Independent revocation | | |
| B05 | Blocker | C4 | Destructive-action interception | | |
| B06 | Blocker | C4 | Approval integrity | | |
| B07 | Required | C4 | Hard execution budgets | | |
| B08 | Required | C1 | Environment isolation | | |
| B09 | Required | C1 | Egress allowlist | | |
| B10 | Required | C3 | Pinned, verified image | | |
| B11 | Required | C3 | Minimal, isolated runtime | | |
| B12 | Blocker | C4 | Reviewed harness and instructions | | |

### R — Run-time

**IF YOU DO NOTHING ELSE — TOP 3:** **R11 — Tested kill switch**; **R13 — Full execution audit**; **R01 — Validate every input boundary, including API responses**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#r--run-time) · [Verification recipes](CHECKLIST-VERIFICATION.md#r--run-time)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| R01 | Required | C5 | Validate every input boundary, including API responses | | |
| R02 | Required | C5 | Separate data from instructions and test injection containment | | |
| R03 | Required | C5/C9 | Prevent output and log leakage | | |
| R04 | Required | C5/C6 | Retrieval-corpus integrity | | |
| R05 | Detection | C6 | Memory isolation and write validation | | |
| R06 | Detection | C6 | Memory provenance and cleanup | | |
| R07 | Required | Obs-T2 | Decision-time context size | | |
| R08 | Detection | C7 | Security monitoring | | |
| R09 | Detection | C7/Obs-T2 | Sequence and context-aware detection | | |
| R10 | Detection | C7 | Misaligned-behavior review | | |
| R11 | Blocker | C8 | Tested kill switch | | |
| R12 | Blocker | C8 | Safe state after stopping | | |
| R13 | Blocker | C9 | Full execution audit | | |
| R14 | Required | C9 | Recovery integrity | | |

### A — Agent

**IF YOU DO NOTHING ELSE — TOP 3:** **A01 — Distinct agent identity**; **A02 — All six identity fields**; **A03 — Content-derived type identity**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#a--agent) · [Verification recipes](CHECKLIST-VERIFICATION.md#a--agent)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| A01 | Blocker | C2/Obs-T1 | Distinct agent identity | | |
| A02 | Blocker | Obs-T1 | All six identity fields | | |
| A03 | Blocker | Obs-T1 | Content-derived type identity | | |
| A04 | Blocker | C9/Obs-T1 | Trustworthy attribution | | |
| A05 | Blocker | C8/C9/Obs-T1 | Operational lookup | | |
| A06 | Detection | Obs-T3 | Parent and prompt provenance | | |
| A07 | Detection | C7/Obs-T1 | Every model in the loop | | |

### C — Configuration

**IF YOU DO NOTHING ELSE — TOP 3:** **C01 — Complete release manifest**; **C03 — Match release identity to running state**; **C04 — Detect drift per agent**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#c--configuration) · [Verification recipes](CHECKLIST-VERIFICATION.md#c--configuration)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| C01 | Required | C1–C6/Obs-T1 | Complete release manifest | | |
| C02 | Required | C1–C7 | Review security-relevant changes | | |
| C03 | Blocker | Obs-T1 | Match release identity to running state | | |
| C04 | Required | C1/C3/C4/Obs-T1 | Detect drift per agent | | |
| C05 | Required | C3/C4/C7 | Control dependency, model, and training changes | | |
| C06 | Required | C4–C9 | Re-test changed behavior | | |
| C07 | Required | C8/C9 | Rollback and restart | | |
| C08 | Required | Obs-T1/Obs-T2/Obs-T3 | Connect configuration to execution | | |

### E — Ecosystem

**IF YOU DO NOTHING ELSE — TOP 3:** **E06 — Enforced gateway boundary**; **E08 — Bounded delegated authority**; **E09 — Recursive shutdown**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#e--ecosystem) · [Verification recipes](CHECKLIST-VERIFICATION.md#e--ecosystem)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| E01 | Required | C1–C9 | Map shared responsibilities | | |
| E02 | Required | C3/C5 | Vet and pin dependencies | | |
| E03 | Required | C5 | Re-check tools on load | | |
| E04 | Required | C5 | Inspect tool metadata | | |
| E05 | Required | C2/C5 | Verified, namespaced tools | | |
| E06 | Required | C1/C2/C4/C5/C9 | Enforced gateway boundary | | |
| E07 | Required | C2/C5 | Untrusted peer messages | | |
| E08 | Blocker | C2/C4 | Bounded delegated authority | | |
| E09 | Blocker | C8 | Recursive shutdown | | |
| E10 | Blocker | C9/Obs-T1 | Audit across service boundaries | | |
| E11 | Required | C9 | Protect shared evidence | | |
| E12 | Detection | C7/C8 | Fleet incident response | | |

## Reading your score

With all 53 items applicable, the maximum is **106 points**. If some items have approved N/A results, use:

**Coverage score = points earned / (2 × number of applicable items).**

Report the number of applicable items, the N/A count, the points earned, and the denominator together. If no items apply, there is no score. Recheck the assessment scope instead of reporting readiness. Compare scores only when the scope and N/A decisions match.

The score tracks what you have shown is in place. It is not a security rating, and it does not approve a release. Report the number of open Blocker gaps and the status of Required and Detection exceptions separately. A high score can't make up for one blocker. A risk acceptance doesn't remove the gap from the score.

Finish with the [checklist's final sign-off](CHECKLIST.md#final-sign-off), including the next review date and what triggers a new review. Recheck the agent's powers on that schedule and remove access it no longer needs. Re-test after changes that matter.

## Using this to evaluate a vendor

- Ask for concrete artifacts: scoped access-token and delegation metadata, front/back audience checks, owner-approved tool versions, cross-tenant cache/task denials, alternative-path and outage tests, release/model manifests, drill results, and traces that show who did what.
- Ask which controls the platform supplies and which your team must set up or build. A platform feature that is turned off in your deployment does not pass.
- For hosted models, ask for the version details the provider shares. Keep them apart from pretraining history it doesn't share. For fine-tuning you run yourself, keep your job and dataset records, even if the base-model provider keeps theirs private.
- Discuss the notes under the harder checklist items. Name the limits and the costs you accept. Then record any allowed risk acceptance, with an owner and approver.
- Treat missing required evidence as a gap. If it blocks sign-off, cut the deployment's actual powers or choose an integration that can meet the requirement. Then re-test.

## Assessing a vendor

**Vendor worksheet reviewed:** 2026-09-16; sources rechecked 2026-09-30. See the [source review](SOURCE-REVIEW.md).

Use this worksheet to ask for, and record, evidence for each BRACE control. A product having a feature does not prove the control is turned on, set up correctly, or complete in your deployment. This worksheet does not rank vendors or give them checkmarks. Those claims would need a current comparison that others can repeat.

Use the [53-item checklist](CHECKLIST.md), its [verification recipes](CHECKLIST-VERIFICATION.md), and the scoring worksheet above. Test the exact product version, plan, region, and configuration you will use. For each deployment, record **demonstrated**, **partial**, **not demonstrated**, or **not applicable, with a reason**. These are evidence results, not vendor rankings.

### Per-control evidence matrix

| BRACE control | Checklist items | Evidence required from vendor and deployment owner |
|---|---|---|
| C1 — Architecture | B08–B09; E06 | Actual network routes, tenant isolation, egress and SSRF controls, and bypass test results. Calling a service "managed" does not prove where its boundary is. |
| C2 — Capability-scoped access | B02–B04; A01; E05–E08 | Separate acting-agent and delegated-subject identities, actual grants, front/back token audiences, supported exchanges, static-key exceptions, and measured revocation time, including caches and open work. |
| C3 — Container | B10–B11; E02 | Build provenance, checks against an approved signer, runtime isolation design, and the split of duties between customer and provider. Managed infrastructure may limit what you can inspect directly. |
| C4 — Harness | B01; B05–B07; B12; E06; E08 | Versioned policies, enforcement on operation and arguments, approval replay tests, hard limits, and every other path that can run the same action. |
| C5 — Data | R01–R04; E02–E07 | Input checks at each boundary, retrieval permissions, reviewed tool publication and rollback, scanner false positives/misses, and containment when injection detection misses. |
| C6 — Memory | R04–R06 | Scope enforcement, records of each entry's source and writer, revocation, cleanup, and how summaries and caches are handled. |
| C7 — Behavioral | R08–R10; A07; E12 | Written detection claims, measured misses and false alarms, identities of checker models, and responder drills. |
| C8 — Kill switch | R11–R12; A05; E09; E12 | Measured stop time across sub-agents, streams, queues, and disconnected workers. Reconciliation for effects that already happened. |
| C9 — Audit trail | R03; R13–R14; A04–A05; E06; E10–E11 | Linked records of actions and results, protected retention, integrity checks against a separate trust anchor, and handling of unclear results and replays. |
| Obs-T1 — Six identity fields | A01–A05; A07; C01; C03–C04; C08; E10 | Accountable party, operational owner, tenant, type hash, instance ID, and trace context. Fields that only link records do not prove who an agent is. |
| Obs-T2 — Context size | R07; R09; C08 | How full the context was, in tokens, at each decision. Include the counting method, limits of any estimate, and values marked unknown. Billing totals alone may not be enough. |
| Obs-T3 — Parent/prompt provenance | A06; C08 | Parent-child trace links, and the prompt the parent passed (or a protected reference to it). Show that links survive handoffs and that access is controlled. |

E01 and the Configuration items (C01–C08) apply across the whole matrix, including model records and the history of training you run yourself. A vendor may cover only part of an item. Name who builds and checks the rest. No product listing changes the checklist's Blocker/Required/Detection rules.

### MCP gateway deployment evidence

Record the deployment pattern: internal HTTP, public third-party service, or local stdio. Request the protocol/extension versions, owner-approved tool inventory, publication/config propagation and rollback evidence, and policy tests for direct, dynamic, CLI/code-mode, and wrapper calls. Verify gateway and backend credentials separately. Test private cache/task/state isolation across tenants and after revocation; test Apps sandbox/CSP/bridge and task cancellation where enabled. An internal mTLS design is one option. A public service may require controls on agent egress and credential access instead; a local server needs host/sandbox enforcement. A clean metadata scan or a project-specific gateway conformance claim is not a BRACE pass.

### Candidate platforms and components

These links are starting points, not verified ratings. The resource catalog has a longer [component list](RESOURCES.md).

| Source | What to investigate |
|---|---|
| [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/) | Runtime, identity, gateway, memory, and observability features for your exact service setup. |
| [Google Gemini Enterprise Agent Platform](https://cloud.google.com/products/gemini-enterprise-agent-platform) | Runtime and tool boundaries, model and deployment versions, and tenant isolation in the service you choose. |
| [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/overview) | Agent lifecycle, tool integration, identity, network controls, and telemetry. |
| [Microsoft Entra Agent ID](https://learn.microsoft.com/en-us/entra/agent-id/what-is-microsoft-entra-agent-id) | How agent identities are issued and scoped, delegated authority, and revoking an agent without revoking its user. |
| [OpenAI Agent Builder](https://developers.openai.com/api/docs/guides/agent-builder) | Workflow versioning and tool controls. OpenAI is deprecating Agent Builder. The official guide says it shuts down on November 30, 2026, and that ChatKit remains available. Plan a migration before you rely on it. |
| [Anthropic trustworthy-agents guidance](https://www.anthropic.com/research/trustworthy-agents) | How duties split across the model, harness, tools, and environment. This guidance does not prove that any managed product has a given feature. |
| [OpenTelemetry GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai) | Existing agent and model attributes and tracing. Status: Development. BRACE maps its needs onto these attributes; see [OTel conventions](otel-conventions.md). Check BRACE-specific fields and audit coverage separately. |

### Reference designs and standards

[OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/) defines portable runtime control hooks. It works alongside BRACE's deployment review. Check framework support and maturity before you rely on a given integration.

The Microsoft Agent Governance Toolkit's [MCP Security Gateway 1.0 specification](https://github.com/microsoft/agent-governance-toolkit/blob/580344a624530b6e9611e67544519bca3107cd31/docs/specs/MCP-SECURITY-GATEWAY-1.0.md) (pinned revision 580344a, 2026-09-25) labels itself **Draft**. It describes interception, scanning, authentication, fingerprinting, audit, and conformance requirements. Written requirements do not show that any implementation has been independently tested against them. Run the relevant tests on the actual implementation.

A gateway circuit breaker does not, by itself, stop remote child agents. A fingerprint of a tool's description and schema does not catch hidden changes to remote code. HMAC authentication does not supply all six BRACE identity fields. Check each of these limits on its own. Don't map one feature to a whole control.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
