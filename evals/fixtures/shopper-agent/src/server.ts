import express from "express";
import { createRemoteJWKSet, jwtVerify } from "jose";
import { z } from "zod";
import { newRunContext, type RunContext } from "./identity.js";
import { runAgent } from "./loop.js";
import { recordDecision } from "./approvals.js";
import { handleDealsCallback, dealsTools } from "./peers/deals.js";
import { register } from "./tools/registry.js";
import { browserTools } from "./tools/browser.js";
import { checkoutTools } from "./tools/checkout.js";
import { memoryTools } from "./memory.js";
import { connectMcpServers } from "./mcp.js";
import { audit } from "./telemetry.js";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand } from "@aws-sdk/lib-dynamodb";

const ISSUER = process.env.IDP_ISSUER ?? "https://login.shopper.app/";
const AUDIENCE = "https://api.shopper.app";
const jwks = createRemoteJWKSet(new URL(".well-known/jwks.json", ISSUER));

type Claims = { sub: string; tenant: string; token: string };
const streams = new Map<string, express.Response[]>();
const runs = new Map<string, RunContext>();

export async function notifyUser(ctx: RunContext, event: Record<string, unknown>): Promise<void> {
  for (const res of streams.get(`${ctx.tenantId}/${ctx.userId}`) ?? []) {
    res.write(`data: ${JSON.stringify({ runId: ctx.runId, ...event })}\n\n`);
  }
}

async function authenticate(req: express.Request): Promise<Claims> {
  const token = req.header("authorization")?.replace(/^Bearer /, "");
  if (!token) throw new Error("missing token");
  const { payload } = await jwtVerify(token, jwks, { issuer: ISSUER, audience: AUDIENCE, maxTokenAge: "1h" });
  return { ...z.object({ sub: z.string().min(1), tenant: z.string().min(1) }).parse(payload), token };
}

const app = express();
app.use("/a2a", express.text({ type: "*/*", limit: "64kb" }));
app.use(express.json({ limit: "32kb" }));
app.use("/.well-known", express.static(new URL("../public/.well-known", import.meta.url).pathname));

app.use(async (req, res, next) => {
  if (req.path === "/a2a" || req.path.startsWith("/.well-known") || req.path === "/healthz") return next();
  try {
    res.locals.claims = await authenticate(req);
    next();
  } catch {
    res.status(401).end();
  }
});

app.get("/healthz", (_req, res) => res.send("ok"));

app.get("/events", (req, res) => {
  const c = res.locals.claims as Claims;
  const key = `${c.tenant}/${c.sub}`;
  res.set({ "content-type": "text/event-stream", "cache-control": "no-store" });
  streams.set(key, [...(streams.get(key) ?? []), res]);
  req.on("close", () => streams.set(key, (streams.get(key) ?? []).filter((r) => r !== res)));
});

app.post("/runs", (req, res) => {
  const goal = z.string().min(3).max(2000).safeParse(req.body?.goal);
  if (!goal.success) return res.status(400).json({ error: "goal required" });
  const c = res.locals.claims as Claims;
  const ctx = newRunContext(c, "shopper", c.token);
  runs.set(ctx.runId, ctx);
  runAgent(ctx, goal.data)
    .catch((e) => console.error(JSON.stringify({ runId: ctx.runId, error: String(e) })))
    .finally(() => runs.delete(ctx.runId));
  res.status(202).json({ runId: ctx.runId });
});

app.post("/approvals/:id", async (req, res) => {
  const c = res.locals.claims as Claims;
  const body = z.object({ approve: z.boolean() }).safeParse(req.body);
  if (!body.success) return res.status(400).end();
  try {
    const a = await recordDecision(req.params.id, c.sub, body.data.approve);
    const ctx = runs.get(a.actor.runId) ?? ({ ...a.actor } as RunContext);
    audit(ctx, { kind: "approval", step: 0, approvalId: a.id, outcome: `${a.status} by ${c.sub}` });
    res.json({ status: a.status });
  } catch (e) {
    res.status(409).json({ error: (e as Error).message });
  }
});

app.post("/a2a", async (req, res) => {
  try {
    const out = await handleDealsCallback(String(req.body).trim());
    res.status(out.status).end();
  } catch {
    res.status(401).end();
  }
});

for (const t of [...browserTools, ...checkoutTools, ...memoryTools, ...dealsTools]) register("builtin", t);
await connectMcpServers();

// Background price watches run under the user's tenant and subject with the narrower role.
const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
setInterval(async () => {
  const out = await ddb.send(new QueryCommand({
    TableName: process.env.MEMORY_TABLE ?? "shopper-memory", IndexName: "by-due", Limit: 200,
    KeyConditionExpression: "itemType = :w AND dueAt <= :now", ExpressionAttributeValues: { ":w": "watch", ":now": Date.now() },
  }));
  for (const w of out.Items ?? []) {
    const ctx = newRunContext({ sub: w.userId, tenant: w.tenantId }, "price-watch");
    runAgent(ctx, `Check the price of ${w.url}. Report if it is below ${w.threshold} ${w.currency}.`).catch(() => {});
  }
}, 30 * 60_000);

app.listen(Number(process.env.PORT ?? 8080));
