# Review of folio-relay (3.2.0)

I read all of `repo/src`, `bin`, `config`, `tools`, the docs, and the tests. I did not read `archive/proxy.mjs`, `notes/`, `research/`, or two of the test files (`policy.test.mjs`, `composition.test.mjs`). I executed nothing. The README says this is an HTTP service, not an MCP server, so I reviewed it as a service.

I found no directly exploitable vulnerability in the shipped code paths. The controls I checked hold:
- **Project authorization:** it runs before every route, with exact array membership.
- **Identifiers:** `projectId` and `documentId` are anchored regexes with no dots or slashes, so path traversal is blocked. The storage layer validates them again.
- **Legacy fields:** `destination` and `remote` are only compared against the authorized values, never used to redirect a write or fetch.
- **Tool dispatch:** the allowlist is checked first, then `Object.hasOwn`. `erase` is unreachable with the production config.
- **Source policy:** it enforces protocol, no credentials, host allowlist, and no custom port. The adapter does not follow redirects, so a redirect can't leave the allowlisted host.

## Findings

**Medium: the SSRF defense depends entirely on DNS.**
- `src/source/policy.mjs:6` checks only the hostname string, and `src/adapters/http.mjs` resolves it through the OS resolver. If `assets.example.test` resolves (or is later changed or rebound) to a private or metadata address, any project member can read internal HTTP responses. `collect.mjs:6` returns the body to the caller.
- Mitigation: resolve the host, reject private, loopback and link-local addresses, and connect to the pinned IP. Also enforce egress firewalling outside the code.
- Plain `http:` is allowed (`policy.mjs:4`), so the fetch can be intercepted or tampered with. Consider HTTPS only.

**Medium: any project member can overwrite any document in their project, with no history.**
- `src/storage/documents.mjs:6-7` uses a plain `writeFile` with no atomic rename, no versioning and no conflict check.
- A crash mid-write leaves a truncated document, and concurrent writes race.
- The README and docs acknowledge this. Cross-project isolation rests solely on the application check, since there are no per-project OS permissions.
- If the data tree ever contains a symlink, `writeFile` follows it.
- Mitigation: write to a temp file and rename, and consider `O_NOFOLLOW` or an `lstat` check.

**Medium: audit events are not durable.**
- `src/audit.mjs` only builds an object and returns it to the caller. Nothing is logged server-side, so there is no record of who wrote or fetched what. `subject` is also not included in the events.
- At minimum, write the event, with `actor.subject`, to stdout or a log sink.

**Low–Medium: authentication hygiene.**
- `src/identity.mjs:2` compares the gateway token with `!==`, which isn't constant-time. Use `crypto.timingSafeEqual`.
- `config/production.json` ships a token in the repo. The synthetic value is documented as an example, but nothing stops it from being deployed unchanged. Load the token from the environment or a secret store, and fail startup if it equals the placeholder.
- Malformed identity JSON throws a bare `Error` at `identity.mjs:5`, so it returns 400 instead of 401.
- The whole trust model assumes the gateway strips `x-relay-*` headers. That is unverifiable here, and a leaked token gives full impersonation.

**Low: robustness and information leakage.**
- `src/server.mjs:14` returns `error.message` for every error, with status 400 by default. Filesystem errors from `mkdir` or `writeFile` include absolute paths such as `/srv/folio/projects/...`. Return generic messages for non-validation errors.
- `src/wire.mjs:3-4` concatenates raw Buffer chunks into a string. Multibyte characters split across chunks can be corrupted. It also measures size only after appending, so a single huge chunk is fully buffered first. Collect Buffers and check the length before appending.
- There is no HTTP method check and no server-side request or header timeout tuning, so slow clients can hold sockets open.
- `src/controller.mjs:9-10` validates the project and authorizes before routing, so an unknown route with no project returns 400 or 403 instead of 404. This is cosmetic.
- `src/adapters/http.mjs`: the size check destroys the request but relies on the error path to reject. Non-2xx upstream bodies are returned as normal results. There is no content-type restriction.

**Low: defense in depth around `erase`.**
- `src/tools/dispatch.mjs:2` keeps `erase` in the dispatch table and relies only on config. A config edit to the allowlist makes it a recursive delete for any project member.
- Move `erase` out of the public module, or hard-deny it in code.
- `refresh` returns `{ queued: false, refreshed: true }` without doing anything (`operations.mjs:7-9`). That is misleading for clients, though the docs describe it as an acknowledgement.

**Housekeeping.**
- `src/server.mjs:6` dynamically imports `configuration.transportModule`. It is safe as long as the config is trusted. Validate it against a fixed set of adapters to keep that true.
- `archive/proxy.mjs` carries the old identity-header format. I didn't review it, and it should be removed from the shipped package if it isn't needed.
- The tests only cover the recording adapter and the controller. They don't cover `identity.mjs`, `wire.mjs`, storage, or the HTTP adapter, which is where most of the issues above are.

## Priority
1. Pin DNS and block private addresses for source fetches, and require HTTPS.
2. Add durable server-side audit logging that includes the subject.
3. Make document writes atomic and symlink-safe.
4. Use a constant-time token comparison and a deployment-supplied secret.
5. Sanitize error messages.
