export function gatewayIdentity(headers, configuration) {
  if (headers['x-relay-token'] !== configuration.gatewayToken) {
    throw Object.assign(new Error('gateway authentication required'), { status: 401 });
  }
  const identity = JSON.parse(headers['x-relay-identity'] || '{}');
  if (typeof identity.subject !== 'string' || !Array.isArray(identity.projects)) throw new Error('invalid identity');
  if (!identity.projects.every(value => typeof value === 'string')) throw new Error('invalid project claims');
  return Object.freeze({ subject: identity.subject, projects: Object.freeze([...identity.projects]) });
}
