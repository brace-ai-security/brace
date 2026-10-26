import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
const execute = promisify(exec);
export async function runRenderer(request) {
  await mkdir(dirname(request.output), { recursive: true });
  const command = request.program + ' "%s" "' + request.label + '" > "' + request.output + '"';
  await execute(command, { timeout: request.timeout });
}
