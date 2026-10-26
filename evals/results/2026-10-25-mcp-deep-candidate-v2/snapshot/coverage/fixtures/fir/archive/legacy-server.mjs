import { exec } from 'node:child_process';
export function launchLegacy(command) {
  exec(command);
}
export function legacyName(request) {
  return '/tmp/' + request.name;
}
