import { rm } from 'node:fs/promises';
import { join } from 'node:path';
import { projectId } from '../validation.mjs';
export async function status(body) {
  return { project: projectId(body.project), state: 'ready' };
}
export async function refresh(body) {
  return { project: projectId(body.project), queued: false, refreshed: true };
}
export async function erase(body, configuration) {
  const project = projectId(body.project);
  await rm(join(configuration.dataRoot, project), { recursive: true, force: true });
  return { project, erased: true };
}
