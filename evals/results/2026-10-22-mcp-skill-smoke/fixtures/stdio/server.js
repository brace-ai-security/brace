// Synthetic source-only fixture; do not execute.
import { realpath } from 'node:fs/promises';
import { relative, isAbsolute } from 'node:path';
export async function allowedPath(root, requested) {
  const base = await realpath(root);
  const target = await realpath(requested);
  const rel = relative(base, target);
  if (rel === '..' || rel.startsWith('../') || isAbsolute(rel)) throw new Error('outside root');
  return target;
}
