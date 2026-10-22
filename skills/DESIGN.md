# BRACE skill design and evidence

Design recorded 2026-10-22. Four directly invocable sibling skills separate the
user's jobs. Conditional reference files supply detail within a job. This is an
engineering choice informed by the sources below, not a research-proven optimum.

## Structure and ownership

| User's job | Entrypoint | Output and boundary |
|---|---|---|
| Review an entire agent | `brace-review` | Canonical 53-item findings JSON, coverage ledger and report. Preserves its existing validation and challenge workflow. |
| Review MCP servers/configuration | `brace-mcp-review` | Focused evidence/coverage report with BRACE and primary-source mappings. No server launch, scanner execution or whole-checklist completion claim. |
| Produce enforcement evidence | `brace-tests` | Tests/drills and dated results for named items in an authorized controlled environment. A proposed test is not permission to run it. |
| Maintain the assessment record | `brace-record` | Evidence-backed draft outcomes, exceptions and N/A requests. People approve; static review ratings alone do not become Pass. |

Inside the MCP folder, `SKILL.md` contains scope, safety boundaries, workflow and
report contract. `references/control-map.md` maps review topics to BRACE and source
authority. `references/http.md` and `references/stdio.md` load only for the transports
present; extension detail is conditional too. `references/advisories.md` is a dated
index, not a live vulnerability feed. The complete folder is independently portable.

These reference files are not independently discoverable skills or subagents.
A separate skill earns its place when it has a distinct user trigger, procedure
and useful output. We do not create a separate skill for each transport, advisory
or checklist item. No umbrella router is required for direct use. Full reviews can
use focused MCP findings as evidence without skipping canonical checklist coverage.

Handoffs preserve component/transport scope, code evidence, BRACE IDs, versions,
source URLs/dates, owners and unknowns. Review vocabulary remains `likely_pass`,
`gap`, `needs_evidence`, `na_candidate`; those are drafts, not approved record states.
MCP Markdown reports are not interchangeable with the full-review JSON schema.

## Official authoring guidance

| Primary source | What it supports | Boundary on the inference |
|---|---|---|
| [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills), living documentation checked 2026-10-22 | One job per skill; concise discriminating descriptions; explicit inputs/outputs; instructions before scripts unless deterministic tooling is needed; test triggering. Metadata is loaded before the skill body. | Product guidance, not a controlled comparison of alternative BRACE architectures. |
| [Agent Skills: creator best practices](https://agentskills.io/skill-creation/best-practices), living guidance checked 2026-10-22 | Coherent units, project-specific expertise, conditional references, calibrated control and real execution traces. Avoid both oversized skills and splitting a job so narrowly that many skills must load together. | Its size recommendations are authoring guidance, not universal accuracy thresholds. |
| [Anthropic: Equipping agents with Agent Skills](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills), 2025-10-16, updated 2025-12-18 | Progressive disclosure from descriptions to workflow to relevant resources; evaluate representative tasks and audit the complete bundle, including scripts and dependencies. | Vendor engineering guidance; does not validate a nested delegation tree or establish BRACE reviewer reliability. |

## Empirical research

| Primary paper and version | Finding relevant to this design | Limits |
|---|---|---|
| [SkillsBench v4](https://arxiv.org/html/2602.12670v4), revised 2026-06-14 | Curated skills improve mean task success in its matched evaluation. Focus and task-specific procedures matter; very large bundles have weaker results in reported groups. | Skill-count/size groups contain different tasks. The “2–3 skills” observation is not a causal splitting experiment, optimal cap or evidence for nested sub-skills. |
| [How Well Do Agentic Skills Work in the Wild? v1](https://arxiv.org/html/2604.04323v1), 2026-04-06 | Autonomous selection, distractors and retrieval can reduce gains compared with forced loading. Evaluate discovery separately from task performance. | Particular models, harnesses and benchmark tasks; not an experiment on BRACE folder layout. |
| [SWE-Skills-Bench v1](https://arxiv.org/html/2603.15401v1), 2026-03-16 | Specialized guidance sometimes helps; incompatible versions and generic instructions can add cost or reduce success. | Preliminary single-model study, with methodological ambiguities. Supports checking compatibility, not a general performance promise. |
| [Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/), TACL 2024 | Tested long-context models can fail to use relevant information depending on its position. | Older models and retrieval/QA tasks, not skill or security-review trials. Motivates context-use regression tests, not a fixed token budget. |
| [Agent Skills Enable a New Class of Realistic and Trivially Simple Prompt Injections v1](https://arxiv.org/html/2510.26328v1), 2025-10-30 | Demonstrates harmful behavior through malicious skill descriptions, bodies and referenced scripts. | Proofs of concept, not a prevalence estimate or proof about every current host. Actual execution boundaries remain essential. |
| [Agent Skills in the Wild v1](https://arxiv.org/html/2601.10338v1), 2026-01-15 | Static/LLM screening flags potentially dangerous patterns and has measured errors. | Flagged does not mean malicious; small validation sample and marketplace scope limit generalization. Investigate evidence rather than assigning binary safety verdicts. |

## Validation and evolution

Test these independently:

- **Discovery:** supplied descriptions select full review, MCP review, testing or
  recordkeeping appropriately; unrelated build/install/help requests do not trigger
  a security audit just because they mention MCP.
- **Focused behavior:** on source-only fixtures, find concrete gaps, retain unknown
  external controls, respect transport/version applicability and resist instructions
  embedded in metadata. A clean scanner result or fixed version is not sufficient.
- **End-to-end quality:** compare the existing full review with the focused workflow
  on the same frozen fixtures, models, evidence and tool budgets. Measure recall,
  false gaps/assurances, source attribution, omissions, cost and latency over repeated
  runs with independent adjudication.

The initial discovery/forward checks are development smoke checks. They do not
qualify a model or show that the new structure beats the existing review. Historical
full-review qualification does not transfer to the MCP skill or revised entrypoints.
Retain evaluated skill versions; make further splits only when actual task traces
or comparative evaluations justify them.

The [2026-10-22 smoke evidence](../evals/results/2026-10-22-mcp-skill-smoke/run.json)
preserves two source-only fixtures, reviewer reports, the initial/revised ten-case
discovery exercise and its limitations. Discovery matched the intended choices in
those ten requests after narrowing descriptions. Forward-review observations led
to clarifications on grouped coverage, platform/version unknowns and speculative
bypasses. These checks used delegated agents, not native host invocation telemetry
or a controlled comparison against the full review; the forward reports precede
the documented wording refinements.
