I found no serious vulnerabilities in the parts I read. I read the OAuth login flow, the HTTP middleware and the browser launcher. The GitHub tool handlers in `pkg/github/*` (about 500 files) were not reviewed beyond grepping for risky patterns, and I didn't check that tests pass.

## Findings

**1. Any local process or web page can abort a login (low severity, denial of service).** In `internal/oauth/callback.go:83-111`, the first result to reach `/callback` wins, and `report` drops everything after it.
- A request with `?error=x` or a wrong `state` is therefore treated as final. It ends the flow with an error and shuts the listener down.
- A malicious web page in the user's browser can send `http://localhost:<port>/callback?state=bad`. With a fixed `--oauth-callback-port` the port is easy to guess.
- This isn't token theft, because the PKCE verifier and state check stop that. It only forces the user to restart authorization.
- Suggested fix: on a bad state, respond 400 and keep waiting for the real callback until the timeout. Only a callback with a matching state should complete the flow.

**2. State comparison isn't constant-time (very low severity).** `callback.go:96` uses `!=`. The risk is theoretical because the state is single-use and the listener is local. `subtle.ConstantTimeCompare` is cheap to use.

**3. The callback listener binds `0.0.0.0` inside Docker (documented risk, medium in some setups).** `beginPKCE` binds all interfaces when it detects a container, and it logs a warning telling the user to publish the port on loopback only.
- Anyone who publishes the port as `-p 8085:8085`, which is common, exposes the callback to the LAN. Combined with finding 1, that lets other machines abort login attempts.
- PKCE and the state parameter still protect the code exchange.
- Suggested fix: make the docs and README examples always show `127.0.0.1:` publishing.

**4. Container detection is heuristic (low severity).** `isRunningInDocker` in `internal/oauth/env.go:56` checks for `/.dockerenv` and strings in `/proc/1/cgroup`.
- Podman, Kubernetes and cgroup v2 hosts often match neither, so the listener stays on loopback and the flow fails.
- That fails closed, which is safe. A confusing failure is the cost.

**5. Request bodies are read in full by two middlewares (low severity).** `pkg/http/middleware/mcp_parse.go:61` and `scope_challenge.go:54` call `io.ReadAll(r.Body)`.
- The code handles a max-bytes error, so a `MaxBytesReader` is presumably applied upstream. I didn't confirm where.
- If a limit isn't set before these middlewares in every deployment path, that's a memory-exhaustion risk. Please check that the limit is installed in front of both.

**6. CORS is wildcard (informational).** `pkg/http/middleware/cors.go:41` sets `Access-Control-Allow-Origin: *`. That's acceptable for a bearer-token API, because browsers don't attach credentials automatically. It would become a problem if cookie-based auth were ever added.

**7. `mcpcurl` runs arbitrary commands (informational).** `cmd/mcpcurl/main.go:388` calls `exec.Command` on a user-supplied command string. It is annotated as a test tool and the user supplies the command, so this is fine as long as it isn't shipped or exposed as a service.

## What looks good
- PKCE (S256) with random state.
- The callback listener defaults to loopback, and its `ReadHeaderTimeout` guards against Slowloris.
- `html/template` escapes error text on the callback page.
- A busy fixed callback port stops the flow instead of silently falling back to device flow.
- Authorization URLs go through elicitation instead of the model's context.
- Token refresh uses a bounded HTTP client with a timeout.
- The flow manager is single-flight, with flow IDs that prevent stale responses from affecting a newer flow.
- `X-Forwarded-*` headers are ignored unless `--trust-proxy-headers` is set.

If you want me to go deeper, I'd start with the tool handlers in `pkg/github` (input validation and write-tool safeguards) and the HTTP server's token and scope handling.
