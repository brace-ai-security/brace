import pino from "pino";
import { manifest } from "../config.js";
import { audit } from "../audit/recorder.js";
import { computeAgentTypeId, newRunContext, setAgentTypeId } from "../agent/identity.js";
import { Halted, killSwitch } from "../control/kill-switch.js";
import { ehr as ehrClient } from "../integrations/ehr-mcp.js";
import { render, sms } from "../integrations/sms.js";

// Daily reminder job (Kubernetes CronJob). Templated reminders only; no model involved.
const log = pino({ level: "info" });

const directory: Array<{ id: string; name: string }> = JSON.parse(process.env.CLINIC_DIRECTORY ?? "[]");
setAgentTypeId(
  computeAgentTypeId({
    imageDigest: process.env.IMAGE_DIGEST ?? "",
    harnessVersion: manifest.harness.version,
    harnessGitSha: process.env.GIT_SHA ?? "",
  }),
);

const ehr = ehrClient(manifest.tools.mcpServers.find((s: { id: string }) => s.id === "ehr"));
const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);

for (const clinic of directory) {
  const ctx = newRunContext({ tenantId: clinic.id, subject: { kind: "system", id: "reminders-cron" }, channel: "reminder", log });
  const abort = new AbortController();
  const unregister = killSwitch.register(ctx.runId, clinic.id, abort);
  try {
    await killSwitch.assertRunning(clinic.id);
    const appts = await ehr.appointmentsOn(clinic.id, tomorrow, abort.signal);
    for (const a of appts) {
      if (!a.smsOptIn) continue;
      await killSwitch.assertRunning(clinic.id);
      const when = new Date(a.start).toLocaleString("en-US", { weekday: "short", hour: "numeric", minute: "2-digit" });
      const res = await sms.send(clinic.id, a.phone, render("reminder", { firstName: "", when, location: a.locationName }), abort.signal);
      await audit.record({
        ...ctx.identity(),
        runId: ctx.runId,
        subject: ctx.subject,
        event: "reminder.sent",
        tool: "sms__send_to_patient",
        // Scheduled, templated send: no model decided this action.
        context: { tokens: null, status: "unavailable", method: "no_model_decision", cachedInputTokens: null, compacted: false },
        detail: { appointmentId: a.id, messageId: res.messageId },
      });
    }
  } catch (err) {
    if (err instanceof Halted) {
      log.warn({ clinic: clinic.id, scope: err.scope }, "reminders halted");
      break;
    }
    log.error({ clinic: clinic.id, err: (err as Error).message }, "reminder run failed");
    await audit.record({ ...ctx.identity(), runId: ctx.runId, subject: ctx.subject, event: "run.stopped", reason: (err as Error).message.slice(0, 200) });
  } finally {
    unregister();
  }
}
process.exit(0);
