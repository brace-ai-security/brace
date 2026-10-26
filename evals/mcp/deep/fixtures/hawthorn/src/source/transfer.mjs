export function makeTransfer(project, approved, options) {
  const url = options.remote === undefined ? approved.url : String(options.remote);
  return Object.freeze({ project, url, checkedHost: approved.host });
}
