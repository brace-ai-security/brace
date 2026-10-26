import test from 'node:test';
import assert from 'node:assert/strict';
import { handle } from '../src/controller.mjs';
import * as transport from '../src/adapters/recording.mjs';
const actor = { subject: 'synthetic-user', projects: ['alpha'] };
const configuration = { allowedHosts: ['assets.example.test'], allowedTools: ['status', 'refresh'] };

test('source collection returns transport text', async () => {
  transport.clear();
  const result = await handle('/sources/collect', { project: 'alpha', url: 'https://assets.example.test/memo' }, actor, configuration, transport);
  assert.equal(result.text, 'synthetic source content');
  assert.equal(transport.requests[0], 'https://assets.example.test/memo');
});
test('project membership is checked before retrieval', async () => {
  transport.clear();
  await assert.rejects(handle('/sources/collect', { project: 'beta', url: 'https://assets.example.test/memo' }, actor, configuration, transport));
  assert.equal(transport.requests.length, 0);
});
test('unknown routes fail after project authorization', async () => {
  await assert.rejects(handle('/missing', { project: 'alpha' }, actor, configuration, transport));
});
