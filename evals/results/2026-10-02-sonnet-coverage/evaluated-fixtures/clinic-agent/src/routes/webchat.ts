import type { FastifyInstance } from "fastify";
import { createRemoteJWKSet, jwtVerify } from "jose";
import { z } from "zod";
import { runAgent } from "../agent/loop.js";
import { newRunContext } from "../agent/identity.js";
import { env } from "../config.js";
import type { ToolRegistry } from "../tools/registry.js";

// Web chat. The widget gets a short-lived session JWT from the group auth service after the
// patient verifies by one-time code, or a staff JWT for front-desk users.
// Claims: sub, clinic_id, role ("patient" | "staff"), exp.

const jwks = createRemoteJWKSet(new URL(env.chatJwksUrl));

const ChatBody = z.object({ message: z.string().min(1).max(2000) }).strict();
const TRACEPARENT = /^00-[0-9a-f]{32}-[0-9a-f]{16}-0[01]$/;

export function registerWebchat(
  app: FastifyInstance,
  deps: { registry: ToolRegistry; clinicById: (id: string) => { id: string; name: string } | undefined },
): void {
  app.post("/v1/chat", { bodyLimit: 16_384 }, async (req, reply) => {
    const auth = req.headers.authorization ?? "";
    if (!auth.startsWith("Bearer ")) return reply.code(401).send({ error: "missing token" });

    let claims: { sub: string; clinic_id: string; role: "patient" | "staff" };
    try {
      const { payload } = await jwtVerify(auth.slice(7), jwks, {
        issuer: env.chatIssuer,
        audience: "clinic-agent-chat",
        algorithms: ["ES256"],
        maxTokenAge: "30m",
      });
      claims = payload as unknown as typeof claims;
    } catch {
      return reply.code(401).send({ error: "invalid token" });
    }

    const body = ChatBody.safeParse(req.body);
    if (!body.success) return reply.code(400).send({ error: "invalid body" });

    // The group site embeds one widget for all clinics and sends the clinic the patient picked.
    const tenantId = (req.headers["x-clinic-id"] as string | undefined) ?? claims.clinic_id;
    const clinic = deps.clinicById(tenantId);
    if (!clinic) return reply.code(404).send({ error: "unknown clinic" });

    const tp = req.headers.traceparent;
    const ctx = newRunContext({
      tenantId: clinic.id,
      subject: { kind: claims.role === "staff" ? "staff" : "patient", id: claims.sub },
      channel: "webchat",
      traceparent: typeof tp === "string" && TRACEPARENT.test(tp) ? tp : undefined,
      log: req.log,
    });

    const out = await runAgent(deps.registry, ctx, clinic, body.data.message);
    return reply.send({ reply: out.text, handoff: out.handoff !== null, runId: ctx.runId });
  });
}
