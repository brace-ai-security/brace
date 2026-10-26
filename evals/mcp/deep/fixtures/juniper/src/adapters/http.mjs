import http from 'node:http';
import https from 'node:https';
export function retrieve(value) {
  const url = new URL(value);
  if (url.protocol !== 'http:' && url.protocol !== 'https:') throw new Error('unsupported transfer protocol');
  const protocol = url.protocol === 'https:' ? https : http;
  return new Promise((resolve, reject) => {
    const request = protocol.get(url, response => {
      let text = '';
      response.setEncoding('utf8');
      response.on('data', chunk => {
        text += chunk;
        if (Buffer.byteLength(text) > 16384) request.destroy(new Error('source too large'));
      });
      response.on('end', () => resolve({ status: response.statusCode, text }));
      response.on('error', reject);
    });
    request.setTimeout(2000, () => request.destroy(new Error('source timeout')));
    request.on('error', reject);
  });
}
