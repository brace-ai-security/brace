import { join } from 'node:path';
export function makeRenderRequest(configuration, workspace, label) {
  return {
    program: configuration.renderProgram,
    label,
    output: join(configuration.receiptRoot, workspace + '.txt'),
    timeout: 2000
  };
}
