export function inspectSource(value, allowedHosts) {
  if (typeof value !== 'string') throw new Error('source URL required');
  const url = new URL(value);
  if (url.protocol !== 'https:' && url.protocol !== 'http:') throw new Error('unsupported protocol');
  if (url.username || url.password) throw new Error('URL credentials forbidden');
  if (!allowedHosts.includes(url.hostname)) throw new Error('source host denied');
  if (url.port) throw new Error('custom source ports forbidden');
  return Object.freeze({ url: url.href, host: url.hostname });
}
