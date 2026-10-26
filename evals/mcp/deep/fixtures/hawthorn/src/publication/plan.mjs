import { projectId } from '../validation.mjs';
export function createPublication(project, document, text, options) {
  const destination = options.destination === undefined ? project : projectId(options.destination);
  return Object.freeze({ project, destination, document, text });
}
