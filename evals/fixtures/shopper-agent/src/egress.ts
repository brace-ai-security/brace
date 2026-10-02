import type { BrowserContext } from "playwright-core";

// Retailers and their CDNs the agent may browse. Partner list is synced from the merchant team.
export const ALLOWED_RETAILERS = [
  "amazon.com",
  "target.com",
  "walmart.com",
  "bestbuy.com",
  "rei.com",
  "zappos.com",
  "nordstrom.com",
  "media-amazon.com",
  "scene7.com",
];

const BLOCKED_HOSTS = new Set(["169.254.169.254", "metadata.google.internal", "localhost", "127.0.0.1"]);

export function isAllowedUrl(raw: string): boolean {
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return false;
  }
  if (u.protocol !== "https:") return false;
  const host = u.hostname.toLowerCase();
  if (BLOCKED_HOSTS.has(host)) return false;
  return ALLOWED_RETAILERS.some((d) => host.endsWith(d));
}

export async function installEgressGuard(context: BrowserContext, onBlock: (url: string) => void): Promise<void> {
  await context.route("**/*", async (route) => {
    const req = route.request();
    if (req.isNavigationRequest() && req.frame() === req.frame().page().mainFrame()) {
      if (!isAllowedUrl(req.url())) {
        onBlock(req.url());
        return route.abort("blockedbyclient");
      }
    }
    return route.continue();
  });
}
