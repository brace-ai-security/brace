import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";
import { env } from "../config.js";

// Deposit refunds through the payments provider. Each clinic is a connected account with its own
// restricted key (refunds on deposits only), stored at clinic-agent/payments/<clinicId>.
// The provider enforces Idempotency-Key for 24 hours.

const sm = new SecretsManagerClient({ region: env.region });
const BASE = process.env.PAYMENTS_API ?? "https://api.payments-provider.example/v2";

async function key(clinicId: string): Promise<string> {
  const s = await sm.send(new GetSecretValueCommand({ SecretId: `clinic-agent/payments/${clinicId}` }));
  return JSON.parse(s.SecretString ?? "{}").restricted_key;
}

export interface Refund {
  id: string;
  depositId: string;
  amountCents: number;
  status: "pending" | "succeeded" | "failed";
}

export const payments = {
  async refundDeposit(
    clinicId: string,
    req: { depositId: string; reason: string; idempotencyKey: string },
    signal?: AbortSignal,
  ): Promise<Refund> {
    const res = await fetch(`${BASE}/deposits/${encodeURIComponent(req.depositId)}/refunds`, {
      method: "POST",
      signal,
      headers: {
        authorization: `Bearer ${await key(clinicId)}`,
        "content-type": "application/json",
        "idempotency-key": req.idempotencyKey,
      },
      body: JSON.stringify({ reason: req.reason, metadata: { source: "clinic-agent" } }),
    });
    if (!res.ok) throw new Error(`refund failed: ${res.status}`);
    return (await res.json()) as Refund;
  },
};
