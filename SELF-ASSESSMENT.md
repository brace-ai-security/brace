# BRACE self-assessment and vendor evaluation

Score the same **53 items** used in the [BRACE sign-off checklist](CHECKLIST.md), across **Build-time, Run-time, Agent, Configuration, and Ecosystem**. The checklist is the source of the full requirements, operational challenges, fallbacks, and acceptable tradeoffs. The [verification guide](CHECKLIST-VERIFICATION.md) supplies a procedure, expected result, and evidence for every matching item ID.

Part of the BRACE Project. License: CC BY 4.0.

## How to use this

Assess a named release and environment, or ask a vendor to demonstrate each requirement for the configuration you would actually use. Read the full checklist item before scoring its short label below. Record the agent-team and platform/vendor responsibilities separately; score the combined evidence for the deployment.

### Scoring and checklist outcomes

| Score | Meaning | Checklist outcome |
|---|---|---|
| **2 — Yes** | The full applicable requirement is implemented and demonstrated with evidence. | Pass |
| **1 — Partial** | Evidence demonstrates only part of the requirement or part of the deployment. | Gap |
| **0 — No** | The requirement is absent or cannot be demonstrated. A claim alone earns no credit. | Gap |
| **N/A** | The feature/exposure is absent, with evidence and an approved rationale. | N/A; exclude from score denominator |

A fallback can earn 2 only when it demonstrably meets the requirement for the assessed configuration. Accepted risk does not turn a Partial or No into a Yes. Provider-undisclosed details must be labeled as such; apply the model-provenance and pinning rules in C01/C05 and assess the available evidence without inventing missing version information.

### Priority gates

The **G1/G2/G3** labels match the checklist and BRACE's adoption priorities. **Obs-T1/Obs-T2/Obs-T3** identify observability requirements, not gate levels.

- **G1:** Every applicable item must score 2; any Partial or No blocks sign-off.
- **G2:** Every applicable item must score 2 or have a valid, explicit, time-bounded risk acceptance.
- **G3:** Every applicable item must score 2 for high-stakes or high-autonomy deployments. For lower-stakes deployments, a Partial or No requires valid, explicit, time-bounded risk acceptance.

Classify stakes and autonomy before assessing gaps. Record owners, evidence, N/A approvals, and exceptions using the [checklist records](CHECKLIST.md#evidence-and-exception-record). A vendor service does not make its responsibilities N/A.

## Assessment worksheet

For each row, ask: **Does this deployment meet the full linked checklist requirement, and can we demonstrate it?** Add a score and an evidence or gap reference. The short labels help you find each item; score against its full requirement.

### B — Build-time

**IF YOU DO NOTHING ELSE — TOP 3:** **B05 — Destructive-action interception**; **B02 — Least-privilege access**; **B01 — Minimal tool surface**. These are the same priority items highlighted in the checklist; the full sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#b--build-time) · [Verification recipes](CHECKLIST-VERIFICATION.md#b--build-time)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| B01 | G1 | C4 | Minimal tool surface | | |
| B02 | G1 | C2 | Least-privilege access | | |
| B03 | G2 | C2 | Credential lifetime and handling | | |
| B04 | G1 | C2 | Independent revocation | | |
| B05 | G1 | C4 | Destructive-action interception | | |
| B06 | G1 | C4 | Approval integrity | | |
| B07 | G2 | C4 | Hard execution budgets | | |
| B08 | G2 | C1 | Environment isolation | | |
| B09 | G2 | C1 | Egress allowlist | | |
| B10 | G2 | C3 | Pinned, verified image | | |
| B11 | G2 | C3 | Minimal, isolated runtime | | |
| B12 | G1 | C4 | Reviewed harness and instructions | | |

### R — Run-time

**IF YOU DO NOTHING ELSE — TOP 3:** **R11 — Tested kill switch**; **R13 — Full execution audit**; **R01 — Validate every input boundary, including API responses**. These are the same priority items highlighted in the checklist; the full sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#r--run-time) · [Verification recipes](CHECKLIST-VERIFICATION.md#r--run-time)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| R01 | G2 | C5 | Validate every input boundary, including API responses | | |
| R02 | G2 | C5 | Separate data from instructions and test injection containment | | |
| R03 | G2 | C5/C9 | Prevent output and log leakage | | |
| R04 | G2 | C5/C6 | Retrieval-corpus integrity | | |
| R05 | G3 | C6 | Memory isolation and write validation | | |
| R06 | G3 | C6 | Memory provenance and cleanup | | |
| R07 | G2 | Obs-T2 | Decision-time context size | | |
| R08 | G3 | C7 | Security monitoring | | |
| R09 | G3 | C7/Obs-T2 | Sequence and context-aware detection | | |
| R10 | G3 | C7 | Misaligned-behavior review | | |
| R11 | G1 | C8 | Tested kill switch | | |
| R12 | G1 | C8 | Safe state after stopping | | |
| R13 | G1 | C9 | Full execution audit | | |
| R14 | G2 | C9 | Recovery integrity | | |

### A — Agent

**IF YOU DO NOTHING ELSE — TOP 3:** **A01 — Distinct agent identity**; **A02 — All six identity fields**; **A03 — Content-derived type identity**. These are the same priority items highlighted in the checklist; the full sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#a--agent) · [Verification recipes](CHECKLIST-VERIFICATION.md#a--agent)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| A01 | G1 | C2/Obs-T1 | Distinct agent identity | | |
| A02 | G1 | Obs-T1 | All six identity fields | | |
| A03 | G1 | Obs-T1 | Content-derived type identity | | |
| A04 | G1 | C9/Obs-T1 | Trustworthy attribution | | |
| A05 | G1 | C8/C9/Obs-T1 | Operational lookup | | |
| A06 | G3 | Obs-T3 | Parent and prompt provenance | | |
| A07 | G3 | C7/Obs-T1 | Every model in the loop | | |

### C — Configuration

**IF YOU DO NOTHING ELSE — TOP 3:** **C01 — Complete release manifest**; **C03 — Match release identity to running state**; **C04 — Detect drift per agent**. These are the same priority items highlighted in the checklist; the full sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#c--configuration) · [Verification recipes](CHECKLIST-VERIFICATION.md#c--configuration)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| C01 | G2 | C1–C6/Obs-T1 | Complete release manifest | | |
| C02 | G2 | C1–C7 | Review security-relevant changes | | |
| C03 | G1 | Obs-T1 | Match release identity to running state | | |
| C04 | G2 | C1/C3/C4/Obs-T1 | Detect drift per agent | | |
| C05 | G2 | C3/C4/C7 | Control dependency, model, and training changes | | |
| C06 | G2 | C4–C9 | Re-test changed behavior | | |
| C07 | G2 | C8/C9 | Rollback and restart | | |
| C08 | G2 | Obs-T1/Obs-T2/Obs-T3 | Connect configuration to execution | | |

### E — Ecosystem

**IF YOU DO NOTHING ELSE — TOP 3:** **E06 — Enforced gateway boundary**; **E08 — Bounded delegated authority**; **E09 — Recursive shutdown**. These are the same priority items highlighted in the checklist; the full sign-off gates still apply.

[Full requirements and operational notes](CHECKLIST.md#e--ecosystem) · [Verification recipes](CHECKLIST-VERIFICATION.md#e--ecosystem)

| Item | Gate | BRACE reference | Requirement | Score | Evidence / gap reference |
|---|---|---|---|---|---|
| E01 | G2 | C1–C9 | Map shared responsibilities | | |
| E02 | G2 | C3/C5 | Vet and pin dependencies | | |
| E03 | G2 | C5 | Re-check tools on load | | |
| E04 | G2 | C5 | Inspect tool metadata | | |
| E05 | G2 | C2/C5 | Verified, namespaced tools | | |
| E06 | G2 | C1/C2/C4/C5/C9 | Enforced gateway boundary | | |
| E07 | G2 | C2/C5 | Untrusted peer messages | | |
| E08 | G1 | C2/C4 | Bounded delegated authority | | |
| E09 | G1 | C8 | Recursive shutdown | | |
| E10 | G1 | C9/Obs-T1 | Audit across service boundaries | | |
| E11 | G2 | C9 | Protect shared evidence | | |
| E12 | G3 | C7/C8 | Fleet incident response | | |

## Reading your score

With all 53 items applicable, the maximum is **106 points**. If some items have approved N/A outcomes, use:

**Coverage score = points earned / (2 × number of applicable items).**

Report the applicable item count, N/A count, points earned, and denominator together. If no items are applicable, the score is undefined; revisit the assessment scope rather than reporting readiness. Compare scores only for comparable scopes and applicability decisions.

The score tracks demonstrated implementation; it is not a security rating or release authorization. Report the count of unresolved G1 gaps and the status of G2/G3 exceptions separately. A high score cannot compensate for one blocker, and lower-stakes risk acceptance does not erase the gap from the score.

Finish with the [checklist's final sign-off](CHECKLIST.md#final-sign-off), including its next-review and re-review triggers. Reassess capabilities on that cadence and remove stale access; re-test after meaningful changes.

## Using this to evaluate a vendor

- Request concrete artifacts: scoped-token metadata, denial records, release/model manifests, drill results, and attributable traces.
- Ask which controls the platform supplies and which your team must configure or implement. A platform feature that is disabled in your deployment does not pass.
- For hosted models, request disclosed version metadata and distinguish it from undisclosed pretraining lineage. For your own fine-tuning, retain your job and dataset records even if the base provider withholds theirs.
- Discuss the operational notes beneath difficult checklist items. Name the limitations and acceptable costs, then record any permitted risk acceptance with an owner and expiry.
- Treat missing required evidence as a gap. If it blocks sign-off, reduce the deployment's actual capabilities or select an integration that can meet the requirement, then re-test.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
