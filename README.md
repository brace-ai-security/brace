# BRACE Framework — security for autonomous AI agents

**BRACE Framework** is a practical, vendor-neutral set of security controls for teams that build and run autonomous AI agents. These agents plan several steps, call tools and APIs, change real systems, and start sub-agents, with no person reviewing each action.

It is built on one idea:

> An autonomous agent combines code with a **runtime configuration** — a container, a harness (the loop that runs the model and hands it tools), a system prompt, a set of tools, a memory store, an identity, and a network path. Two agents built from the same model can behave completely differently depending on how those parts are configured. Review the **configuration together with the harness, tools, and generated code**. Code review is still needed, but on its own it doesn't show the whole running agent.

BRACE defines controls for that configuration, says which to build first, and lists the records you need to run and check those controls.

**BRACE stands for** its five aspects: **B**uild-time, **R**un-time, **A**gent, **C**onfiguration, **E**cosystem.

**Website:** https://braceframework.org

---

## Start here

- **[Sign-off checklist](CHECKLIST.md)** — a 53-item go/no-go review across all five BRACE aspects. It is for the engineer or manager who approves an agent for production, and it notes what is hard, what to do if you can't fully comply, and which tradeoffs are acceptable. If you read one thing, read this.
- **[Self-assessment](SELF-ASSESSMENT.md)** — score the same 53 checklist items for a running deployment or a vendor.
- **[Source review](SOURCE-REVIEW.md)** — supporting sources, corrections, and the limits of the evidence.

---

## The framework in one screen

BRACE has **nine controls** (C1–C9) and **three observability requirements** (Obs-T1 to Obs-T3). The [checklist](CHECKLIST.md) uses these codes on every item.

**Build-time controls** are set when the agent is built and locked into what you deploy:

| Code | Control | What it does |
|---|---------|--------------|
| C1 | Architecture | Isolate the agent's environment and network. Allow only the outside destinations its task needs. Limit damage by design, not by trusting good behavior. |
| C2 | Capability-scoped API access | Give each token only the powers it needs (`read:tickets`, not `*`). Keep tokens short-lived, limited to one service, and bound to their holder where possible. Make sure you can cut off the agent without cutting off its user. |
| C3 | Container | Run a pinned, signed, minimal image whose build record you have checked. Use a stronger sandbox, such as a microVM, when the agent runs untrusted code. The image digest is part of the agent's identity. |
| C4 | Harness | Enforce which tools, arguments, and budgets the agent may use. **Block destructive actions** unless someone with authority approves that exact action. Treat every consequential action as destructive when one agent can read untrusted input, reach sensitive data, and act on the outside world. |

**Run-time controls** work on every run:

| Code | Control | What it does |
|---|---------|--------------|
| C5 | Data | Treat all outside input as untrusted, including API responses. Check it at the boundary. Assume some prompt injections will work, and make sure other controls still block the harm. Keep secrets out of outputs and logs. |
| C6 | Memory | Separate memory by tenant, agent type, and instance. Check what gets written, and record where each entry came from. Apply the same care to the documents the agent searches. |
| C7 | Behavioral | Watch for security problems, separately from answer quality. Look for evasion, privilege escalation, and attacks spread across several allowed steps. |

**Closure controls** let you stop the agent and explain what it did:

| Code | Control | What it does |
|---|---------|--------------|
| C8 | Kill Switch | A *tested* way to stop the agent and all its sub-agents within a set time, leaving things in a safe state. The agent can't disable or delay it. |
| C9 | Audit Trail | A full record of every action, decision, and result, not just the final answer. The agent can't erase or rewrite it. |

**Observability requirements** are the data the controls depend on. They are not separate defenses:

| Code | Requirement | What it adds |
|---|-------------|--------------|
| Obs-T1 | Required identity fields | Six fields on every action (below). |
| Obs-T2 | Context-size logging | How full the model's context was when it decided, so you can compare behavior at different context sizes. Mark missing values as unknown, never zero. |
| Obs-T3 | Sub-agent and parent-prompt provenance | Which sub-agent ran, and the prompt its parent gave it. |

**Every control has two halves:** the settings for each agent type, and the support from shared infrastructure and services. You can't secure one half alone. For example, an agent can't present a narrowly scoped token unless the identity system can issue one.

### The six required identity fields (Obs-T1)

Every action records: **accountable party**, **operational owner**, **tenant**, **agent-type-id**, **agent-instance-id**, and **trace context**. (Optional: region, trust domain.)

The **agent-type-id** is a fingerprint (a content hash) of the container digest, harness, system prompt, model ID and version (including checkpoint and fine-tune or adapter references), and configuration. Recompute it whenever one of those inputs changes. Compare what is running with the approved manifest to catch drift. A local hash can't prove that a hosted provider's hidden state is unchanged. Record model and training history using the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields). See **[otel-conventions.md](otel-conventions.md)** for the proposed OpenTelemetry attribute names (`agent.type.id`, `agent.instance.id`, `agent.context.size`, `agent.parent.prompt`).

---

## What to ship first

Build the twelve elements (nine controls and three observability requirements) in stages. Apply the checklist’s release gates at each stage. Start in this order:

- **Tier 1 — prevent damage, keep track of who did what.** Harness blocking of destructive actions (C4), capability-scoped tokens (C2), a tested kill switch (C8), an audit trail (C9), and the six identity fields (Obs-T1). Once you show they are enforced and the audit covers every action, these controls limit damage and let you rebuild what happened.
- **Tier 2 — harden the substrate (the environment the agent runs on), and expose hidden failures.** Network and egress isolation (C1), a signed, minimal container (C3), input validation (C5), and context-size logging (Obs-T2).
- **Tier 3 — active detection.** Security monitoring with baselines of normal action sequences (C7), memory scoping and source records (C6), and sub-agent and parent-prompt provenance (Obs-T3).

The [checklist](CHECKLIST.md) turns these priorities into **G1/G2/G3** gates on each item. G stands for gate. A G1 gap blocks release. A G2 gap needs a written, approved risk acceptance. A G3 gap blocks high-stakes or high-autonomy deployments, and needs a written, approved risk acceptance for lower-stakes ones. Fallbacks may cost features or add manual work. They don't turn a gap into a pass on their own.

Use the checklist for the requirements, the [verification guide](CHECKLIST-VERIFICATION.md) for tests and evidence, and the [self-assessment](SELF-ASSESSMENT.md) to score the same item IDs. The [website guides](https://braceframework.org/guides/) explain the principles and link to those items.

---

## How BRACE relates to OWASP, NIST, and MITRE

BRACE organizes deployment checks to sit alongside existing security guidance. Its grouping and release gates are this project's design choices. They are not claims that other frameworks lack practical controls:

- **[OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)** — a threat catalog of ten risks ([ASI01–ASI10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)). BRACE names the controls that reduce them. A risk-to-control table is in the [OWASP proposal](outreach/owasp-agentic-controls-proposal.md). It is a historical draft, so check it against the current checklist.
- **[OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/)** — policy hooks and enforcement while the agent runs. It complements BRACE's deployment review.
- **[MITRE ATLAS](https://atlas.mitre.org/)** — a catalog of attacker techniques against AI systems. The [ATLAS mapping](mappings/mitre-atlas.md) shows which BRACE items address each of its 208 techniques in release v2026.09.
- **[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) / [ISO/IEC 42001](https://www.iso.org/standard/81230.html)** — references for governance and management systems. BRACE adds technical checks for each deployment alongside them. See the [AI RMF mapping](mappings/nist-ai-rmf.md) and the [ISO/IEC 42001 mapping](mappings/iso-iec-42001.md). Mapping is not compliance: passing BRACE items doesn't mean an organization meets either one.

Use OWASP and MITRE to know *what can go wrong*. Use BRACE to know *what to build and in what order*.

### What BRACE emphasizes

Five concrete requirements BRACE brings together:

1. Treat the **harness, system prompt, and built-in tools** as security artifacts. Version them, review their diffs, and keep them separate from outside tools. The harness is where destructive actions are blocked.
2. **Six required identity fields** on every action, including the content-hashed agent-type-id.
3. **Context-size logging** at decision time, with behavior baselines split by context-size range.
4. **Sub-agent and parent-prompt provenance** as a required field. It separates "the sub-agent misbehaved" from "the parent gave it a bad prompt."
5. **Drift detection** for each agent, using infrastructure-as-code: compare the running container, harness, MCP server list, system prompt, and network policy with what was approved.

---

## Two threat models, one containment layer

BRACE was built for the **hijacked or misused agent**: one manipulated by prompt injection, a poisoned tool, or a supply-chain attack. It also helps contain the **misaligned insider**, where the model itself acts as a deliberate adversary. Containment does not depend on *why* an agent went rogue. A scoped token, an egress allowlist, and a tested kill switch limit the damage either way.

BRACE does **not** detect misaligned *intent* hidden inside allowed behavior, such as a model faking alignment or deliberately underperforming. That is a problem for model research and monitoring, the field of AI control work such as Google DeepMind's [AI Control Roadmap](https://arxiv.org/abs/2607.13087). BRACE is the containment layer. AI control is the detection layer. Use both.

---

## Status and honesty

BRACE **brings together agent-security practices already used in production**. It is not yet a validated standard. The individual controls are widely used. BRACE adds one way to organize them, and logging for each agent. The framework as a whole has not been measured against a control group. It is an open project that keeps changing. Apply it, critique it, and contribute (see **[CONTRIBUTING.md](CONTRIBUTING.md)**).

---

## Citing BRACE

This repository is the framework. There is no separate paper. See the [source review](SOURCE-REVIEW.md) for primary sources and limits.

To cite BRACE, use [`CITATION.cff`](CITATION.cff), or reference this repository and the project site directly.

## Repository contents

| File | What it is |
|------|------------|
| [CHECKLIST.md](CHECKLIST.md) | The 53-item sign-off review, with what is hard, fallbacks, and tradeoffs. |
| [SOURCE-REVIEW.md](SOURCE-REVIEW.md) | Dated source review covering all 53 items, with sources and the limits of what was checked. |
| [CHECKLIST-VERIFICATION.md](CHECKLIST-VERIFICATION.md) | A test, expected result, and evidence for every checklist item, plus model and training provenance fields. |
| [SELF-ASSESSMENT.md](SELF-ASSESSMENT.md) | Scoring worksheet for the same 53 checklist item IDs and gates. |
| [otel-conventions.md](otel-conventions.md) | Proposed OpenTelemetry attributes for agent identity and provenance. |
| [mappings/](mappings/) | How BRACE items line up with [MITRE ATLAS](mappings/mitre-atlas.md), the [NIST AI RMF](mappings/nist-ai-rmf.md), and [ISO/IEC 42001](mappings/iso-iec-42001.md). Each row is rated Direct, Partial, or Out of scope. |
| [VENDOR-MATRIX.md](VENDOR-MATRIX.md) | Evidence to request when evaluating vendor and platform support for each control. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to propose changes, report a real-world incident, or map a vendor product. |
| [GOVERNANCE.md](GOVERNANCE.md) | How the project is run, and how to become a co-maintainer. |
| [ROADMAP.md](ROADMAP.md) | What's planned, and how priorities are set. |
| [ADOPTERS.md](ADOPTERS.md) | Teams, assessors, and products using BRACE — and how to get listed. |
| [outreach/](outreach/) | Proposals to OWASP, NIST CAISI, CoSAI, CSA, and the OpenTelemetry GenAI SIG, plus the launch write-up. Drafts marked historical are not current evidence. |
| [CITATION.cff](CITATION.cff) | How to cite BRACE. |

## License

Released under [CC BY 4.0](LICENSE). Use it, adapt it, and build on it. Just credit the source.
