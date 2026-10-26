import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { materialize } from '../src/storage/files.mjs';
test('ordinary nested entries are materialized', async () => {
  const root = await mkdtemp(join(tmpdir(), 'parcel-test-'));
  try {
    const count = await materialize(root, 'bay', [{ name: 'a/b.txt', content: 'ok' }]);
    assert.equal(count, 1);
    assert.equal(await readFile(join(root, 'bay/a/b.txt'), 'utf8'), 'ok');
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
test('empty batches report zero materialized entries', async () => {
  const root = await mkdtemp(join(tmpdir(), 'parcel-test-'));
  try {
    assert.equal(await materialize(root, 'bay', []), 0);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
