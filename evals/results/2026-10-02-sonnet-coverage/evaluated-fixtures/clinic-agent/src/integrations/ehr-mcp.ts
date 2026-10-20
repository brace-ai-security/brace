import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";
import { Agent } from "undici";
import type { PeerCertificate } from "node:tls";
import { env } from "../config.js";
import type { ConfiguredServer } from "../tools/registry.js";
import type { ServerMeta } from "../tools/metadata-scan.js";

// EHR access goes through the EHR vendor's MCP server. Each clinic has its own OAuth client in the
// EHR, so tokens are clinic-scoped on the EHR side. Client secrets live in Secrets Manager under
// clinic-agent/ehr/<clinicId>; access tokens last 5 minutes and are cached until 30 s before expiry.

const sm = new SecretsManagerClient({ region: env.region });

function pinnedDispatcher(server: ConfiguredServer): Agent {
  const expected = server.tlsCertSha256.toLowerCase();
  return new Agent({
    connect: {
      checkServerIdentity: (_host: string, cert: PeerCertificate) => {
        const got = cert.fingerprint256.replace(/:/g, "").toLowerCase();
        return got === expected ? undefined : new Error(`EHR MCP certificate mismatch: ${got}`);
      },
    },
  });
}

type Token = { value: string; exp: number };
const tokens = new Map<string, Token>();

async function ehrToken(clinicId: string, scope: string): Promise<string> {
  const cacheKey = `${clinicId}|${scope}`;
  const hit = tokens.get(cacheKey);
  if (hit && hit.exp - 30_000 > Date.now()) return hit.value;

  const sec = await sm.send(new GetSecretValueCommand({ SecretId: `clinic-agent/ehr/${clinicId}` }));
  const { client_id, client_secret, token_url } = JSON.parse(sec.SecretString ?? "{}");
  const res = await fetch(token_url, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "client_credentials", client_id, client_secret, scope }),
  });
  if (!res.ok) throw new Error(`EHR token request failed: ${res.status}`);
  const body = (await res.json()) as { access_token: string; expires_in: number };
  tokens.set(cacheKey, { value: body.access_token, exp: Date.now() + body.expires_in * 1000 });
  return body.access_token;
}

const SCOPES = "patient.read appointment.read appointment.write";
const sessions = new Map<string, Client>();

async function session(server: ConfiguredServer, clinicId: string): Promise<Client> {
  const existing = sessions.get(clinicId);
  if (existing) return existing;
  const token = await ehrToken(clinicId, SCOPES);
  const transport = new StreamableHTTPClientTransport(new URL(server.url), {
    requestInit: {
      headers: { authorization: `Bearer ${token}`, "x-clinic-id": clinicId },
      // @ts-expect-error undici dispatcher is accepted by Node's fetch
      dispatcher: pinnedDispatcher(server),
    },
  });
  const client = new Client({ name: "clinic-agent", version: "3.4.1" });
  await client.connect(transport);
  sessions.set(clinicId, client);
  setTimeout(() => {
    sessions.delete(clinicId);
    void client.close();
  }, 4 * 60_000).unref();
  return client;
}

export function ehr(server: ConfiguredServer) {
  return {
    async catalog(): Promise<{ reportedName?: string; meta: ServerMeta }> {
      const c = await session(server, "_catalog");
      const [tools, prompts, templates] = await Promise.all([
        c.listTools(),
        c.listPrompts().catch(() => ({ prompts: [] })),
        c.listResourceTemplates().catch(() => ({ resourceTemplates: [] })),
      ]);
      return {
        reportedName: c.getServerVersion()?.name,
        meta: {
          instructions: c.getInstructions(),
          tools: tools.tools as ServerMeta["tools"],
          prompts: prompts.prompts as ServerMeta["prompts"],
          resourceTemplates: templates.resourceTemplates as ServerMeta["resourceTemplates"],
        },
      };
    },

    async call(tool: string, input: Record<string, unknown>, opts: { clinicId: string; signal: AbortSignal }): Promise<unknown> {
      const c = await session(server, opts.clinicId);
      const res = await c.callTool({ name: tool, arguments: input }, undefined, { signal: opts.signal, timeout: 15_000 });
      if (res.isError) throw new Error(`EHR tool ${tool} returned an error`);
      return res.structuredContent ?? res.content;
    },

    async getAppointment(clinicId: string, appointmentId: string, signal: AbortSignal) {
      return (await this.call("get_appointment", { appointmentId }, { clinicId, signal })) as {
        id: string;
        patientId: string;
        start: string;
        serviceCode: string;
        payerId?: string;
        depositId?: string;
        status: string;
      };
    },

    async appointmentsOn(clinicId: string, date: string, signal: AbortSignal) {
      return (await this.call("list_appointments_by_date", { date }, { clinicId, signal })) as Array<{
        id: string;
        patientId: string;
        start: string;
        phone: string;
        smsOptIn: boolean;
        locationName: string;
      }>;
    },
  };
}
export type Ehr = ReturnType<typeof ehr>;
