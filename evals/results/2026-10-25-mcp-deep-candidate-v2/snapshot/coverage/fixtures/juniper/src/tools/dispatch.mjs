import { status, refresh, erase } from './operations.mjs';
const operations = Object.freeze({ status, refresh, erase });
export async function dispatchTool(name, body, configuration) {
  if (!configuration.allowedTools.includes(name)) throw new Error('tool denied');
  if (!Object.hasOwn(operations, name)) throw new Error('unknown tool');
  return operations[name](body, configuration);
}
