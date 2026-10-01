# BRACE self-assessment and vendor evaluation

Use this worksheet to score the same **53 items** as the [BRACE sign-off checklist](CHECKLIST.md), across **Build-time, Run-time, Agent, Configuration, and Ecosystem**. The checklist holds the full requirements, the hard parts, fallbacks, and tradeoffs you can accept. The [verification guide](CHECKLIST-VERIFICATION.md) gives each item a test, the result to expect, and the evidence to keep.

Part of the BRACE Project. License: CC BY 4.0.

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

The **G1/G2/G3** labels match the checklist. G stands for gate: a checkpoint a release must clear before it ships. **Obs-T1/Obs-T2/Obs-T3** name observability requirements, not gates.

- **G1:** Every applicable item must score 2; any Partial or No blocks sign-off.
- **G2:** Every applicable item must score 2, or have a written, approved risk acceptance.
- **G3:** For high-stakes or high-autonomy deployments, every applicable item must score 2. For lower-stakes deployments, a Partial or No needs a written, approved risk acceptance.

Rate the deployment's stakes and autonomy before you judge any gaps. Record owners, evidence, N/A approvals, and exceptions in the [checklist records](CHECKLIST.md#evidence-and-exception-record). Using a vendor's service doesn't make its part of a control N/A.

## Assessment worksheet

For each row, ask: **Does this deployment meet the full checklist requirement, and can we show it?** Add a score and a link to the evidence or gap. The short labels help you find each item. Score against its full requirement.

### B — Build-time

**IF YOU DO NOTHING ELSE — TOP 3:** **B05 — Destructive-action interception**; **B02 — Least-privilege access**; **B01 — Minimal tool surface**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

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

**IF YOU DO NOTHING ELSE — TOP 3:** **R11 — Tested kill switch**; **R13 — Full execution audit**; **R01 — Validate every input boundary, including API responses**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

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

**IF YOU DO NOTHING ELSE — TOP 3:** **A01 — Distinct agent identity**; **A02 — All six identity fields**; **A03 — Content-derived type identity**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

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

**IF YOU DO NOTHING ELSE — TOP 3:** **C01 — Complete release manifest**; **C03 — Match release identity to running state**; **C04 — Detect drift per agent**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

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

**IF YOU DO NOTHING ELSE — TOP 3:** **E06 — Enforced gateway boundary**; **E08 — Bounded delegated authority**; **E09 — Recursive shutdown**. These are the same top-three items the checklist highlights. All sign-off gates still apply.

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

With all 53 items applicable, the maximum is **106 points**. If some items have approved N/A results, use:

**Coverage score = points earned / (2 × number of applicable items).**

Report the number of applicable items, the N/A count, the points earned, and the denominator together. If no items apply, there is no score. Recheck the assessment scope instead of reporting readiness. Compare scores only when the scope and N/A decisions match.

The score tracks what you have shown is in place. It is not a security rating, and it does not approve a release. Report the number of open G1 gaps and the status of G2 and G3 exceptions separately. A high score can't make up for one blocker. A risk acceptance doesn't remove the gap from the score.

Finish with the [checklist's final sign-off](CHECKLIST.md#final-sign-off), including the next review date and what triggers a new review. Recheck the agent's powers on that schedule and remove access it no longer needs. Re-test after changes that matter.

## Using this to evaluate a vendor

- Ask for concrete artifacts: scoped-token metadata, denial records, release and model manifests, drill results, and traces that show who did what.
- Ask which controls the platform supplies and which your team must set up or build. A platform feature that is turned off in your deployment does not pass.
- For hosted models, ask for the version details the provider shares. Keep them apart from pretraining history it doesn't share. For fine-tuning you run yourself, keep your job and dataset records, even if the base-model provider keeps theirs private.
- Discuss the notes under the harder checklist items. Name the limits and the costs you accept. Then record any allowed risk acceptance, with an owner and approver.
- Treat missing required evidence as a gap. If it blocks sign-off, cut the deployment's actual powers or choose an integration that can meet the requirement. Then re-test.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
