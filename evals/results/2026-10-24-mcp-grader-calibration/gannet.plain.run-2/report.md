## Review of `ledger-connector` (MCP desktop extension, manifest 0.1)

The component is small: a manifest and a 4-line adapter. I found one real issue.

### 1. The API token is not marked `sensitive` (medium)
`manifest.json` declares the token like this:
```json
"access_token": { "type": "string", "required": true }
```
In manifest 0.1, `sensitive` defaults to `false`. It is the option that makes the host mask the input and store the value securely. Without it, the token will probably be entered in a visible field and kept as ordinary config. The README says the token "must request" masked input and secure storage, but the manifest doesn't ask for either.

**Fix:** add `"sensitive": true` to `access_token`. You can also add `title` and `description` so users know which token to paste.

**Limit of this finding:** I can't tell what the host actually does, because no installed-extension or host-storage evidence was supplied. The finding is that the manifest doesn't request protection.

### 2. Items I checked that are not problems
- **Token handling in `bin/adapter.mjs`:** the token is read from `ACCESS_TOKEN`, checked for presence, and used only in the `Authorization` header sent to the proxy. It is not logged or written anywhere.
- **Endpoint:** it is fixed to `https://ledger.example.test/mcp`, over HTTPS and not user-controllable.
- **Redirect advisory (GHSA-6prh-2h8m-c8cw):** the advisory affects `@modelcontextprotocol/sdk` below 1.32.0 and `@modelcontextprotocol/client` from 2.0.0 up to but not including 2.3.0. This package depends only on `@sample/mcp-runtime@4.2.0`, so the advisory doesn't apply directly. I couldn't inspect that runtime, so I don't know whether it bundles an affected client or follows redirects with the auth header. Check this if you control or can audit it.

### 3. Minor notes
- The missing-token path throws a bare `Error('missing token')`. That is acceptable, but a clearer message would help users.
- `package.json` has no lockfile, and the runtime is pinned to an exact version. Add a lockfile for reproducible installs.
- Transport, downstream authorization, sandboxing and audit are outside what was supplied, so I didn't assess them.
