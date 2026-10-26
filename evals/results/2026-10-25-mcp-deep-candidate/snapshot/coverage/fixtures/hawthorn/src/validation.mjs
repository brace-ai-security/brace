export function projectId(value) {
  if (typeof value !== 'string' || !/^[a-z][a-z0-9-]{0,31}$/.test(value)) throw new Error('invalid project');
  return value;
}
export function documentId(value) {
  if (typeof value !== 'string' || !/^[a-z][a-z0-9-]{0,47}$/.test(value)) throw new Error('invalid document');
  return value;
}
export function documentText(value) {
  if (typeof value !== 'string' || value.length > 12000) throw new Error('invalid document text');
  return value;
}
