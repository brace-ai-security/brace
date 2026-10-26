export { workspaceName, receiptLabel } from './validation.mjs';
export const protocolVersion = 1;
export function capabilities() {
  return Object.freeze(['archives', 'receipts']);
}
