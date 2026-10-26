import { requireOperator } from '../identity.mjs';
export async function dispatch(route, body, principal) {
  requireOperator(principal);
  if (route !== '/health') throw new Error('route not found');
  return { status: 'ok', note: 'compatibility transport' };
}
