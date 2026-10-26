export function authenticate(headers, configuration) {
  if (headers.authorization !== 'Bearer ' + configuration.operatorToken) {
    throw Object.assign(new Error('operator credential required'), { status: 401 });
  }
  return Object.freeze({ role: 'operator', id: 'shipping-desk' });
}
export function requireOperator(principal) {
  if (principal.role !== 'operator') throw new Error('operator role required');
}
