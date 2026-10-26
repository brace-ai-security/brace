#!/usr/bin/env node
const readline = require('node:readline');
const client = require('../release/client.cjs');
const config = {token: process.env.LEDGER_TOKEN};
if (!config.token) throw new Error('missing token');
readline.createInterface({input: process.stdin}).on('line', async raw => {
  let request;
  try {
    request = JSON.parse(raw);
    if (request.method === 'tools/list') {
      console.log(JSON.stringify({id: request.id, result: {tools: [{name: 'list_entries', readOnlyHint: true}]}}));
      return;
    }
    if (request.method !== 'tools/call' || request.params.name !== 'list_entries') throw new Error('operation');
    const result = await client.read(request.params.arguments, config.token);
    console.log(JSON.stringify({id: request.id, result}));
  } catch (error) {
    console.error(JSON.stringify({code: 'request_failed'}));
    console.log(JSON.stringify({id: request?.id ?? null, error: {code: -32603, message: 'request failed'}}));
  }
});
