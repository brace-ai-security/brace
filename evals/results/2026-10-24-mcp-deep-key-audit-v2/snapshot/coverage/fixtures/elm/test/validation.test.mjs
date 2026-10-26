import test from 'node:test';
import assert from 'node:assert/strict';
import { workspaceName, receiptLabel, decodeEntries } from '../src/validation.mjs';
import { authenticate, requireOperator } from '../src/identity.mjs';
const configuration = { operatorToken: 'synthetic-test-token' };

test('workspace names preserve simple warehouse identifiers', () => {
  assert.equal(workspaceName('bay-17'), 'bay-17');
  assert.equal(workspaceName('a'), 'a');
});
test('workspace names reject path syntax', () => {
  for (const value of ['../bay', '/tmp', '.', '', 'UPPER', 'bay/name']) {
    assert.throws(() => workspaceName(value));
  }
});
test('workspace length is bounded', () => {
  assert.equal(workspaceName('a'.repeat(32)).length, 32);
  assert.throws(() => workspaceName('a'.repeat(33)));
});
test('labels remain arbitrary single line text', () => {
  assert.equal(receiptLabel('Bay 17: fragile'), 'Bay 17: fragile');
  assert.equal(receiptLabel('Bay 17 — fragile'), 'Bay 17 — fragile');
  assert.equal(receiptLabel('quoted "value"'), 'quoted "value"');
});
test('multiline labels are not accepted', () => {
  assert.throws(() => receiptLabel('a\nb'));
  assert.throws(() => receiptLabel('a\rb'));
});
test('empty and excessive labels are not accepted', () => {
  assert.throws(() => receiptLabel(''));
  assert.throws(() => receiptLabel('x'.repeat(121)));
});
test('archive entries preserve text content', () => {
  const result = decodeEntries([{ name: 'nested/item.txt', content: 'parcel' }], 64);
  assert.deepEqual(result, [{ name: 'nested/item.txt', content: 'parcel' }]);
});
test('archive entry count is bounded', () => {
  assert.throws(() => decodeEntries([{}, {}], 1));
  assert.throws(() => decodeEntries({}, 64));
});
test('archive content is a bounded string', () => {
  assert.throws(() => decodeEntries([{ name: 'a', content: 17 }], 64));
  assert.throws(() => decodeEntries([{ name: 'a', content: 'x'.repeat(4097) }], 64));
});
test('only the exact configured token authenticates', () => {
  assert.equal(authenticate({ authorization: 'Bearer synthetic-test-token' }, configuration).role, 'operator');
  assert.throws(() => authenticate({}, configuration));
  assert.throws(() => authenticate({ authorization: 'Bearer other' }, configuration));
});
test('dispatch role cannot be replaced by a body value', () => {
  assert.throws(() => requireOperator({ role: 'viewer' }));
  assert.doesNotThrow(() => requireOperator({ role: 'operator' }));
});
