import type Anthropic from "@anthropic-ai/sdk";
import { allowlist, policy } from "../config.js";
import { audit, AuditUnavailable, redactPhi } from "../audit/recorder.js";
import { BudgetExceeded, type RunBudget } from "../agent/budget.js";
import type { ContextSize } from "../agent/context-size.js";
import { AGENT_INSTANCE_ID, type RunContext } from "../agent/identity.js";
import { Halted, killSwitch } from "../control/kill-switch.js";
import type { Ehr } from "../integrations/ehr-mcp.js";
import { payments } from "../integrations/payments.js";
import { render, sms, TEMPLATES, type TemplateId } from "../integrations/sms.js";
import { checkEligibilityForAppointment } from "../workflows/eligibility-check.js";
import { checkApproval, requestApproval } from "./approvals.js";
import type { RegisteredTool, ToolRegistry } from "./registry.js";

export interface Decision {
  contextSize: ContextSize;
  budget: RunBudget;
}

const ALLOWED = new Set(allowlist.tools.map((t) => t.tool));
// Arguments the harness consumes itself; they are never forwarded to a tool.
const CONTROL_ARGS = new Set(["approvalId", "clinicId"]);

function toolResult(id: string, content: unknown, isError = false): Anthropic.ToolResultBlockParam {
  return { type: "tool_result", tool_use_id: id, content: JSON.stringify(content), is_error: isError };
}

function summarize(tool: string, args: Record<string, unknown>): string {
  return `${tool}(${Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ")})`.slice(0, 500);
}

export async function executeTool(
  registry: ToolRegistry,
  ctx: RunContext,
  call: Anthropic.ToolUseBlock,
  d: Decision,
): Promise<Anthropic.ToolResultBlockParam> {
  const input = (call.input ?? {}) as Record<string, unknown>;
  const base = {
    ...ctx.identity(),
    runId: ctx.runId,
    subject: ctx.subject,
    tool: call.name,
    toolUseId: call.id,
    policyVersion: policy.version,
    context: d.contextSize,
  };
  const deny = async (reason: string) => {
    await audit.record({ ...base, event: "tool.denied", reason });
    return toolResult(call.id, { error: "denied", reason }, true);
  };

  if (!ALLOWED.has(call.name)) return deny("not_allowlisted");
  const tool = registry.get(call.name);
  if (!tool) return deny("not_registered");

  await killSwitch.assertRunning(ctx.tenantId);
  await d.budget.toolCall(call.name);

  // Front-desk staff working one clinic's chat can act for a sibling clinic in the group.
  const clinicId = typeof input.clinicId === "string" && input.clinicId ? input.clinicId : ctx.tenantId;
  const args = Object.fromEntries(Object.entries(input).filter(([k]) => !CONTROL_ARGS.has(k)));

  let approvalId: string | undefined;
  if (policy.highImpactTools.includes(call.name)) {
    if (typeof input.approvalId !== "string") {
      const rec = await requestApproval({
        tool: call.name,
        tenantId: clinicId,
        agentInstanceId: AGENT_INSTANCE_ID,
        runId: ctx.runId,
        args,
        summary: summarize(call.name, args),
      });
      await audit.record({ ...base, event: "tool.approval_requested", approvalId: rec.id });
      return toolResult(call.id, { status: "pending_approval", approvalId: rec.id, expiresAt: rec.expiresAt });
    }
    const check = await checkApproval({ approvalId: input.approvalId, tool: call.name, tenantId: clinicId, args });
    if (!check.ok) return deny(check.reason);
    approvalId = check.approval.id;
  }

  try {
    const raw = await tool.invoke(args, { clinicId, signal: d.budget.signal, runCtx: ctx, context: d.contextSize });
    ctx.log.info({ tool: call.name, toolUseId: call.id, clinicId, result: raw }, "tool result");
    const safe = redactPhi(raw);
    await audit.record({ ...base, event: "tool.executed", approvalId, detail: { clinicId } });
    return toolResult(call.id, safe);
  } catch (err) {
    if (err instanceof Halted || err instanceof BudgetExceeded || err instanceof AuditUnavailable) throw err;
    await audit.record({ ...base, event: "tool.failed", approvalId, reason: (err as Error).message.slice(0, 300) });
    return toolResult(call.id, { error: "tool_failed" }, true);
  }
}

type Native = Omit<RegisteredTool, "key" | "serverId">;

export function nativeTools(ehr: Ehr): Record<string, Native[]> {
  const contact = async (clinicId: string, patientId: string, signal: AbortSignal) =>
    (await ehr.call("get_patient_contact", { patientId }, { clinicId, signal })) as { phone: string; smsOptIn: boolean; firstName: string };

  return {
    payments: [
      {
        name: "refund_deposit",
        definition: {
          name: "payments__refund_deposit",
          description: "Refund a patient's appointment deposit. Requires staff approval.",
          input_schema: {
            type: "object",
            properties: {
              depositId: { type: "string" },
              reason: { type: "string", enum: ["no_show_waived", "clinic_cancelled", "billing_error"] },
              approvalId: { type: "string" },
            },
            required: ["depositId", "reason"],
          },
        },
        invoke: async (a, o) =>
          payments.refundDeposit(o.clinicId, { depositId: String(a.depositId), reason: String(a.reason), idempotencyKey: `refund-${a.depositId}` }, o.signal),
      },
    ],
    sms: [
      {
        name: "send_to_patient",
        definition: {
          name: "sms__send_to_patient",
          description: "Send a templated SMS to the phone number on the patient's record.",
          input_schema: {
            type: "object",
            properties: {
              patientId: { type: "string" },
              template: { type: "string", enum: Object.keys(TEMPLATES) },
              vars: { type: "object", additionalProperties: { type: "string" } },
            },
            required: ["patientId", "template"],
          },
        },
        invoke: async (a, o) => {
          const c = await contact(o.clinicId, String(a.patientId), o.signal);
          if (!c.smsOptIn) throw new Error("patient has not opted in to SMS");
          const body = render(a.template as TemplateId, { firstName: c.firstName, ...((a.vars as Record<string, string>) ?? {}) });
          return sms.send(o.clinicId, c.phone, body, o.signal);
        },
      },
      {
        name: "send_freeform",
        definition: {
          name: "sms__send_freeform",
          description: "Send a non-template SMS to the patient's phone on record. Requires staff approval.",
          input_schema: {
            type: "object",
            properties: { patientId: { type: "string" }, body: { type: "string", maxLength: 320 }, approvalId: { type: "string" } },
            required: ["patientId", "body"],
          },
        },
        invoke: async (a, o) => {
          const c = await contact(o.clinicId, String(a.patientId), o.signal);
          if (!c.smsOptIn) throw new Error("patient has not opted in to SMS");
          return sms.send(o.clinicId, c.phone, String(a.body).slice(0, 320), o.signal);
        },
      },
    ],
    insurance: [
      {
        name: "check_eligibility",
        definition: {
          name: "insurance__check_eligibility",
          description: "Check whether the patient's insurance covers an appointment.",
          input_schema: { type: "object", properties: { appointmentId: { type: "string" } }, required: ["appointmentId"] },
        },
        invoke: async (a, o) =>
          checkEligibilityForAppointment(ehr, { appointmentId: String(a.appointmentId) }, {
            clinicId: o.clinicId,
            ctx: o.runCtx as RunContext,
            signal: o.signal,
            context: o.context,
          }),
      },
    ],
  };
}
