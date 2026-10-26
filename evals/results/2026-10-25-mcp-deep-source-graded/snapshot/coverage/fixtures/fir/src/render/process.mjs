import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';
const execute = promisify(execFile);
export async function runRenderer(request) {
  await mkdir(dirname(request.output), { recursive: true });
  const { stdout } = await execute(request.program, ['%s', request.label], { timeout: request.timeout });
  await writeFile(request.output, stdout, 'utf8');
}
