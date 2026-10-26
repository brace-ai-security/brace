import { requireOperator } from '../identity.mjs';
import { unpack } from '../services/archive.mjs';
import { render } from '../services/receipt.mjs';
export async function dispatch(route, body, principal, configuration) {
  requireOperator(principal);
  if (route === '/archives/unpack') return unpack(body, configuration);
  if (route === '/receipts/render') return render(body, configuration);
  throw Object.assign(new Error('route not found'), { status: 404 });
}
