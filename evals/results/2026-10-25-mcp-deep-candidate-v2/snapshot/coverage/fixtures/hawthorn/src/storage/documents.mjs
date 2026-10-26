import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { projectId, documentId } from '../validation.mjs';
export async function writeDocument(root, project, document, text) {
  const directory = join(root, projectId(project));
  await mkdir(directory, { recursive: true });
  await writeFile(join(directory, documentId(document) + '.txt'), text, 'utf8');
}
export async function readDocument(root, project, document) {
  return readFile(join(root, projectId(project), documentId(document) + '.txt'), 'utf8');
}
