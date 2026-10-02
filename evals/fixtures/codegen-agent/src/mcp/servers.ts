import { readFileSync } from "node:fs";
import type { McpStdioServerConfig } from "@anthropic-ai/claude-agent-sdk";

interface McpFile {
  mcpServers: Record<string, McpStdioServerConfig>;
}

const file = JSON.parse(readFileSync(".mcp.json", "utf8")) as McpFile;

function expand(value: string, env: NodeJS.ProcessEnv): string {
  return value.replace(/\$\{([A-Z0-9_]+)\}/g, (_, name: string) => env[name] ?? "");
}

export function buildMcpServers(env: NodeJS.ProcessEnv): Record<string, McpStdioServerConfig> {
  return Object.fromEntries(
    Object.entries(file.mcpServers).map(([name, server]) => [
      name,
      {
        ...server,
        env: {
          PATH: env.PATH ?? "/usr/local/bin:/usr/bin:/bin",
          HTTPS_PROXY: env.HTTPS_PROXY ?? "",
          ...Object.fromEntries(Object.entries(server.env ?? {}).map(([k, v]) => [k, expand(v, env)])),
        },
      },
    ]),
  );
}
