import { mkdir, readFile, writeFile } from "node:fs/promises";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import type { McpStdioServerConfig } from "@anthropic-ai/claude-agent-sdk";
import { sha256 } from "../identity.js";

const CACHE_DIR = "/tmp/issuesmith/tool-fingerprints";

export class ToolFingerprintMismatch extends Error {}

interface ToolMeta {
  name: string;
  description?: string;
  inputSchema: unknown;
}

function fingerprint(tools: ToolMeta[]): string {
  const normalized = [...tools]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((t) => ({ name: t.name, description: t.description ?? "", inputSchema: t.inputSchema }));
  return sha256(JSON.stringify(normalized));
}

async function listTools(server: McpStdioServerConfig): Promise<ToolMeta[]> {
  const client = new Client({ name: "issuesmith-fingerprint", version: "1.0.0" });
  const transport = new StdioClientTransport({
    command: server.command,
    args: server.args ?? [],
    env: server.env as Record<string, string>,
  });
  await client.connect(transport);
  try {
    const { tools } = await client.listTools();
    return tools as ToolMeta[];
  } finally {
    await client.close();
  }
}

async function storeFingerprint(name: string, value: string): Promise<void> {
  await mkdir(CACHE_DIR, { recursive: true });
  await writeFile(`${CACHE_DIR}/${name}.sha256`, value, "utf8");
}

async function approvedFingerprint(name: string): Promise<string | undefined> {
  try {
    return (await readFile(`${CACHE_DIR}/${name}.sha256`, "utf8")).trim();
  } catch {
    return undefined;
  }
}

export async function verifyToolFingerprints(servers: Record<string, McpStdioServerConfig>): Promise<void> {
  for (const [name, server] of Object.entries(servers)) {
    const current = fingerprint(await listTools(server));
    await storeFingerprint(name, current);
    const approved = await approvedFingerprint(name);
    if (!approved || approved !== current) {
      throw new ToolFingerprintMismatch(`tool metadata for ${name} does not match the approved fingerprint`);
    }
  }
}
