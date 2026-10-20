import Anthropic from "@anthropic-ai/sdk";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { AGENT_MODEL, budgets, ROOT } from "../config.js";
import { audit, AuditUnavailable } from "../audit/recorder.js";
import { Halted, killSwitch } from "../control/kill-switch.js";
import { executeTool } from "../tools/executor.js";
import type { ToolRegistry } from "../tools/registry.js";
import { BudgetExceeded, DynamoQuotaStore, RunBudget } from "./budget.js";
import { classifyIntent } from "./classifier.js";
import { completeFromUsage, measureBeforeCall, spanAttributes } from "./context-size.js";
import type { RunContext } from "./identity.js";

const SYSTEM_TEMPLATE = readFileSync(join(ROOT, "prompts/system.md"), "utf8");
const anthropic = new Anthropic({ maxRetries: 1 });
const quotaStore = new DynamoQuotaStore();

export interface AgentReply {
  text: string;
  handoff: null | { reason: string };
}

function escapeTags(s: string): string {
  return s.replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export async function runAgent(
  registry: ToolRegistry,
  ctx: RunContext,
  clinic: { name: string },
  patientText: string,
): Promise<AgentReply> {
  const ident = () => ({ ...ctx.identity(), runId: ctx.runId, subject: ctx.subject });
  const budget = new RunBudget(budgets, quotaStore, { tenantId: ctx.tenantId, subjectId: ctx.subject.id });
  const unregister = killSwitch.register(ctx.runId, ctx.tenantId, budget.abort);
  await audit.record({ ...ident(), event: "run.started", detail: { channel: ctx.channel } });

  try {
    await killSwitch.assertRunning(ctx.tenantId);

    const intent = await classifyIntent(anthropic, patientText);
    await audit.record({ ...ident(), event: "intent.classified", detail: { ...intent } });
    if (intent.failure) ctx.log.warn({ classifier: intent.requestedModel, failure: intent.failure }, "intent classifier control failure");
    if (intent.route === "staff") {
      await audit.record({ ...ident(), event: "run.stopped", reason: `routed_to_staff:${intent.failure ?? intent.intent}` });
      return { text: "Thanks. A member of our front desk team will get back to you shortly.", handoff: { reason: intent.failure ?? String(intent.intent) } };
    }

    const system = SYSTEM_TEMPLATE.replace("{{clinicName}}", clinic.name);
    const tools = registry.definitions();
    const messages: Anthropic.MessageParam[] = [
      { role: "user", content: `<patient_message>${escapeTags(patientText)}</patient_message>` },
    ];

    for (;;) {
      budget.turn();
      await killSwitch.assertRunning(ctx.tenantId);

      const req = { model: AGENT_MODEL, system, tools, messages };
      const pre = await measureBeforeCall(anthropic, req, budget.signal);
      const res = await anthropic.messages.create({ ...req, max_tokens: 1024 }, { signal: budget.signal });
      const contextSize = completeFromUsage(pre, res.usage);
      await budget.recordUsage(res.usage, AGENT_MODEL);

      const toolUses = res.content.filter((b): b is Anthropic.ToolUseBlock => b.type === "tool_use");
      await audit.record({
        ...ident(),
        event: "model.decision",
        context: contextSize,
        detail: {
          servedModel: res.model,
          stopReason: res.stop_reason,
          proposed: toolUses.map((t) => ({ id: t.id, name: t.name })),
          span: spanAttributes(contextSize),
        },
      });

      if (res.stop_reason !== "tool_use" || toolUses.length === 0) {
        const text = res.content
          .filter((b): b is Anthropic.TextBlock => b.type === "text")
          .map((b) => b.text)
          .join("\n")
          .slice(0, 320);
        await audit.record({ ...ident(), event: "run.completed" });
        return { text, handoff: null };
      }

      messages.push({ role: "assistant", content: res.content });
      const results: Anthropic.ToolResultBlockParam[] = [];
      for (const call of toolUses) {
        results.push(await executeTool(registry, ctx, call, { contextSize, budget }));
      }
      messages.push({ role: "user", content: results });
    }
  } catch (err) {
    const reason =
      err instanceof BudgetExceeded
        ? `budget:${err.limit}`
        : err instanceof Halted
          ? `halted:${err.scope}`
          : err instanceof AuditUnavailable
            ? "audit_unavailable"
            : budget.signal.aborted
              ? `aborted:${String((budget.signal.reason as Error)?.message ?? "")}`
              : `error:${(err as Error).message.slice(0, 200)}`;
    try {
      await audit.record({ ...ident(), event: "run.stopped", reason });
    } catch {
      ctx.log.error({ runId: ctx.runId, reason }, "run stopped and audit delivery failed");
    }
    return { text: "Sorry, we couldn't finish that here. Our front desk will follow up.", handoff: { reason } };
  } finally {
    budget.dispose();
    unregister();
  }
}
