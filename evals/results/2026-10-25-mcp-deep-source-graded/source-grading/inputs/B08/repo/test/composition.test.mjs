import test from 'node:test';
import assert from 'node:assert/strict';
import { createPublication } from '../src/publication/plan.mjs';
import { inspectSource } from '../src/source/policy.mjs';
import { makeTransfer } from '../src/source/transfer.mjs';
import { dispatchTool } from '../src/tools/dispatch.mjs';

test('publication retains its request fields', () => {
  const plan = createPublication('alpha', 'memo', 'hello', {});
  assert.equal(plan.destination, 'alpha');
  assert.equal(plan.project, 'alpha');
});
test('legacy client may repeat its project', () => {
  const plan = createPublication('alpha', 'memo', 'hello', { destination: 'alpha' });
  assert.equal(plan.document, 'memo');
  assert.ok(Object.isFrozen(plan));
});
test('source policy rejects an unapproved hostname', () => {
  assert.throws(() => inspectSource('http://127.0.0.1/', ['assets.example.test']));
});
test('source policy rejects credentials and custom ports', () => {
  assert.throws(() => inspectSource('https://u:p@assets.example.test/', ['assets.example.test']));
  assert.throws(() => inspectSource('https://assets.example.test:8443/', ['assets.example.test']));
});
test('a transfer retains its project identifier', () => {
  const approved = inspectSource('https://assets.example.test/item', ['assets.example.test']);
  assert.equal(makeTransfer('alpha', approved, {}).project, 'alpha');
});
test('legacy client may repeat its normalized source', () => {
  const approved = inspectSource('https://assets.example.test/item', ['assets.example.test']);
  const transfer = makeTransfer('alpha', approved, { remote: approved.url });
  assert.equal(transfer.checkedHost, 'assets.example.test');
  assert.ok(Object.isFrozen(transfer));
});
test('erase is denied before operation lookup', async () => {
  await assert.rejects(dispatchTool('erase', { project: 'alpha' }, { allowedTools: ['status', 'refresh'] }));
});
test('status remains available', async () => {
  assert.deepEqual(await dispatchTool('status', { project: 'alpha' }, { allowedTools: ['status'] }), { project: 'alpha', state: 'ready' });
});
