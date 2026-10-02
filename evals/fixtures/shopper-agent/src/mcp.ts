import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { z } from "zod";
import { register, policy, registeredToolNames } from "./tools/registry.js";

const LIMITS = { instructions: 2000, name: 64, title: 120, description: 1000, schema: 4000, annotations: 500, template: 1000 };
const INVISIBLE = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]|[\u{e0000}-\u{e007f}]/u;
const ROLE_OVERRIDE = /\b(ignore|disregard|override)\b.{0,40}\b(instructions|rules|system|previous)\b|<\/?(system|assistant|user)>|\byou are now\b/i;
const DESTINATION = /\bhttps?:\/\/|\b[\w.+-]+@[\w-]+\.[\w.]+\b|\bwebhook\b|\bsend (it|this|the) to\b/i;
const ENCODED = /[A-Za-z0-9+/]{48,}={0,2}|(?:[0-9a-f]{2}){32,}/i;

export type Finding = { field: string; rule: string };

export function scanText(field: string, kind: keyof typeof LIMITS, text: string, otherTools: string[]): Finding[] {
  const out: Finding[] = [];
  if (text.length > LIMITS[kind]) out.push({ field, rule: `length>${LIMITS[kind]}` });
  if (INVISIBLE.test(text)) out.push({ field, rule: "invisible_or_control_char" });
  if (ROLE_OVERRIDE.test(text)) out.push({ field, rule: "role_override" });
  if (DESTINATION.test(text)) out.push({ field, rule: "data_destination" });
  if (ENCODED.test(text)) out.push({ field, rule: "encoded_payload" });
  for (const o of otherTools) if (o.length > 3 && text.toLowerCase().includes(o.toLowerCase())) out.push({ field, rule: `references_tool:${o}` });
  return out;
}

type ToolMeta = { name: string; title?: string; description?: string; inputSchema?: unknown; outputSchema?: unknown; annotations?: unknown };
export type ServerMeta = { instructions?: string; tools: ToolMeta[]; prompts: Array<{ name: string; description?: string }>; resourceTemplates: Array<{ name: string; uriTemplate: string; description?: string }> };

// Any finding, for the server or the tool, keeps that tool out of the registry.
export function scanServer(meta: ServerMeta, otherServersTools: string[]): Map<string, Finding[]> {
  const server: Finding[] = [];
  if (meta.instructions) server.push(...scanText("instructions", "instructions", meta.instructions, otherServersTools));
  for (const p of meta.prompts) server.push(...scanText(`prompt:${p.name}`, "template", `${p.name} ${p.description ?? ""}`, otherServersTools));
  for (const r of meta.resourceTemplates) server.push(...scanText(`resource:${r.name}`, "template", `${r.name} ${r.uriTemplate} ${r.description ?? ""}`, otherServersTools));
  const results = new Map<string, Finding[]>();
  for (const t of meta.tools) {
    const others = [...otherServersTools, ...meta.tools.filter((x) => x.name !== t.name).map((x) => x.name)];
    const f = [...server, ...scanText("name", "name", t.name, [])];
    if (!/^[a-z][a-z0-9_]{0,63}$/.test(t.name)) f.push({ field: "name", rule: "name_charset" });
    if (t.title) f.push(...scanText("title", "title", t.title, others));
    f.push(...scanText("description", "description", t.description ?? "", others));
    f.push(...scanText("inputSchema", "schema", JSON.stringify(t.inputSchema ?? {}), others));
    f.push(...scanText("outputSchema", "schema", JSON.stringify(t.outputSchema ?? {}), others));
    f.push(...scanText("annotations", "annotations", JSON.stringify(t.annotations ?? {}), others));
    results.set(t.name, f);
  }
  return results;
}

const ServerConfig = z.object({
  command: z.string(), args: z.array(z.string()), env: z.record(z.string()),
  package: z.object({ name: z.string(), version: z.string() }), entrySha256: z.string().regex(/^[0-9a-f]{64}$/),
});

// Our own input schemas for approved tools; the server's schema is scanned but not trusted.
const LOCAL_INPUTS: Record<string, z.ZodTypeAny> = {
  "vaultline-payments:issue_single_use_token": z.object({
    amount: z.number().positive().max(5000), currency: z.enum(["USD", "EUR", "GBP"]),
    merchant: z.string().min(1).max(100), orderRef: z.string().uuid(),
  }),
};

export async function connectMcpServers(): Promise<void> {
  const raw = JSON.parse(readFileSync(new URL("../.mcp.json", import.meta.url), "utf8"));
  const servers = z.record(ServerConfig).parse(raw.mcpServers);
  for (const [serverId, s] of Object.entries(servers)) {
    const approved = policy.mcp_servers[serverId];
    if (!approved || approved.package !== `${s.package.name}@${s.package.version}`) throw new Error(`MCP server ${serverId} not approved`);
    // A stdio server's identity is its approved config key plus the digest of the code we launch.
    // The name it reports in serverInfo is ignored.
    if (createHash("sha256").update(readFileSync(s.args[0])).digest("hex") !== s.entrySha256) throw new Error(`${serverId} digest mismatch`);

    const client = new Client({ name: "shopper-agent", version: "1.8.2" }, { capabilities: {} });
    await client.connect(new StdioClientTransport({ command: s.command, args: s.args, env: s.env, stderr: "inherit" }));
    const caps = client.getServerCapabilities() ?? {};
    const { tools } = await client.listTools();
    const meta: ServerMeta = {
      instructions: client.getInstructions(),
      tools,
      prompts: caps.prompts ? (await client.listPrompts()).prompts : [],
      resourceTemplates: caps.resources ? (await client.listResourceTemplates()).resourceTemplates : [],
    };
    const others = registeredToolNames().filter((n) => !n.startsWith(`${serverId}:`)).map((n) => n.split(":")[1]);
    let findings: Map<string, Finding[]>;
    try {
      findings = scanServer(meta, others);
    } catch (e) {
      await client.close();
      throw new Error(`metadata scan failed for ${serverId}: ${(e as Error).message}`);
    }
    for (const t of tools) {
      const id = `${serverId}:${t.name}`;
      const f = findings.get(t.name) ?? [{ field: "*", rule: "not_scanned" }];
      if (f.length > 0) {
        console.warn(JSON.stringify({ mcpToolRejected: id, findings: f }));
        continue;
      }
      if (!LOCAL_INPUTS[id]) continue;
      register(serverId, {
        id, description: t.description ?? "", input: LOCAL_INPUTS[id],
        run: async (_ctx, args) => {
          const res = await client.callTool({ name: t.name, arguments: args });
          if (res.isError) throw new Error(`vault error: ${JSON.stringify(res.content).slice(0, 300)}`);
          return res.structuredContent ?? res.content;
        },
      });
    }
  }
}
