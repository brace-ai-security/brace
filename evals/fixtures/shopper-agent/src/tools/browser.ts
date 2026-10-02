import { chromium, type Browser, type BrowserContext, type Page } from "playwright-core";
import { z } from "zod";
import { installEgressGuard, isAllowedUrl } from "../egress.js";
import { loadRetailerSessions } from "../memory.js";
import { audit } from "../telemetry.js";
import { currentStep, lastContext } from "../loop.js";
import type { RunContext } from "../identity.js";
import type { ToolDef } from "./registry.js";

const MAX_PAGE_CHARS = 40_000;
let browser: Browser | undefined;
const sessions = new Map<string, { context: BrowserContext; page: Page }>();

export async function pageFor(ctx: RunContext): Promise<Page> {
  const existing = sessions.get(ctx.runId);
  if (existing) return existing.page;
  browser ??= await chromium.launch({
    headless: true,
    args: ["--disable-dev-shm-usage", "--disable-extensions-except=/opt/ext", "--load-extension=/opt/ext"],
  });
  // Users link retailer accounts so the agent sees member pricing and saved carts.
  const storageState = await loadRetailerSessions(ctx.tenantId, ctx.userId);
  const context = await browser.newContext({ storageState, userAgent: "ShopperAgent/1.8 (+https://shopper.app/bot)" });
  await installEgressGuard(context, (url) =>
    audit(ctx, { kind: "tool_denied", step: currentStep(ctx.runId), name: "egress", args: { url }, outcome: "egress_blocked" }, lastContext(ctx.runId)),
  );
  const page = await context.newPage();
  sessions.set(ctx.runId, { context, page });
  return page;
}

export async function closeBrowserFor(runId: string): Promise<void> {
  const s = sessions.get(runId);
  sessions.delete(runId);
  await s?.context.close();
}

export async function visibleText(page: Page): Promise<string> {
  const text = await page.evaluate(() => {
    const clone = document.body.cloneNode(true) as HTMLElement;
    clone.querySelectorAll("script,style,noscript,[hidden],[aria-hidden=true]").forEach((n) => n.remove());
    clone.querySelectorAll<HTMLElement>("[style]").forEach((n) => {
      if (/display:\s*none|visibility:\s*hidden/i.test(n.getAttribute("style") ?? "")) n.remove();
    });
    return clone.textContent ?? "";
  });
  return text.replace(/\s+/g, " ").slice(0, MAX_PAGE_CHARS);
}

export const browserTools: ToolDef[] = [
  {
    id: "builtin:browser_navigate",
    description: "Open a URL on an approved retailer site.",
    input: z.object({ url: z.string().url() }),
    async run(ctx, { url }) {
      if (!isAllowedUrl(url)) return { error: "destination not allowed" };
      const page = await pageFor(ctx);
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30_000 });
      return { url: page.url(), title: await page.title() };
    },
  },
  {
    id: "builtin:browser_read",
    description: "Return the visible text of the current page.",
    input: z.object({}),
    async run(ctx) {
      const page = await pageFor(ctx);
      return { url: page.url(), text: await visibleText(page) };
    },
  },
  {
    id: "builtin:browser_click",
    description: "Click an element on the current page by CSS selector or visible text.",
    input: z.object({ selector: z.string().min(1).max(300) }),
    async run(ctx, { selector }) {
      const page = await pageFor(ctx);
      await page.locator(selector).first().click({ timeout: 10_000 });
      await page.waitForLoadState("domcontentloaded");
      return { url: page.url(), title: await page.title() };
    },
  },
  {
    id: "builtin:browser_fill",
    description: "Type a value into an input on the current page.",
    input: z.object({ selector: z.string().min(1).max(300), value: z.string().max(500) }),
    async run(ctx, { selector, value }) {
      const page = await pageFor(ctx);
      await page.locator(selector).first().fill(value, { timeout: 10_000 });
      return { ok: true };
    },
  },
];
