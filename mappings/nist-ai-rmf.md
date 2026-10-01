# BRACE and the NIST AI RMF

This page maps every subcategory in the Core of the NIST AI Risk Management Framework to the items in the [BRACE sign-off checklist](../CHECKLIST.md). It uses [AI RMF 1.0 (NIST AI 100-1)](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf), released 26 January 2023. That is still the current version on 2026-10-01: the [NIST AI RMF page](https://www.nist.gov/itl/ai-risk-management-framework) says 1.0 is being revised under the White House AI Action Plan, but no newer version has been published.

## How to read this mapping
- **Direct** — passing the listed BRACE items produces evidence that meets this outcome for a deployed agent.
- **Partial** — the listed items supply part of the evidence; the rest needs organization-level work outside BRACE.
- **Out of scope** — BRACE doesn't address it (for example, workforce diversity, impact on communities, or organizational policy); say why in a few words.
BRACE is a technical deployment checklist. The AI RMF is voluntary and organization-wide. Passing BRACE items does not mean an organization has implemented the AI RMF.

Item IDs refer to the [checklist](../CHECKLIST.md). "Sign-off record" is the [final sign-off](../CHECKLIST.md#final-sign-off), including the deployment record and the stakes and autonomy rating. "Priority gates" are the [G1/G2/G3 rules](../CHECKLIST.md#priority-gates-g). "Evidence record" is the [evidence and exception record](../CHECKLIST.md#evidence-and-exception-record), including owners and risk acceptances. An item supplies evidence only when its result is Pass. Tests and evidence for each item are in the [verification guide](../CHECKLIST-VERIFICATION.md).

## Summary

| Function | Subcategories | Direct | Partial | Out of scope |
|---|---|---|---|---|
| GOVERN | 19 | 1 | 13 | 5 |
| MAP | 18 | 4 | 9 | 5 |
| MEASURE | 22 | 2 | 13 | 7 |
| MANAGE | 13 | 3 | 9 | 1 |
| **Total** | **72** | **10** | **44** | **18** |

## GOVERN

| Subcategory | Outcome (summary) | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| GOVERN 1.1 | Legal and regulatory duties for AI are known, managed, and written down. | Partial | E11 | E11 keeps audit records as long as the law requires; every other legal duty is outside BRACE. |
| GOVERN 1.2 | Trustworthy-AI traits are built into organizational policies and practices. | Partial | Priority gates, Sign-off record | The gates give a release rule for security and accountability only; the policy itself and the other traits are organizational work. |
| GOVERN 1.3 | The organization decides how much risk management each system needs, based on its risk tolerance. | Partial | Sign-off record, Priority gates | The stakes and autonomy rating decides when G3 items must pass; setting the organization's tolerance happens outside BRACE. |
| GOVERN 1.4 | The risk process and its results are set by clear policies and controls based on risk priorities. | Partial | Priority gates, Evidence record, Sign-off record | Each release has written pass rules and a recorded result, but the organization-wide process is not BRACE's. |
| GOVERN 1.5 | Monitoring and periodic review of the risk process are planned, with roles and review frequency set. | Partial | Sign-off record, Evidence record | BRACE sets a next review date, reopen triggers, and an owner per item for one agent, not for the whole risk program. |
| GOVERN 1.6 | There is a way to inventory AI systems. | Partial | C01, A03, A05, A07 | The manifest, type ID, and lookup drill describe each agent; keeping a list of all AI systems is organizational work. |
| GOVERN 1.7 | AI systems can be retired safely. | Partial | B04, R12, E09, C07 | Revoking access, stopping sub-agents, and leaving work in a safe state support retirement, but BRACE has no retirement process. |
| GOVERN 2.1 | Roles, duties, and lines of communication for AI risk are written down and clear. | Partial | A02, E01, A05, Evidence record | Every action names an accountable party and owner, and each control has a named owner on both sides; organization-wide roles are outside BRACE. |
| GOVERN 2.2 | Staff and partners get AI risk training. | Out of scope | — | BRACE does not cover training. |
| GOVERN 2.3 | Executive leaders take responsibility for AI risk decisions. | Partial | Sign-off record, Priority gates | BRACE names who approves release and who accepts each risk; making that person an executive is the organization's choice. |
| GOVERN 3.1 | Risk decisions are informed by a diverse team. | Out of scope | — | Team diversity is a workforce matter. |
| GOVERN 3.2 | Policies define roles for human-AI setups and oversight. | Partial | B06, B05, R11, A02 | BRACE records who may approve high-impact actions and who may stop the agent; the wider policy is organizational. |
| GOVERN 4.1 | Policies build a critical-thinking, safety-first culture. | Out of scope | — | Culture is an organizational matter. |
| GOVERN 4.2 | Teams write down AI risks and impacts and share them more widely. | Partial | Sign-off record, Evidence record, B05 | BRACE records the worst credible damage, the risky capability combination, and accepted exposure; wider impacts and sharing are not covered. |
| GOVERN 4.3 | Practices support AI testing, finding incidents, and sharing information. | Partial | C06, R08, E12 | Release tests, security alerts, and an incident drill with a named reporting decision cover one agent; organization-wide practice is outside BRACE. |
| GOVERN 5.1 | Feedback from people outside the team about social impacts is gathered and used. | Out of scope | — | BRACE does not collect outside feedback on impacts. |
| GOVERN 5.2 | The team regularly folds reviewed outside feedback into design. | Out of scope | — | BRACE does not cover feedback from AI actors. |
| GOVERN 6.1 | Policies cover third-party AI risks, including intellectual property. | Partial | E01, E02, C05, B10 | BRACE vets, pins, and assigns owners to third-party parts; intellectual property and the policy itself are outside BRACE. |
| GOVERN 6.2 | There are backup plans for failures or incidents in high-risk third-party data or AI. | Direct | E12, C05, E06, C07 | A drill handles a compromised shared tool, model changes have pause rules, gateways fail closed, and rollback is tested. |

## MAP

| Subcategory | Outcome (summary) | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| MAP 1.1 | Purpose, uses, laws, users, settings, and possible impacts are written down. | Partial | Sign-off record | The deployment record covers task, setting, tenants, data, actions, autonomy, and worst damage, but not laws or wider social impact. |
| MAP 1.2 | Diverse, cross-field people help set the context, and that is recorded. | Out of scope | — | Team makeup is a workforce matter. |
| MAP 1.3 | The organization's mission and AI goals are written down. | Out of scope | — | Mission is set by the organization. |
| MAP 1.4 | The business value of the system is defined. | Out of scope | — | BRACE does not judge business value. |
| MAP 1.5 | The organization's risk tolerances are set and written down. | Partial | Priority gates, Sign-off record | The gates fix what blocks release and need approved risk acceptance for gaps; overall tolerance is set by the organization. |
| MAP 1.6 | System requirements are gathered, and design accounts for social and technical effects. | Partial | B05, B02, B01 | BRACE supplies security requirements for the agent; other requirements, such as user privacy promises, need separate work. |
| MAP 2.1 | The tasks the system supports and the methods it uses are defined. | Direct | Sign-off record, B01, C01 | The deployment record names the task, each tool has a task reason, and the manifest lists every model. |
| MAP 2.2 | The system's knowledge limits and how people oversee its output are written down. | Partial | B05, B06, R11 | BRACE documents approval and stop points; it does not document what the model knows or doesn't know. |
| MAP 2.3 | Scientific soundness and test, evaluation, verification, and validation (TEVV) needs are written down, including data choices. | Partial | C06, C01 | BRACE sets up security tests and records dataset versions, but not data quality or construct validity. |
| MAP 3.1 | Possible benefits are examined and written down. | Out of scope | — | BRACE does not assess benefits. |
| MAP 3.2 | Possible costs of AI errors, tied to risk tolerance, are examined and written down. | Partial | Sign-off record, Evidence record, B05 | BRACE records worst credible damage and the exposure of each accepted gap; it does not cost out ordinary errors. |
| MAP 3.3 | The system's intended scope is set and written down. | Direct | Sign-off record, B01, B02, B08 | The allowed task, tools, permissions, and reachable systems are written down and enforced. |
| MAP 3.4 | Operator skill with the system, and related standards, are defined and checked. | Partial | R11, E12, A05 | Drills show operators can stop, find, and contain the agent; training and certification are outside BRACE. |
| MAP 3.5 | Human oversight processes are defined, checked, and written down. | Direct | B05, B06, R11, R08 | High-impact actions need tested approvals, a named person can stop the agent, and alerts reach a named responder. |
| MAP 4.1 | Technical and legal risks of all parts, including third-party ones, are mapped. | Partial | E02, E01, C01, B10 | BRACE vets each part's source, publisher, and known flaws; legal and intellectual property risks are not covered. |
| MAP 4.2 | Internal risk controls for each part, including third-party AI, are written down. | Direct | E01, C01, E02, A07 | Every outside part and model is listed, with the controls that apply and an owner on each side. |
| MAP 5.1 | The likelihood and size of each impact are written down. | Partial | Sign-off record, Evidence record | BRACE records worst credible damage and accepted exposure; it does not rate likelihood or helpful impacts. |
| MAP 5.2 | People and practices are in place to gather feedback about impacts. | Out of scope | — | BRACE does not cover engagement with affected people. |

## MEASURE

| Subcategory | Outcome (summary) | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| MEASURE 1.1 | Methods and metrics are chosen for the biggest risks first, and unmeasured risks are noted. | Partial | Priority gates, Evidence record, R10, R07 | BRACE sets measurable targets and records what each check can't prove, but only for security risks. |
| MEASURE 1.2 | Metrics and controls are reviewed and updated, including error reports and community impact. | Partial | C06, R09, C04 | Controls are re-tested each release and detection miss rates are measured; community impact is not covered. |
| MEASURE 1.3 | Experts who did not build the system, or independent assessors, take part in reviews. | Partial | Sign-off record, B12, C02 | BRACE requires named reviewers, but it does not require them to be independent of the builders. |
| MEASURE 2.1 | Test sets, metrics, and test tools are written down. | Partial | Evidence record, C06 | Security tests record fixtures, targets, tester, date, and setup differences; quality tests are outside BRACE. |
| MEASURE 2.2 | Tests with human subjects meet protection rules and represent the population. | Out of scope | — | BRACE does not run tests on people. |
| MEASURE 2.3 | Performance or assurance criteria are measured in conditions like real use. | Direct | C06, R11, B04, E09 | Release candidates are tested through the real harness, with measured stop and revocation times and recorded setup differences. |
| MEASURE 2.4 | The system and its parts are watched in production. | Partial | R08, R09, C04, R13 | BRACE watches actions, drift, and security signals; it keeps answer quality out of scope. |
| MEASURE 2.5 | The system is shown to be valid and reliable, with limits noted. | Out of scope | — | BRACE does not test whether the agent's answers are correct. |
| MEASURE 2.6 | The system is tested for safety, stays within risk tolerance, and fails safely. | Partial | R12, R11, B05, B07 | BRACE tests safe stopping, blocked high-impact actions, and hard limits; it does not test harmful content or other safety risks. |
| MEASURE 2.7 | Security and resilience are evaluated and written down. | Direct | C06, R02, E06, R14 | Attack cases, bypass tests, and recovery tests run against each release candidate, and the results are kept. |
| MEASURE 2.8 | Transparency and accountability risks are examined and written down. | Partial | A02, R13, E10, A04 | Every action can be traced to an agent, owner, and tenant; transparency to users is not covered. |
| MEASURE 2.9 | The model is explained, validated, and documented, and output is read in context. | Partial | C01, A07, R13 | BRACE documents which models ran and what they did; it does not explain or validate the model. |
| MEASURE 2.10 | Privacy risk is examined and written down. | Partial | R03, R05, R04, B02 | BRACE tests leakage and tenant separation; a full privacy risk review is outside BRACE. |
| MEASURE 2.11 | Fairness and bias are evaluated. | Out of scope | — | BRACE does not test fairness or bias. |
| MEASURE 2.12 | Environmental impact is assessed. | Out of scope | — | BRACE does not measure environmental impact. |
| MEASURE 2.13 | The test methods themselves are checked for how well they work. | Partial | R09, R10, R02 | BRACE measures detector misses and false alarms and repeats attacks; other test methods are not reviewed. |
| MEASURE 3.1 | People and methods are in place to track known and new risks over time. | Partial | R08, E12, C05, Sign-off record | Monitoring, provider notices, and review triggers track security risks; other risks need separate tracking. |
| MEASURE 3.2 | Risk tracking is planned for risks that are hard to measure. | Partial | R10, C05, R09, Evidence record | Fallbacks record what is uncertain and who owns it, but only for security risks. |
| MEASURE 3.3 | Users and affected people can report problems and appeal outcomes. | Out of scope | — | BRACE has no user feedback or appeal process. |
| MEASURE 4.1 | Measurement fits the real setting and draws on domain experts and users. | Partial | C06, Evidence record | Tests run on the real release and record setup differences; consulting experts and users is outside BRACE. |
| MEASURE 4.2 | Experts and AI actors help confirm the system works as intended. | Out of scope | — | BRACE does not check intended performance with experts. |
| MEASURE 4.3 | Gains or drops in performance are found through consultation and field data. | Out of scope | — | BRACE does not track performance with affected communities. |

## MANAGE

| Subcategory | Outcome (summary) | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| MANAGE 1.1 | A decision is made on whether the system meets its goals and should go ahead. | Partial | Sign-off record, Priority gates | BRACE ends in a GO or NO-GO on security grounds; whether the agent meets its goals is judged elsewhere. |
| MANAGE 1.2 | Risk treatment is prioritized by impact, likelihood, and resources. | Partial | Priority gates, Sign-off record | Gates and the stakes rating set fixed priorities for security gaps; they do not weigh likelihood or cost. |
| MANAGE 1.3 | Responses to high-priority risks are planned and written down (reduce, transfer, avoid, or accept). | Partial | Evidence record, Priority gates | Each security gap gets a fix, a cut in powers, or an approved acceptance with an owner; other risks are not covered. |
| MANAGE 1.4 | Leftover risks to buyers and end users are written down. | Partial | Evidence record, Sign-off record | Accepted gaps record their exposure and compensating controls; telling buyers and users is outside BRACE. |
| MANAGE 2.1 | Resources and non-AI alternatives are considered to reduce impact. | Out of scope | — | BRACE does not compare AI with non-AI options. |
| MANAGE 2.2 | There are ways to keep a deployed system's value over time. | Partial | C04, C05, C07 | Drift checks, model-change controls, and rollback keep the approved setup running; value is not measured. |
| MANAGE 2.3 | There are steps to respond to and recover from a newly found risk. | Direct | E12, C07, R14, R12 | A tested incident drill, rollback, checked recovery, and safe-state steps handle new problems. |
| MANAGE 2.4 | There are ways, with named owners, to replace, disengage, or shut off a system that misbehaves. | Direct | R11, E09, B04, A05 | A named person can stop the agent and its sub-agents within a tested time and cut off its access. |
| MANAGE 3.1 | Third-party risks and benefits are watched, and controls are applied and written down. | Partial | E01, E03, E02, C05 | Tools and models are re-checked on load and watched for flaws; third-party benefits and non-security risks are outside BRACE. |
| MANAGE 3.2 | Pre-trained models are watched as part of regular upkeep. | Direct | C05, C03, A07, C01 | Every model is pinned or tracked, changes trigger re-tests, and the running model is checked against the manifest. |
| MANAGE 4.1 | Post-deployment monitoring covers user input, appeals and overrides, retirement, incidents, recovery, and change. | Partial | R08, E12, C02, C07 | BRACE covers monitoring, override, incidents, recovery, and change review; user input and appeals are not covered. |
| MANAGE 4.2 | Measurable improvements are built into updates, with input from interested parties. | Partial | C06, Sign-off record | Each release is re-tested and gaps are tracked to an owner; engagement with interested parties is outside BRACE. |
| MANAGE 4.3 | Incidents are shared with affected parties, and handled and recorded. | Partial | E12, R13, R12 | BRACE records what happened and names who decides on outside reporting; telling affected communities is outside BRACE. |

## NIST AI 600-1 risks

[NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf), the Generative AI Profile (July 2024), lists 12 risks. BRACE helps with four:

| Risk | BRACE items | Note |
|---|---|---|
| Information Security | R01, R02, B05, E06 | Covers prompt injection, poisoned retrieval and memory (R04, R05), and model-file integrity (C05). It does not limit offensive cyber uses of the model. |
| Value Chain and Component Integration | C01, E02, C05, E01 | Lists, vets, pins, and assigns owners to models, tools, datasets, and services. |
| Data Privacy | R03, B02, R05, R04 | Blocks leaks and enforces tenant separation. It does not cover training data or de-anonymization. |
| Human-AI Configuration | B06, B05 | Approvals show the reviewer the exact action. BRACE does not measure automation bias or over-reliance. |

BRACE does not address CBRN Information or Capabilities; Confabulation; Dangerous, Violent, or Hateful Content; Environmental Impacts; Harmful Bias or Homogenization; Information Integrity; Intellectual Property; or Obscene, Degrading, and/or Abusive Content.

## Limits

- This mapping is BRACE's judgment. NIST has not reviewed or endorsed it.
- "Direct" means evidence for one deployed agent and one release. An organization needs that evidence for each agent and each release.
- BRACE covers security and control. It does not test accuracy, fairness, or social impact, so most GOVERN and MAP outcomes stay Partial or Out of scope.
- Only items with a Pass result count. A Gap, an accepted risk, or an N/A supplies no evidence for an outcome.
- The AI RMF Playbook's suggested actions and the AI 600-1 action tables (for example, GV-1.1-001) are not mapped.
- AI RMF 1.0 is under revision. Recheck this mapping when NIST publishes a new version. Last checked 2026-10-01.
- 600-1 names one risk "Harmful Bias or Homogenization" in its list and "Harmful Bias and Homogenization" in its section heading. This page uses the list name.

---
*Part of [BRACE](../README.md), a security framework for autonomous AI agents. CC BY 4.0.*
