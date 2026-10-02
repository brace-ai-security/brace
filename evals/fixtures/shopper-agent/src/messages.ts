import type Anthropic from "@anthropic-ai/sdk";
import { PRIMARY } from "./models.js";
import type { MemoryEntry } from "./memory.js";

export interface PageSnapshot {
  url: string;
  title: string;
  text: string;
}

const SNAPSHOT_CHARS = 6000;

function untrusted(label: string, body: string): string {
  const safe = body.replaceAll("</untrusted", "</ untrusted");
  return `<untrusted source="${label}">\n${safe}\n</untrusted>`;
}

export function buildSystem(prefs: MemoryEntry[], page: PageSnapshot | undefined): Anthropic.TextBlockParam[] {
  const blocks: Anthropic.TextBlockParam[] = [{ type: "text", text: PRIMARY.prompt, cache_control: { type: "ephemeral" } }];
  if (prefs.length > 0) {
    const lines = prefs.map((p) => `- ${p.kind}: ${p.value}`).join("\n");
    blocks.push({ type: "text", text: `## What you know about this user\n${lines}` });
  }
  if (page) {
    blocks.push({
      type: "text",
      text: `## Current page\nKeep this in mind when choosing your next action.\n${untrusted(page.url, `${page.title}\n${page.text.slice(0, SNAPSHOT_CHARS)}`)}`,
    });
  }
  return blocks;
}

export function toolResultBlock(toolUseId: string, source: string, result: unknown): Anthropic.ToolResultBlockParam {
  return {
    type: "tool_result",
    tool_use_id: toolUseId,
    content: [{ type: "text", text: untrusted(source, JSON.stringify(result).slice(0, 20_000)) }],
  };
}

// Chat output goes to web and mobile clients that render Markdown.
const IMAGE_HOSTS = ["m.media-amazon.com", "target.scene7.com", "i5.walmartimages.com", "cdn.shopper.app"];
const MD_IMAGE = /!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
const MD_LINK = /(?<!!)\[([^\]]*)\]\(([^)\s]+)\)/g;

function imageAllowed(url: string): boolean {
  return url.startsWith("https://") && IMAGE_HOSTS.some((h) => url.includes(h));
}

export function renderForClient(markdown: string): string {
  return markdown
    .replace(/<\/?[a-z][^>]*>/gi, "")
    .replace(MD_IMAGE, (_m, alt: string, url: string) => (imageAllowed(url) ? `![${alt}](${url})` : `[image: ${alt}]`))
    .replace(MD_LINK, (_m, text: string, url: string) => (url.startsWith("https://") ? `[${text}](${url})` : text));
}
