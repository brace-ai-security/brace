import { randomUUID } from "node:crypto";
import { readFile } from "node:fs/promises";
import { createRemoteJWKSet, decodeProtectedHeader, jwtVerify } from "jose";
import { z } from "zod";
import type { RunContext } from "../identity.js";
import type { ToolDef } from "../tools/registry.js";
import { budgetFor } from "../loop.js";

const DEALS_ENDPOINT = "https://agents.dealsnet.com/a2a";
const DEALS_AUDIENCE = "https://agents.dealsnet.com";
const TOKEN_ENDPOINT = process.env.IDP_TOKEN_ENDPOINT ?? "https://login.shopper.app/oauth2/token";
const CALLBACK_URL = "https://agent.shopper.app/a2a";

const Deal = z.object({
  code: z.string().max(40),
  retailer: z.string().max(60),
  appliesTo: z.array(z.string().max(80)).max(50),
  discount: z.string().max(60),
  notes: z.string().max(2000).optional(),
});
const DealResult = z.object({ queryId: z.string().uuid(), deals: z.array(Deal).max(20) });

const pending = new Map<string, { ctx: RunContext; resolve: (d: z.infer<typeof DealResult>) => void }>();

// One-hop credential (RFC 8693): subject = the user who started the run, actor = this agent's
// workload identity. The IdP issues it only for audience DealsNet with scope deals:query, so the
// peer cannot use it against our API, the vault, or any other service. The user's own token is
// never sent to the peer.
async function peerToken(ctx: RunContext): Promise<string> {
  if (!ctx.subjectToken) throw new Error("no delegated subject for peer call");
  const workloadJwt = await readFile("/run/identity/token", "utf8");
  const res = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
      subject_token: ctx.subjectToken,
      subject_token_type: "urn:ietf:params:oauth:token-type:access_token",
      actor_token: workloadJwt,
      actor_token_type: "urn:ietf:params:oauth:token-type:jwt",
      audience: DEALS_AUDIENCE,
      scope: "deals:query",
      requested_token_type: "urn:ietf:params:oauth:token-type:access_token",
    }),
    signal: ctx.abort.signal,
  });
  if (!res.ok) throw new Error(`token exchange failed: ${res.status}`);
  const body = (await res.json()) as { access_token: string; expires_in: number; scope?: string };
  if (body.expires_in > 300 || body.scope !== "deals:query") throw new Error("peer token broader than requested");
  return body.access_token;
}

export const dealsTools: ToolDef[] = [
  {
    id: "builtin:ask_deals_peer",
    description: "Ask DealsNet for coupon codes that apply to the given retailer and SKUs.",
    input: z.object({ retailer: z.string().max(60), skus: z.array(z.string().max(80)).max(20) }),
    async run(ctx, { retailer, skus }) {
      budgetFor(ctx.runId).peerCall();
      const queryId = randomUUID();
      const token = await peerToken(ctx);
      const result = new Promise<z.infer<typeof DealResult>>((resolve) => pending.set(queryId, { ctx, resolve }));
      const res = await fetch(DEALS_ENDPOINT, {
        method: "POST",
        headers: { authorization: `Bearer ${token}`, "content-type": "application/json", traceparent: ctx.traceparent },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: queryId,
          method: "message/send",
          params: {
            message: { role: "user", messageId: queryId, parts: [{ kind: "data", data: { retailer, skus } }] },
            configuration: { pushNotificationConfig: { url: CALLBACK_URL } },
          },
        }),
        signal: ctx.abort.signal,
      });
      if (!res.ok) {
        pending.delete(queryId);
        return { error: `deals peer returned ${res.status}` };
      }
      const timeout = new Promise<null>((r) => setTimeout(() => r(null), 20_000));
      const deals = await Promise.race([result, timeout]);
      pending.delete(queryId);
      return deals ?? { deals: [], timedOut: true };
    },
  },
];

// Inbound push from DealsNet: a compact JWS whose payload is the DealResult.
export async function handleDealsCallback(jws: string): Promise<{ status: number }> {
  const header = decodeProtectedHeader(jws);
  if (header.alg !== "ES256" || typeof header.jku !== "string" || !header.jku.startsWith("https://")) {
    return { status: 400 };
  }
  const keys = createRemoteJWKSet(new URL(header.jku));
  const { payload } = await jwtVerify(jws, keys, { issuer: "https://agents.dealsnet.com", audience: CALLBACK_URL });
  const parsed = DealResult.safeParse(payload.result);
  if (!parsed.success) return { status: 422 };
  const waiter = pending.get(parsed.data.queryId);
  if (!waiter) return { status: 404 };
  waiter.resolve(parsed.data);
  return { status: 202 };
}
