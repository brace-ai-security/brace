# Threat-model control map

Use these mappings to select relevant existing BRACE controls. They are design
prompts, not additional checklist requirements or a replacement for the
[current checklist](https://braceframework.org/CHECKLIST.md). Item IDs below are
BRACE IDs; threat IDs in a project document identify that project's own scenarios.

| Design concern | BRACE control and representative items | Evidence to request later |
|---|---|---|
| Cross-tenant/host exposure and exfiltration | C1 Architecture: B08 environment isolation (host/tenant boundaries); B09 egress allowlist (outgoing destinations); E06 MCP gateway boundary when present | Allowed route plus denied tenant/host/destination paths, including redirects and helper fetches. B09 does not establish filesystem isolation. |
| Credentials, delegation and independent revocation | C2 Capability-scoped access: B02 least privilege; B03 credential lifetime/handling; B04 independent revocation; A01 distinct agent identity; E08 bounded delegation | Effective destination permissions, subject/actor/audience checks, escalation denial and measured cutoff. |
| Executable artifacts, sandbox and dependency changes | C3 Container: B10 pinned/verified container images when used; B11 isolated runtime; E02 dependency vetting; C01 release manifest; C03 running identity; C04 drift detection; C05 dependency/model changes | Select controls for the actual packaging, provenance, host isolation and drift design; do not infer that a container exists. Record managed-service visibility limits. |
| Consequential actions and unsafe capability combinations | C4 Harness: B01 minimal tool surface; B05 destructive-action interception | Enforce permitted operations at execution, including equivalent helper, peer and raw paths. |
| Approval integrity | C4 Harness: B06 approval integrity | Bind operation/target/arguments/instance; test expiry and concurrent approval reuse. |
| Resource exhaustion and runaway work | C4 Harness: B07 hard execution budgets | Per-run and aggregate tenant/fleet limits, helper accounting, concurrency and charging-order evidence. |
| Trusted instructions and later executable changes | C4 Harness: B12 reviewed harness and instructions; C02 change review | Reviewed prompt/rules/hook versions and denied unauthorized changes. B12 is not the budget control. |
| Untrusted input and prompt injection | C5 Data: R01 input boundaries; R02 injection containment | Structural/content checks and schema-valid attacks cannot bypass independent action authority; include an allowed-task control. |
| Generated output, interpreters and leakage | C5 Data: R03 output validation and leakage | Safe rendering/interpretation, permitted recipients and secrets absent from unintended sinks. |
| External tool publication and metadata, where present | C5 Data: E03 re-check tools on load; E04 inspect metadata; E05 verified namespaces | Approved-definition changes blocked, hostile metadata handled as data, server identity not inferred from names. |
| MCP enforcement and peer messaging, where present | C1/C2/C5: E06 gateway boundary; E07 untrusted peer messages | Actual MCP transport authorization or host controls, and authenticated/authorized replay-resistant peer calls. Do not impose these on an offline tool-free design. |
| Retrieval, persistent memory and later influence | C6 Memory: R04 retrieval access; R05 memory isolation/write integrity; R06 memory lineage/cleanup | Tenant/source access checks, write provenance, poisoning/removal tests and coverage of derived copies. Inspect later-consumed files too; broader artifact coverage is a research-informed refinement. |
| Multi-step abuse or unintended goal pursuit | C7 Behavioral: R08 security monitoring; R09 sequence detection; R10 observable misalignment behavior | Labeled harmful/benign sequences, actual alert delivery, false-block/missed-detection limits; no inference of hidden intent. |
| Failure to stop future effects or recover safely | C8 Kill switch: R11 independent tested stop; R12 safe shutdown/reconciliation; E09 descendant shutdown; C9 R14 record integrity/replay | Pre-implementation stop/recovery requirements, independent authority and descendant coverage, reconciliation/idempotency assumptions. These are design requirements, not incident handling. |
| Missing attribution, evidence or accountable ownership | C9 Audit: R13 full execution audit; A02 six identity fields; E10 cross-service audit; E11 protected shared evidence; E01 shared responsibilities; A05 instance/owner lookup | Complete action/destination evidence with protected detail, retention and audit-failure behavior. Do not equate correlation labels with authenticated identity. |

Observability supports these controls: Obs-T1 maps to A02 (identity fields),
Obs-T2 to R07 (decision-time context with counting uncertainty), and Obs-T3 to A06
(parent/prompt provenance when sub-agents exist). Release/configuration links under
A03, A07 and C01–C08 help state what exact design and dependencies evidence covers.
The exact BRACE schema, gates and context metric are framework design judgments.
For an item not defined here, consult its current checklist text before selecting
it. If that text is unavailable, retain a provisional C1–C9 control mapping and a
verification question rather than guessing the item's meaning.

## Source basis and limits

Sources checked 2026-10-23:

- [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html):
  system/dataflow modeling, threats, responses and validation. Guidance, not proof
  that a threat inventory is complete or a deployment is safe.
- [OWASP Multi-Agentic System Threat Modeling Guide v1.0](https://genai.owasp.org/resource/multi-agentic-system-threat-modeling-guide-v1-0/),
  2025-04-23: agentic/multi-agent threat-modeling reference. Its taxonomy does not
  require deploying multiple agents or prove isolation between them.
- [Meta Agents Rule of Two](https://ai.meta.com/blog/practical-ai-agent-security/),
  2025-10-31: a design heuristic about combining untrusted inputs, sensitive access
  and external/state-changing actions. BRACE B05 defines its own approval/isolation
  requirement. Neither task intent nor a claimed second-model defense proves safety.
- [BRACE dated evidence review](https://braceframework.org/RESEARCH-2026-10-22.md):
  primary-source context and proposed refinements. Research results have specific
  attacker/model/harness assumptions; distinguish them from protocol requirements
  and the adopted project's actual policies.

Recheck versioned specifications and advisories before making version-specific
claims. When unavailable, record the source/date limit; this skill does not require
a literature survey for every design. A threat register records credible scenarios
and uncertainty, not empirical exploit frequency or deployment authorization.
