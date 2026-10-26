# Dated advisory mapping

Checked in BRACE's 2026-10-22 research. This is a starting index, not a live feed,
exhaustive vulnerability database or minimum universally safe version list.
Recheck the original record when reviewing a matching package. Read affected
ranges and prerequisites before claiming exposure. Record unresolved/opaque remote
versions as unknown. Branches and prereleases require their own range handling.

## MCP SDKs and server integration

| Original advisory | Issue-specific fix/action to verify | BRACE mapping |
|---|---|---|
| [TS shared-server leak GHSA-jm63-cq47-j5jp](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-jm63-cq47-j5jp), 2026-10-15 | Affected server 2.0.0–<2.3.0: upgrade to 2.3.0 and use fresh-server factories/proper per-request or per-session construction. The advisory excludes stdio and SDK 1.26+. | E06, R04 |
| [TS validation exhaustion GHSA-46jr-4wx8-v453](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-46jr-4wx8-v453), 2026-10-15 | SDK 1.32.0/server 2.3.0 fix: explicitly configure `maxToolInputElements` (off by default) plus suitable body/parser limits. HTTP applicability matters. | B07, R01, E06 |
| [TS body/batch exhaustion GHSA-f897-62hf-6gxq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-f897-62hf-6gxq), 2026-10-15 | Fixes: SDK 1.30.1; server/node 2.1.0; hono 2.0.1. Patched body and batch defaults address different allocations; update each installed affected package. | B07, R01, E06 |
| [TS issuer binding GHSA-6qxp-vccf-f47h](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h), 2026-09-30 | SDK 1.31.0/client/core 2.2.0; configure `expectedIssuer`, bind/clear saved registrations and assess credential rotation/revocation. | B02–B04, E06 |
| [TS audience GHSA-rvq5-wwqv-78pq](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-rvq5-wwqv-78pq), 2026-10-05 | SDK 1.32.0/server 2.3.0/express 2.0.2/server-legacy 2.3.1. Configure `expectedResource` plus verified `AuthInfo.resource`, or enforce audience inside custom verification. Upgrade alone changes nothing. | B02, E06 |
| [TS redirects GHSA-6prh-2h8m-c8cw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6prh-2h8m-c8cw), 2026-10-02 | SDK 1.32.0/client 2.3.0. Review custom headers and 307/308 bodies; `redirectPolicy:'follow'` can restore exposure. Ordinary Authorization stripping is a distinct behavior. | B03, B09, E06, E12 |
| [TS experimental tasks GHSA-22jm-h49p-29qw](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-22jm-h49p-29qw), 2026-10-02 | Affected SDK 1.24.0–<1.32.0: shared taskStore isolation fixed 1.32.0. 2.x excluded. Do not conflate legacy session-based tasks with redesigned Tasks handles. | E06, E09 |
| [Python issuer binding GHSA-qx49-fqc8-xw99](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-qx49-fqc8-xw99), 2026-09-28 | mcp 1.30.0/2.2.0; unattended providers require `issuer=`, saved registrations need rebinding/clearing, deprecated provider needs migration. Assess exposure cleanup. | B02–B04, E06, E12 |
| [Python audience GHSA-w4fh-qvv9-3v23](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-w4fh-qvv9-3v23), 2026-10-05 | mcp 1.30.0/2.2.0 plus `validate_token_resource=True`, correct `resource_server_url`, verified `AccessToken.resource`; custom audience checks may provide an alternative. | B02, E06 |
| [Python schema refs GHSA-rwrf-2pqf-9j8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-rwrf-2pqf-9j8j), 2026-09-28 | mcp 1.30.0/2.2.0 restricts output-schema resolution. Prior network/file resolution can stall or cause SSRF; advisory does not prove local file bytes reach the server. | R01, B09, E04, E06 |
| [Python redirects GHSA-5h93-6whr-6q8j](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-5h93-6whr-6q8j), 2026-10-02 | mcp 1.30.0/2.2.0; inspect cross-origin custom headers/bodies and any overridden redirect policy. Use final configured endpoints where appropriate. | B03, B09, E06 |
| [Python body allocation GHSA-fmmv-w9g8-j3gc](https://github.com/modelcontextprotocol/python-sdk/security/advisories/GHSA-fmmv-w9g8-j3gc), 2026-09-30 | mcp 1.29.1/2.1.0; check body limits before allocation, including unauthenticated OAuth endpoints and proxy/application parsers. | B07, R01, E06 |
| [Splunk SVD-2026-1004](https://advisory.splunk.com/advisories/SVD-2026-1004), 2026-10-07 | MCP Server 1.2.1; attacker tool-administrator changes destination, and another authorized executor runs it. Not an unauthenticated universal token leak. | B03, E03, E06, E12 |

## Adjacent components: read only when present

- **Hooks and local executable configuration:** [VS Code GHSA-w79w-rj9h-vg4f](https://github.com/microsoft/vscode/security/advisories/GHSA-w79w-rj9h-vg4f),
  fixed 1.132.1; map B05/B12/C02. A file-write tool may alter future execution.
- **Filesystem tools and helper fetches:** [LangChain GHSA-gr75-jv2w-4656](https://github.com/langchain-ai/langchain/security/advisories/GHSA-gr75-jv2w-4656)
  (glob/symlink/path boundaries) and [GHSA-r7w7-9xr2-qq2r](https://github.com/langchain-ai/langchain/security/advisories/GHSA-r7w7-9xr2-qq2r)
  (image-counter DNS rebinding); map B09/B11/R01. Verify package-specific conditions.
- **Persistent state:** [LangGraph namespace GHSA-6hmw-9432-67qq](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-6hmw-9432-67qq),
  Postgres 3.1.3/SQLite 3.1.2 with checkpoint 4.3.0; [auth-hook GHSA-4hm6-w6qq-w73v](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-4hm6-w6qq-w73v),
  API 0.15.0; [checkpoint revival GHSA-fjqc-hq36-qh5p](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-fjqc-hq36-qh5p),
  checkpoint 4.1.1. Map R04–R06/R14/A04; do not infer safe decoding from a signature.
- **Model/preprocessing services:** inspect applicable [vLLM advisories](https://github.com/vllm-project/vllm/security/advisories),
  including October 20 image dispatch, audio OOM, token bounds and CORS/no-auth.
  Map B07–B09/R01/C05; these are not MCP protocol flaws.
- **Artifact verification:** [Cosign GHSA-fx35-mq7g-6g98](https://github.com/sigstore/cosign/security/advisories/GHSA-fx35-mq7g-6g98),
  fixes 2.6.5/3.1.3, concerns legacy blob bundles; OCI image verification and modern
  protobuf bundles are explicitly unaffected. Map B10/C05 only where the path is used.
