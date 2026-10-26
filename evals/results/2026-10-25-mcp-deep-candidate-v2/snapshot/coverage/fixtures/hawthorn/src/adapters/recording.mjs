export const requests = [];
export async function retrieve(url) {
  requests.push(url);
  return { status: 200, text: 'synthetic source content' };
}
export function clear() {
  requests.length = 0;
}
