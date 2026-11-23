<!-- GENERATED from ROLES.md in the BRACE repository. Do not edit by hand; CI/CD regenerates this copy. Content below is copied exactly. -->
# BRACE role map

Securing an agent takes more than the team that builds it. This page shows which role should handle each item in the [sign-off checklist](CHECKLIST.md), and each sign-off duty. Use it in step 2 of the checklist, when you give every item an owner.

## The roles

| Role | Who it usually is | What it brings |
|---|---|---|
| **Agent team** | The engineers who build the agent. | The harness, system prompt, tools, model choice, release manifest, and tests. |
| **Operations** | The people who run the agent in production, including analytics and on-call. | Monitoring, alerts, drills, the stop control, drift checks, and pulling records during an incident. |
| **Security** | The security team, including red team and detection engineering. | Threat review, attack testing, detection rules, dependency vetting, and incident response. |
| **Infrastructure** | The platform team that runs shared services. | Identity and secrets, network and egress rules, container runtime and sandbox, the MCP gateway, and the logging pipeline. |
| **Governance** | A cross-team group with authority to approve risk, such as a risk committee or AI review board. | Harm and autonomy ratings, risk acceptance, change rules, and the separate deployment decision and high-risk rollout oversight. |
| **Business owner** | The person or team that owns what the agent is for. | The agent's task and allowed actions, the worst damage it could do, and approval of high-impact actions while it runs. Usually the **accountable party** and **operational owner** in A02's identity fields. |
| **Data and privacy** | The data protection officer, privacy team, or the owners of the data sets the agent uses. | What data is sensitive, who may see it, what memory and logs may keep, redaction, and retention rules. |
| **Model team** | The team that trains, fine-tunes, or hosts your own models. Only needed if you do that. | Training-run and dataset records, signed weights, and checker models. If you only call hosted models, the Agent team takes these shares. |
| **Vendors** | Outside providers: the model provider, MCP server publishers, a managed gateway or runtime. | Evidence for their half of each control, such as isolation records, served model versions, and audit exports. |
| **Independent audit** | Internal audit or an outside assessor who didn't build or run the agent. Optional, but useful in regulated settings. | A check of the evidence before release, and of whether approvals were kept separate from the work. |

## How to read this map

- **Lead** — one role per item. The Lead makes sure the item gets done and answers for its evidence. Put the Lead's name in the owner column of the [evidence record](CHECKLIST.md#evidence-and-exception-record).
- **Shares** — roles that do part of the work, supply evidence, or must review it. An item can have several.
- A role not listed can still help.

Each item has exactly one Lead, because shared ownership with no single answer tends to mean no one does the work. Two roles never lead: **Vendors**, because someone inside your organization must answer for each item, and **Independent audit**, because it checks the work rather than doing it.

This map is a starting point, not a rule. Move a Lead when your teams are set up differently. For example, a platform team that builds the harness for every agent could lead B05 and B06. Record the change in the evidence record.

## Who leads and shares how much

| Role | Leads items | Shares items | Leads duties | Shares duties |
|---|---|---|---|---|
| Agent team | 23 | 17 | 2 | 5 |
| Operations | 6 | 13 | 2 | 2 |
| Security | 7 | 29 | 0 | 8 |
| Infrastructure | 15 | 17 | 0 | 4 |
| Governance | 2 | 7 | 7 | 4 |
| Business owner | 0 | 8 | 2 | 5 |
| Data and privacy | 0 | 7 | 1 | 1 |
| Model team | 0 | 7 | 0 | 0 |
| Vendors | 0 | 8 | 0 | 1 |
| Independent audit | 0 | 0 | 1 | 1 |

Governance and the Business owner lead few items but own most sign-off decisions. Infrastructure leads many items because an agent can't show a narrow token, an egress rule, or a gateway unless the platform provides it. Every BRACE control has these two halves: what the agent team sets, and what shared services support.

## Checklist items

### B — Build-time

| Item | Gate | Title | Lead | Shares |
|---|---|---|---|---|
| B05 | Blocker | Destructive-action interception | **Agent team** | Business owner, Security, Governance |
| B02 | Blocker | Least-privilege access | **Infrastructure** | Agent team, Security |
| B01 | Blocker | Minimal tool surface | **Agent team** | Security |
| B03 | Required | Credential lifetime and handling | **Infrastructure** | Security |
| B04 | Blocker | Independent revocation | **Infrastructure** | Operations, Security |
| B06 | Blocker | Approval integrity | **Agent team** | Business owner, Security, Infrastructure |
| B07 | Required | Hard execution budgets | **Agent team** | Business owner, Infrastructure, Operations |
| B08 | Required | Environment isolation | **Infrastructure** | Security |
| B09 | Required | Egress allowlist | **Infrastructure** | Security, Operations |
| B10 | Required | Pinned, verified image | **Infrastructure** | Security, Agent team |
| B11 | Required | Minimal, isolated runtime | **Infrastructure** | Security, Agent team, Vendors |
| B12 | Blocker | Reviewed harness and instructions | **Agent team** | Security, Governance |

### R — Run-time

| Item | Gate | Title | Lead | Shares |
|---|---|---|---|---|
| R11 | Blocker | Tested kill switch | **Operations** | Infrastructure, Agent team |
| R13 | Blocker | Full execution audit | **Agent team** | Infrastructure, Operations |
| R01 | Required | Validate every input boundary, including API responses | **Agent team** | Security |
| R02 | Required | Separate data from instructions and test injection containment | **Security** | Agent team |
| R03 | Required | Prevent output and log leakage | **Agent team** | Security, Data and privacy, Infrastructure |
| R04 | Required | Retrieval-corpus integrity | **Agent team** | Data and privacy, Infrastructure, Security |
| R05 | Detection | Memory isolation and write validation | **Agent team** | Data and privacy, Security |
| R06 | Detection | Memory provenance and cleanup | **Agent team** | Operations, Data and privacy |
| R07 | Required | Decision-time context size | **Agent team** | Operations |
| R08 | Detection | Security monitoring | **Security** | Operations |
| R09 | Detection | Sequence and context-aware detection | **Security** | Operations, Agent team |
| R10 | Detection | Misaligned-behavior review | **Security** | Agent team, Governance |
| R12 | Blocker | Safe state after stopping | **Agent team** | Operations, Business owner |
| R14 | Required | Recovery integrity | **Agent team** | Infrastructure, Operations |

### A — Agent

| Item | Gate | Title | Lead | Shares |
|---|---|---|---|---|
| A01 | Blocker | Distinct agent identity | **Infrastructure** | Agent team |
| A02 | Blocker | All six identity fields | **Agent team** | Infrastructure, Business owner, Governance |
| A03 | Blocker | Content-derived type identity | **Agent team** | Model team |
| A04 | Blocker | Trustworthy attribution | **Infrastructure** | Agent team, Security |
| A05 | Blocker | Operational lookup | **Operations** | Business owner, Governance, Infrastructure |
| A06 | Detection | Parent and prompt provenance | **Agent team** | Data and privacy, Security |
| A07 | Detection | Every model in the loop | **Agent team** | Model team, Security |

### C — Configuration

| Item | Gate | Title | Lead | Shares |
|---|---|---|---|---|
| C01 | Required | Complete release manifest | **Agent team** | Infrastructure, Model team, Data and privacy |
| C03 | Blocker | Match release identity to running state | **Infrastructure** | Agent team, Operations, Model team |
| C04 | Required | Detect drift per agent | **Operations** | Infrastructure, Security, Model team |
| C02 | Required | Review security-relevant changes | **Governance** | Agent team, Security |
| C05 | Required | Control dependency, model, and training changes | **Agent team** | Model team, Security, Vendors |
| C06 | Required | Re-test changed behavior | **Agent team** | Security, Business owner |
| C07 | Required | Rollback and restart | **Operations** | Agent team, Infrastructure |
| C08 | Required | Connect configuration to execution | **Operations** | Agent team, Infrastructure |

### E — Ecosystem

| Item | Gate | Title | Lead | Shares |
|---|---|---|---|---|
| E06 | Required | Enforced gateway boundary | **Infrastructure** | Security, Agent team, Vendors |
| E08 | Blocker | Bounded delegated authority | **Agent team** | Infrastructure, Security |
| E09 | Blocker | Recursive shutdown | **Operations** | Agent team, Infrastructure |
| E01 | Required | Map shared responsibilities | **Governance** | Agent team, Infrastructure, Vendors |
| E02 | Required | Vet and pin dependencies | **Security** | Agent team, Model team, Vendors |
| E03 | Required | Re-check tools on load | **Infrastructure** | Security, Vendors |
| E04 | Required | Inspect tool metadata | **Security** | Infrastructure |
| E05 | Required | Verified, namespaced tools | **Infrastructure** | Security |
| E07 | Required | Untrusted peer messages | **Agent team** | Security |
| E10 | Blocker | Audit across service boundaries | **Infrastructure** | Operations, Security, Vendors |
| E11 | Required | Protect shared evidence | **Infrastructure** | Governance, Data and privacy, Security, Vendors |
| E12 | Detection | Fleet incident response | **Security** | Operations, Governance, Business owner |

## Sign-off duties

These steps come from the checklist's [how-to](CHECKLIST.md#how-to-use-this-checklist), [priority gates](CHECKLIST.md#priority-gates), and [final sign-off](CHECKLIST.md#final-sign-off). They aren't numbered items, but someone has to own them.

| Duty | Lead | Shares |
|---|---|---|
| Describe the deployment: task, allowed actions, and worst credible damage | **Business owner** | Agent team, Security, Governance |
| Rate how sensitive the data is, and which tenants' data the agent can reach | **Data and privacy** | Business owner, Agent team |
| Rate potential harm and autonomy, and record why | **Governance** | Business owner, Security, Agent team |
| Approve high-impact actions while the agent runs (B05, B06) | **Business owner** | Governance |
| Run the verification recipes against the release candidate | **Agent team** | Operations, Security, Infrastructure |
| Approve each N/A | **Governance** | Security |
| Approve Required and Detection risk acceptances | **Governance** | Security, Business owner |
| Fix gaps and track remediation owners | **Agent team** | Operations, Security, Infrastructure |
| Record emergency changes (C02) | **Operations** | Governance |
| Check evidence independently before a deployment decision, at least for Blocker items | **Independent audit** | Governance |
| Own and record the deployment decision separately from BRACE findings, including a gradual monitored high-risk rollout | **Governance** | Business owner, Security |
| Keep the stop control, response steps, and evidence reachable by operators | **Operations** | Infrastructure |
| Get evidence for the vendor half of each control (E01) | **Governance** | Agent team, Infrastructure, Vendors |
| Schedule and run re-reviews | **Governance** | Agent team, Independent audit |
| Decide on outside reporting and information sharing after an incident (E12) | **Governance** | Security, Business owner, Data and privacy |

## Keep approval separate from the work

- Someone outside the Agent team should approve risk acceptances and N/A decisions, and own the deployment decision independently of BRACE findings. A team that approves its own gaps has a reason to approve them.
- High-impact actions at run time (B05, B06) should be approved by the Business owner or another named authority, not by the team that built the agent.
- Security should not be the only reviewer of evidence it produced. Where Security leads an item, such as R02 or E02, have the Agent team or Operations check the result.
- A vendor's statement is evidence to check, not a Pass. The internal Lead decides whether it meets the item.
- Agents must never hold a role. A role that can approve, stop, or change the agent needs a person or a system the agent can't control (see R11, B06, and E10).

## Small teams

In a small company, one person may hold several roles. That's fine, as long as:

- every item still has a named Lead;
- the person who approves a risk acceptance isn't the only person who built the agent; if that can't be avoided, record it as a gap in the sign-off record;
- the stop control works without the Agent team, for example at night or when they are unavailable.

Drop the Model team if you don't train or host models, and Independent audit if no one requires it. Don't drop Vendors: if you use an outside model, tool, or service, its half of each control still needs evidence (E01).

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
