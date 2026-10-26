# Shared primary-reference packet

Identical in both arms. This packet supplies library/format semantics, not finding
locations or an answer key. Recorded 2026-10-23. Model web lookup is unavailable.

- Express 4 error handling: https://expressjs.com/en/4x/guide/error-handling/
  Official framework documentation, retrieved 2026-10-23. Rejected async-handler
  promises need explicit forwarding to the framework error path.
- Node 20 runtime options: https://nodejs.org/download/release/latest-v20.x/docs/api/cli.html#--unhandled-rejectionsmode
  Official runtime documentation, retrieved 2026-10-23. The default unhandled
  rejection mode raises an uncaught exception when no relevant hook is installed.
- Desktop manifest 0.1: https://github.com/modelcontextprotocol/mcpb/blob/v0.1.0/MANIFEST.md#user-configuration
  Versioned format specification. The sensitive string option requests masked
  input and secure storage; its default is false. Installed-host behavior still
  needs evidence.
- MCP security guidance: https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices
  Protocol-project guidance, bundled review date 2026-10-22. Scope credential,
  process and transport boundaries to the component actually supplied.
- TypeScript SDK redirect advisory: https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw
  Maintainer advisory, published 2026-10-02, checked 2026-10-23. SDK HTTP clients
  before 1.32.0 can forward custom headers and request bodies across redirects.
  Check package, version and use of the affected client; an unrelated component
  is not vulnerable merely because it participates in MCP.
- OWASP Logging: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
  Guidance, bundled review date 2026-10-22. Keep credentials out of diagnostic
  output and distinguish diagnostic sinks from authorized secret consumers.

The external semantics above were rechecked on 2026-10-24 before the campaign.
See verification-2026-10-24.json for short primary excerpts, the versioned manifest
blob ID and the maintainer advisory ranges/dates. These records are identical in
both arms and contain no fixture labels or answer locations.
