import { makeTransfer } from './transfer.mjs';
import { eventFor } from '../audit.mjs';
export async function collectSource(project, approved, body, configuration, transport) {
  const transfer = makeTransfer(project, approved, body);
  const result = await transport.retrieve(transfer.url);
  return {
    text: result.text,
    event: eventFor('source.collected', project, { host: approved.host }),
    status: result.status
  };
}
