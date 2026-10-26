export async function readJson(request) {
  let text = '';
  for await (const chunk of request) {
    text += chunk;
    if (Buffer.byteLength(text) > 32768) throw new Error('body too large');
  }
  const body = JSON.parse(text || '{}');
  if (!body || Array.isArray(body) || typeof body !== 'object') throw new Error('object required');
  return body;
}
export function respond(response, status, body) {
  response.writeHead(status, { 'content-type': 'application/json' });
  response.end(JSON.stringify(body));
}
