import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, BatchGetCommand } from "@aws-sdk/lib-dynamodb";
import { env } from "../config.js";

// Stop control. Operators write halted=true on "global" or "tenant#<clinicId>" in the control table.
// The agent only reads this table; every model turn and every tool call checks it, and a watcher
// aborts in-flight work for halted scopes.
export class Halted extends Error {
  constructor(public scope: string) {
    super(`agent halted (${scope})`);
  }
}

const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({ region: env.region }));
const POLL_MS = 2000;

type Active = { tenantId: string; abort: AbortController };
const active = new Map<string, Active>();

let lastRead = 0;
let halted = new Set<string>();

async function refresh(): Promise<void> {
  const res = await ddb.send(
    new BatchGetCommand({
      RequestItems: {
        [env.controlTable]: {
          Keys: [{ pk: "global" }, ...[...new Set([...active.values()].map((a) => a.tenantId))].map((t) => ({ pk: `tenant#${t}` }))],
          ConsistentRead: true,
        },
      },
    }),
  );
  const next = new Set<string>();
  for (const item of res.Responses?.[env.controlTable] ?? []) {
    if (item.halted === true) next.add(String(item.pk));
  }
  halted = next;
  lastRead = Date.now();
}

export const killSwitch = {
  register(runId: string, tenantId: string, abort: AbortController): () => void {
    active.set(runId, { tenantId, abort });
    return () => active.delete(runId);
  },

  async assertRunning(tenantId: string): Promise<void> {
    if (Date.now() - lastRead > POLL_MS) {
      try {
        await refresh();
      } catch {
        // If the control table cannot be read, treat the agent as halted.
        throw new Halted("control-unreadable");
      }
    }
    if (halted.has("global")) throw new Halted("global");
    if (halted.has(`tenant#${tenantId}`)) throw new Halted(`tenant#${tenantId}`);
  },

  startWatcher(): NodeJS.Timeout {
    return setInterval(async () => {
      try {
        await refresh();
      } catch {
        halted = new Set(["global"]);
      }
      for (const [runId, a] of active) {
        if (halted.has("global") || halted.has(`tenant#${a.tenantId}`)) {
          a.abort.abort(new Halted(halted.has("global") ? "global" : `tenant#${a.tenantId}`));
          active.delete(runId);
        }
      }
    }, POLL_MS);
  },
};
