# BRACE Framework — security for autonomous AI agents

**BRACE Framework** is a practical, vendor-neutral set of security controls for teams that build and operate autonomous AI agents — the kind that plan multiple steps, call tools and APIs, change real systems, and spawn sub-agents without a human reviewing each action.

It is built around one idea:

> An autonomous agent combines code with a **runtime configuration** — a container, a harness (the loop that runs the model and hands it tools), a system prompt, a set of tools, a memory store, an identity, and a network path. Two agents built from the same model can behave completely differently depending on how those parts are configured. Review the **configuration together with the harness, tools, and generated code**. Code review remains necessary; it does not capture the complete running agent by itself.

BRACE defines controls for that configuration, sets implementation priorities, and specifies the records needed to operate and verify those controls.

**BRACE stands for** the five concerns it organizes: **B**uild-time, **R**un-time, **A**gent, **C**onfiguration, **E**cosystem.

**Website:** https://braceframework.org

---

## Start here

- **[Sign-off checklist](CHECKLIST.md)** — a 53-item go/no-go review across all five BRACE aspects, with operational notes and acceptable tradeoffs for the engineer or manager approving an agent for production. If you read one thing, read this.
- **[Self-assessment](SELF-ASSESSMENT.md)** — score the same 53 checklist items for an existing deployment or vendor evaluation.
- **[Source review](SOURCE-REVIEW.md)** — supporting references, practical corrections, and limits of the evidence.

---

## The framework in one screen

BRACE specifies **nine controls** and **three observability requirements**.

**Build-time controls** (fixed when the agent is built, frozen into the deployed artifact):

| # | Control | What it does |
|---|---------|--------------|
| 1 | Architecture | Environment and network isolation; bound the blast radius by topology, not good behavior. |
| 2 | Capability-scoped API access | Tokens grant specific capabilities (`read:tickets`, not `*`); least privilege. |
| 3 | Container | Signed, minimal, kernel-isolated image; the image hash is part of the agent's identity. |
| 4 | Harness | Enforces permitted tools, arguments, and limits, including **destructive-action interception**: high-impact operations are blocked unless specifically authorized. |

**Run-time controls** (active on every execution):

| # | Control | What it does |
|---|---------|--------------|
| 5 | Data | Treat all external input as untrusted; validate at the boundary; assume prompt injection sometimes succeeds. |
| 6 | Memory | Scope memory per instance and per type; validate writes; keep provenance per entry. |
| 7 | Behavioral | Security-anomaly monitoring (distinct from quality monitoring): evasion, privilege escalation, multi-step composed attacks. |

**Closure controls** (stop and explain):

| # | Control | What it does |
|---|---------|--------------|
| 8 | Kill Switch | A *tested* way to halt the agent and its sub-agents within a risk-matched budget, leaving a safe state. |
| 9 | Audit Trail | The full execution graph for every action — not just the final output. |

**Observability requirements** (the data the controls above depend on — not separate defenses):

| # | Requirement | What it adds |
|---|-------------|--------------|
| T1 | Required identity fields | Six fields on every action (below). |
| T2 | Context-size logging | The context size at decision time, so baselines can be split by context-size range. |
| T3 | Sub-agent & parent-prompt provenance | Which sub-agent ran, and the prompt the parent gave it. |

**Every control and observability requirement has two halves:** the settings for each agent type and the support provided by shared infrastructure and services. You cannot secure one half alone: an agent cannot present a narrowly scoped token unless the identity system can issue one.

### The six required identity fields (T1)

Every action carries: **accountable party**, **operational owner**, **tenant**, **agent-type-id**, **agent-instance-id**, and **trace context**. (Optional: region, trust domain.)

The **agent-type-id** is a content hash — a fingerprint — over the container digest, harness, system prompt, model identifier/version (including checkpoint and fine-tune/adapter references where applicable), and config. Recompute it when recorded inputs change and compare running artifacts with the approved manifest to detect drift. A local hash cannot prove that undisclosed hosted-provider state is unchanged. Record model and owned-training lineage using the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields). See **[otel-conventions.md](otel-conventions.md)** for the proposed OpenTelemetry attribute keys (`agent.type.id`, `agent.instance.id`, `agent.context.size`, `agent.parent.prompt`).

---

## What to ship first

Build the twelve elements in stages, applying the checklist’s release gates at each stage. Start in this order:

- **Tier 1 — prevent damage, preserve attribution.** Harness enforcement of destructive-action permissions (Control 4), capability-scoped tokens (Control 2), a tested kill switch (Control 8), an audit trail (Control 9), and the six identity fields (T1). These controls bound damage and support reconstruction when enforcement and audit coverage are demonstrated.
- **Tier 2 — harden the substrate, surface invisible failures.** Architecture/egress isolation (Control 1), a signed and minimal container (Control 3), input validation (Control 5), context-size logging (T2).
- **Tier 3 — active detection.** Behavioral monitoring with sequence-pattern baselines (Control 7), memory provenance and scoping (Control 6), sub-agent and parent-prompt provenance (T3).

The [checklist](CHECKLIST.md) applies these priorities as **G1/G2/G3** gates to individual items: G1 gaps block release; G2 gaps need explicit, time-bounded acceptance; G3 gaps block high-stakes or high-autonomy deployments and require documented acceptance for lower-stakes deployments. Operational fallbacks may reduce functionality or introduce manual work; they do not automatically turn a gap into a pass.

Use the checklist as the source of requirements, the [verification guide](CHECKLIST-VERIFICATION.md) for exercises and evidence, and the [self-assessment](SELF-ASSESSMENT.md) to score the same item IDs. The website guides explain the principles and link to those items.

---

## How BRACE relates to OWASP, NIST, and MITRE

BRACE organizes deployment checks alongside existing security guidance. Its grouping and adoption gates are project design choices, not claims that other frameworks lack practical controls:

- **OWASP Top 10 for Agentic Applications** — a threat catalog. BRACE maps each of its ten risks (ASI01–ASI10) to the controls that mitigate them.
- **[OWASP Agent Control Standard (ACS)](https://genai.owasp.org/resource/agent-control-standard-acs/)** — runtime policy hooks and enforcement; complements BRACE's deployment review.
- **MITRE ATLAS** — an attacker-technique catalog. BRACE maps the agentic techniques to controls.
- **NIST AI RMF / ISO 42001** — governance and compliance. BRACE is the technical control layer underneath the governance.

Use OWASP and MITRE to know *what can go wrong*. Use BRACE to know *what to build and in what order*.

### What BRACE emphasizes

Five concrete requirements this project brings together:

1. Treat the **harness, system prompt, and built-in tools** as hardening artifacts — versioned, diff-reviewed, distinct from the external tool surface. This is where destructive-action permissions are enforced.
2. **Six required identity fields** on every action, including the content-hashed agent-type-id.
3. **Context-size logging** at decision time, with baselines split by context-size range.
4. **Sub-agent and parent-prompt provenance** as a first-class field — separating "the sub-agent misbehaved" from "the parent prompted it badly."
5. **Infrastructure-as-code drift detection** applied at agent granularity (container, harness, MCP server list, system prompt, network policy).

---

## Two threat models, one containment layer

BRACE was built for the **hijacked-or-misused agent** — an agent manipulated by prompt injection, a poisoned tool, or a supply-chain compromise. It also contains the **misaligned-insider** model (the model itself acting as a deliberate adversary), because containment does not depend on *why* an agent went rogue: a scoped token, an egress allowlist, and a tested kill switch bound the damage either way.

What BRACE does **not** do is detect misaligned *intent* inside otherwise-authorized behavior (alignment faking, sandbagging). That is a model-and-monitoring problem — the domain of AI control work such as Google DeepMind's AI Control Roadmap. BRACE is the containment layer; AI control is the detection layer; the two compose.

---

## Status and honesty

BRACE is a **synthesis of agent-security practice already in production** across the industry — not yet a validated standard. The individual controls are widely deployed; what BRACE adds is the unified organization and the agent-granularity instrumentation. The integrated framework has not yet been measured against a control group. It is an open, evolving project — apply it, critique it, and contribute (see **[CONTRIBUTING.md](CONTRIBUTING.md)**).

---

## The paper

The repository is the reviewable framework artifact. A standalone paper and the previously claimed 35+ incident corpus were not available in this checkout for the 2026-09-16 source audit; neither is treated as verified evidence for checklist requirements. See the [source review](SOURCE-REVIEW.md) for primary references and limits.

To cite BRACE, use [`CITATION.cff`](CITATION.cff), or reference this repository and the project site directly.

## Repository contents

| File | What it is |
|------|------------|
| [CHECKLIST.md](CHECKLIST.md) | The 53-item sign-off review, with operational challenges, fallbacks, and tradeoffs. |
| [SOURCE-REVIEW.md](SOURCE-REVIEW.md) | Dated source review covering all 53 items, with references and verification limits. |
| [CHECKLIST-VERIFICATION.md](CHECKLIST-VERIFICATION.md) | Practical verification recipes for every checklist item, including model and training provenance fields. |
| [SELF-ASSESSMENT.md](SELF-ASSESSMENT.md) | Scoring worksheet for the same 53 checklist item IDs and gates. |
| [otel-conventions.md](otel-conventions.md) | Proposed OpenTelemetry attributes for agent identity and provenance. |
| [VENDOR-MATRIX.md](VENDOR-MATRIX.md) | Evidence to request when evaluating vendor and platform support for each control. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to propose changes, report incidents, or map a vendor product. |
| [GOVERNANCE.md](GOVERNANCE.md) | How the project is run, and how to become a co-maintainer. |
| [ROADMAP.md](ROADMAP.md) | What's planned, and how priorities are set. |
| [ADOPTERS.md](ADOPTERS.md) | Teams, assessors, and products using BRACE — and how to get listed. |
| [outreach/](outreach/) | Proposals to OWASP, NIST CAISI, and the OpenTelemetry GenAI SIG, plus the launch write-up. |
| [CITATION.cff](CITATION.cff) | How to cite BRACE. |

## License

Released under [CC BY 4.0](LICENSE). Use it, adapt it, build on it — just credit the source.
