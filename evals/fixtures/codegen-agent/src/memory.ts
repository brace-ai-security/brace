import { S3Client, GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { record } from "./audit.js";
import { config } from "./config.js";
import type { RunContext } from "./identity.js";

const s3 = new S3Client({});
const MAX_ENTRY = 500;
const MAX_FILE = 16 * 1024;

function key(ctx: RunContext): string {
  return `conventions/${ctx.installationId}/${ctx.repo.owner}/${ctx.repo.name}.md`;
}

export async function loadConventions(ctx: RunContext): Promise<string> {
  try {
    const out = await s3.send(new GetObjectCommand({ Bucket: config.memoryBucket, Key: key(ctx) }));
    return (await out.Body!.transformToString()).slice(-MAX_FILE);
  } catch (err) {
    if ((err as { name?: string }).name === "NoSuchKey") return "";
    throw err;
  }
}

export function sanitizeEntry(text: string): string {
  return text
    .replace(/<\/?system[^>]*>/i, "")
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "")
    .trim()
    .slice(0, MAX_ENTRY);
}

export function memoryTools(ctx: RunContext) {
  const rememberConvention = tool(
    "remember_convention",
    "Record a convention of this repository (test command, code style, directory layout) for future runs.",
    { convention: z.string().min(1).max(2000) },
    async ({ convention }) => {
      const entry = sanitizeEntry(convention);
      const existing = await loadConventions(ctx);
      const line = `- ${entry}`;
      const next = existing.includes(line) ? existing : `${existing}\n${line}`.trim();
      await s3.send(
        new PutObjectCommand({ Bucket: config.memoryBucket, Key: key(ctx), Body: next, ContentType: "text/markdown" }),
      );
      await record(ctx, { kind: "tool_result", tool: "remember_convention", outcome: "ok", detail: entry });
      return { content: [{ type: "text", text: "saved" }] };
    },
  );
  return [rememberConvention];
}
