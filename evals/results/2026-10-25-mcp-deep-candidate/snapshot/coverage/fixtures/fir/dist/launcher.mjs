import manifest from './launch-manifest.json' with { type: 'json' };
import { loadConfiguration } from '../src/configuration.mjs';
const configuration = await loadConfiguration(manifest);
const implementation = await import(manifest.implementation);
await implementation.start(configuration);
