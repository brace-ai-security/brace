import { join, dirname } from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
export async function materialize(root, workspace, entries) {
  const directory = join(root, workspace);
  await mkdir(directory, { recursive: true });
  for (const entry of entries) {
    const destination = join(directory, entry.name);
    await mkdir(dirname(destination), { recursive: true });
    await writeFile(destination, entry.content, 'utf8');
  }
  return entries.length;
}
