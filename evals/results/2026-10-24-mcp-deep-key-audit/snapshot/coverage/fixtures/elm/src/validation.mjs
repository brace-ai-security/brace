export function workspaceName(value) {
  if (typeof value !== 'string' || !/^[a-z0-9-]{1,32}$/.test(value)) throw new Error('invalid workspace');
  return value;
}
export function decodeEntries(value, limit) {
  if (!Array.isArray(value) || value.length > limit) throw new Error('invalid entries');
  return value.map(entry => {
    if (typeof entry.name !== 'string' || entry.name.length > 160) throw new Error('invalid entry name');
    if (typeof entry.content !== 'string' || entry.content.length > 4096) throw new Error('invalid entry content');
    return { name: entry.name, content: entry.content };
  });
}
export function receiptLabel(value) {
  if (typeof value !== 'string' || value.length === 0 || value.length > 120) throw new Error('invalid label');
  if (value.includes('\n') || value.includes('\r')) throw new Error('single line label required');
  return value;
}
