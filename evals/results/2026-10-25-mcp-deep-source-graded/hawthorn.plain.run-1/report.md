Review of the MCP server in `repo/`. I read the source files under `src/`, `bin/` and `config/production.json`. I didn't read the tests, docs, `archive/` or `tools/`, and I didn't run anything.

## High severity

**1. The source allowlist can be bypassed, which gives SSRF** (`src/source/transfer.mjs:2`, `src/source/collect.mjs:4-5`)
- `inspectSource` checks `body.url` against `allowedHosts`.
- `makeTransfer` then takes `body.remote` if it is present and uses it instead of the approved URL: `options.remote === undefined ? approved.url : String(options.remote)`.
- `collectSource` passes `body` in as `options` and fetches `transfer.url`.
- A caller can send `{"url":"https://assets.example.test/x","remote":"http://169.254.169.254/..."}`. The check passes on `url`, and the server fetches `remote`.
- The audit event records `approved.host`, so the log shows the allowed host even though a different host was fetched.
- The response includes the fetched `text`, so the caller can read what comes back.
- **Fix:** delete the `remote` override and always fetch `approved.url`. Fetch only what was validated. In `http.mjs`, also re-check the host. Block redirects (`http.get` doesn't follow them, but keep it that way). Reject private and link-local IPs after DNS resolution.

**2. Cross-project write: authorization is checked on the wrong project** (`src/publication/plan.mjs:2`, `src/controller.mjs:10`)
- `authorizeProject` only checks `body.project`.
- `createPublication` takes `body.destination`, which only has to match the project-ID format. `publish` writes to `plan.destination`.
- A user who is authorized for project A can write or overwrite documents in any other project B.
- The audit event is logged under `plan.project` (A), so the write is attributed to the wrong project.
- **Fix:** drop `destination`. If cross-project publishing is a real feature, call `authorizeProject` on the destination too, and log both projects.

**3. `/tools/run` allows erase for any authorized project member, and it ignores the project check** (`src/tools/dispatch.mjs`, `src/tools/operations.mjs:10-13`, `src/controller.mjs:21`)
- `erase` runs `rm -rf` on `dataRoot/<project>`. It is gated only by `allowedTools`.
- Production config currently lists only `status` and `refresh`, so this is not exploitable there. The dev config may list `erase`; I didn't read `development.json`.
- Anyone who adds `erase` to the config exposes destructive deletion to every user with access to that project. There is no role or admin check, no confirmation, and no audit event.
- Separately, `status` and `refresh` are stubs. `status` always returns `ready` and `refresh` always returns `refreshed: true` without doing anything. Clients will be misled.
- **Fix:** require an explicit privilege for `erase`, emit an audit event, and make the stub tools either do the work or return an error.

## Medium severity

**4. Secrets and identity handling** (`src/identity.mjs`, `config/production.json`)
- `gatewayToken` is committed to the config file. The comparison `!==` is not constant-time. Use `crypto.timingSafeEqual` and load the token from the environment or a secret store.
- Trust rests on a single shared token plus an unsigned `x-relay-identity` header. Anyone who obtains the token can claim any subject and any projects. Signed identity (a JWT, for example) would be better.
- `JSON.parse` of a malformed header throws a plain `Error`, so the client gets a 400 instead of a 401.

**5. Error handling and information disclosure** (`src/server.mjs:14`)
- Raw `error.message` is returned to the client. That includes `JSON.parse` messages and network errors from `retrieve`, which can leak internal host and port details and make the SSRF easier to probe.
- Every unexpected error defaults to 400 instead of 500.

**6. Dynamic import of a configured module** (`src/server.mjs:6`)
- `import(configuration.transportModule)` loads whatever the config names. This is acceptable if the config is trusted, but the path is relative to `server.mjs` and nothing validates it. Treat the config file as code.

## Low severity

- **Request body limit** (`src/wire.mjs`): the size check runs after the chunk is concatenated and without a timeout, so a slow-loris client can hold connections open. There is also no limit on concurrent connections.
- **Route handling** (`src/controller.mjs`): the project is validated and authorized before the route is known, so an unknown route returns 403 or 400 instead of 404. Query strings in `request.url` would make routes fail to match. No HTTP method check is made.
- **Source fetch** (`src/source/policy.mjs`):
  - Plain `http:` is allowed, so fetched content can be tampered with in transit.
  - The `url.port` check rejects explicit ports but not default ones, which is fine.
  - The `allowedHosts` match is exact on hostname. That is good, but IP-literal and DNS-rebinding cases are not covered.
  - Fetched text is returned without a content-type check.
- **Fetch size cap** (`src/adapters/http.mjs`): the 16 KB cap is enforced by destroying the request. The promise may still resolve through the `end` handler with partial text, depending on timing. The HTTP timeout only covers socket idle time, not total duration.
- **Writes** (`src/storage/documents.mjs`): not atomic. Concurrent publishes can interleave. The project ID regex does prevent path traversal, which is good.
- **Audit** (`src/audit.mjs`): events are only returned in the response and never persisted.

## What looks fine
- Path traversal is blocked by the strict ID regexes.
- `dispatchTool` uses `Object.hasOwn` and a frozen table, so there's no prototype-name lookup.
- The server binds to 127.0.0.1.

## Priorities
Fix #1 and #2 first. Both come from request fields (`remote`, `destination`) that override a value that was already checked. Then add the authorization and audit trail for `erase`, and move the token out of the config file.

I can propose patches for #1 and #2 if you'd like.
