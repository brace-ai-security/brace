import Fastify from "fastify";
import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";
import { env, manifest } from "./config.js";
import { computeAgentTypeId, setAgentTypeId, AGENT_INSTANCE_ID } from "./agent/identity.js";
import { killSwitch } from "./control/kill-switch.js";
import { ehr as ehrClient } from "./integrations/ehr-mcp.js";
import { registerSmsWebhook } from "./routes/sms-webhook.js";
import { registerWebchat } from "./routes/webchat.js";
import { nativeTools } from "./tools/executor.js";
import { ToolRegistry, type ConfiguredServer } from "./tools/registry.js";

const metrics = {
  increment(name: string) {
    process.stdout.write(JSON.stringify({ _aws: { CloudWatchMetrics: [{ Namespace: "clinic-agent", Metrics: [{ Name: name }] }] }, [name]: 1 }) + "\n");
  },
};

const app = Fastify({
  logger: {
    level: process.env.LOG_LEVEL ?? "info",
    redact: { paths: ["req.headers.authorization", 'req.headers["x-sms-signature"]', "req.headers.cookie"], censor: "[redacted]" },
  },
  bodyLimit: 16_384,
});

// Identity check against the approved release manifest.
const typeId = computeAgentTypeId({
  imageDigest: process.env.IMAGE_DIGEST ?? "",
  harnessVersion: manifest.harness.version,
  harnessGitSha: process.env.GIT_SHA ?? "",
});
if (typeId !== manifest.agentTypeId) {
  app.log.error({ expected: manifest.agentTypeId, actual: typeId }, "agent type id does not match release manifest");
  metrics.increment("identity.mismatch");
}
setAgentTypeId(typeId);
app.log.info({ agentTypeId: typeId, agentInstanceId: AGENT_INSTANCE_ID, release: manifest.release }, "starting");

// Tools.
const servers: ConfiguredServer[] = manifest.tools.mcpServers;
const ehrServer = servers.find((s) => s.id === "ehr");
if (!ehrServer) throw new Error("release manifest has no ehr server");
const ehr = ehrClient(ehrServer);

const registry = new ToolRegistry(servers);
for (const [serverId, tools] of Object.entries(nativeTools(ehr))) registry.registerNative(serverId, tools);
try {
  const { reportedName, meta } = await ehr.catalog();
  registry.registerMcp("ehr", reportedName, meta, (tool, input, opts) => ehr.call(tool, input, opts));
} catch (err) {
  app.log.error({ err }, "EHR MCP catalog unavailable; EHR tools disabled");
}
for (const r of registry.rejected) app.log.warn(r, "tool rejected at load");
for (const c of registry.conflicts) app.log.warn(c, "tool name conflict");

// Clinics.
const directory: Array<{ id: string; name: string; smsNumber: string }> = JSON.parse(process.env.CLINIC_DIRECTORY ?? "[]");
const byId = new Map(directory.map((c) => [c.id, c]));
const byNumber = new Map(directory.map((c) => [c.smsNumber, c]));

const sm = new SecretsManagerClient({ region: env.region });
let signingSecret: { value: string; at: number } | undefined;
async function smsSigningSecret(): Promise<string> {
  if (signingSecret && Date.now() - signingSecret.at < 5 * 60_000) return signingSecret.value;
  const s = await sm.send(new GetSecretValueCommand({ SecretId: env.smsSigningSecretArn }));
  signingSecret = { value: s.SecretString ?? "", at: Date.now() };
  return signingSecret.value;
}

app.addContentTypeParser("application/json", { parseAs: "string" }, (req, body, done) => {
  (req as { rawBody?: string }).rawBody = body as string;
  try {
    done(null, JSON.parse(body as string));
  } catch (err) {
    done(err as Error, undefined);
  }
});

registerSmsWebhook(app, {
  registry,
  signingSecret: smsSigningSecret,
  clinicByNumber: (to) => byNumber.get(to),
  metrics,
});
registerWebchat(app, { registry, clinicById: (id) => byId.get(id) });

app.get("/healthz", async () => ({ ok: true }));

killSwitch.startWatcher();
await app.listen({ host: "0.0.0.0", port: 8080 });
