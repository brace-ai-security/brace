# open-agent-security

Find known-dangerous AI agent setups in a repository, in seconds. Part of the
[BRACE framework](https://braceframework.org) for securing AI agents.

It reads files and matches fixed patterns. It starts no server, runs no model, sends
nothing over the network and needs no dependencies beyond Python 3.11 or newer.

## Install and run

```bash
uvx open-agent-security .            # or: pipx run open-agent-security .
uvx open-agent-security . --host     # also check the agent settings on this machine
pip install open-agent-security      # to install the command
open-agent-security . --fail-on high # exit 1 on a high or worse finding
```

Each problem is reported with its file and line, why it matters and how to fix it.

## Rules

| ID | Severity | Problem |
|---|---|---|
| AP01 | high | Agent runs with all permission checks turned off |
| AP02 | critical | Unattended agent in CI with permission checks turned off |
| AP03 | critical | Agent workflow triggered by `pull_request_target` |
| AP04 | high | MCP server installed from an unpinned package |
| AP05 | high | Secret written directly in agent configuration |
| AP06 | high | Agent allowed to run any shell command (Claude Code settings) |
| AP07 | medium | Remote MCP server reached over plain HTTP |
| AP08 | high | Agent tool container can take over the host |
| AP09 | medium | Lethal combination: untrusted input, private data and a way out (inferred, marked *likely*) |
| AP10 | low | Agent image not pinned to a digest |

Details and fixes: https://braceframework.org/anti-patterns/

## Outputs

Text (default), JSON, SARIF 2.1.0 for GitHub code scanning, a Markdown summary, a GitLab
SAST report and JUnit XML. Secrets are redacted in all of them. Use `--output NAME=FILE`,
for example `--output sarif=results.sarif`. Exit code 0 means nothing at or above the
threshold, 1 means findings or an incomplete scan.

Silence a reviewed finding with `open-agent-security: ignore` on the line, an
`.open-agent-security-ignore` file or `.open-agent-security.toml`; suppressed findings
stay visible in SARIF and JSON.

## Documentation

Full guide (options, configuration, GitHub Action, pre-commit, GitLab CI, limits):
https://braceframework.org/tools/brace/SCAN.md (rules in detail:
https://braceframework.org/tools/brace/SCAN-DETAILS.md). Website: https://braceframework.org

A clean scan means none of these patterns was found. It is not a security review and not
BRACE compliance. For that, use [BRACE Starter](https://braceframework.org/starter/) or the
[sign-off checklist](https://braceframework.org/checklist/).

## Licence

Code: Apache License 2.0 (see LICENSE and NOTICE). BRACE documentation: CC BY 4.0.
