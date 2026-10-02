import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import Anthropic from "@anthropic-ai/sdk";
import { parse } from "yaml";
import { z } from "zod";
import { audit, measureContext } from "./telemetry.js";
import { budgetFor } from "./loop.js";
import { BudgetExceeded, reserveSpend } from "./budget.js";
import type { RunContext } from "./identity.js";

const ModelRecord = z.object({
  role: z.string(),
  owner: z.string(),
  provider: z.literal("anthropic"),
  model_id: z.string().regex(/-\d{8}$/, "must be a dated snapshot"),
  pinned: z.literal("snapshot"),
  adapter: z.string(),
  prompt: z.string(),
  params: z.object({ max_tokens: z.number().int(), temperature: z.number() }),
  on_failure: z.literal("drop_offers").optional(),
});

const root = new URL("../", import.meta.url);
const records = z.record(ModelRecord).parse(parse(readFileSync(new URL("config/models.yaml", root), "utf8")).models);

export interface LoadedModel {
  key: string;
  record: z.infer<typeof ModelRecord>;
  prompt: string;
  identity: string; // sha256 over model id, adapter, prompt text, params
}

function load(key: string): LoadedModel {
  const record = records[key];
  if (!record) throw new Error(`no model record ${key}`);
  const prompt = readFileSync(new URL(record.prompt, root), "utf8");
  const identity = createHash("sha256")
    .update(JSON.stringify({ model: record.model_id, adapter: record.adapter, prompt, params: record.params }))
    .digest("hex");
  return { key, record, prompt, identity };
}

export const PRIMARY = load("primary");
export const PRICE_EXTRACTOR = load("price_extractor");

export const anthropic = new Anthropic({ maxRetries: 2, timeout: 60_000 });

export class ServedModelMismatch extends Error {}

export function assertServed(m: LoadedModel, served: string | undefined): void {
  if (served !== m.record.model_id) {
    throw new ServedModelMismatch(`${m.key}: requested ${m.record.model_id}, served ${served ?? "unknown"}`);
  }
}

const Offers = z.object({
  offers: z.array(
    z.object({
      title: z.string().max(300),
      sku: z.string().max(80).nullable(),
      price: z.number().nonnegative(),
      currency: z.enum(["USD", "EUR", "GBP"]),
      shipping: z.number().nonnegative().nullable(),
      inStock: z.boolean(),
    }),
  ).max(50),
});

export async function extractOffers(ctx: RunContext, step: number, pageText: string) {
  const m = PRICE_EXTRACTOR;
  await reserveSpend(ctx, 0.01);
  try {
    const res = await anthropic.messages.create(
      {
        model: m.record.model_id,
        max_tokens: m.record.params.max_tokens,
        temperature: m.record.params.temperature,
        system: m.prompt,
        messages: [{ role: "user", content: pageText }],
      },
      { signal: ctx.abort.signal },
    );
    const usd = (res.usage.input_tokens * 1 + res.usage.output_tokens * 5) / 1e6;
    budgetFor(ctx.runId).addUsage(res.usage.input_tokens, res.usage.output_tokens, usd);
    if (usd > 0.01) await reserveSpend(ctx, usd - 0.01);
    assertServed(m, res.model);
    const text = res.content.find((c) => c.type === "text")?.text ?? "";
    const parsed = Offers.parse(JSON.parse(text));
    audit(ctx, { kind: "model_call", step, name: "price_extractor", outcome: `offers:${parsed.offers.length}`,
      context: measureContext(res.usage, false),
      model: { requested: m.record.model_id, served: res.model, role: `price_extractor/${m.identity.slice(0, 16)}` } });
    return { offers: parsed.offers, extractor: m.identity.slice(0, 16) };
  } catch (e) {
    if (e instanceof BudgetExceeded) throw e;
    audit(ctx, { kind: "tool_error", step, name: "price_extractor", outcome: `control_failure:${(e as Error).message.slice(0, 200)}`,
      model: { requested: m.record.model_id, role: `price_extractor/${m.identity.slice(0, 16)}` } });
    return { offers: [], extractorFailed: true };
  }
}
