# OpenTelemetry attributes for agent identity and provenance

This doc defines four proposed OpenTelemetry attributes for autonomous AI agents.

The OpenTelemetry GenAI semantic conventions already cover per-call telemetry for
model invocations: prompt and completion content, and token counts per call
(`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`). They do not cover
agent identity or provenance. Telemetry today can tell you a model call happened
and how many tokens it cost. It cannot tell you which agent *type* took the action,
how full the context was at the moment of the decision, or which parent spawned a
given sub-agent.

The four attributes below fill that gap. They are additive. They extend the GenAI
conventions; they do not change any existing attribute. Each maps to a BRACE
observability requirement (T1, T2, or T3).

## The four attributes

| Attribute key | Type | Requirement level | Description | Example value |
| --- | --- | --- | --- | --- |
| `agent.type.id` | string | Required | Content hash over the agent's defining inputs: container digest, harness version, system prompt, model identifier/version (including applicable checkpoint and fine-tune/adapter references), and configuration. A fingerprint of the agent *type*. Two deployments with any of those inputs different have different `agent.type.id` values. | `sha256:9f1c...e3a` |
| `agent.instance.id` | string | Required | Id of a specific running agent instance. Each invocation gets one. Sub-agents are regular instances and get their own `agent.instance.id`. | `01HXYZ...K7` |
| `agent.context.size` | int | Recommended | Number of tokens in the model's context at the moment of the action or decision. This is the live context occupancy, not a per-call token count. | `42137` |
| `agent.parent.prompt` | string or reference | Conditionally required | The prompt the parent agent gave this sub-agent. Required when the agent was spawned by a parent. May be the full prompt body or a reference (for example a hash, with the body stored in a separate tier). | `sha256:a1b2...` or the prompt text |

Notes on the values:

- `agent.type.id` and `agent.instance.id` carry the `sha256:` and ULID-style forms
  shown above only by convention. Any stable, collision-resistant string is valid.
  What matters is that `agent.type.id` changes when and only when one of its defining
  inputs changes, and that `agent.instance.id` is unique per running instance.
- `agent.context.size` is the context occupancy at decision time. A long-running
  agent emits a different value on each action as its context fills. This is distinct
  from the existing GenAI per-call token counts, which measure one model call.
- `agent.parent.prompt` is sensitive. Parent-passed prompts routinely contain
  customer data, tool outputs, and business logic. The reference form
  (a hash on the span, body in a separate, stricter-access tier) is the recommended
  default for shared-tenant deployments. The full-body form is for deployments that
  retain their audit data locally and have a policy reason to capture it inline.

### Scope of identity and checklist priorities

The type hash fingerprints the recorded configuration; verify its inputs against running artifacts. It cannot identify undisclosed weights, training lineage, or changes behind a hosted-model alias. Keep requested model IDs, observed served versions, and owned training/fine-tuning run and dataset references in the release manifest using the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields). Record provider-hidden fields explicitly; do not put secrets or training datasets into span attributes.

The attribute requirement levels above describe this telemetry proposal. Production sign-off uses the [checklist](CHECKLIST.md): identity is **Obs-T1 / G1**, context size is **Obs-T2 / G2**, and parent/prompt provenance is **Obs-T3 / G3**. G3 is blocking for high-stakes or high-autonomy deployments; permitted lower-stakes deferrals require documented acceptance. Parent provenance is applicable when sub-agents exist. These gate labels are distinct from the observability requirement numbers.

## Mapping to BRACE observability requirements

BRACE names three observability requirements (T1, T2, T3) that its controls depend
on. The four attributes map as follows:

| Attribute | BRACE requirement | What it makes answerable |
| --- | --- | --- |
| `agent.type.id` | T1 — required identity fields | "Which agent *type* took this action?" Attribution down to the exact container, harness, prompt, model, and config. |
| `agent.instance.id` | T1 — required identity fields | "Which running instance took this action?" Per-invocation attribution, including for sub-agents. |
| `agent.context.size` | T2 — context size per action | "How full was the context when the agent decided?" Near-limit degraded behavior becomes visible; anomaly baselines can be conditioned on context occupancy. |
| `agent.parent.prompt` | T3 — sub-agent and parent-prompt provenance | "Which parent spawned this sub-agent, and what did it tell the sub-agent to do?" Separates "the sub-agent type misbehaved" from "the parent told it to." |

`agent.type.id` and `agent.instance.id` are the two T1 fields that are net-new at
the agent layer (see "The six BRACE identity fields" below). `agent.context.size`
covers T2 in full. `agent.parent.prompt` covers the prompt-provenance half of T3;
the parent-child call graph itself rides on W3C Trace Context, which OpenTelemetry
already propagates.

## The six BRACE identity fields

BRACE requires a minimum set of six identity fields on every agent action, enforced
as a complete set:

1. **Accountable party** — which legal entity is responsible.
2. **Operational owner** — which team owns deployment, configuration, and remediation.
3. **Tenant** — on whose behalf the agent is acting.
4. **Agent-type-id** — `agent.type.id` above.
5. **Agent-instance-id** — `agent.instance.id` above.
6. **Trace context** — the call graph that led to the action (W3C Trace Context).

Four of the six already map to existing identity and trace primitives:

- Accountable party, operational owner, and tenant map to existing identity
  primitives (OIDC claims, IdP tenant/org ids, IAM tags, SPIFFE trust-domain and
  path components). They are emission discipline on fields most identity providers
  already carry.
- Trace context maps directly to W3C Trace Context (`traceparent`, `tracestate`),
  which OpenTelemetry already propagates.

The two net-new fields are agent-type-id and agent-instance-id. An identity provider
sees the *workload* that authenticated, not the agent *type* (its content) or the
specific *instance*. Two deployments sharing one service-account credential look
identical in IdP logs even if one runs prompt v1.2 on one model and the other runs
prompt v1.3 on another. `agent.type.id` and `agent.instance.id` are the attributes
that close that gap, and they are why these two are proposed as new OpenTelemetry
attributes rather than mapped onto existing ones.

## Worked example: a span/log record with all four attributes plus the six identity fields

A sub-agent action, emitted as span attributes. The four proposed attributes are
marked. The six BRACE identity fields are present: four ride existing primitives
(accountable party, operational owner, tenant, trace context), and two are the
net-new agent attributes (`agent.type.id`, `agent.instance.id`).

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
  `agent.instance.id` are the two net-new agent attributes. Trace context is the
  `trace_context` block (W3C Trace Context).
- **T1** is satisfied: every required identity field is on the action, including the
  two net-new ones.
- **T2** is satisfied by `agent.context.size`: 42,137 tokens of context at decision
  time. The existing `gen_ai.usage.*` counts measure the single model call; they are
  shown alongside to make the distinction concrete.
- **T3** is satisfied by `agent.parent.instance_id` plus `agent.parent.prompt`:
  this action came from a sub-agent, spawned by instance `01HXYW...A2`, which passed
  the prompt referenced by hash `sha256:a1b2...`. The parent-child edge is also in
  the trace context (`parent_id`).

With this record, any action traces from action to instance to type to operational
owner to accountable party, with tenant and the full call graph alongside, and with
the parent prompt that produced a sub-agent action recoverable.

## Backward compatibility

The four attributes are purely additive.

- They add four new attribute keys. They change no existing GenAI attribute and no
  existing semantic.
- Existing `gen_ai.*` attributes keep their current meaning. `agent.context.size`
  does not replace or overload the per-call token counts; it sits next to them.
- A consumer that does not know these attributes ignores them, exactly as it ignores
  any other unknown attribute. Existing dashboards, exporters, and queries keep
  working unchanged.
- A producer can adopt the attributes incrementally: emit `agent.type.id` and
  `agent.instance.id` first (T1), add `agent.context.size` next (T2), add
  `agent.parent.prompt` when it spawns sub-agents (T3). Partial adoption is valid.
- The attributes use the existing OpenTelemetry attribute model and types (string,
  int). No new data model, transport, or wire change is required.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
