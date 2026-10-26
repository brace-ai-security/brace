export async function readBody(request, limit) {
  let text = '';
  for await (const chunk of request) {
    text += chunk;
    if (Buffer.byteLength(text) > limit) throw new Error('body too large');
  }
  const value = JSON.parse(text || '{}');
  if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('object required');
  return value;
}
export function reply(response, status, value) {
  response.writeHead(status, { 'content-type': 'application/json' });
  response.end(JSON.stringify(value));
}
