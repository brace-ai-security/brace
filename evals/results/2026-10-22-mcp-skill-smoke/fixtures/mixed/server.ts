// Synthetic source-only fixture. Deployment and upstream token verifier are external.
import { requireBearerAuth } from '@modelcontextprotocol/express';
import { verifiedJwtClaims } from './identity';
export const auth = requireBearerAuth({
  verifier: { async verifyAccessToken(token) {
    const claims = await verifiedJwtClaims(token);
    return { token, clientId: claims.azp, scopes: claims.scopes, expiresAt: claims.exp };
  } },
  requiredScopes: ['invoices:read'],
});
export function invoiceForTenant(authenticatedTenant, requestedTenant, store) {
  if (authenticatedTenant !== requestedTenant) throw new Error('tenant forbidden');
  return store.readTenant(requestedTenant);
}
export const validationOptions = { maxBodySize: '4mb' };
