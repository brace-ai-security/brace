import {randomUUID} from 'node:crypto';
export function register(app, createTransport) {
  const secret = process.env.GATEWAY_KEY;
  if (!secret) throw new Error('missing gateway key');
  const sessions = {};
  app.use('/mcp', (req, res, next) => {
    if (req.headers.authorization !== `Bearer ${secret}`) return res.sendStatus(401);
    next();
  });
  app.post('/mcp/init', (req, res) => {
    const id = randomUUID();
    sessions[id] = createTransport();
    res.json({session: id});
  });

  app.get('/mcp', async (req, res) => {
    const session = sessions[req.headers['mcp-session-id']];
    if (!session) return res.sendStatus(404);
    await session.handleRequest(req, res);
  });
  app.delete('/mcp', async (req, res) => {
    const session = sessions[req.headers['mcp-session-id']];
    if (!session) return res.sendStatus(404);
    await session.handleRequest(req, res);
  });
}
