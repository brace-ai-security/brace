import { createRemoteJWKSet, decodeProtectedHeader, jwtVerify } from "jose";
import { randomUUID } from "node:crypto";
import { z } from "zod";
import { env } from "../config.js";

// Insurance-eligibility peer agent, reached over A2A (JSON-RPC message/send).
//
// Authority: for each call we exchange the agent's workload token for a token that is only good
// for the eligibility agent (audience), only for read (scope eligibility:read), and only for this
// clinic and patient (RFC 8693 token exchange, with the patient as the subject). The eligibility
// agent cannot book, cancel, or refund anything, so asking it to act gains this agent nothing.
//
// Answers come back as a signed attestation (JWS) inside a data part.

const Eligibility = z
  .object({
    status: z.enum(["active", "inactive", "unknown"]),
    planName: z.string().max(120).optional(),
    copayCents: z.number().int().nonnegative().optional(),
    depositWaived: z.boolean().default(false),
    checkedAt: z.string().datetime(),
  })
  .strict();
export type Eligibility = z.infer<typeof Eligibility>;

const Rpc = z.object({
  jsonrpc: z.literal("2.0"),
  id: z.string(),
  result: z.object({
    kind: z.literal("message"),
    parts: z.array(z.object({ kind: z.literal("data"), data: z.object({ attestation: z.string().max(8192) }) })).min(1),
  }),
});

async function exchangeToken(workloadToken: string, clinicId: string, patientId: string): Promise<string> {
  const res = await fetch(env.tokenExchangeUrl, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
      subject_token: workloadToken,
      subject_token_type: "urn:ietf:params:oauth:token-type:jwt",
      audience: "eligibility-agent",
      scope: `eligibility:read clinic:${clinicId} patient:${patientId}`,
      requested_token_type: "urn:ietf:params:oauth:token-type:access_token",
    }),
  });
  if (!res.ok) throw new Error(`token exchange failed: ${res.status}`);
  return ((await res.json()) as { access_token: string }).access_token;
}

export async function checkEligibility(
  req: { clinicId: string; patientId: string; payerId?: string; serviceCode: string; dateOfService: string },
  opts: { workloadToken: string; traceparent: string; signal: AbortSignal },
): Promise<Eligibility> {
  const token = await exchangeToken(opts.workloadToken, req.clinicId, req.patientId);
  const requestId = randomUUID();
  const res = await fetch(env.eligibilityUrl, {
    method: "POST",
    signal: opts.signal,
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json", traceparent: opts.traceparent },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: requestId,
      method: "message/send",
      params: {
        message: {
          role: "user",
          messageId: requestId,
          parts: [{ kind: "data", data: { type: "eligibility.check", ...req } }],
        },
      },
    }),
  });
  if (!res.ok) throw new Error(`eligibility peer error: ${res.status}`);
  const text = await res.text();
  if (text.length > 64_000) throw new Error("eligibility response too large");
  const rpc = Rpc.parse(JSON.parse(text));

  const attestation = rpc.result.parts[0]!.data.attestation;
  const header = decodeProtectedHeader(attestation);
  if (!header.jku) throw new Error("attestation missing key set url");
  const keys = createRemoteJWKSet(new URL(header.jku));
  const { payload } = await jwtVerify(attestation, keys, {
    issuer: env.eligibilityIssuer,
    audience: "clinic-agent",
    maxTokenAge: "5m",
    algorithms: ["ES256"],
  });
  return Eligibility.parse(payload.eligibility);
}
