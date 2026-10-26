import { join, dirname, resolve, relative, isAbsolute } from 'node:path';
import { mkdir, writeFile } from 'node:fs/promises';
export async function materialize(root, workspace, entries) {
  const directory = resolve(root, workspace);
  const destinations = entries.map(entry => {
    const destination = resolve(directory, entry.name);
    const suffix = relative(directory, destination);
    if (!suffix || suffix === '..' || suffix.startsWith('../') || isAbsolute(suffix)) throw new Error('entry outside workspace');
    return { destination, content: entry.content };
  });
  await mkdir(directory, { recursive: true });
  for (const entry of destinations) {
    await mkdir(dirname(entry.destination), { recursive: true });
    await writeFile(entry.destination, entry.content, 'utf8');
  }
  return entries.length;
}
