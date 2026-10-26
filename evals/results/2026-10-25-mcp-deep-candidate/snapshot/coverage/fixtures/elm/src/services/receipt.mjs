import { workspaceName, receiptLabel } from '../validation.mjs';
import { makeRenderRequest } from '../render/request.mjs';
import { runRenderer } from '../render/process.mjs';
export async function render(body, configuration) {
  const workspace = workspaceName(body.workspace);
  const label = receiptLabel(body.label);
  const request = makeRenderRequest(configuration, workspace, label);
  await runRenderer(request);
  return { workspace, rendered: true };
}
