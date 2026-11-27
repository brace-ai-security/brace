# Request: clarify agent version and run identity guidance in GenAI semantic conventions

> **Historical outreach draft — source review 2026-09-16, revised 2026-11-24:** Do not use its novelty, vendor-coverage, or incident-count claims as current evidence. See [SOURCE-REVIEW.md](../../SOURCE-REVIEW.md), the [current checklist](../../CHECKLIST.md), and the [current attribute guide](../../otel-conventions.md) before adapting this draft.

> **Note, 2026-11-26:** GenAI conventions v0.1.0 (2026-11-21) removed `gen_ai.agent.version` and `gen_ai.agent.id` from the internal `invoke_agent` span. BRACE now records the type hash for in-process agents in the `service.version` resource attribute, and keeps `gen_ai.agent.version` only on the client `invoke_agent` span. Point 1 below applies to that client span. If adapted, also ask whether `service.version` is the intended place for an in-process agent's version. See the [current attribute guide](../../otel-conventions.md#where-the-type-hash-goes).

**To:** OpenTelemetry GenAI semantic-conventions working group / SIG
**From:** The BRACE Project
**Status:** Guidance clarification request (no new attributes requested)
**License:** CC BY 4.0

## Summary

BRACE now uses only standard OTel attributes. It defines no custom attributes. We are not asking for new attributes. We ask the SIG to clarify two points in the guidance, so that BRACE's use matches the conventions' intent:

1. **`gen_ai.agent.version` may carry a content hash.** BRACE sets it to a hash (for example `sha256:9f1c...`) over the container digest, harness version, system prompt, model ID and version, and configuration. The hash changes when, and only when, one of those inputs changes. The human release label goes in `service.version`. Please confirm this is a valid use, or say what you would prefer.
2. **How to identify a single agent run.** BRACE uses `service.instance.id` when one run is one process. Otherwise it treats the run's own `invoke_agent` span as the run, identified by its trace ID and span ID, with span links for async work. It never uses `gen_ai.agent.id` or `gen_ai.conversation.id` for this. Please confirm, or name the pattern you recommend.

## What BRACE maps to standard attributes

Checked on 2026-11-24 against [open-telemetry/semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai). The `gen_ai.*` attributes have status Development.

- **Agent type**: content hash in `gen_ai.agent.version`; release label in `service.version`. Inputs shown with `gen_ai.agent.name`, `gen_ai.request.model`, `gen_ai.response.model`, `oci.manifest.digest` and `gen_ai.system_instructions_ref`.
- **Agent run**: `service.instance.id`, or the run's `invoke_agent` span.
- **Context size at decision time**: `gen_ai.usage.input_tokens` on the model-call span that produced the decision, with the cache counts and `gen_ai.conversation.compacted`.
- **Parent-to-child provenance**: the agent-as-tool `execute_tool` span with `gen_ai.transfer.target.name` and `gen_ai.transfer.mode`. The child's own `invoke_agent` span carries `gen_ai.input.messages` or `gen_ai.input.messages_ref`. The parent link comes from trace context. Opt-in `gen_ai.tool.call.arguments` stays an option.
- **End user**: `user.id`.

## What BRACE keeps out of OTel

Tenant, accountable party and operational owner have no OTel attribute. BRACE does not invent one. It records them in the audit record, from verified identity claims (OIDC or IdP tenant and org IDs, IAM tags, SPIFFE IDs), and joins the record to spans by trace ID. We mention this only so the SIG knows the gap exists. ECS `organization.*` is the closest well-known field outside OTel.

## Ask

- Clarify in the `gen_ai.agent.version` description whether a content hash is an acceptable value.
- Add guidance on how to identify one agent run, including sub-agent runs and async work.

We are glad to supply worked examples from the companion guide.

---

Part of BRACE, a security framework for autonomous AI agents. CC BY 4.0.
