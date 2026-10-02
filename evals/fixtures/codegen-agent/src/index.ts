import { createHmac, timingSafeEqual } from "node:crypto";
import Fastify from "fastify";
import { Queue } from "bullmq";
import { context, propagation, trace } from "@opentelemetry/api";
import { SecretsManagerClient, GetSecretValueCommand } from "@aws-sdk/client-secrets-manager";
import { computeAgentTypeId, newInstanceId, type RunContext } from "./identity.js";
import type { RunJob } from "./worker.js";

const TRIGGER_LABEL = "issuesmith";
const MAX_BODY = 256 * 1024;

const queue = new Queue<RunJob>("issuesmith-runs", { connection: { url: process.env.REDIS_URL } });
const secrets = new SecretsManagerClient({});
const tracer = trace.getTracer("issuesmith");

const webhookSecret = (
  await secrets.send(new GetSecretValueCommand({ SecretId: "issuesmith/github-webhook-secret" }))
).SecretString!;

function validSignature(raw: Buffer, header: string | undefined): boolean {
  if (!header?.startsWith("sha256=")) return false;
  const expected = Buffer.from(createHmac("sha256", webhookSecret).update(raw).digest("hex"));
  const given = Buffer.from(header.slice("sha256=".length));
  return expected.length === given.length && timingSafeEqual(expected, given);
}

const app = Fastify({ bodyLimit: MAX_BODY });
app.addContentTypeParser("application/json", { parseAs: "buffer" }, (_req, body, done) => done(null, body));

app.post("/webhooks/github", async (req, reply) => {
  const raw = req.body as Buffer;
  if (!validSignature(raw, req.headers["x-hub-signature-256"] as string | undefined)) {
    return reply.code(401).send();
  }
  if (req.headers["x-github-event"] !== "issues") return reply.code(204).send();

  const payload = JSON.parse(raw.toString("utf8"));
  if (payload.action !== "labeled" || payload.label?.name !== TRIGGER_LABEL) return reply.code(204).send();

  const [owner, name] = String(payload.repository.full_name).split("/");
  const installationId = Number(payload.installation.id);

  await tracer.startActiveSpan("issuesmith.enqueue", async (span) => {
    const carrier: Record<string, string> = {};
    propagation.inject(context.active(), carrier);
    const ctx: RunContext = Object.freeze({
      tenant: `${installationId}/${owner}/${name}`,
      installationId,
      repo: { owner, name },
      issueNumber: Number(payload.issue.number),
      accountableParty: "team:developer-productivity",
      operationalOwner: "oncall:devprod-agents",
      delegatedSubject: String(payload.sender.login),
      agentTypeId: computeAgentTypeId("implementer"),
      agentInstanceId: newInstanceId(),
      traceparent: carrier.traceparent,
    });
    await queue.add(
      "run",
      { ctx, issue: { title: String(payload.issue.title), body: String(payload.issue.body ?? "") } },
      { jobId: ctx.agentInstanceId, attempts: 1, removeOnComplete: 1000 },
    );
    span.end();
  });
  return reply.code(202).send();
});

await app.listen({ host: "0.0.0.0", port: 8080 });
