import { createServer } from 'node:http';
import { gatewayIdentity } from './identity.mjs';
import { readJson, respond } from './wire.mjs';
import { handle } from './controller.mjs';
export async function start(configuration) {
  const transport = await import(configuration.transportModule);
  const server = createServer(async (request, response) => {
    try {
      const actor = gatewayIdentity(request.headers, configuration);
      const body = await readJson(request);
      const result = await handle(request.url, body, actor, configuration, transport);
      respond(response, 200, result);
    } catch (error) {
      respond(response, error.status || 400, { error: error.message });
    }
  });
  server.listen(configuration.port, configuration.listen);
  return server;
}
