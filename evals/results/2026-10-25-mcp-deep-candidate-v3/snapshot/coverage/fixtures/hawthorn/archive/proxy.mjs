import http from 'node:http';
export function rawProxy(request, response) {
  http.get(request.headers['x-target'], upstream => upstream.pipe(response));
}
export function rawIdentity(headers) {
  return { subject: headers['x-user'], projects: ['*'] };
}
