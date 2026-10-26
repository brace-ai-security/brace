import test from 'node:test';
import assert from 'node:assert/strict';
import { createPublication } from '../src/publication/plan.mjs';
import { inspectSource } from '../src/source/policy.mjs';
import { makeTransfer } from '../src/source/transfer.mjs';
import { dispatchTool } from '../src/tools/dispatch.mjs';

test('publication uses the authorized project', () => {
  const plan = createPublication('alpha', 'memo', 'hello', {});
  assert.equal(plan.destination, 'alpha');
  assert.equal(plan.project, 'alpha');
});
test('legacy destination cannot select another project', () => {
  assert.throws(() => createPublication('alpha', 'memo', 'hello', { destination: 'beta' }));
});
test('source policy rejects an unapproved hostname', () => {
  assert.throws(() => inspectSource('http://127.0.0.1/', ['assets.example.test']));
});
test('source policy rejects credentials and custom ports', () => {
  assert.throws(() => inspectSource('https://u:p@assets.example.test/', ['assets.example.test']));
  assert.throws(() => inspectSource('https://assets.example.test:8443/', ['assets.example.test']));
});
test('a transfer preserves the checked URL', () => {
  const approved = inspectSource('https://assets.example.test/item', ['assets.example.test']);
  assert.equal(makeTransfer('alpha', approved, {}).url, approved.url);
});
test('legacy remote cannot select an unapproved endpoint', () => {
  const approved = inspectSource('https://assets.example.test/item', ['assets.example.test']);
  assert.throws(() => makeTransfer('alpha', approved, { remote: 'http://127.0.0.1:9090/private' }));
});
test('erase is denied before operation lookup', async () => {
  await assert.rejects(dispatchTool('erase', { project: 'alpha' }, { allowedTools: ['status', 'refresh'] }));
});
test('status remains available', async () => {
  assert.deepEqual(await dispatchTool('status', { project: 'alpha' }, { allowedTools: ['status'] }), { project: 'alpha', state: 'ready' });
});
