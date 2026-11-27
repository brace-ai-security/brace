# OpenTelemetry attributes for agent identity and provenance

This document says which OpenTelemetry (OTel) attributes to use for BRACE's observability requirements. BRACE reuses existing OTel attributes wherever they fit. It defines no custom attributes. Identity facts that OTel has no attribute for live in the audit record.

Checked on 2026-11-24 against the OTel GenAI semantic conventions in [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai), and rechecked on 2026-11-26 against its first standalone release, v0.1.0, published 2026-11-21 (date from the GitHub release record).

**Release v0.1.0 changes (checked 2026-11-26).** The release notes list breaking changes. Two matter here. First, `gen_ai.agent.id` and `gen_ai.agent.version` were removed from the internal (in-process) agent span, `gen_ai.invoke_agent.internal`. The client span, `gen_ai.client.invoke_agent`, for an agent invoked out of process, still lists both as conditionally required, and both are still Development. BRACE therefore moved the type hash for in-process agents to `service.version` (see [Where the type hash goes](#where-the-type-hash-goes)). Second, the cache attributes were removed from the internal agent span. They are still defined on model-call spans, which is where this document puts them. Also still defined: `gen_ai.conversation.id`, `gen_ai.conversation.compacted`, `gen_ai.usage.input_tokens`, `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`, `gen_ai.transfer.target.name` and `gen_ai.transfer.mode` (agent-as-tool span), `gen_ai.input.messages_ref` and `gen_ai.system_instructions_ref`. `service.version` was checked in the main semantic-conventions registry on 2026-11-26: Stable, and "the format is not defined by these conventions" (its examples include a commit hash). Not rechecked: `user.id`, `oci.manifest.digest`, other `service.*` attributes, which live outside the GenAI repository. The BRACE requirements are unchanged; only the attribute that carries the type hash for in-process agents changed.

**Stability.** Every `gen_ai.*` attribute named here has status **Development**. Names and meanings can still change. Recheck the conventions before you depend on them, and pin the semantic-conventions version your instrumentation emits.

No SDK or backend supplies all six identity fields, parent links, or a complete audit trail on its own. Check your instrumentation and retention end to end.

## Attribute table

| BRACE need | Where to record it | Standard or audit record |
| --- | --- | --- |
| Obs-T1: agent type (content hash), in-process agent | `service.version` resource attribute, set to the content hash (for example `sha256:9f1c...`) | Standard |
| Obs-T1: agent type (content hash), agent called out of process | `gen_ai.agent.version` on the `gen_ai.client.invoke_agent` span, set to the content hash | Standard (Development) |
| Human release label | Release manifest, keyed by the type hash | Audit record |
| Obs-T1: inputs to the type hash | `gen_ai.agent.name`, `gen_ai.request.model`, `gen_ai.response.model`, `oci.manifest.digest`, `gen_ai.system_instructions_ref` | Standard (Development) |
| Obs-T1: agent instance (one per run) | `service.instance.id` when one run is one process; otherwise the run's own `invoke_agent` span (its trace ID and span ID) | Standard |
| Obs-T1: provider-hosted agent resource, if any | `gen_ai.agent.id` | Standard (Development) |
| Obs-T1: tenant | Audit record, from verified identity claims | Audit record |
| Obs-T1: accountable party | Audit record, from verified identity claims | Audit record |
| Obs-T1: operational owner | Audit record, from verified identity claims | Audit record |
| End user the agent acts for | `user.id` (never the deprecated `enduser.*`) | Standard (Development) |
| Obs-T1: trace context | W3C Trace Context (`traceparent`, `tracestate`), span parentage, span links | Standard |
| Conversation or session, if any | `gen_ai.conversation.id` | Standard (Development) |
| Obs-T2: context size at the decision | `gen_ai.usage.input_tokens` on the model-call span that produced the decision | Standard (Development) |
| Obs-T2: cached part of that context | `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens` | Standard (Development) |
| Obs-T2: context was compacted | `gen_ai.conversation.compacted` | Standard (Development) |
| Obs-T2: tokenizer or counting method | Audit record | Audit record |
| Obs-T3: parent-to-child handoff | `execute_tool` span (agent-as-tool) with `gen_ai.transfer.target.name` and `gen_ai.transfer.mode` | Standard (Development) |
| Obs-T3: parent-to-child link | W3C Trace Context span parentage, or span links for async handoffs | Standard |
| Obs-T3: prompt the parent gave the child | `gen_ai.input.messages` or `gen_ai.input.messages_ref` on the child's `invoke_agent` span; or `gen_ai.tool.call.arguments` (opt-in) on the agent-as-tool span | Standard (Development) |

BRACE defines no custom attributes. Every span attribute above is a standard OTel attribute. What OTel does not cover goes in the audit record.

## How BRACE uses the standard attributes

- **Agent type.** Compute a content hash over the agent's defining inputs: container digest, harness version, system prompt, model ID and version (including checkpoint and fine-tune or adapter references), and configuration. The hash must change when, and only when, one of those inputs changes. A label you pick by hand does not count. Record it as described in [Where the type hash goes](#where-the-type-hash-goes). Keep the human release label, such as `1.3`, in the release manifest stored under the hash. Emit the standard inputs next to the hash, so readers can see what went into it. Don't use `gen_ai.agent.id` for the hash. OTel defines it as a stable ID for a hosted agent resource, usually assigned by the provider (for example a Bedrock agent ARN).
- **Agent instance.** Each run needs its own identity. Sub-agents are regular runs and get their own. If one run is one process, use `service.instance.id`. Otherwise, the run is its own `invoke_agent` span. Its trace ID and span ID identify the run. For async work, link back to that span with span links. Never put a run ID in `gen_ai.agent.id` (OTel says not to record in-memory instance IDs there) or in `gen_ai.conversation.id` (a conversation can span many runs, and OTel forbids filling it with a new UUID).
- **Tenant, accountable party and operational owner.** OTel has no attribute for these. Don't invent one. Record them in the audit record, taken from verified identity claims: OIDC claims, IdP tenant or org IDs, IAM tags, or SPIFFE IDs. Record them the same way on every action. Join audit records to spans by trace ID. The closest well-known field outside OTel is ECS `organization.*`. Record the end user, if any, in `user.id`.

### Where the type hash goes

- **In-process agent.** Set the `service.version` resource attribute to the type hash. Every span the agent emits then carries it, including model-call spans. If one process hosts several agent types, give each type its own tracer provider with its own resource, so each type has its own `service.version`. Set `gen_ai.agent.name` on the `invoke_agent` span as usual.
- **Agent called out of process.** Set `gen_ai.agent.version` to the callee's type hash on the `gen_ai.client.invoke_agent` span, where v0.1.0 still lists it (Conditionally Required, Development). The callee's own spans carry the hash in their `service.version`.

Why: v0.1.0 removed `gen_ai.agent.version` and `gen_ai.agent.id` from `gen_ai.invoke_agent.internal` (release notes, PRs #242 and #322). Recording a listed attribute where the conventions no longer list it would drift from them. The new `gen_ai.main_agent` entity does not fit: it has no version attribute, and `gen_ai.main_agent.id` must be a stable, provider-assigned ID, never one generated in process. `service.version` is a stable OTel resource attribute for the version of the running component, and a content hash is a valid version string. This keeps the rule that BRACE defines no custom attributes. Sources: [v0.1.0 release notes](https://github.com/open-telemetry/semantic-conventions-genai/releases/tag/v0.1.0); [gen-ai-agent-spans.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md), [client-invoke-agent.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-invoke-agent.md) and [model/gen-ai/entities.yaml](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/model/gen-ai/entities.yaml), read 2026-11-26.

Notes on the values:

- The `sha256:` form is only a convention. Hash a documented manifest with a collision-resistant hash.
- **Context size.** Use `gen_ai.usage.input_tokens` from the model call that produced the decision. It counts all input tokens across modalities, so it is how full the context was for that call. The cache counts are subsets of it. A long-running agent emits a different value on each call as its context fills. Document the tokenizer or counting method, and how compaction is handled, in the audit record. Mark estimates and their limits there too. If the value isn't available, leave it out and record it as unknown. Never emit zero instead. The provider may hide some context, so the count can be low.
- **Parent prompt.** The child's own `invoke_agent` span carries the prompt in `gen_ai.input.messages` or `gen_ai.input.messages_ref`. The parent link comes from trace context. Content attributes are opt-in and sensitive. Prompts a parent passes often hold customer data, tool output and business logic. For deployments shared by several tenants, use `gen_ai.input.messages_ref` by default, pointing to separate storage with stricter access. Put the full prompt on a span only when your audit storage and data-handling policy allow it.

### Scope of identity and checklist priorities

The type hash fingerprints the recorded setup. Check its inputs against what is actually running. It cannot identify weights or training history a provider doesn't share, or changes behind a hosted-model alias. Keep the model IDs you request, the versions actually served, and your own training and fine-tuning run and dataset references in the release manifest. Use the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields). Mark fields the provider hides as hidden. Don't put secrets or training data in span attributes.

Production sign-off uses the [checklist](CHECKLIST.md). There, identity fields are **Obs-T1** (A02, gate **Blocker**), context size is **Obs-T2** (R07, gate **Required**), and parent and prompt provenance is **Obs-T3** (A06, gate **Detection**). A Required gap needs a written, approved risk acceptance. For high-stakes or high-autonomy deployments, a Detection gap remains an open finding without a BRACE GO/NO-GO release verdict. Accountable people own any gradual, closely monitored rollout, stop conditions and recovery. For lower-risk deployments, a Detection gap needs a written, approved risk acceptance. Parent provenance applies only when sub-agents exist. Gate numbers and Obs-T numbers are separate schemes.

## The six BRACE identity fields

BRACE requires these six identity fields on every agent action:

1. **Accountable party**: which legal entity is responsible. Record it in the audit record from a verified identity claim.
2. **Operational owner**: which team owns deployment, configuration and remediation. Record it in the audit record from a verified identity claim.
3. **Tenant**: on whose behalf the agent is acting. Record it in the audit record from a verified identity claim. Record the end user, if any, in `user.id`.
4. **Agent-type-id**: the content hash in `service.version` (in-process), or in `gen_ai.agent.version` on the client `invoke_agent` span (out of process).
5. **Agent-instance-id**: `service.instance.id` when one run is one process; otherwise the run's `invoke_agent` span.
6. **Trace context**: the call graph that led to the action, as W3C Trace Context. Check async handoffs. Use span links where a parent-child tree doesn't show the relationship. Trace IDs only link records; they don't prove identity.

BRACE keeps the type ID and instance ID separate from login identity. An identity provider sees the *workload* that signed in, not the agent *type* (its content) or the specific *instance*. Two deployments sharing one service-account credential look the same in IdP logs, even if one runs prompt v1.2 on one model and the other runs prompt v1.3 on another. The type hash and run identity close that gap.

## Worked example

The parent's agent-as-tool call, the child's run, and the child's model call, as span attributes. The audit record for the same action holds the accountable party, operational owner and tenant, joined by trace ID.

Parent's `execute_tool` span (agent-as-tool):

```json
{
  "span.name": "execute_tool research_agent",
  "attributes": {
    "gen_ai.operation.name":       "execute_tool",
    "gen_ai.transfer.target.name": "research_agent",
    "gen_ai.transfer.mode":        "return_to_caller"
  },
  "trace_context": { "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "0020000000000001" }
}
```

Child's `invoke_agent` span, a child of the span above. Its trace ID and span ID identify this run:

```json
{
  "span.name": "invoke_agent research_agent",
  "attributes": {
    "gen_ai.operation.name":          "invoke_agent",
    "gen_ai.agent.name":              "research_agent",
    "gen_ai.input.messages_ref":      "s3://audit-restricted/prompts/a1b2..."
  },
  "resource": {
    "service.version":                "sha256:9f1c...e3a",
    "oci.manifest.digest":            "sha256:77ab..."
  },
  "trace_context": {
    "trace_id":  "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id":   "0030000000000002",
    "parent_id": "0020000000000001"
  }
}
```

Child's model-call span, a child of the `invoke_agent` span. It shares the resource above, so it carries the same `service.version`:

```json
{
  "span.name": "chat claude-opus",
  "attributes": {
    "user.id":                               "user-1234",
    "gen_ai.agent.name":                     "research_agent",
    "gen_ai.request.model":                  "claude-opus",
    "gen_ai.usage.input_tokens":             42137,
    "gen_ai.usage.cache_read.input_tokens":  30000,
    "gen_ai.usage.output_tokens":            280,
    "gen_ai.conversation.compacted":         false
  },
  "trace_context": {
    "trace_id":  "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id":   "00f067aa0ba902b7",
    "parent_id": "0030000000000002"
  }
}
```

Audit record for the same action:

```json
{
  "trace_id":           "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id":            "00f067aa0ba902b7",
  "accountable_party":  "acme-corp",
  "operational_owner":  "platform-team",
  "tenant":             "customer-co",
  "identity_source":    "oidc:org_id claim",
  "token_count_method": "provider-reported usage"
}
```

Reading the records:

- **Obs-T1** is met: the type hash is in the `service.version` resource attribute, the run is the child's `invoke_agent` span, and trace context links it all. The audit record joined by trace ID holds the accountable party, operational owner and tenant.
- **Obs-T2** is met: the call that produced the decision had 42,137 input tokens, of which 30,000 came from cache. The context was not compacted.
- **Obs-T3** is met: the child's span descends from the parent's agent-as-tool span. That span names the target and mode. The child's `invoke_agent` span references the prompt in `gen_ai.input.messages_ref`.

## Compatibility

- BRACE does not recognize the old names: `agent.type.id`, `agent.instance.id`, `agent.context.size`, `agent.parent.prompt`, or any attribute under the former BRACE custom prefix. BRACE review treats them as not meeting the requirements. Move to the attributes and audit-record fields above.
- Existing OTel attributes keep their OTel meaning. Don't put a run ID in `gen_ai.agent.id` or `gen_ai.conversation.id`.
- A producer can adopt in steps: Obs-T1 first, then Obs-T2, then Obs-T3 when it starts sub-agents. Partial adoption is valid telemetry, but checklist sign-off still needs every requirement its gates call for.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
