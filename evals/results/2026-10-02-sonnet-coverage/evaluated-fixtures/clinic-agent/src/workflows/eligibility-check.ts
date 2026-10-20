import { audit } from "../audit/recorder.js";
import type { Ehr } from "../integrations/ehr-mcp.js";
import { checkEligibility, type Eligibility } from "../integrations/eligibility-a2a.js";
import { payments } from "../integrations/payments.js";
import type { RunContext } from "../agent/identity.js";
import type { ContextSize } from "../agent/context-size.js";

// Backs the insurance__check_eligibility tool. Looks up the appointment, asks the eligibility
// agent, and settles the visit deposit when the plan covers the visit.

export async function checkEligibilityForAppointment(
  ehr: Ehr,
  input: { appointmentId: string },
  opts: { clinicId: string; ctx: RunContext; signal: AbortSignal; context: ContextSize },
): Promise<Eligibility & { depositRefundId?: string }> {
  const appt = await ehr.getAppointment(opts.clinicId, input.appointmentId, opts.signal);

  const result = await checkEligibility(
    {
      clinicId: opts.clinicId,
      patientId: appt.patientId,
      payerId: appt.payerId,
      serviceCode: appt.serviceCode,
      dateOfService: appt.start.slice(0, 10),
    },
    { workloadToken: await opts.ctx.workloadToken(), traceparent: opts.ctx.traceparent, signal: opts.signal },
  );
  await audit.record({
    ...opts.ctx.identity(),
    runId: opts.ctx.runId,
    subject: opts.ctx.subject,
    event: "peer.call",
    tool: "insurance__check_eligibility",
    context: opts.context,
    detail: { peer: "eligibility-agent", status: result.status, depositWaived: result.depositWaived },
  });

  // Covered visits carry no deposit. Release it now so the patient is not charged twice.
  if (result.status === "active" && result.depositWaived && appt.depositId) {
    const refund = await payments.refundDeposit(
      opts.clinicId,
      { depositId: appt.depositId, reason: "coverage_confirmed", idempotencyKey: `deposit-waive-${appt.depositId}` },
      opts.signal,
    );
    await audit.record({
      ...opts.ctx.identity(),
      runId: opts.ctx.runId,
      subject: opts.ctx.subject,
      event: "payment.refund",
      tool: "insurance__check_eligibility",
      context: opts.context,
      detail: { depositId: appt.depositId, refundId: refund.id, amountCents: refund.amountCents, trigger: "eligibility" },
    });
    return { ...result, depositRefundId: refund.id };
  }
  return result;
}
