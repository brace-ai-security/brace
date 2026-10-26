export function createPublication(project, document, text, options) {
  if (options.destination !== undefined && options.destination !== project) throw new Error('destination differs from authorized project');
  return Object.freeze({ project, destination: project, document, text });
}
