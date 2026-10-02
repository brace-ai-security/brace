import type Anthropic from "@anthropic-ai/sdk";
import { BudgetExceeded, RunBudget, acquireRunSlot, reserveSpend } from "./budget.js";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { BatchGetCommand, DynamoDBDocumentClient } from "@aws-sdk/lib-dynamodb";
import { audit, measureContext, type ContextMeasure } from "./telemetry.js";
import { PRIMARY, anthropic, assertServed } from "./models.js";
import { buildSystem, renderForClient, toolResultBlock, type PageSnapshot } from "./messages.js";
import { dispatch, toolsForModel, POLICY_VERSION } from "./tools/registry.js";
import { closeBrowserFor, pageFor, visibleText } from "./tools/browser.js";
import { readEntries } from "./memory.js";
import { notifyUser } from "./server.js";
import type { RunContext } from "./identity.js";

const MAX_HISTORY_TURNS = 24;
const USD_PER_MTOK_IN = 3;
const USD_PER_MTOK_OUT = 15;
const PAGE_TOOLS = new Set(["builtin:browser_navigate", "builtin:browser_click", "builtin:browser_read"]);

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const CONTROL_TABLE = process.env.CONTROL_TABLE ?? "shopper-control";

async function isHalted(ctx: RunContext): Promise<boolean> {
  try {
    const out = await ddb.send(new BatchGetCommand({
      RequestItems: { [CONTROL_TABLE]: { Keys: [{ pk: "killswitch#global" }, { pk: `killswitch#${ctx.tenantId}` }] } },
    }));
    return (out.Responses?.[CONTROL_TABLE] ?? []).some((r) => r.state === "on");
  } catch {
    return false;
  }
}

const runState = new Map<string, { budget: RunBudget; step: number; lastContext: ContextMeasure }>();
export const budgetFor = (runId: string) => runState.get(runId)!.budget;
export const currentStep = (runId: string) => runState.get(runId)?.step ?? 0;
export const lastContext = (runId: string): ContextMeasure =>
  runState.get(runId)?.lastContext ?? { method: "unavailable", reason: "no model decision yet" };

export async function runAgent(ctx: RunContext, userGoal: string): Promise<void> {
  let releaseSlot: () => Promise<void>;
  try {
    releaseSlot = await acquireRunSlot(ctx);
  } catch (e) {
    audit(ctx, { kind: "budget_stop", step: 0, outcome: (e as Error).message }, lastContext(ctx.runId));
    await notifyUser(ctx, { type: "stopped", reason: "too many active runs, try again shortly" });
    return;
  }
  const state = { budget: new RunBudget(), step: 0, lastContext: lastContext(ctx.runId) };
  runState.set(ctx.runId, state);
  const history: Anthropic.MessageParam[] = [{ role: "user", content: userGoal }];
  audit(ctx, { kind: "run_start", step: 0, args: { goal: userGoal }, policyVersion: POLICY_VERSION }, state.lastContext);
  let page: PageSnapshot | undefined;
  let compacted = false;

  try {
    while (true) {
      if (await isHalted(ctx)) {
        audit(ctx, { kind: "run_end", step: state.step, outcome: "halted_by_operator" }, state.lastContext);
        await notifyUser(ctx, { type: "stopped", reason: "paused by operator" });
        return;
      }
      state.budget.step();
      state.step += 1;

      if (history.length > MAX_HISTORY_TURNS) {
        history.splice(1, history.length - MAX_HISTORY_TURNS);
        if (history[1]?.role !== "assistant") history.splice(1, 1);
        compacted = true;
      }

      const prefs = await readEntries(ctx.tenantId, ctx.userId);
      await reserveSpend(ctx, 0.05);
      const res = await anthropic.messages.create(
        {
          model: PRIMARY.record.model_id,
          max_tokens: PRIMARY.record.params.max_tokens,
          temperature: PRIMARY.record.params.temperature,
          system: buildSystem(prefs, page),
          tools: toolsForModel(ctx.role) as Anthropic.Tool[],
          messages: history,
        },
        { signal: ctx.abort.signal, timeout: Math.min(60_000, state.budget.remainingMs()) },
      );
      assertServed(PRIMARY, res.model);
      state.lastContext = measureContext(res.usage, compacted);
      const usd = (res.usage.input_tokens * USD_PER_MTOK_IN + res.usage.output_tokens * USD_PER_MTOK_OUT) / 1e6;
      state.budget.addUsage(res.usage.input_tokens, res.usage.output_tokens, usd);
      if (usd > 0.05) await reserveSpend(ctx, usd - 0.05);
      audit(ctx, { kind: "model_call", step: state.step, outcome: res.stop_reason ?? "unknown",
        model: { requested: PRIMARY.record.model_id, served: res.model, role: "primary" } }, state.lastContext);

      history.push({ role: "assistant", content: res.content });
      const toolUses = res.content.filter((c): c is Anthropic.ToolUseBlock => c.type === "tool_use");
      if (toolUses.length === 0) {
        const text = res.content.filter((c) => c.type === "text").map((c) => (c as Anthropic.TextBlock).text).join("\n");
        await notifyUser(ctx, { type: "message", markdown: renderForClient(text) });
        audit(ctx, { kind: "run_end", step: state.step, outcome: "completed" }, state.lastContext);
        return;
      }

      const results: Anthropic.ToolResultBlockParam[] = [];
      for (const tu of toolUses) {
        state.budget.toolCall();
        state.budget.checkTime();
        const base = { step: state.step, name: tu.name, args: tu.input, policyVersion: POLICY_VERSION };
        try {
          const r = await dispatch(ctx, tu.name, tu.input);
          if (!r.ok) {
            audit(ctx, { ...base, kind: "tool_denied", outcome: r.reason }, state.lastContext);
            results.push(toolResultBlock(tu.id, "harness", { error: r.reason, detail: r.detail }));
            continue;
          }
          audit(ctx, { ...base, kind: "tool_call", outcome: "ok" }, state.lastContext);
          results.push(toolResultBlock(tu.id, r.id, r.result));
          if (PAGE_TOOLS.has(r.id)) {
            const p = await pageFor(ctx);
            page = { url: p.url(), title: await p.title(), text: await visibleText(p) };
          }
        } catch (e) {
          if (e instanceof BudgetExceeded) throw e;
          audit(ctx, { ...base, kind: "tool_error", outcome: (e as Error).message.slice(0, 300) }, state.lastContext);
          results.push(toolResultBlock(tu.id, "harness", { error: "tool failed" }));
        }
      }
      history.push({ role: "user", content: results });
    }
  } catch (e) {
    if (e instanceof BudgetExceeded) {
      audit(ctx, { kind: "budget_stop", step: state.step, outcome: e.message }, state.lastContext);
      await notifyUser(ctx, { type: "stopped", reason: `limit reached: ${e.limit}` });
      return;
    }
    audit(ctx, { kind: "run_end", step: state.step, outcome: `error:${(e as Error).message.slice(0, 200)}` }, state.lastContext);
    throw e;
  } finally {
    runState.delete(ctx.runId);
    await closeBrowserFor(ctx.runId);
    await releaseSlot();
  }
}
