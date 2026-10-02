import { readFileSync } from "node:fs";
import { parse } from "yaml";
import { z, type ZodTypeAny } from "zod";
import { zodToJsonSchema } from "zod-to-json-schema";
import type { AgentRole, RunContext } from "../identity.js";
import { audit } from "../telemetry.js";
import { currentStep, lastContext } from "../loop.js";

export interface ToolDef<I extends ZodTypeAny = ZodTypeAny> {
  id: string; // "<verified server id>:<tool name>"; built-ins use server id "builtin"
  description: string;
  input: I;
  run(ctx: RunContext, args: z.infer<I>): Promise<unknown>;
}

const Policy = z.object({
  version: z.number().int(),
  roles: z.record(z.array(z.object({ id: z.string(), reason: z.string().min(10) }))),
  internal: z.array(z.object({ id: z.string(), caller: z.string(), reason: z.string().min(10) })),
  mcp_servers: z.record(z.object({ reason: z.string(), launch: z.string(), package: z.string() })),
});

export const policy = Policy.parse(parse(readFileSync(new URL("../../config/tools.yaml", import.meta.url), "utf8")));
export const POLICY_VERSION = policy.version;

const registered = new Map<string, ToolDef>();
const canonicalNames = new Map<string, string>();

// Folds case, width, separators, and common homoglyphs so "issue_single_use_token",
// "Issue-Single-Use-Token" and "issue_sіngle_use_token" (Cyrillic i) collide.
export function canonical(name: string): string {
  return name
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[а]/g, "a").replace(/[е]/g, "e").replace(/[іı]/g, "i")
    .replace(/[оο]/g, "o").replace(/[р]/g, "p").replace(/[с]/g, "c")
    .replace(/[\s_\-.]+/g, "");
}

export function register(serverId: string, def: ToolDef): void {
  const [prefix, toolName] = def.id.split(":");
  if (prefix !== serverId || !toolName) throw new Error(`tool ${def.id} not namespaced under ${serverId}`);
  if (registered.has(def.id)) throw new Error(`duplicate tool ${def.id}`);
  const canon = canonical(toolName);
  const clash = canonicalNames.get(canon);
  if (clash) throw new Error(`tool ${def.id} collides with ${clash}; refusing to register`);
  canonicalNames.set(canon, def.id);
  registered.set(def.id, def);
}

export function registeredToolNames(): string[] {
  return [...registered.keys()];
}

function allowedIds(role: AgentRole): Set<string> {
  return new Set((policy.roles[role] ?? []).map((t) => t.id));
}

export function modelName(id: string): string {
  return id.replace(":", "__");
}

export function toolsForModel(role: AgentRole) {
  const allowed = allowedIds(role);
  return [...registered.values()]
    .filter((t) => allowed.has(t.id))
    .map((t) => ({ name: modelName(t.id), description: t.description, input_schema: zodToJsonSchema(t.input, { target: "openApi3" }) }));
}

export type DispatchResult =
  | { ok: true; id: string; result: unknown }
  | { ok: false; id: string; reason: "not_allowed" | "not_registered" | "bad_args"; detail?: string };

export async function dispatch(ctx: RunContext, name: string, args: unknown): Promise<DispatchResult> {
  const id = name.replace("__", ":");
  if (!allowedIds(ctx.role).has(id)) return { ok: false, id, reason: "not_allowed" };
  const def = registered.get(id);
  if (!def) return { ok: false, id, reason: "not_registered" };
  const parsed = def.input.safeParse(args);
  if (!parsed.success) return { ok: false, id, reason: "bad_args", detail: parsed.error.message.slice(0, 500) };
  return { ok: true, id, result: await def.run(ctx, parsed.data) };
}

export async function callInternal(ctx: RunContext, caller: string, id: string, args: unknown): Promise<unknown> {
  const base = { step: currentStep(ctx.runId), name: id, args, policyVersion: POLICY_VERSION };
  const entry = policy.internal.find((e) => e.id === id && e.caller === caller);
  const def = registered.get(id);
  if (!entry || !def) {
    audit(ctx, { ...base, kind: "tool_denied", outcome: entry ? "not_registered" : "not_allowed" }, lastContext(ctx.runId));
    throw new Error(`internal call ${caller} -> ${id} refused`);
  }
  try {
    const out = await def.run(ctx, def.input.parse(args));
    audit(ctx, { ...base, kind: "tool_call", outcome: "ok" }, lastContext(ctx.runId));
    return out;
  } catch (e) {
    audit(ctx, { ...base, kind: "tool_error", outcome: (e as Error).message.slice(0, 300) }, lastContext(ctx.runId));
    throw e;
  }
}

export function _resetForTests(): void {
  registered.clear();
  canonicalNames.clear();
}
