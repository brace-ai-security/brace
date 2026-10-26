import { decodeEntries, workspaceName } from '../validation.mjs';
import { materialize } from '../storage/files.mjs';
export async function unpack(body, configuration) {
  const workspace = workspaceName(body.workspace);
  const entries = decodeEntries(body.entries, configuration.maxEntries);
  const count = await materialize(configuration.workspaceRoot, workspace, entries);
  return { workspace, count };
}
