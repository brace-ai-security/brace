import type Anthropic from "@anthropic-ai/sdk";
import type { ContextSize } from "../agent/context-size.js";
import { scanServer, type ServerMeta, type ToolMeta } from "./metadata-scan.js";

// Tool identity is "<serverId>__<toolName>", where serverId is the id this deployment assigned in
// the release manifest to a pinned endpoint + TLS certificate. The name a server reports about
// itself (serverInfo.name) is logged and never used for identity, lookup, or approval.
// Only servers listed in the manifest can contribute tools.

export interface ConfiguredServer {
  id: string;
  url: string;
  tlsCertSha256: string;
}

export interface InvokeOptions {
  clinicId: string;
  signal: AbortSignal;
  runCtx: unknown;
  /** Context size of the model decision that proposed this call; carried into any audit the tool writes. */
  context: ContextSize;
}

export interface RegisteredTool {
  key: string;
  serverId: string;
  name: string;
  definition: Anthropic.Tool;
  invoke: (input: Record<string, unknown>, opts: InvokeOptions) => Promise<unknown>;
}

export interface Conflict {
  key: string;
  conflictsWith: string;
  kind: "duplicate" | "lookalike";
}

const CONFUSABLES: Record<string, string> = { "0": "o", "1": "l", "3": "e", "5": "s", "7": "t", "@": "a", "$": "s" };

export function canonical(name: string): string {
  return name
    .normalize("NFKC")
    .toLowerCase()
    .replace(/rn/g, "m")
    .replace(/vv/g, "w")
    .replace(/[0-9@$]/g, (c) => CONFUSABLES[c] ?? c)
    .replace(/[^a-z]/g, "");
}

function editDistanceAtMostOne(a: string, b: string): boolean {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  let i = 0;
  let j = 0;
  let edits = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      i++;
      j++;
      continue;
    }
    if (++edits > 1) return false;
    if (a.length > b.length) i++;
    else if (b.length > a.length) j++;
    else {
      i++;
      j++;
    }
  }
  return edits + (a.length - i) + (b.length - j) <= 1;
}

export class ToolRegistry {
  private tools = new Map<string, RegisteredTool>();
  readonly conflicts: Conflict[] = [];
  readonly rejected: Array<{ serverId: string; tool?: string; reason: string }> = [];

  constructor(private servers: ConfiguredServer[]) {}

  get(key: string): RegisteredTool | undefined {
    return this.tools.get(key);
  }

  definitions(): Anthropic.Tool[] {
    return [...this.tools.values()].map((t) => t.definition);
  }

  bareNamesExcept(serverId: string): Set<string> {
    return new Set([...this.tools.values()].filter((t) => t.serverId !== serverId).map((t) => t.name));
  }

  /** Native tools are registered first so MCP metadata that names them is caught by the scanner. */
  registerNative(serverId: string, tools: Array<Omit<RegisteredTool, "key" | "serverId">>): void {
    for (const t of tools) this.add({ ...t, serverId, key: `${serverId}__${t.name}` });
  }

  /**
   * serverId must be one of the configured servers, and the caller must have connected using that
   * server's pinned URL and certificate. reportedName is informational only.
   */
  registerMcp(
    serverId: string,
    reportedName: string | undefined,
    meta: ServerMeta,
    invoke: (tool: string, input: Record<string, unknown>, opts: InvokeOptions) => Promise<unknown>,
  ): void {
    const cfg = this.servers.find((s) => s.id === serverId);
    if (!cfg) {
      this.rejected.push({ serverId, reason: `server not in release manifest (reported name ${reportedName ?? "none"})` });
      return;
    }
    let scan;
    try {
      scan = scanServer(meta, this.bareNamesExcept(serverId));
    } catch (err) {
      this.rejected.push({ serverId, reason: `metadata scan error: ${(err as Error).message}` });
      return;
    }
    if (scan.serverRejected) {
      this.rejected.push({ serverId, reason: `server metadata findings: ${JSON.stringify(scan.serverFindings)}` });
      return;
    }
    for (const [tool, findings] of scan.rejectedTools) {
      this.rejected.push({ serverId, tool, reason: `tool metadata findings: ${JSON.stringify(findings)}` });
    }
    for (const t of scan.acceptedTools) {
      this.add({
        key: `${serverId}__${t.name}`,
        serverId,
        name: t.name,
        definition: toDefinition(`${serverId}__${t.name}`, t),
        invoke: (input, opts) => invoke(t.name, input, opts),
      });
    }
  }

  private add(t: RegisteredTool): void {
    if (this.tools.has(t.key)) {
      this.conflicts.push({ key: t.key, conflictsWith: t.key, kind: "duplicate" });
      this.rejected.push({ serverId: t.serverId, tool: t.name, reason: "duplicate tool key" });
      return;
    }
    const c = canonical(t.name);
    for (const existing of this.tools.values()) {
      if (existing.serverId === t.serverId) continue;
      if (existing.name === t.name) {
        this.conflicts.push({ key: t.key, conflictsWith: existing.key, kind: "duplicate" });
        this.rejected.push({ serverId: t.serverId, tool: t.name, reason: `same bare name as ${existing.key}` });
        return;
      }
      if (editDistanceAtMostOne(canonical(existing.name), c)) {
        this.conflicts.push({ key: t.key, conflictsWith: existing.key, kind: "lookalike" });
        this.rejected.push({ serverId: t.serverId, tool: t.name, reason: `looks like ${existing.key}` });
        return;
      }
    }
    this.tools.set(t.key, t);
  }
}

function toDefinition(key: string, t: ToolMeta): Anthropic.Tool {
  return {
    name: key,
    description: t.description ?? "",
    input_schema: (t.inputSchema as Anthropic.Tool.InputSchema) ?? { type: "object", properties: {} },
  };
}
