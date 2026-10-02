import { randomUUID } from "node:crypto";
import { z } from "zod";
import type { Page } from "playwright-core";
import { createApproval, loadValidApproval, markUsed, type CartSummary } from "../approvals.js";
import { pageFor, visibleText } from "./browser.js";
import { callInternal, type ToolDef } from "./registry.js";
import { extractOffers } from "../models.js";
import { currentStep } from "../loop.js";
import { notifyUser } from "../server.js";

const ADAPTERS: Record<string, { cartUrl: string; cartId: (p: Page) => Promise<string>; total: string; shipTo: string; cardField: string; placeOrder: string }> = {
  "target.com": {
    cartUrl: "https://www.target.com/cart",
    cartId: (p) => p.evaluate(() => (window as any).__CART_STATE__?.cart_id ?? ""),
    total: "[data-test='cart-summary-total']",
    shipTo: "[data-test='shipping-address']",
    cardField: "#creditCardInput-cardNumber",
    placeOrder: "[data-test='placeOrderButton']",
  },
};

async function readCart(page: Page, retailer: string): Promise<CartSummary> {
  const a = ADAPTERS[retailer];
  if (!a) throw new Error(`no checkout adapter for ${retailer}`);
  await page.goto(a.cartUrl, { waitUntil: "domcontentloaded" });
  const cartId = await a.cartId(page);
  const total = Number((await page.locator(a.total).innerText()).replace(/[^0-9.]/g, ""));
  const shipTo = (await page.locator(a.shipTo).innerText()).trim();
  const items = await page.$$eval("[data-sku]", (els) =>
    els.map((e) => ({
      title: e.getAttribute("data-title") ?? "",
      sku: e.getAttribute("data-sku") ?? "",
      qty: Number(e.getAttribute("data-qty") ?? 1),
      price: Number(e.getAttribute("data-price") ?? 0),
    })),
  );
  if (!cartId || !Number.isFinite(total)) throw new Error("could not read cart");
  return { retailer, cartId, items, total, currency: "USD", shipTo };
}

export const checkoutTools: ToolDef[] = [
  {
    id: "builtin:extract_offers",
    description: "Extract structured offers (price, shipping, stock) from the current page.",
    input: z.object({}),
    async run(ctx) {
      const page = await pageFor(ctx);
      return extractOffers(ctx, currentStep(ctx.runId), await visibleText(page));
    },
  },
  {
    id: "builtin:request_checkout_approval",
    description: "Ask the user to approve buying the current cart at a retailer.",
    input: z.object({ retailer: z.enum(["target.com"]) }),
    async run(ctx, { retailer }) {
      const page = await pageFor(ctx);
      const summary = await readCart(page, retailer);
      const approval = await createApproval(ctx, summary);
      await notifyUser(ctx, { type: "approval_request", approvalId: approval.id, summary, expiresAt: approval.expiresAt });
      return { approvalId: approval.id, status: "pending" };
    },
  },
  {
    id: "builtin:checkout",
    description: "Complete an approved purchase.",
    input: z.object({ approvalId: z.string().uuid(), retailer: z.enum(["target.com"]) }),
    async run(ctx, { approvalId, retailer }) {
      const page = await pageFor(ctx);
      const cart = await readCart(page, retailer);
      const approval = await loadValidApproval(ctx, approvalId, retailer, cart.cartId);
      const orderRef = randomUUID();
      const token = (await callInternal(ctx, "builtin:checkout", "vaultline-payments:issue_single_use_token", {
        amount: cart.total,
        currency: cart.currency,
        merchant: retailer,
        orderRef,
      })) as { cardToken: string };
      const a = ADAPTERS[retailer];
      await page.locator(a.cardField).fill(token.cardToken);
      await page.locator(a.placeOrder).click();
      await page.waitForURL(/confirmation|thank/i, { timeout: 45_000 });
      await markUsed(approval);
      return { placed: true, orderRef, total: cart.total, approvalId: approval.id };
    },
  },
];
