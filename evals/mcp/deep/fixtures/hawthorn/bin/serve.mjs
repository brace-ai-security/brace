import { readFile } from 'node:fs/promises';
import { start } from '../src/server.mjs';
const configuration = JSON.parse(await readFile(new URL('../config/production.json', import.meta.url), 'utf8'));
await start(configuration);
