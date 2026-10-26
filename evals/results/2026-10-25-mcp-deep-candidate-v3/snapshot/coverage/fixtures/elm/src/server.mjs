import { createServer } from 'node:http';
import { readBody, reply } from './wire.mjs';
import { authenticate } from './identity.mjs';
export async function start(configuration) {
  const { dispatch } = await import(configuration.routeModule);
  const server = createServer(async (request, response) => {
    try {
      const principal = authenticate(request.headers, configuration);
      const body = await readBody(request, configuration.maxBodyBytes);
      const result = await dispatch(request.url, body, principal, configuration);
      reply(response, 200, result);
    } catch (error) {
      reply(response, error.status || 400, { error: error.message });
    }
  });
  server.listen(configuration.port, configuration.listen);
  return server;
}
