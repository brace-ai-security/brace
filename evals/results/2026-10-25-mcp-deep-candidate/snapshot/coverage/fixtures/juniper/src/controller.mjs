import { projectId, documentId, documentText } from './validation.mjs';
import { authorizeProject } from './policy.mjs';
import { createPublication } from './publication/plan.mjs';
import { publish } from './publication/commit.mjs';
import { inspectSource } from './source/policy.mjs';
import { collectSource } from './source/collect.mjs';
import { dispatchTool } from './tools/dispatch.mjs';
export async function handle(route, body, actor, configuration, transport) {
  const project = projectId(body.project);
  authorizeProject(actor, project);
  if (route === '/documents/publish') {
    const document = documentId(body.document);
    const text = documentText(body.text);
    const plan = createPublication(project, document, text, body);
    return publish(plan, configuration);
  }
  if (route === '/sources/collect') {
    const approved = inspectSource(body.url, configuration.allowedHosts);
    return collectSource(project, approved, body, configuration, transport);
  }
  if (route === '/tools/run') return dispatchTool(body.tool, body, configuration);
  throw Object.assign(new Error('unknown route'), { status: 404 });
}
