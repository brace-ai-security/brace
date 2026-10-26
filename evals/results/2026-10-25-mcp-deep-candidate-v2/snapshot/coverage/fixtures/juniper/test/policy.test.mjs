import test from 'node:test';
import assert from 'node:assert/strict';
import { projectId, documentId, documentText } from '../src/validation.mjs';
import { authorizeProject } from '../src/policy.mjs';
import { gatewayIdentity } from '../src/identity.mjs';
const actor = { subject: 'synthetic-user', projects: ['alpha'] };

test('project membership uses exact identifiers', () => {
  assert.equal(authorizeProject(actor, 'alpha').project, 'alpha');
  assert.throws(() => authorizeProject(actor, 'beta'));
  assert.throws(() => authorizeProject(actor, 'alph'));
});
test('identifiers reject traversal and separators', () => {
  for (const value of ['../beta', 'a/b', '/beta', '.', '', 'UPPER']) {
    assert.throws(() => projectId(value));
    assert.throws(() => documentId(value));
  }
});
test('ordinary identifiers and bounded text are preserved', () => {
  assert.equal(projectId('alpha-1'), 'alpha-1');
  assert.equal(documentId('release-notes'), 'release-notes');
  assert.equal(documentText('hello'), 'hello');
  assert.throws(() => documentText('x'.repeat(12001)));
});
test('gateway credential is checked before claims', () => {
  assert.throws(() => gatewayIdentity({ 'x-relay-identity': 'invalid' }, { gatewayToken: 'synthetic-token' }));
});
test('gateway claims must have subject and projects', () => {
  const headers = { 'x-relay-token': 'synthetic-token', 'x-relay-identity': JSON.stringify(actor) };
  const identity = gatewayIdentity(headers, { gatewayToken: 'synthetic-token' });
  assert.equal(identity.subject, 'synthetic-user');
  assert.deepEqual(identity.projects, ['alpha']);
  assert.ok(Object.isFrozen(identity.projects));
});
test('malformed claim collections fail', () => {
  const headers = { 'x-relay-token': 'synthetic-token', 'x-relay-identity': '{"subject":"user","projects":"alpha"}' };
  assert.throws(() => gatewayIdentity(headers, { gatewayToken: 'synthetic-token' }));
});
