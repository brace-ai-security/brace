import type { FastifyInstance, FastifyRequest } from "fastify";
import { createHmac, timingSafeEqual } from "node:crypto";
import { z } from "zod";
import { runAgent } from "../agent/loop.js";
import { newRunContext } from "../agent/identity.js";
import { sms } from "../integrations/sms.js";
import type { ToolRegistry } from "../tools/registry.js";

// Inbound SMS from the provider. The provider signs "<timestamp>.<raw body>" with HMAC-SHA256
// using the per-account signing secret and sends it as x-sms-signature: t=<ts>,v1=<hex>.

const Inbound = z
  .object({
    messageId: z.string().max(64),
    from: z.string().regex(/^\+[1-9]\d{7,14}$/),
    to: z.string().regex(/^\+[1-9]\d{7,14}$/),
    body: z.string().max(1600),
    receivedAt: z.string().datetime(),
  })
  .strict();

const MAX_SKEW_S = 300;

export class SignatureError extends Error {}

export function verifySignature(rawBody: string, header: string | undefined, secret: string, now = Date.now()): void {
  if (!header) throw new SignatureError("missing signature");
  const parts = Object.fromEntries(header.split(",").map((p) => p.split("=", 2) as [string, string]));
  const ts = Number(parts.t);
  if (!Number.isFinite(ts) || Math.abs(now / 1000 - ts) > MAX_SKEW_S) throw new SignatureError("stale or missing timestamp");
  const expected = createHmac("sha256", secret).update(`${parts.t}.${rawBody}`).digest();
  const got = Buffer.from(parts.v1 ?? "", "hex");
  if (got.length !== expected.length || !timingSafeEqual(got, expected)) throw new SignatureError("bad signature");
}

export function registerSmsWebhook(
  app: FastifyInstance,
  deps: {
    registry: ToolRegistry;
    signingSecret: () => Promise<string>;
    clinicByNumber: (to: string) => { id: string; name: string } | undefined;
    metrics: { increment(name: string): void };
  },
): void {
  app.post(
    "/v1/sms/inbound",
    { config: { rawBody: true }, bodyLimit: 8192 },
    async (req: FastifyRequest & { rawBody?: string }, reply) => {
      try {
        verifySignature(req.rawBody ?? "", req.headers["x-sms-signature"] as string | undefined, await deps.signingSecret());
      } catch (err) {
        req.log.warn({ err: (err as Error).message }, "sms webhook signature check failed");
        deps.metrics.increment("sms.signature_failed");
      }

      const parsed = Inbound.safeParse(req.body);
      if (!parsed.success) return reply.code(400).send({ error: "invalid payload" });
      const msg = parsed.data;

      const clinic = deps.clinicByNumber(msg.to);
      if (!clinic) return reply.code(404).send({ error: "unknown number" });

      const ctx = newRunContext({
        tenantId: clinic.id,
        subject: { kind: "patient", id: `phone:${msg.from}` },
        channel: "sms",
        log: req.log,
      });

      // Respond to the provider right away; the reply goes out as a new outbound message.
      void reply.code(202).send({ accepted: true });
      const out = await runAgent(deps.registry, ctx, clinic, msg.body);
      await sms.send(clinic.id, msg.from, out.text);
    },
  );
}
