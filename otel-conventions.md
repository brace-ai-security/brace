# OpenTelemetry attributes for agent identity and provenance

This document proposes four custom OpenTelemetry attributes for autonomous AI agents. The proposal is tracked in [open-telemetry/semantic-conventions-genai#334](https://github.com/open-telemetry/semantic-conventions-genai/issues/334) (open).

The OpenTelemetry GenAI conventions now live in their own repository, [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai). The current [agent spans page](https://github.com/open-telemetry/semantic-conventions-genai/blob/b9ecbaef4ac462cc2b6f7f7763b2cff1d15d5400/docs/gen-ai/gen-ai-agent-spans.md) (pinned revision b9ecbae, 2026-09-30) already defines agent identity and version attributes, model references, and agent and tool spans. Their status is **Development**. BRACE's type ID (a content hash) and instance ID (one per run) mean something different from a provider-assigned `gen_ai.agent.id`. Don't overwrite that standard field with a short-lived run ID.

The four `agent.*` attributes below are **custom attributes that BRACE proposes**. OpenTelemetry has not adopted them. They carry BRACE's observability requirements next to the standard attributes. No SDK or backend supplies all six identity fields, parent links, or a complete audit trail on its own. Check your instrumentation and retention end to end.

## The four attributes

| Attribute key | Type | Requirement level | Description | Example value |
| --- | --- | --- | --- | --- |
| `agent.type.id` | string | Required | Content hash over the agent's defining inputs: container digest, harness version, system prompt, model identifier/version (including applicable checkpoint and fine-tune/adapter references), and configuration. A fingerprint of the agent *type*. Deployments with different defining inputs have different `agent.type.id` values. | `sha256:9f1c...e3a` |
| `agent.instance.id` | string | Required | ID of a specific running agent instance. Each invocation gets one. Sub-agents are regular instances and get their own `agent.instance.id`. | `01HXYZ...K7` |
| `agent.context.size` | int | Recommended | Number of tokens in the model's context at the moment of the action or decision. This is the live context occupancy, not a per-call token count. | `42137` |
| `agent.parent.prompt` | string or reference | Conditionally required | The prompt the parent agent gave this sub-agent. Required when the agent was spawned by a parent. May be the full prompt body or a reference (for example a hash, with the body stored in a separate tier). | `sha256:a1b2...` or the prompt text |

Notes on the values:

- The `sha256:` and ULID-style forms shown above for `agent.type.id` and
  `agent.instance.id` are only a convention. The type ID must be a hash of content; a fixed label you pick does not count. Hash a documented manifest with a collision-resistant hash. Instance IDs need to be unique, not hashed.
  What matters is that `agent.type.id` changes when and only when one of its defining
  inputs changes, and that `agent.instance.id` is unique per running instance.
- `agent.context.size` is how full the context was when the agent decided. A long-running
  agent emits a different value on each action as its context fills. Record the tokenizer or counting method, when you measured, how cached input counts, and how compaction (shrinking the context) is handled. Mark estimates and their limits in the audit record. If the value isn't available, leave out the number and record it as unknown. Never emit zero instead. GenAI usage counts can help estimate it, but they may not show context the provider hides.
- `agent.parent.prompt` is sensitive. Prompts a parent passes often contain
  customer data, tool output, and business logic. For deployments shared by several tenants,
  use the reference form by default: a hash on the span, with the text kept in separate storage
  with stricter access. Put the full prompt on the span only when your audit storage and data-handling policy allow it.

### Scope of identity and checklist priorities

The type hash fingerprints the recorded setup. Check its inputs against what is actually running. It cannot identify weights or training history a provider doesn't share, or changes behind a hosted-model alias. Keep the model IDs you request, the versions actually served, and your own training and fine-tuning run and dataset references in the release manifest. Use the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields). Mark fields the provider hides as hidden. Don't put secrets or training data in span attributes.

The requirement levels in the table belong to this telemetry proposal. Production sign-off uses the [checklist](CHECKLIST.md) instead. There, identity fields are **Obs-T1** (A02, gate **G1**), context size is **Obs-T2** (R07, gate **G2**), and parent and prompt provenance is **Obs-T3** (A06, gate **G3**). G stands for gate. A G2 gap needs a written, approved risk acceptance. A G3 gap blocks high-stakes or high-autonomy deployments; for lower-stakes deployments it needs a written, approved risk acceptance. Parent provenance applies only when sub-agents exist. Gate numbers and Obs-T numbers are separate schemes.

## Mapping to BRACE observability requirements

BRACE names three observability requirements (Obs-T1, Obs-T2, Obs-T3) that its controls depend
on. The four attributes map to them as follows:

| Attribute | BRACE requirement | What it makes answerable |
| --- | --- | --- |
| `agent.type.id` | Obs-T1 — required identity fields | "Which agent *type* took this action?" Attribution down to the exact container, harness, prompt, model, and config. |
| `agent.instance.id` | Obs-T1 — required identity fields | "Which running instance took this action?" Per-invocation attribution, including for sub-agents. |
| `agent.context.size` | Obs-T2 — context size per action | "How full was the context when the agent decided?" You can see behavior that degrades near the limit, and split anomaly baselines by context size. |
| `agent.parent.prompt` | Obs-T3 — sub-agent and parent-prompt provenance | "Which parent spawned this sub-agent, and what did it tell the sub-agent to do?" Separates "the sub-agent type misbehaved" from "the parent told it to." |

`agent.type.id` and `agent.instance.id` are the two custom Obs-T1 fields in this proposal (see "The six BRACE identity fields" below). `agent.context.size`
covers all of Obs-T2. `agent.parent.prompt` covers the prompt half of Obs-T3.
The parent-child call graph itself uses W3C Trace Context, which OpenTelemetry
can pass along when instrumented correctly. Check async handoffs. Use span links where a parent-child tree doesn't show the relationship.

## The six BRACE identity fields

BRACE requires at least these six identity fields on every agent action. All six
must be present:

1. **Accountable party** — which legal entity is responsible.
2. **Operational owner** — which team owns deployment, configuration, and remediation.
3. **Tenant** — on whose behalf the agent is acting.
4. **Agent-type-id** — `agent.type.id` above.
5. **Agent-instance-id** — `agent.instance.id` above.
6. **Trace context** — the call graph that led to the action (W3C Trace Context).

Four of the six already map to existing identity and trace primitives:

- Accountable party, operational owner, and tenant map to existing identity
  primitives (OIDC claims, IdP tenant or org IDs, IAM tags, SPIFFE trust-domain and
  path parts). Record these values the same way on every action, using verified identity data from your deployment.
- Trace context maps directly to W3C Trace Context (`traceparent`, `tracestate`),
  which OpenTelemetry can pass along when instrumented correctly. Check async handoffs. Use span links where a parent-child tree doesn't show the relationship. Trace IDs only link records; they don't prove identity.

BRACE keeps agent-type-id and agent-instance-id separate. An identity provider
sees the *workload* that signed in, not the agent *type* (its content) or the
specific *instance*. Two deployments sharing one service-account credential look
identical in IdP logs even if one runs prompt v1.2 on one model and the other runs
prompt v1.3 on another. `agent.type.id` and `agent.instance.id` close that gap.
That is why these two are proposed as new OpenTelemetry attributes instead of
being mapped onto existing ones.

## Worked example: a span/log record with all four attributes plus the six identity fields

A sub-agent action, emitted as span attributes. All six BRACE identity fields are present.
Four use existing identity and trace fields (accountable party, operational owner,
tenant, trace context). Two are the BRACE-proposed attributes (`agent.type.id`,
`agent.instance.id`). The `agent.accountable_party`, `agent.operational_owner`,
`agent.tenant`, and `agent.parent.instance_id` keys are example names only; they are not part of the four-attribute proposal.

```json
{
  "span.name": "agent.action",
  "attributes": {
    "agent.accountable_party":   "acme-corp",
    "agent.operational_owner":   "platform-team",
    "agent.tenant":              "customer-co/user-1234",

    "agent.type.id":             "sha256:9f1c...e3a",
    "agent.instance.id":         "01HXYZ...K7",

    "agent.context.size":        42137,

    "agent.parent.instance_id":  "01HXYW...A2",
    "agent.parent.prompt":       "sha256:a1b2...",

    "gen_ai.usage.input_tokens":  3120,
    "gen_ai.usage.output_tokens": 280
  },
  "trace_context": {
    "trace_id":  "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id":   "00f067aa0ba902b7",
    "parent_id": "0020000000000001"
  }
}
```

Reading the record:

- The **six BRACE identity fields** are all present. Accountable party, operational
  owner, and tenant come from identity primitives. `agent.type.id` and
  `agent.instance.id` are the two BRACE-proposed agent attributes. Trace context is the
  `trace_context` block (W3C Trace Context).
- **Obs-T1** is met: every required identity field is on the action, including the
  two proposed ones.
- **Obs-T2** is met by `agent.context.size`: 42,137 tokens of context at decision
  time. The existing `gen_ai.usage.*` counts measure one model call. They are
  shown next to it to make the difference clear.
- **Obs-T3** is met by `agent.parent.instance_id` plus `agent.parent.prompt`:
  this action came from a sub-agent, spawned by instance `01HXYW...A2`, which passed
  the prompt referenced by hash `sha256:a1b2...`. The parent-child edge is also in
  the trace context (`parent_id`).

With this record, you can trace any action to its instance, type, operational
owner, and accountable party. The tenant and full call graph come with it, and you
can recover the parent prompt behind a sub-agent action.

## Backward compatibility

The four attributes are purely additive.

- They add four new attribute keys. They change no existing GenAI attribute or
  its meaning.
- Existing `gen_ai.*` attributes keep their current meaning. `agent.context.size`
  does not replace or overload the per-call token counts; it sits next to them.
- A consumer that doesn't know these attributes ignores them, like any other unknown
  attribute. Existing dashboards, exporters, and queries keep working.
- A producer can adopt the attributes in steps: emit `agent.type.id` and
  `agent.instance.id` first (Obs-T1), add `agent.context.size` next (Obs-T2), and add
  `agent.parent.prompt` when it starts sub-agents (Obs-T3). Partial adoption is valid
  telemetry, but checklist sign-off still needs every requirement its gates call for.
- The attributes use the existing OpenTelemetry attribute model and types (string,
  int). No new data model, transport, or wire change is required.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
