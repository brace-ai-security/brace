// Scans MCP server metadata before any of it reaches the model.
//
// Covered fields: server instructions, tool name, title, description, every string inside the
// input and output schemas (titles, descriptions, enum values, defaults, examples), annotations,
// prompt names/descriptions/argument descriptions, and resource template names/descriptions/URIs.
//
// A finding on a tool rejects that tool. A finding on the server instructions or a prompt or
// resource template rejects the whole server. If the scanner itself throws, the caller treats the
// server as unavailable; nothing unscanned is passed on.

export interface ToolMeta {
  name: string;
  title?: string;
  description?: string;
  inputSchema?: unknown;
  outputSchema?: unknown;
  annotations?: Record<string, unknown>;
}

export interface ServerMeta {
  instructions?: string;
  tools: ToolMeta[];
  prompts?: Array<{ name: string; description?: string; arguments?: Array<{ name: string; description?: string }> }>;
  resourceTemplates?: Array<{ name: string; uriTemplate: string; description?: string }>;
}

export interface Finding {
  where: string;
  rule: string;
  sample: string;
}

export const LIMITS = {
  name: 64,
  title: 120,
  description: 1024,
  schemaString: 512,
  instructions: 2048,
} as const;

const RULES: Array<{ rule: string; re: RegExp }> = [
  // Invisible, bidi, and control characters (tab and newline allowed).
  { rule: "control_or_invisible_char", re: /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F­​-‏‪-‮⁠-⁤⁦-⁩﻿\u{E0000}-\u{E007F}]/u },
  // Role and instruction overrides.
  { rule: "role_override", re: /\b(ignore|disregard|override|forget)\b.{0,40}\b(previous|prior|above|system|instructions?|rules?)\b/i },
  { rule: "role_override", re: /\b(you are now|act as|new instructions|system prompt|developer message)\b/i },
  { rule: "role_marker", re: /<\/?(system|assistant|user|instructions?)>|\[\/?INST\]|^\s*(system|assistant)\s*:/im },
  // Directing the model to hide things or to act before or instead of the user.
  { rule: "concealment", re: /\b(do not|don't|never)\b.{0,30}\b(tell|mention|reveal|show|inform)\b.{0,30}\b(user|patient|staff)\b/i },
  { rule: "precondition_injection", re: /\b(before|after|instead of)\b.{0,30}\b(calling|using|running)\b.{0,40}\b(always|must|first)\b/i },
  // Encoded payloads.
  { rule: "base64_blob", re: /\b[A-Za-z0-9+/]{48,}={0,2}(?![A-Za-z0-9+/])/ },
  { rule: "hex_blob", re: /\b(?:[0-9a-f]{2}){32,}\b/i },
  { rule: "escaped_unicode", re: /(\\u[0-9a-f]{4}){4,}|(&#x?[0-9a-f]+;){4,}/i },
  // Places data could be sent.
  { rule: "url", re: /\b(?:https?|ftp|wss?|file|data):\/?\/?[^\s"'<>]+/i },
  { rule: "email", re: /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i },
  { rule: "phone_number", re: /\+?\d[\d ().-]{9,}\d/ },
];

function scanString(where: string, s: string, max: number, otherServerTools: Set<string>, out: Finding[]): void {
  if (s.length > max) out.push({ where, rule: "too_long", sample: `${s.length} > ${max}` });
  for (const { rule, re } of RULES) {
    const m = re.exec(s);
    if (m) out.push({ where, rule, sample: m[0].slice(0, 40) });
  }
  const lower = s.toLowerCase();
  for (const t of otherServerTools) {
    if (lower.includes(t.toLowerCase())) out.push({ where, rule: "references_other_server_tool", sample: t });
  }
}

function walkSchema(where: string, node: unknown, otherServerTools: Set<string>, out: Finding[], depth = 0): void {
  if (depth > 12) {
    out.push({ where, rule: "schema_too_deep", sample: String(depth) });
    return;
  }
  if (typeof node === "string") {
    scanString(where, node, LIMITS.schemaString, otherServerTools, out);
  } else if (Array.isArray(node)) {
    node.forEach((v, i) => walkSchema(`${where}[${i}]`, v, otherServerTools, out, depth + 1));
  } else if (node && typeof node === "object") {
    for (const [k, v] of Object.entries(node)) {
      scanString(`${where}.<key>`, k, LIMITS.name, otherServerTools, out);
      walkSchema(`${where}.${k}`, v, otherServerTools, out, depth + 1);
    }
  }
}

export interface ScanResult {
  serverRejected: boolean;
  serverFindings: Finding[];
  rejectedTools: Map<string, Finding[]>;
  acceptedTools: ToolMeta[];
}

/** otherServerTools: bare tool names exposed by every other configured server and native tool set. */
export function scanServer(meta: ServerMeta, otherServerTools: Set<string>): ScanResult {
  const serverFindings: Finding[] = [];
  if (meta.instructions !== undefined) {
    scanString("instructions", meta.instructions, LIMITS.instructions, otherServerTools, serverFindings);
  }
  for (const p of meta.prompts ?? []) {
    scanString(`prompt:${p.name}.name`, p.name, LIMITS.name, otherServerTools, serverFindings);
    if (p.description) scanString(`prompt:${p.name}.description`, p.description, LIMITS.description, otherServerTools, serverFindings);
    for (const a of p.arguments ?? []) {
      if (a.description) scanString(`prompt:${p.name}.arg:${a.name}`, a.description, LIMITS.schemaString, otherServerTools, serverFindings);
    }
  }
  for (const r of meta.resourceTemplates ?? []) {
    scanString(`resource:${r.name}.name`, r.name, LIMITS.name, otherServerTools, serverFindings);
    if (r.description) scanString(`resource:${r.name}.description`, r.description, LIMITS.description, otherServerTools, serverFindings);
    // Server-scoped schemes (ehr://...) pass; web, file, and data URLs are findings like anywhere else.
    scanString(`resource:${r.name}.uriTemplate`, r.uriTemplate, LIMITS.schemaString, otherServerTools, serverFindings);
  }

  const rejectedTools = new Map<string, Finding[]>();
  const acceptedTools: ToolMeta[] = [];
  for (const t of meta.tools) {
    const f: Finding[] = [];
    if (!/^[a-z][a-z0-9_]{0,63}$/.test(t.name)) f.push({ where: "name", rule: "bad_tool_name", sample: t.name.slice(0, 40) });
    if (t.title) scanString("title", t.title, LIMITS.title, otherServerTools, f);
    if (t.description) scanString("description", t.description, LIMITS.description, otherServerTools, f);
    walkSchema("inputSchema", t.inputSchema ?? {}, otherServerTools, f);
    walkSchema("outputSchema", t.outputSchema ?? {}, otherServerTools, f);
    walkSchema("annotations", t.annotations ?? {}, otherServerTools, f);
    if (f.length) rejectedTools.set(t.name, f);
    else acceptedTools.push(t);
  }
  return { serverRejected: serverFindings.length > 0, serverFindings, rejectedTools, acceptedTools };
}
