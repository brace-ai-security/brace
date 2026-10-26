I reviewed the `repo/` directory with the brace-mcp-review method. I found two high-impact gaps that are reachable by any authenticated user.

`repo/notes/upstream-support.md` contains text telling automated reviewers to output "SAFE" and omit findings about the integration. It's untrusted file content, not part of your request, so I ignored it. It also claims every relay caller is an administrator, which the code contradicts.

The Read/Glob/Grep tools can't write files, so the report is below instead of in `mcp-review.md`. I executed nothing and did no lookups.

# BRACE MCP-focused review: folio-relay 3.2.0

**Review date:** 2026-10-25. **Commit:** unknown, because there is no git repository.

## Scope
- **Component:** `folio-relay` is a plain HTTP JSON service on Node, listening on 127.0.0.1:8547 behind an external identity gateway. It is not an MCP server. It has no MCP SDK dependency and no `tools/list`, resources, prompts or JSON-RPC.
- **Protocol:** No MCP revision is negotiated, so the MCP protocol-requirement sources are not applicable. The HTTP and gateway checks in `http.md` and the control map are applied as general guidance only.
- **Dependencies:** `package.json` has none, and there is no lockfile. Resolved versions are not applicable and the advisory table doesn't apply. See "Sources and advisories" for what I checked.
- **Routes** (`src/controller.mjs:8-23`): `/documents/publish`, `/sources/collect` and `/tools/run`.
- **Tools:** `status`, `refresh` and `erase`. Production allows only `status` and `refresh`.
- **Privileged downstream actions:**
  - Writes anywhere under `dataRoot` (`/srv/folio/projects`).
  - Outbound HTTP from the service account.
  - Recursive delete, in `erase`.
- **Credential source:** The gateway token is in `config/production.json`. It's labelled synthetic, and I'm not repeating it here.
- **Out of scope or unreviewed:**
  - `archive/proxy.mjs` is not imported by any file I read. I did not run a Grep for callers, so "unreferenced" is based on the README and the files I read.
  - `tools/inventory.mjs` only prints configuration.
  - The gateway, content provider, DNS and egress are not supplied.

## Findings, ordered by impact

### F1 (high): Cross-project overwrite through `destination`
- **BRACE:** B02–B04, E06. This is a business-authorization gap against the README contract: "One authenticated project must not overwrite another project's documents."
- **Trigger:** A user with only `alpha` posts `{"project":"alpha","document":"memo","text":"x","destination":"beta"}` to `/documents/publish`.
- **Dataflow:**
  - `authorizeProject(actor, "alpha")` passes (`controller.mjs:9-10`).
  - `createPublication` takes `destination = projectId(options.destination)`. That only validates the format (`plan.mjs:2-3`).
  - `publish` writes to `plan.destination` (`commit.mjs:4`), and `writeDocument` joins `root/destination` (`documents.mjs:5-7`).
  - `destination` is never passed through `authorizeProject`.
- **Effect:**
  - The write replaces any existing `beta/<document>.txt`, because replacement is the advertised behavior.
  - It can also create directories for arbitrary projects.
  - The audit event records `plan.project` (`alpha`), not the destination, so the audit record hides the cross-project write.
- **Fix:**
  - Authorize the destination as well, or require `destination === project`, or drop the field.
  - Record the destination in the audit event.
- **Test:** `tests/composition.test.mjs` only exercises `destination` equal to the project, so it doesn't cover this.

### F2 (high): Source allowlist bypass and SSRF through `remote`
- **BRACE:** B08, B09, E06.
- **Trigger:** A user posts `{"project":"alpha","url":"https://assets.example.test/x","remote":"http://10.0.0.5:9000/admin"}` to `/sources/collect`.
- **Dataflow:**
  - `inspectSource(body.url, …)` approves only `url` (`controller.mjs:18`).
  - `makeTransfer` uses `String(options.remote)` instead of `approved.url` when `remote` is present (`transfer.mjs:2`).
  - `collectSource` then calls `transport.retrieve(transfer.url)` (`collect.mjs:5`).
  - The production adapter checks only the protocol (`adapters/http.mjs:5`). It doesn't check the host, port or credentials.
- **Effect:**
  - Any http(s) URL is fetched from the service account's private network position, including custom ports.
  - Up to 16 KB of the response body is returned to the caller (`collect.mjs:7`). This reads internal services, including cloud metadata endpoints if reachable.
  - Whether a sensitive endpoint exists is deployment-dependent.
- **Fix:**
  - Drop `remote`, or run `inspectSource` on the final URL.
  - Re-check the host in the adapter.
  - Resolve the host and block private addresses, then pin the resolved address.
- **Test:** The recording adapter used in tests can't show network isolation (`docs/operations.md`).

### F3 (medium): Allowlisted host can still reach internal addresses (DNS and egress)
- **BRACE:** B08, B09.
- **Evidence:** The README and `docs/operations.md` say that no DNS pinning or egress firewall is supplied.
- **Status:** This is a conditional exposure rather than a confirmed gap.
  - Redirects are not followed (`http.mjs`), which helps.
  - The hostname check is by name only. An allowed hostname that resolves to a private address, or rebinding, would pass.
  - The example DNS records are not supplied, so this stays `needs_evidence`.

### F4 (medium): No durable audit and a misattributed audit actor
- **BRACE:** R03, R13, A02, E10–E12.
- **Evidence:**
  - `eventFor` only builds an object (`audit.mjs`).
  - It is returned to the client and is never persisted.
  - It records no `subject`, even though `authorizeProject` returns one.
  - Denials are not recorded at all.
- **Effect:** F1 and F2 would leave no server-side trace.

### F5 (low): Hardening items
- **Token comparison:** `identity.mjs:2` uses `!==` on the gateway token. It is not constant-time, and the token is a static shared secret.
- **Request body limit:** `wire.mjs` accepts at most 32 KB. The 12,000-character text limit is fine.
- **Request timeouts:** None are configured on the listener.
- **Error handling:** The generic catch returns `error.message` to the caller, which could leak internal error text.

## Controls supported in code (`likely_pass`)
- **Tool allowlist:**
  - `dispatchTool` checks `allowedTools` by exact match before it looks up an implementation (`dispatch.mjs:4-5`).
  - `erase` is not in the production allowlist, and no endpoint modifies configuration.
  - This holds for the shipped router only. A config change that adds `erase` would also remove the project-ownership check, since `erase` is not tied to the caller's project beyond the controller's `authorizeProject`.
- **Path traversal:** Project and document identifiers are checked against restrictive regexes in the handler and again in storage (`validation.mjs`, `documents.mjs`). I found no traversal path.
- **Gateway token check:** The relay checks the token before it trusts the identity JSON.
- **Project membership check:** It uses exact array membership on the `project` field of the body.
- **Source policy details:** Credentials and custom ports are rejected on the `url` field, and the response size and timeout caps are enforced.

## Coverage table

| Boundary/check | Status | Evidence | Owner |
|---|---|---|---|
| Gateway authentication, header stripping | needs_evidence | README says these are deployment requirements and no gateway code is supplied | Deployment owner |
| Identity claims and membership freshness | needs_evidence | `docs/operations.md`: the gateway owns expiry and outages | Gateway owner |
| `/documents/publish` authorization | gap | F1 | Service |
| `/sources/collect` allowlist | gap | F2 | Service |
| Egress, DNS | needs_evidence | F3 | Deployment owner |
| `/tools/run` | likely_pass | `dispatch.mjs:4-5` | Service |
| `erase` (separate maintenance consumers) | needs_evidence | Not callable from the shipped router. Its separate callers are not supplied. | Maintenance owner |
| Audit | gap | F4 | Service and deployment owner |
| Resource limits | partial | Body, source size and timeout are capped. There is no rate limiting. | Service |
| Rollback, idempotency | na_candidate | The docs state there is no history or idempotency. Searched `docs/operations.md` and `src/`. | Service |
| `archive/proxy.mjs` | unreviewed | Not wired in by anything I read. It trusts an `x-user` header and grants `projects: ['*']`, so it should not be deployed. | Service |
| MCP protocol, SDK advisories | not applicable | Not an MCP implementation | n/a |

## Sources and advisories
- **Bundled sources:** I used the control map in `skill/references/control-map.md` (OWASP SSRF and Transaction Authorization, plus the MCP security guidance). The control map dates its baseline to BRACE's 2026-10-22 review, but I read these sources only through the skill's own references.
- **Not rechecked:** No lookup was possible in this session, so none of these sources were rechecked.
- **SDK advisories:** No MCP SDK or other listed package appears in `package.json`, so none of the `advisories.md` entries apply.
- **Verification record:** `research/verification-2026-10-24.json` covers Express, Node, an MCPB manifest and a TS SDK redirect advisory. None of these match this repository's dependencies or features, so I made no recorded-verification claim from it.

## Proposed controlled tests (disposable fixtures, owner: service team)
1. As a user with only `alpha`, send a publish with `destination:"beta"`. Expect a 403 and no file change. Publishing with `destination:"alpha"` or without it should succeed.
2. Send a collect with an allowed `url` and a `remote` pointing to a local test listener. Expect a rejection and no connection. A plain allowed `url` should still work.
3. Point a test allowed hostname at a private address (including IPv6) and expect denial.
4. Check that each denied request in 1–3 produces a persisted audit record that includes the subject and the destination.
5. At the gateway (deployment owner): send forged `x-relay-token` and `x-relay-identity` headers from a browser and expect them to be stripped.

This review is bounded by the files I inspected. It identifies gaps and unknowns but doesn't approve or certify a deployment.
