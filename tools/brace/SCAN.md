# open-agent-security

Find known-dangerous AI agent setups in a repository, in seconds. Part of the
[BRACE framework](https://braceframework.org) for securing AI agents.

```bash
uvx open-agent-security .            # or: pipx run open-agent-security .
uvx open-agent-security . --host     # also check the agent settings on this machine
```

It reports each problem with its file and line, why it matters and how to fix it:

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
| AP09 | medium | Lethal combination: untrusted input, private data and a way out (inferred from server and package names, marked *likely*) |
| AP10 | low | Agent image not pinned to a digest (Dockerfiles, in repositories that contain an agent) |

Details and fixes: https://braceframework.org/anti-patterns/

AP01 and AP02 count a bare `--yolo`, and Copilot CLI's `--allow-all-tools` and `--allow-all`,
only as arguments of an agent CLI that takes them (Gemini CLI, Qwen Code, Codex, Crush,
Copilot), because object-detection tools and Deno use the same flags. Such a flag counts when
the CLI (`gemini`, `qwen`, `codex`, `copilot`, `crush`, `@google/gemini-cli`, `@qwen-code/...`)
is a word anywhere in the same simple command (split at `&&`, `||`, `;`, `|` and line breaks
not continued with `\`; in a JSON file also at string quotes), so wrappers such as `op run --`,
`docker run img`, `ssh box`, `find -exec`, `parallel` or `xvfb-run` do not hide it, unless that
word is an argument of an install command (`npm`/`pnpm`/`yarn`/`bun install|add|i`,
`pip`/`pipx`/`uv install`, `brew install`, `apt`/`apt-get`/`apk`/`yum`/`dnf install`). It also
counts as an item of a list whose earlier quoted item is the CLI, or of a list passed to a call
that names it (`spawn("gemini", [` then `"--yolo"` on the next line); in a JSON object or YAML
mapping whose `command:`, `cmd:` or `entrypoint:` is the CLI (compose, Kubernetes, Zed
`agent_servers`); when pushed onto a list (`args.push("--yolo")`, `.append`, `+= [...]`) that a
later spawn, exec or subprocess call passes with the CLI; and, in YAML, under a key that names
the CLI (`codex-args:`, `gemini_cli_args:`) or in a step that uses an agent action. So
`npm install -g @google/gemini-cli && apt-get install -y jq` and `deno run --allow-all x.ts &&
codex exec ...` count nothing. The short `-y` (Gemini CLI, Qwen Code, Crush) counts only after
the CLI, so `npx -y` does not. Codex's full-access sandbox counts in any spelling:
`--sandbox danger-full-access`, `sandbox_mode`, the TypeScript SDK's `sandboxMode` and
openai/codex-action's `sandbox:` input.

**This scanner errs toward reporting.** A missed bypass costs more than a false positive, and
a false positive is easy to silence after review: add `open-agent-security: ignore` on the
line, or list the file in `.open-agent-security-ignore` (see below). So a reviewed guard,
help text or test that names a bypass flag may be reported; silence it with an inline mark or
the ignore file. A bypass flag is treated as only mentioned, and not reported, in these forms
only:

- inside a comment, a Python docstring or a block comment (strings are skipped whole when
  looking for block comments: template literals with their `${...}`, Groovy and Kotlin, Java
  and Scala triple-quoted strings, Go and Rust raw strings); a block comment never hides a
  line whose command is an agent CLI;
- in Markdown files, which are not read for these rules;
- as a quoted literal compared or searched for: `== "--flag"`, `!= "--flag"`, `"--flag" in x`,
  `"--flag" not in x`, `x in ("--a", "--flag")` (not `for x in`), `.includes(`, `.contains(`,
  `.has(`, `.indexOf(`, `.startsWith(`, `.endsWith(`, a `re.*(` or `RegExp(` pattern, a
  JavaScript or Ruby `/regex/` literal; an argument of `grep`, `egrep`, `fgrep`, `rg`, `ag`,
  `ack`, `findstr` or `Select-String`; a shell `case` pattern (`--flag)`); a JavaScript
  `case '--flag':` label; or the right side of `==`, `!=`, `=~` or `=` in `[[ ]]`, `[ ]` or
  `test`;
- as a value under Claude Code settings' `permissions.deny` or `permissions.ask`, in a JSON or
  YAML file whose name contains `settings`;
- as an item of a list assigned to a name whose last word is `block`, `blocked`, `blocklist`,
  `deny`, `denied`, `denylist`, `forbid`, `forbidden`, `ban`, `banned`, `disallow`,
  `disallowed`, `reject` or `rejected` (`BLOCKED`, `deny`, `forbidden`), when the list names no
  agent CLI and, in code, every other use of the name in the file is a membership test
  (`x in NAME`, `any(f in cmd for f in NAME)`, `NAME.includes(x)`, `NAME.has(x)`); in JSON and
  YAML the key alone qualifies.

Everything else counts: help text, prompts, error messages and descriptions that name the flag
(even with words such as "never" or "do not"), a function argument in a test assertion
(`expect(validate("--flag"))`), a `"name": "--flag"` entry in a flags catalog, lists named
`BLOCKED_FLAGS`, `ask` or `UNSAFE_ARGS`, a lone quoted flag in an argument list and an item of
a `for` loop's list. Trailing comments are removed before a value is examined, so a comment
after a YAML value does not change how the value is read.

Bypass mode written as JSON counts anywhere: nested under another key, inside a JSON string
(a devcontainer command that writes settings), or as the VS Code extension's
`claudeCode.initialPermissionMode`. In `.ini` and `.cfg` files `;` starts a comment only at
the start of a line. A file's own report
format cannot hide anything either: only a whole `.json` or `.sarif` file that is exactly a
JSON, SARIF or GitLab SAST report from this scanner is skipped, never a script, workflow,
Dockerfile or agent config file. AP03 reads
workflows in `.github/workflows/` at any depth, so nested projects count.

MCP servers are read from these formats:

| File | Where the servers are |
|---|---|
| `.mcp.json`, `mcp.json`, `.cursor/mcp.json`, `.roo/mcp.json`, `mcp_config.json`, `claude_desktop_config.json`, `cline_mcp_settings.json`, `.gemini/settings.json`, `.qwen/settings.json`, any other JSON | `mcpServers` (also `mcp_servers`, and `projects.<path>.mcpServers` in `~/.claude.json`) |
| `.vscode/mcp.json` and other files named `*mcp*` | `servers` |
| `.vscode/settings.json` | `mcp.servers`, and Amp's `amp.mcpServers` |
| `.amp/settings.json` | `amp.mcpServers` (a literal dotted key) |
| `opencode.json`, `opencode.jsonc` | `mcp` (`command` is a list; env is `environment`) |
| `crush.json`, `.crush.json` | `mcp` |
| `.zed/settings.json` | `context_servers` (`command` may be `{path, args, env}`) |
| `.codex/config.toml` | `[mcp_servers.<name>]` and `[mcp_servers.<name>.env]` tables |

An agent config file that does not parse makes the scan incomplete.

## Safe to run

- Standard library only, Python 3.11 or newer.
- It reads files and matches fixed patterns. It starts no server, runs no model and sends
  nothing over the network. Run it with `python -I` (as the GitHub Action does) and
  nothing in the scanned folder can be imported. To run the package as a module, use
  `python -I -m open_agent_security .`: plain `python -m` puts the current folder first on
  the import path, so a scanned repository's own `tomllib.py`, `argparse.py` or
  `open_agent_security/` would be imported. The `open-agent-security` command and the
  pre-commit hook are not affected.
- In the scanned folder it reads regular files up to 1 MB with known config and source
  extensions, Makefiles (`Makefile`, `GNUmakefile`, `*.mk`), justfiles, Dockerfiles
  (`Dockerfile`, `Containerfile`, `Dockerfile.<tag>`, `*.dockerfile`), `.env` files, shell
  start-up files (`.zshrc`, `.bashrc`, `.bash_aliases`, `.bash_profile`, `.zprofile`,
  `.profile`, `.envrc`, `.zshenv`, with `#` comments) and extensionless scripts that start
  with `#!`; names are compared without regard to case.
  It never follows symlinks and never opens FIFOs or other special files; it lists them in
  a note, and the headline then says some files could not be read. A symlink to a path
  inside the scanned folder that the walk reads anyway (`CLAUDE.md -> AGENTS.md`,
  `.claude/skills -> ../.agents/skills`) hides nothing: it is counted in a note only. A
  symlinked folder named for agent config or CI (`.claude`, `.github`, ...) still counts as
  skipped, since its files would lose that role. Ignore entries apply to symlinks too. A NUL byte alone does
  not make a file binary: otherwise printable text is read with its NULs removed.
- The scan is incomplete (exit code 1 unless `--fail-on none`) when it cannot read a file
  the rules need: agent config, a CI file or workflow, a Dockerfile or a script, whether it
  is too large, unreadable or a symlink; an oversized file that contains a bypass flag; or
  an unreadable folder that could hold them (the scanned folder itself, `.claude`, `.github`,
  `.gemini`, `.qwen`, `.codex`, `.cursor`, `.vscode`, `.roo`, `.zed`, `.gitlab`, `.circleci`,
  `.buildkite`, `.tekton`, `.woodpecker` and the folders inside them).
- It does not enter version-control and cache folders (`.git`, `.hg`, `.svn`,
  `__pycache__`) or dependency folders (`node_modules`, `site-packages`, and `.venv` or
  `venv` when it holds a `pyvenv.cfg`); a note counts the folders skipped. A real `.git`
  folder (one with a `HEAD` file) is skipped without a note. Every other folder is scanned,
  tool caches such as `.cache`, `.idea` and `.next` included.
- Known token formats (GitHub, OpenAI, Anthropic, AWS, Slack tokens and webhook URLs,
  GitLab, Google, Stripe, npm, PyPI, Hugging Face, Notion, Zapier `sk-ak-`, JWTs, PEM private
  keys and inline Google Cloud service-account keys), credentials after `Bearer`, `Basic`,
  `Authorization:` or `X-Api-Key:`, and values under secret-looking names are reported as
  secrets and replaced with
  `<redacted>` in finding details, in every output format, and so are user names and
  passwords inside URLs (`https://<redacted>@host`); file names are shown as they are.
  Names are judged wherever they appear: env keys (`"BRAVE_API_KEY": "BSA..."`), header names
  (`"X-API-Key": "..."`), URL query parameters (`?api_key=...`), `KEY=value` arguments
  (`docker -e API_TOKEN=...`), Claude Code settings `env`, and flags (`--api-key=...`,
  `--token ...`). A secret-looking name has a word that is `key`, `pass`, `pwd`, `auth`,
  `authorization` or `cred`, or ends with `token`, `secret`, `password`, `passwd`,
  `passphrase`, `credential`, `apikey`, `accesskey`, `privatekey`, `secretkey`, `authkey`
  or `oauth` (`API_KEY`, `authToken`, `PGPASSWORD`), and no word
  `public` or `publishable`. Its value must be 16 or more characters mixing letters and
  digits, or, when a word holds `pass` or `pwd` or ends with `secret`, any 8 or more printable
  characters (`"NEO4J_PASSWORD": "correct-horse-battery"`). Stripe test keys are reported as
  test keys. Obvious placeholders
  (`YOUR-TOKEN`, `ghp_xxxx…`), references to a secret kept elsewhere (`${VAR}`, `$VAR`,
  `%VAR%`, `{{...}}`, `env:...`, `op://...`), URLs, file paths, numbers and booleans are not
  reported, nor are names that end by saying what else the value is (`TOKEN_FILE`,
  `AUTH_URL`, `KEY_ID`, `PRIMARY_KEY_COLUMN`). Treat redaction as a safeguard, not a guarantee
  for every secret format.
- `--host` reads the MCP config files of Claude Desktop, Claude Code, Cursor, VS Code,
  Windsurf and Devin Desktop, and `~/.claude/settings.json`, following symlinks and up to
  5 MB each. It shows paths under your home folder as `~/`.

## Options

| Option | Meaning |
|---|---|
| `--fail-on LEVEL` | Exit 1 when a finding is `critical`, `high` (default), `medium` or `low` or worse, or when the scan is incomplete. `none` exits 0 unless the scan could not run. |
| `--json` | Print JSON instead of text (the same as `--output json=-`). |
| `--output NAME=FILE` | Also write the `NAME` report to `FILE`: `text`, `json`, `sarif`, `markdown`, `gitlab-sast`, `junit`, or a loaded plugin's. Repeat it for more than one. `FILE` `-` replaces the report on standard output. Markdown appends to `FILE`; the others replace it. |
| `--sarif FILE` | Also write SARIF 2.1.0 for GitHub code scanning (the same as `--output sarif=FILE`). |
| `--markdown FILE` | Also append a Markdown summary, for example to `$GITHUB_STEP_SUMMARY` (the same as `--output markdown=FILE`). |
| `--host` | Also read the agent settings on this machine. |
| `--config FILE` | Read settings from FILE instead of `.open-agent-security.toml` in the scanned folder. |
| `--no-config` | Ignore `.open-agent-security.toml`. |
| `--list-rules` | List the rules with their severity after config and plugins, then exit. Add `--json` for JSON. |
| `--plugin NAME` | Load an installed plugin. Repeat it for more than one. See [Plugins](#plugins). |
| `--version` | Print the version. |

Exit codes: 0 means nothing at or above the threshold, 1 means findings or an incomplete
scan, 2 means bad arguments (an unknown `--output` name included), a path that isn't a
folder, a config file or plugin that can't be used, or an output file that can't be
written, and 3 means an internal error.

## Output formats

File paths in every format are relative to the current folder when the scanned folder is
inside it, otherwise to the scanned folder. Secrets are redacted in all of them. Machine
formats (JSON, SARIF, GitLab SAST, JUnit) keep each path exactly, however long, with bytes
that are not UTF-8 written as `\xNN` (as `%NN` in a SARIF URI); text and Markdown show it
printable and cut to 300 characters. Reports the scanner wrote itself (JSON, SARIF, GitLab
SAST or JUnit) found in the scanned folder are not scanned, and a note counts them.

- **text** (the default): grouped by rule, with why and how to fix.
- **json**: every finding with its rule's title, why, fix and checklist items, plus
  `truncated`, `incomplete`, `notes`, `suppressed` and `config`. The shape is described by
  a JSON Schema shipped in the package, `open_agent_security/report/schema/report-1.schema.json`,
  which the `schema` key names. Keys may be added; existing ones keep their meaning while
  the schema stays at version 1. Each finding has an `id`: a hash of the rule, the path in
  the scanned folder, the redacted detail and which occurrence it is, so it stays the same
  when lines move and never hashes a raw secret.
- **sarif**: SARIF 2.1.0 for GitHub code scanning and other SARIF tools. Each result carries
  the same `id` as a `partialFingerprints` entry (`openAgentSecurity/v1`) and a `%SRCROOT%`
  base. Rules have readable names, Markdown help, `security-severity`, CWE tags
  (`external/cwe/cwe-798`) and relationships to the OWASP Top 10 for Agentic Applications
  (2026), the OWASP MCP Top 10 (2025), MITRE ATLAS (v2026.10) and CWE entries, derived from
  the BRACE mappings ([OWASP Agentic](https://braceframework.org/mappings/owasp-agentic-top-10/),
  [OWASP MCP](https://braceframework.org/mappings/owasp-mcp-top-10/),
  [ATLAS](https://braceframework.org/mappings/mitre-atlas/)). The invocation always says
  whether the scan was complete and how many findings were suppressed, lists the notes
  (gaps as warnings), and counts findings on this machine (`--host`), which SARIF leaves out.
  At most 5,000 results are listed, with a note when there are more.
- **markdown**: a summary table for a pull request or job summary, at most 200 rows.
- **gitlab-sast**: a GitLab SAST report (schema 15.2.5) for merge request security widgets;
  GitLab does not read SARIF. Host findings are left out, as in SARIF. GitLab deduplicates
  findings by their location (file and lines) and identifiers. Findings of one rule on the
  same line each get an identifier of their own (their fingerprint, after the rule
  identifier, which stays primary), their detail in the name and their short id in
  `location.method`; GitLab may still show them as one vulnerability, so read the JSON or
  text output for every finding on such a line.
- **junit**: JUnit XML for CI dashboards: a failed test case per finding, a passed one per
  rule without findings, and a "the scan is complete" case that is an error when the scan
  is incomplete.

Skipped files are listed as notes: files over 1 MB, binary or unreadable files (including
bytes that start like UTF-16 but are not), symlinks and special files, and agent config
files that don't parse. The scan is **incomplete** when a file the rules need was skipped:
an agent config file (`.mcp.json`, `mcp.json`, `claude_desktop_config.json`,
`.claude/settings.json`, or an `agent-config` entry, also when it is a symlink, or a
symlinked folder that holds agent config or CI, unless an ignore entry matches it), a CI
file or workflow, a Dockerfile or a shell
script. It is also incomplete when an agent config file didn't parse, when the scan stopped
at 200,000 files, or when one check found more than 100 findings in one file (the rest are
not shown). An incomplete scan never reports itself clean, and it fails unless
`--fail-on none`. When other files were skipped, the scan is complete but the headline says
how many files could not be read instead of reporting the folder clean.

JSON with comments, trailing commas or a byte-order mark (JSONC, as VS Code uses) is read
normally, and so are UTF-16 files with a byte-order mark and any line-ending style.

## Silencing a reviewed finding

- Add `open-agent-security: ignore` on the reported line, normally in a comment. This works
  in any file that allows comments, JSONC included.
- Or list entries in `.open-agent-security-ignore` at the root of the scanned folder:

```text
# Comments start with #.
fixtures/              # a folder, at any depth
/build/out.sh          # a leading / anchors the pattern to the scanned folder
docs/**/*.sh           # * stays within one folder; ** crosses folders
vendor/**              # everything inside vendor/ (as in git, not a file named vendor)
!fixtures/keep.sh      # ! brings a path back
AP04 .mcp.json         # a rule ID first limits the entry to that rule
```

The file holds at most 200 entries of at most 200 characters and 16 folders each; later
or longer lines are not read, and patterns of more than 16 folders are skipped with a
note. A rule ID can be a plugin's (`ACME01` or `ACME-01 path`): capital letters, digits,
`_` and `-`, starting with a letter. An ID that no loaded rule has matches nothing and is
named in a note. An ignore file that is a symlink, larger than the file size limit or
unreadable is not applied, and a note says so.

Whatever hides findings or files is always shown, in every output format: when the ignore
file or the config file has entries, rules are off or re-rated, inline marks suppressed a
finding, or limits were lowered, the scan adds a note such as `.open-agent-security-ignore:
2 entries; inline ignore marks: 1 finding; 3 findings suppressed; 4 files and 1 folder not
scanned because of ignore entries`.

## Configuration file

Put `.open-agent-security.toml` at the root of the scanned folder. It is optional and read
only from that folder (never from a parent or your home folder). Every key is optional:

```toml
version = 1
fail-on = "high"                         # the command line's --fail-on wins
include = ["deploy/*.tpl"]               # more files to read as text
agent-config = ["config/mcp.*.json"]     # more files to treat as agent config

[rules]                                  # off, or a different severity
AP10 = "off"
AP07 = "high"

[[ignore]]
path = "fixtures/"

[[ignore]]
path = ".vscode/mcp.json"
rules = ["AP04"]
reason = "reviewed"

[[tokens]]
name = "acme"
prefix = "acme_"
charset = "alnum"
min = 24
max = 200

[limits]
max-file-bytes = 1048576
max-files = 200000
```

- Command-line flags override the file, and the file overrides the defaults. The GitHub
  Action always passes `--fail-on`, so a pull request cannot lower its gate. When `fail-on`
  comes from the file, a note says so and names the value.
- `ignore` paths use the same patterns as `.open-agent-security-ignore`, which still works;
  both lists apply, and a leading `/` anchors an `ignore` path to the scanned folder.
  `include` and `agent-config` patterns must stay inside the scanned folder: no absolute
  paths and no `..`. Agent config is read as JSON or JSONC, so an `agent-config` pattern that
  names a `.yaml`, `.yml` or `.toml` file is an error (Codex's `.codex/config.toml` is read
  without one). A pattern may have at most 16 folders, and
  `ignore` may expand to at most 1,000 path-and-rule pairs; more is an error. An agent config file that doesn't parse makes the
  scan incomplete.
- `tokens` adds secret formats to detect and redact: a literal `prefix` followed by `min`
  to `max` (8 to 400) characters of one `charset`: `alnum`, `alnum-dash`, `hex` or
  `base64`. Regular expressions are not accepted.
- `limits` can be lowered freely; a lowered limit is listed in the suppression note. Higher
  values are capped at 16 MB and 1,000,000 files, with a note.
- A file that is not valid TOML, an unknown key, an unknown rule ID or a bad value stops
  the scan with exit code 2.
- What the file turns off is shown: the scan adds a note such as `config
  .open-agent-security.toml: 1 rule off, 2 ignore entries; 3 findings suppressed; 1 file
  not scanned because of ignore entries`. `ignore` holds at most 200 entries. JSON
  output has `config` (the file used, or null) and `suppressed` (findings dropped by ignore
  entries, inline marks or rules turned off).
- The file cannot load plugins. A `plugins` key is ignored with a note.

## Plugins

A plugin is an installed Python package that adds rules and checks. It exposes a
`register(registry)` function as an entry point in the `open_agent_security.plugins` group.
Installed plugins are never loaded unless you name them with `--plugin NAME` or in the
`OPEN_AGENT_SECURITY_PLUGINS` environment variable (comma-separated). Nothing in the
scanned folder can load one, and there is no way to load a plugin from a path.

A loaded plugin is ordinary Python running with your full rights; there is no sandbox.
Install only plugins you trust. Plugin rule IDs cannot use the `APnn` form, which is kept
for built-in rules. If a plugin check fails, the scan notes it and is incomplete. The GitHub
Action runs built-in rules only.

The plugin API (`Registry`, `RuleMeta`, `Finding`, and the `Collector`, `Parser`, `Check`
and `Reporter` interfaces in `open_agent_security/plugin.py`) is provisional and may change
in a minor release. A plugin reporter is chosen with `--output NAME=FILE`; it declares
`media = "json"` or `"text"` so the scanner can make its output safe in a GitHub Actions log
(text is assumed), and `appends = True` to append to `FILE`.

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: brace-ai-security/open-agent-security@v3.1.1   # or pin a commit SHA
  with:
    fail-on: high          # critical | high | medium | low | none
    upload-sarif: "false"  # "true" needs permissions: security-events: write
    # category: open-agent-security   # set a different one per scan in the same workflow
```

The Action uses the runner's preinstalled Python unless you set `python-version`. It
writes SARIF to the runner's temporary folder and outputs `findings`, `incomplete` and
`sarif`. File and server names come from the scanned repository, so the Action turns off
workflow commands (`::error::`, `::add-mask::`) while the scanner prints, with a random
token, and under `GITHUB_ACTIONS` the text output and error messages also break up any
`::` at the start of a line and any `##[`, and JSON output writes `#` as `\u0023`. The
Action clears `OPEN_AGENT_SECURITY_PLUGINS`, so it runs built-in rules only. The job summary lists at most 200 findings and SARIF at most
5,000 (with a note when there are more); the JSON output has all of them.

## pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/brace-ai-security/open-agent-security
    rev: v3.1.1   # or a commit SHA
    hooks:
      - id: open-agent-security
```

The hook scans the whole repository on every commit, because AP10 depends on more than
one file (a Dockerfile counts only in a repository that contains an agent).

## GitLab CI

```yaml
# .gitlab-ci.yml
open-agent-security:
  image: python:3.12-slim
  script:
    - pip install open-agent-security
    - open-agent-security . --fail-on high --output gitlab-sast=gl-sast-report.json --output junit=junit.xml
  artifacts:
    when: always
    reports:
      sast: gl-sast-report.json
      junit: junit.xml
```

## Limits

A clean scan means none of these patterns was found. It is not a security review and not
BRACE compliance. For that, use [BRACE Starter](https://braceframework.org/starter/) or the
full [sign-off checklist](https://braceframework.org/checklist/).
