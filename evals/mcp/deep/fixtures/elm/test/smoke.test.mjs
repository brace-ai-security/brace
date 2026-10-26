import test from 'node:test';
import assert from 'node:assert/strict';
import { dispatch } from '../src/routes/shipping.mjs';
import { makeRenderRequest } from '../src/render/request.mjs';
const configuration = {
  workspaceRoot: '/tmp/parcel-example/workspaces',
  receiptRoot: '/tmp/parcel-example/receipts',
  renderProgram: '/usr/bin/printf',
  maxEntries: 64
};
test('unknown routes are rejected', async () => {
  await assert.rejects(dispatch('/missing', {}, { role: 'operator' }, configuration));
});
test('role checks precede route operations', async () => {
  await assert.rejects(dispatch('/archives/unpack', {}, { role: 'viewer' }, configuration));
});
test('receipt request preserves label as data', () => {
  const request = makeRenderRequest(configuration, 'bay-17', 'handle with care');
  assert.equal(request.label, 'handle with care');
  assert.equal(request.output, '/tmp/parcel-example/receipts/bay-17.txt');
  assert.equal(request.program, '/usr/bin/printf');
  assert.equal(request.timeout, 2000);
});
