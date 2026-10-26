import {randomUUID} from 'node:crypto';
export function register(app, createTransport) {
  const secret = process.env.GATEWAY_KEY;
  if (!secret) throw new Error('missing gateway key');
  const sessions = new Map();
  app.use('/mcp', (req, res, next) => {
    if (req.headers.authorization !== `Bearer ${secret}`) return res.sendStatus(401);
    next();
  });
  app.post('/mcp/init', (req, res) => {
    const id = randomUUID();
    sessions.set(id, createTransport());
    res.json({session: id});
  });
  const route = fn => (req, res, next) => Promise.resolve(fn(req, res)).catch(next);
  app.get('/mcp', route(async (req, res) => {
    const session = sessions.get(req.headers['mcp-session-id']);
    if (!session) return res.sendStatus(404);
    await session.handleRequest(req, res);
  }));
  app.delete('/mcp', route(async (req, res) => {
    const session = sessions.get(req.headers['mcp-session-id']);
    if (!session) return res.sendStatus(404);
    await session.handleRequest(req, res);
  }));
}
