export function eventFor(action, project, fields) {
  return Object.freeze({
    action,
    project,
    fields: Object.freeze({ ...fields }),
    timestamp: new Date().toISOString()
  });
}
