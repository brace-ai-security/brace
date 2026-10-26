import { readFile } from 'node:fs/promises';
export async function loadConfiguration(manifest) {
  const read = async name => JSON.parse(await readFile(new URL('../' + name, import.meta.url), 'utf8'));
  const base = await read(manifest.base);
  const overlay = await read(manifest.overlay);
  const configuration = Object.freeze({ ...base, ...overlay });
  if (!Number.isInteger(configuration.port)) throw new Error('port required');
  if (!configuration.workspaceRoot.startsWith('/')) throw new Error('absolute workspace root required');
  if (!configuration.routeModule.startsWith('./routes/')) throw new Error('route outside distribution');
  return configuration;
}
