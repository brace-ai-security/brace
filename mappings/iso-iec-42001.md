# BRACE and ISO/IEC 42001

This page maps the clause headings and Annex A control titles of ISO/IEC 42001:2023, Edition 1 (AI management systems), to the items in the [BRACE sign-off checklist](../CHECKLIST.md). It shows where a passed BRACE item gives evidence for a deployed agent, and where the work belongs to the wider management system. The standard is published by ISO and IEC at [iso.org/standard/81230.html](https://www.iso.org/standard/81230.html).

> **Source limit:** This mapping uses only the publicly listed clause headings and Annex A control titles. The full paywalled text was not reviewed. It is not a compliance or certification assessment.

## How to read this mapping
- **Direct** — passing the listed BRACE items produces evidence directly relevant to this control for a deployed agent.
- **Partial** — the listed items supply some evidence; the management-system work is outside BRACE.
- **Out of scope** — BRACE doesn't address it; say why in a few words.

BRACE item IDs link to the [checklist](../CHECKLIST.md). Tests and evidence for each item are in the [verification guide](../CHECKLIST-VERIFICATION.md).

## Summary

| Annex A objective | Controls | Direct | Partial | Out of scope |
|---|---|---|---|---|
| A.2 Policies related to AI | 3 | 0 | 0 | 3 |
| A.3 Internal organization | 2 | 0 | 1 | 1 |
| A.4 Resources for AI systems | 5 | 0 | 4 | 1 |
| A.5 Assessing impacts of AI systems | 4 | 0 | 2 | 2 |
| A.6 AI system life cycle | 9 | 3 | 5 | 1 |
| A.7 Data for AI systems | 5 | 0 | 3 | 2 |
| A.8 Information for interested parties | 4 | 0 | 2 | 2 |
| A.9 Use of AI systems | 3 | 0 | 2 | 1 |
| A.10 Third-party and customer relationships | 3 | 0 | 2 | 1 |
| **Total** | **38** | **3** | **21** | **14** |

## Management system clauses (4–10)

| Clause | Heading | BRACE items | How BRACE helps |
|---|---|---|---|
| 4 | Context of the organization | sign-off record, E01 | The deployment record writes down the agent's task, tenants, data, autonomy, and worst credible damage. |
| 5 | Leadership | sign-off record, A02 | The sign-off record names the accountable party, the approver, and the GO or NO-GO decision for each release. |
| 6 | Planning | priority gates, evidence and exception record, B05 | The gates and the harm and autonomy rating decide which gaps block release and which need a signed risk acceptance. |
| 7 | Support | evidence and exception record, C01, E11 | Each item keeps an owner, dated evidence, and a release manifest, stored with access and retention rules. |
| 8 | Operation | C02, C06, B12, C04 | Changes to the agent are reviewed, re-tested before promotion, and checked for drift after release. |
| 9 | Performance evaluation | R08, R13, C04, sign-off record | Monitoring, a full action record, and scheduled re-reviews show whether the agent's controls still work. |
| 10 | Improvement | E12, C06, evidence and exception record | Incident drills, re-tests, and tracked remediation owners turn found gaps into fixes. |

## Annex A controls

### A.2 Policies related to AI

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.2.2 | AI policy | Out of scope | — | BRACE checks one deployment; it does not write an organization's AI policy. |
| A.2.3 | Alignment with other organizational policies | Out of scope | — | BRACE does not compare policies across the organization. |
| A.2.4 | Review of the AI policy | Out of scope | — | BRACE reviews releases, not the organization's policy documents. |

### A.3 Internal organization

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.3.2 | AI roles and responsibilities | Partial | A02, E01, sign-off record | Every action names an accountable party and an operational owner, and every control has a named owner. |
| A.3.3 | Reporting of concerns | Out of scope | — | BRACE has no channel for staff to raise concerns about AI. |

### A.4 Resources for AI systems

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.4.2 | Resource documentation | Partial | C01, B01, E01 | The release manifest and tool inventory list the parts that make up the agent and who owns each one. |
| A.4.3 | Data resources | Partial | C01, R04, B08 | The manifest records dataset and retrieval settings, and the agent's reachable data stores are listed and tested. |
| A.4.4 | Tooling resources | Partial | B01, E02, C01 | Every tool the agent can call is listed, justified, vetted, and pinned; tools used to build models are covered only by version records. |
| A.4.5 | System and computing resources | Partial | B07, B11, B08, C01 | Compute budgets, runtime limits, and reachable systems are set and tested for the deployed agent. |
| A.4.6 | Human resources | Out of scope | — | BRACE does not assess staff skills or staffing. |

### A.5 Assessing impacts of AI systems

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.5.2 | AI system impact assessment process | Partial | sign-off record, priority gates, B05 | Each release rates its potential harm and autonomy, but only for security damage, not wider impact. |
| A.5.3 | Documentation of AI system impact assessments | Partial | sign-off record, evidence and exception record | The rating, its reason, and its approver are recorded with the release. |
| A.5.4 | Assessing AI system impact on individuals or groups of individuals | Out of scope | — | BRACE does not assess fairness, rights, or other effects on people. |
| A.5.5 | Assessing societal impacts of AI systems | Out of scope | — | BRACE does not assess effects on society. |

### A.6 AI system life cycle

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.6.1.2 | Objectives for responsible development of AI systems | Out of scope | — | BRACE does not set development objectives for the organization. |
| A.6.1.3 | Processes for responsible design and development | Partial | B12, C02, C06 | Harness, prompt, and config changes go through review, a recorded author, and release testing. |
| A.6.2.2 | AI system requirements and specification | Partial | sign-off record, B01, B05 | The deployment record and tool allowlist state what the agent may do; functional requirements are outside BRACE. |
| A.6.2.3 | Documentation of AI system design and development | Partial | C01, B12, C02 | Versioned manifests and reviewed diffs record how each release was built and changed. |
| A.6.2.4 | AI system verification and validation | Partial | C06, R02, B05 | Release candidates are tested against allowed tasks and attacks; accuracy and fitness testing are outside BRACE. |
| A.6.2.5 | AI system deployment | Direct | C03, B10, sign-off record, C07 | Only a signed, approved setup that matches its manifest may run, with a tested rollback. |
| A.6.2.6 | AI system operation and monitoring | Direct | R08, C04, R09, R11 | Security monitoring, drift checks, and a tested kill switch cover the running agent. |
| A.6.2.7 | AI system technical documentation | Partial | C01, A03, evidence and exception record | The manifest, identity hash inputs, and test evidence describe the agent; user-facing documentation is outside BRACE. |
| A.6.2.8 | AI system recording of event logs | Direct | R13, A02, E10, E11 | Every action is logged with six identity fields, kept across services, and protected from the agent. |

### A.7 Data for AI systems

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.7.2 | Data for development and enhancement of AI systems | Partial | C01, C05 | Training runs your team performs are linked to dataset versions and test results; data selection is outside BRACE. |
| A.7.3 | Acquisition of data | Partial | R04, E02 | Only approved sources may add retrieval content, and outside datasets are vetted before use. |
| A.7.4 | Quality of data for AI systems | Out of scope | — | BRACE checks data integrity and trust, not whether data is fit to train or evaluate a model. |
| A.7.5 | Data provenance | Partial | R04, R06, C01, C05 | Retrieval chunks and memory entries keep their source and writer; training data provenance is limited to version records. |
| A.7.6 | Data preparation | Out of scope | — | BRACE does not cover cleaning, labeling, or transforming data. |

### A.8 Information for interested parties

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.8.2 | System documentation and information for users | Out of scope | — | BRACE produces records for operators and reviewers, not for users. |
| A.8.3 | External reporting | Partial | E12 | The incident drill names who decides whether to report outside the organization. |
| A.8.4 | Communication of incidents | Partial | E12, R08 | Alerts reach named responders, and the fleet drill tests who is told; outside communication is not tested. |
| A.8.5 | Information for interested parties | Out of scope | — | BRACE does not decide what to tell people outside the deployment team. |

### A.9 Use of AI systems

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.9.2 | Processes for responsible use of AI systems | Partial | B05, B06, sign-off record | High-impact actions need a specific approval, and each release needs a recorded GO decision. |
| A.9.3 | Objectives for responsible use of AI systems | Out of scope | — | BRACE does not set the organization's goals for using AI. |
| A.9.4 | Intended use of the AI system | Partial | sign-off record, B01, B02 | The intended task is written down, and tools and credentials are limited to it and tested. |

### A.10 Third-party and customer relationships

| Control | Title | Coverage | BRACE items | How BRACE helps |
|---|---|---|---|---|
| A.10.2 | Allocating responsibilities | Partial | E01 | Each control names an owner on the agent team and an owner at the platform or vendor; contracts are outside BRACE. |
| A.10.3 | Suppliers | Partial | E02, C05, E03, E01 | Tools, servers, and models from suppliers are vetted, pinned, and re-checked when they change. |
| A.10.4 | Customers | Out of scope | — | BRACE isolates tenants' data but does not cover what customers are told or promised. |

## Sources used for clause and control titles

All retrieved 2026-10-01. A control title was used only where at least two of the sources below agreed on it.

- ISO, [ISO/IEC 42001:2023 catalogue page](https://www.iso.org/standard/81230.html) and [Online Browsing Platform preview](https://www.iso.org/obp/ui/en/#iso:std:iso-iec:42001:ed-1:v1:en). Both block scripted retrieval. On 2026-10-01 the preview was opened in a browser as an anonymous user. It confirmed Edition 1 and the clause headings 4 to 9, including subclauses 4.1 to 8.4. It showed that Annex A is Table A.1, "Control objectives and controls", but the table itself is not in the free preview. Clause 10 and every Annex A title therefore come from the secondary sources below.
- Advisera, [ISO 42001 requirements: clauses and structure](https://advisera.com/articles/iso-42001-clauses-requirements/) — clause headings 4–10.
- Modulos, [ISO/IEC 42001 clauses 4–10](https://docs.modulos.ai/frameworks/iso-42001/clauses-4-10.html) — clause headings 4–10 and Annex A objective titles.
- ISMS.online, [ISO 42001 Annex A controls](https://www.isms.online/iso-42001/annex-a-controls/) — all 38 control IDs and titles.
- DeepInspect, [ISO 42001 Annex A controls](https://www.deepinspect.ai/blog/iso-42001-annex-a-controls) — all 38 control IDs and titles.
- RiskProfs, [ISO 42001 Annex A controls list](https://riskprofs.com/iso-42001-annex-a-controls-list/) — all 38 control IDs and titles.
- TCSA, [ISO 42001 controls](https://www.tcsa.in/frameworks/iso-42001/controls) — all 38 control IDs, with some titles shortened.

Wording differences, resolved by the majority of the four full lists:

- A.5.4: two sources say "Assessing AI system impact on individuals or groups of individuals"; RiskProfs and TCSA use shorter forms.
- A.6.1.3: sources differ after "Processes for responsible ... design and development". This page uses the shortest form, shared by RiskProfs and TCSA.
- A.7.5: three sources say "Data provenance"; TCSA says "Provenance of data".
- A.10.2: three sources say "Allocating responsibilities"; RiskProfs says "Allocation of responsibilities".
- A.8 objective: ISMS.online and DeepInspect add "of AI systems" to the title; four sources do not.
- One public page ([Presencis](https://cdn.presencis.com/regulations/iso-42001/article-A/)) lists different IDs and titles, such as A.3.4 and A.6.7, that match no other source. It was not used.

## Limits

- Coverage grades rest on control titles only. A control's full text may ask for more or less than its title suggests.
- BRACE checks one deployed agent's security controls. An ISO/IEC 42001 management system covers the whole organization and all its AI systems.
- BRACE deals with security harm: hijacked or misaligned agents. It does not assess fairness, accuracy, or effects on people and society.
- "Direct" means a passed item gives relevant evidence. It does not mean the control is met.
- Clause and control titles were checked on 2026-10-01. Recheck them against the official text before relying on this page in an audit.

---
*Part of [BRACE](../README.md), a security framework for autonomous AI agents. CC BY 4.0.*
