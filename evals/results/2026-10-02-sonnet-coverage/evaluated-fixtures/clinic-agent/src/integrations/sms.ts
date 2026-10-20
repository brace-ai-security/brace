import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";
import { env } from "../config.js";

// Outbound SMS. One sending number per clinic. Templates are the only bodies sms__send_to_patient
// can send; free-form text goes through sms__send_freeform, which needs approval.

const sm = new SecretsManagerClient({ region: env.region });
const BASE = process.env.SMS_API ?? "https://api.sms-provider.example/v1";

export const TEMPLATES = {
  reminder: "Hi {firstName}, reminder: {when} at {location}. Reply Y to confirm or call us to change.",
  booked: "Hi {firstName}, you're booked for {when} at {location}.",
  rescheduled: "Hi {firstName}, your appointment moved to {when} at {location}.",
  cancelled: "Hi {firstName}, your appointment on {when} is cancelled.",
} as const;
export type TemplateId = keyof typeof TEMPLATES;

export function render(id: TemplateId, vars: Record<string, string>): string {
  return TEMPLATES[id].replace(/\{(\w+)\}/g, (_, k: string) => (vars[k] ?? "").replace(/[^\p{L}\p{N} .,:'/-]/gu, "").slice(0, 60));
}

async function creds(clinicId: string): Promise<{ token: string; from: string }> {
  const s = await sm.send(new GetSecretValueCommand({ SecretId: `clinic-agent/sms/${clinicId}` }));
  const v = JSON.parse(s.SecretString ?? "{}");
  return { token: v.api_token, from: v.from_number };
}

export const sms = {
  async send(clinicId: string, to: string, body: string, signal?: AbortSignal): Promise<{ messageId: string }> {
    const c = await creds(clinicId);
    const res = await fetch(`${BASE}/messages`, {
      method: "POST",
      signal,
      headers: { authorization: `Bearer ${c.token}`, "content-type": "application/json" },
      body: JSON.stringify({ from: c.from, to, body }),
    });
    if (!res.ok) throw new Error(`sms send failed: ${res.status}`);
    return (await res.json()) as { messageId: string };
  },
};
