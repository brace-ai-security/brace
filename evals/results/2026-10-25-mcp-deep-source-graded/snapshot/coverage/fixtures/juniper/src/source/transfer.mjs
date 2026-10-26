export function makeTransfer(project, approved, options) {
  if (options.remote !== undefined && options.remote !== approved.url) throw new Error('remote differs from approved source');
  return Object.freeze({ project, url: approved.url, checkedHost: approved.host });
}
