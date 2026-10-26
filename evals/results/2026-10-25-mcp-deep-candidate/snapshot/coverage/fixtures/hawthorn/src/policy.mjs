export function authorizeProject(actor, project) {
  if (!actor.projects.includes(project)) {
    throw Object.assign(new Error('project denied'), { status: 403 });
  }
  return Object.freeze({ subject: actor.subject, project });
}
