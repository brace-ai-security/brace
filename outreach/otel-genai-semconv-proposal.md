# Proposal: agent identity and provenance attributes for GenAI semantic conventions

> **Historical outreach draft — source review 2026-09-16:** Do not use its novelty, vendor-coverage, or incident-count claims as current evidence. See [SOURCE-REVIEW.md](../SOURCE-REVIEW.md), the [current checklist](../CHECKLIST.md), and [current telemetry proposal](../otel-conventions.md) before adapting this draft.

**To:** OpenTelemetry GenAI semantic-conventions working group / SIG
**From:** The BRACE Project
**Status:** Proposal — adopt as experimental attributes
**License:** CC BY 4.0

## Summary

This proposes four new attributes for the OpenTelemetry GenAI semantic conventions,
scoped to autonomous AI agents: `agent.type.id`, `agent.instance.id`,
`agent.context.size`, and `agent.parent.prompt`. They are additive and proposed at
experimental stability. They let agent telemetry answer three questions it cannot
answer today: which agent *type* took an action, how full the model's context was at
the moment of a decision, and which parent spawned a given sub-agent.

## Motivation

The GenAI conventions cover the model call well. They define prompt and completion
content and per-call token counts (`gen_ai.usage.input_tokens`,
`gen_ai.usage.output_tokens`). For a single LLM request that is enough.

It is not enough for an autonomous agent: a loop that runs a model, calls tools on
its behalf, accumulates context, and spawns sub-agents. Three concrete questions
come up in production and post-incident review, and current agent telemetry cannot
answer any of them.

1. **Which agent *type* took this action?** Two agent deployments can share one
   service-account credential and look identical in identity-provider logs, even if
   one runs system-prompt v1.2 on one model and the other runs v1.3 on another. The
   identity layer records *who authenticated*, not *what is running*. When an agent
   misbehaves, "which exact build — container, harness, prompt, model, config —
   produced this action?" is currently unanswerable from telemetry.

2. **How full was the context when the agent decided?** Agents degrade as context
   fills toward the limit. The existing token counts measure one call. They do not
   record the live context occupancy at decision time, so near-limit degraded
   behavior is invisible and anomaly baselines cannot be conditioned on it.

3. **Which parent spawned this sub-agent, and what did it tell it to do?** In
   multi-agent workflows, a parent spawns sub-agents and hands each a prompt. When a
   sub-agent does something harmful, review cannot separate "the sub-agent type
   misbehaved" from "the parent told it to" without the parent-passed prompt as
   first-class telemetry.

These are not exotic. They are the everyday attribution questions for any deployment
running more than one agent type, any long-running agent, and any multi-agent system.

## Proposed attributes

Full definitions, types, requirement levels, examples, a worked span/log record, and
the backward-compatibility analysis are in the companion reference
(`otel-conventions.md`). Summary:

| Attribute key | Type | Requirement level | Description |
| --- | --- | --- | --- |
| `agent.type.id` | string | Required | Content hash over container digest, harness version, system prompt, model id, and config. Fingerprint of the agent *type*. |
| `agent.instance.id` | string | Required | Id of a specific running agent instance. Sub-agents are regular instances. |
| `agent.context.size` | int | Recommended | Tokens in the model's context at the moment of the action or decision. |
| `agent.parent.prompt` | string or reference | Conditionally required (when spawned by a parent) | The prompt the parent agent gave this sub-agent. May be the full body or a reference (hash). |

## Rationale per attribute

**`agent.type.id` (string, required).** The defining property of an agent is its
content, not the identity it authenticates with. A content hash over container
digest, harness version, system prompt, model id, and config gives a stable
fingerprint of the agent *type*. It changes when, and only when, one of those inputs
changes — which makes silent config or prompt drift detectable from telemetry alone.
This cannot be derived from existing identity claims, because the identity provider
sees the workload, not its content. This is why it is a new attribute and not a
mapping onto an existing one.

**`agent.instance.id` (string, required).** Fifty instances under one service account
are indistinguishable in identity-provider logs. Per-instance attribution has to be
emitted at the agent layer. Treating sub-agents as regular instances — each with its
own `agent.type.id` and `agent.instance.id` — keeps the model uniform: there is no
special "sub-agent" entity, only instances with parent edges in the trace context.

**`agent.context.size` (int, recommended).** Context occupancy at decision time is a
distinct signal from per-call token usage. A long-running agent emits a rising value
across actions as its context fills. Recording it makes near-limit degradation
visible and lets anomaly detection condition on how full the context was. Recommended
rather than required because not every producer can cheaply measure live context
occupancy, but it is low-cost where the harness already tracks it.

**`agent.parent.prompt` (string or reference, conditionally required).** Required when
the agent was spawned by a parent, because without the parent-passed prompt, review
cannot attribute a sub-agent's action between the sub-agent type and the parent's
instruction. It allows a reference form (hash on the span, body in a separate tier)
because parent-passed prompts routinely carry customer data, tool output, and
business logic, and emitting them inline can turn the trace store into a
high-sensitivity store. The reference form keeps the provenance link while letting
deployments manage the sensitive body separately.

## Stability and backward compatibility

The attributes are additive and proposed at **experimental** stability.

- They add four new keys. They change no existing GenAI attribute and no existing
  semantic.
- `agent.context.size` sits alongside the existing `gen_ai.usage.*` token counts; it
  does not replace or overload them.
- Consumers that do not recognize the attributes ignore them, as with any unknown
  attribute. Existing dashboards, exporters, and queries are unaffected.
- Producers can adopt incrementally: `agent.type.id` and `agent.instance.id` first,
  then `agent.context.size`, then `agent.parent.prompt` when sub-agents are spawned.
- The attributes use the existing attribute model and types (string, int). No data
  model, transport, or wire change is needed.

Starting at experimental stability lets the names and requirement levels settle with
SIG and implementer feedback before any stability commitment.

## Prior art

- **BRACE** — *A Unified Security Framework for Autonomous AI Agents* (CC BY
  4.0). BRACE names three observability requirements that its controls depend
  on: T1 required identity fields, T2 context size per action, and T3 sub-agent and
  parent-prompt provenance. These four attributes are the OpenTelemetry expression of
  the parts of T1/T2/T3 that are net-new at the agent layer. BRACE's analysis notes
  that the GenAI conventions today define per-call token counts but no
  agent-deployment-granularity attributes — specifically no required identity fields,
  no context size at decision time, and no parent-passed prompt as a span attribute.
- **Existing GenAI token-count attributes** — `gen_ai.usage.input_tokens` and
  `gen_ai.usage.output_tokens`. These establish the convention of recording token
  quantities on GenAI telemetry. `agent.context.size` follows that convention for a
  different quantity: live context occupancy at decision time rather than per-call
  usage.
- **W3C Trace Context** — already propagated by OpenTelemetry. It carries the
  parent-child call graph, including the parent edge for sub-agents.
  `agent.parent.prompt` adds the *content* the parent passed; the *edge* is already
  available in trace context, so this proposal does not duplicate it.

## Ask

Adopt these four attributes as **experimental** attributes in the GenAI agent
conventions:

- `agent.type.id` (string, required)
- `agent.instance.id` (string, required)
- `agent.context.size` (int, recommended)
- `agent.parent.prompt` (string or reference, conditionally required when spawned by
  a parent)

We are glad to bring this as a registry/attributes PR against the semantic-conventions
repository, iterate on naming and requirement levels with the SIG, and supply the
worked examples and backward-compatibility analysis from the companion reference.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
