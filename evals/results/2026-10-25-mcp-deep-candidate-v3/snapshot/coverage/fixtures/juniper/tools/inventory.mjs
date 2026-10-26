import { readFile } from 'node:fs/promises';
const name = process.argv.includes('--development') ? 'development' : 'production';
const configuration = JSON.parse(await readFile(new URL('../config/' + name + '.json', import.meta.url), 'utf8'));
const summary = {
  profile: name,
  listen: configuration.listen,
  port: configuration.port,
  transport: configuration.transportModule,
  allowedHosts: configuration.allowedHosts,
  allowedTools: configuration.allowedTools,
  dataRoot: configuration.dataRoot
};
console.log(JSON.stringify(summary, null, 2));
