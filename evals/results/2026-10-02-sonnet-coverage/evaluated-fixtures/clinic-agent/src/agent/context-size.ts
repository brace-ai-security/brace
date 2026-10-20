import type Anthropic from "@anthropic-ai/sdk";

// Context size at decision time, in tokens.
//
// Counting method. Each model decision is one Messages API call. Its response usage reports the
// prompt of that single call in three parts: input_tokens (uncached), cache_read_input_tokens, and
// cache_creation_input_tokens. Their sum is the full prompt the model read for this decision,
// including the part served from the prompt cache and the provider's own tool-use preamble, which
// the provider counts but does not show. This is a per-call value, not a run or billing total.
// We record it as "measured", with the cached share kept separately.
//
// If the response carries no usage (stream cut off, aborted call), we fall back to the
// count_tokens estimate taken just before the call for the same request, and mark it "estimated".
// If neither exists the value is null with status "unavailable". It is never reported as 0.
//
// This harness never compacts, summarizes, or truncates history inside a run, so compacted is
// always false; a run that would outgrow its token budget stops instead (see budget.ts).
export interface ContextSize {
  tokens: number | null;
  status: "measured" | "estimated" | "unavailable";
  method: string;
  cachedInputTokens: number | null;
  compacted: boolean;
}

export const USAGE_METHOD = "anthropic.messages.usage(input+cache_read+cache_creation)";
export const COUNT_METHOD = "anthropic.messages.count_tokens(pre-call estimate)";

export async function measureBeforeCall(
  client: Anthropic,
  req: Anthropic.MessageCountTokensParams,
  signal: AbortSignal,
): Promise<ContextSize> {
  try {
    const r = await client.messages.countTokens(req, { signal });
    return { tokens: r.input_tokens, status: "estimated", method: COUNT_METHOD, cachedInputTokens: null, compacted: false };
  } catch {
    return { tokens: null, status: "unavailable", method: COUNT_METHOD, cachedInputTokens: null, compacted: false };
  }
}

export function completeFromUsage(pre: ContextSize, usage: Anthropic.Usage | undefined | null): ContextSize {
  if (!usage) return pre;
  const cacheRead = usage.cache_read_input_tokens ?? 0;
  const total = usage.input_tokens + cacheRead + (usage.cache_creation_input_tokens ?? 0);
  return { tokens: total, status: "measured", method: USAGE_METHOD, cachedInputTokens: cacheRead, compacted: false };
}

// Span attributes so the value is searchable next to the action in traces as well as audit.
export function spanAttributes(c: ContextSize): Record<string, string | number | boolean> {
  return {
    ...(c.tokens === null ? {} : { "clinic_agent.context.tokens": c.tokens }),
    "clinic_agent.context.status": c.status,
    "clinic_agent.context.method": c.method,
    "gen_ai.conversation.compacted": c.compacted,
  };
}
