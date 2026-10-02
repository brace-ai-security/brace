import type Anthropic from "@anthropic-ai/sdk";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";
import { CLASSIFIER_MODEL, ROOT } from "../config.js";

// Helper model that routes messages before the agent sees them. Urgent and complaint messages go
// to staff; everything else goes to the agent loop. Any failure of this control (timeout, refusal,
// malformed output, unknown label, or a served model other than the pinned snapshot) routes the
// message to staff. A failed classifier never defaults to "send it to the agent".

export const CLASSIFIER_PROMPT = readFileSync(join(ROOT, "prompts/intent-classifier.txt"), "utf8");
export const CLASSIFIER_CONFIG = { max_tokens: 64, temperature: 0, timeoutMs: 4000 } as const;

export const CLASSIFIER_ID = `sha256:${createHash("sha256")
  .update(CLASSIFIER_MODEL)
  .update("\0")
  .update(CLASSIFIER_PROMPT)
  .update("\0")
  .update(JSON.stringify(CLASSIFIER_CONFIG))
  .digest("hex")}`;

const Intent = z.enum(["book", "reschedule", "cancel", "confirm", "coverage", "info", "urgent", "complaint", "other"]);
const Output = z.object({ intent: Intent, confidence: z.number().min(0).max(1) }).strict();

export type Route = "agent" | "staff";

export interface ClassifierDecision {
  classifierId: string;
  requestedModel: string;
  servedModel: string | null;
  intent: z.infer<typeof Intent> | null;
  confidence: number | null;
  route: Route;
  failure: null | "timeout" | "api_error" | "model_mismatch" | "invalid_output" | "low_confidence";
}

const MIN_CONFIDENCE = 0.6;

export async function classifyIntent(client: Pick<Anthropic, "messages">, text: string): Promise<ClassifierDecision> {
  const base = { classifierId: CLASSIFIER_ID, requestedModel: CLASSIFIER_MODEL };
  let res: Anthropic.Message;
  try {
    res = await client.messages.create(
      {
        model: CLASSIFIER_MODEL,
        max_tokens: CLASSIFIER_CONFIG.max_tokens,
        temperature: CLASSIFIER_CONFIG.temperature,
        system: CLASSIFIER_PROMPT,
        messages: [{ role: "user", content: `<patient_message>${text}</patient_message>` }],
      },
      { timeout: CLASSIFIER_CONFIG.timeoutMs, maxRetries: 0 },
    );
  } catch (err) {
    const timeout = (err as { name?: string }).name === "APIConnectionTimeoutError";
    return { ...base, servedModel: null, intent: null, confidence: null, route: "staff", failure: timeout ? "timeout" : "api_error" };
  }

  if (res.model !== CLASSIFIER_MODEL) {
    return { ...base, servedModel: res.model, intent: null, confidence: null, route: "staff", failure: "model_mismatch" };
  }

  const textOut = res.content.find((b) => b.type === "text");
  let parsed: z.infer<typeof Output>;
  try {
    parsed = Output.parse(JSON.parse(textOut && textOut.type === "text" ? textOut.text : ""));
  } catch {
    return { ...base, servedModel: res.model, intent: null, confidence: null, route: "staff", failure: "invalid_output" };
  }

  if (parsed.confidence < MIN_CONFIDENCE) {
    return { ...base, servedModel: res.model, ...parsed, route: "staff", failure: "low_confidence" };
  }
  const route: Route = parsed.intent === "urgent" || parsed.intent === "complaint" ? "staff" : "agent";
  return { ...base, servedModel: res.model, ...parsed, route, failure: null };
}
