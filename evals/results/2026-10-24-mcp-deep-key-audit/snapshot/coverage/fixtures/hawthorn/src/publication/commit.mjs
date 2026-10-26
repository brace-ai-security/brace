import { writeDocument } from '../storage/documents.mjs';
import { eventFor } from '../audit.mjs';
export async function publish(plan, configuration) {
  await writeDocument(configuration.dataRoot, plan.destination, plan.document, plan.text);
  const event = eventFor('document.published', plan.project, { document: plan.document });
  return { document: plan.document, event };
}
