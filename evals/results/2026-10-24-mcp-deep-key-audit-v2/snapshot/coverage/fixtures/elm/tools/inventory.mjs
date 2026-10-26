import { readFile } from 'node:fs/promises';
const manifest = JSON.parse(await readFile(new URL('../dist/launch-manifest.json', import.meta.url), 'utf8'));
const base = JSON.parse(await readFile(new URL('../' + manifest.base, import.meta.url), 'utf8'));
const overlayName = process.argv.includes('--development') ? 'config/development.json' : manifest.overlay;
const overlay = JSON.parse(await readFile(new URL('../' + overlayName, import.meta.url), 'utf8'));
const merged = { ...base, ...overlay };
console.log(JSON.stringify({
  implementation: manifest.implementation,
  overlay: overlayName,
  router: merged.routeModule,
  listen: merged.listen,
  port: merged.port,
  workspaceRoot: merged.workspaceRoot,
  receiptRoot: merged.receiptRoot
}, null, 2));
