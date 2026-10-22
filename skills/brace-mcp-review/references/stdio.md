# Local process and stdio review

OAuth/HTTP middleware is not the local stdio authorization boundary. Inspect the
host, process identity, inherited environment, filesystem, network and sandbox.
Primary basis: [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices).

## Inspect without launching

- Read `.mcp.json`, host settings, executable scripts and container definitions as
  text. JSON/JSONC/YAML parsing must not source environment files, evaluate shell
  expressions or invoke constructors. Report redacted secret locations.
- Trace command, arguments, working directory, environment/PATH and package resolver.
  Identify shell wrappers, pipe-to-shell installation, unpinned `npx`/`uvx` packages,
  floating images, executable hooks and generated trusted instruction files.
  An argv array avoids shell parsing but does not prevent option/path injection.
- Determine the actual process user, allowed paths/mounts, capabilities, accessible
  sockets, network policy and credential custody. A local server can inherit the
  user's full authority even if its tools describe themselves as read-only.
- Trace symlink/glob/canonical-path handling and every equivalent filesystem/API
  route. Exact package pins and metadata hashes do not prove implementation safety.
- Review process-tree termination, child/queued work, open pipes, credential
  revocation and cleanup. Killing the launching shell does not prove descendants stop.
- Inspect stdout/stderr and debug logging for protocol contamination and credential
  exposure, including subprocess stdin and deployment helpers. Do not print secrets
  discovered in configuration to demonstrate their presence.

## Scanner boundary

[Snyk Agent Scan](https://github.com/snyk/agent-scan) documents that discovery can
execute configured stdio commands and send configured remote credentials. Treat
scanner startup as execution of an untrusted supply-chain input. Do not run it as
part of a read-only review. An authorized runtime follow-up needs a disposable
environment, fake credentials, bounded egress and reviewed launch commands.

Propose controlled checks for allowed operations plus blocked host/tenant access,
path/symlink escapes, unexpected egress, future hook registration and descendants
surviving shutdown. Where host configuration is unavailable, identify the owner and
missing evidence; a server-only repository cannot establish the host's isolation.
