# open-agent-security: scanner rules in detail

The full specification behind the rules in [SCAN.md](SCAN.md): which agent CLI flags AP01 and
AP02 count, when a flag that is only mentioned is not reported, how the other rules read
agent configuration, what the scanner reads and skips, and how suppressed findings appear in
SARIF and JSON. [SCAN.md](SCAN.md) is the short guide to install, run, options and CI.

## Which flags count, and which mentions do not

A bypass value on its own (`CLAUDE_PERMISSION_MODE=bypassPermissions`,
`q.setPermissionMode("bypassPermissions")`, `MODE = "bypassPermissions"` then
`permission_mode=MODE`) is reported once per line, and not again on a line where the flag
that takes it was reported.

AP01 and AP02 count a bare `--yolo`, and Copilot CLI's `--allow-all-tools`,
`--allow-all-paths` and `--allow-all`, only as arguments of an agent CLI that takes them
(Gemini CLI, Qwen Code, Codex, Crush, Copilot), because object-detection tools and Deno use the
same flags. Such a flag counts when the CLI (`gemini`, `qwen`, `codex`, `copilot`, `crush`,
`gemini-cli`, `qwen-code`, also inside a URL or image such as
`npx https://github.com/google-gemini/gemini-cli` or `gemini-cli/sandbox:0.1.1`,
`@google/gemini-cli`, `@qwen-code/...`) is a word anywhere in the same simple command (split at `&&`, `||`, `;`, `|` and line breaks
not continued with `\`; in a JSON file also at string quotes), so wrappers such as `op run --`,
`docker run img`, `ssh box`, `find -exec`, `parallel` or `xvfb-run` do not hide it, unless that
word is an argument of an install command (`npm`/`pnpm`/`yarn`/`bun install|add|i`,
`pip`/`pipx`/`uv install`, `brew install`, `apt`/`apt-get`/`apk`/`yum`/`dnf install`). It also
counts as an item of a list whose earlier quoted item is the CLI, or of a list passed to a call
that names it (`spawn("gemini", [` then `"--yolo"` on the next line); in a JSON object or YAML
mapping whose `command:`, `cmd:` or `entrypoint:` is the CLI (compose, Kubernetes, Zed
`agent_servers`); when pushed onto a list (`args.push("--yolo")`, `.append`, `+= [...]`) that a
later spawn, exec or subprocess call passes with the CLI; when assigned (shell, Make, an env
file or YAML) to a variable or key whose name holds a gated CLI's name (`GEMINI_FLAGS="--yolo"`,
`GEMINI_ARGS := --yolo`, `QWEN_OPTS: --yolo`); and, in YAML, under a key that names
the CLI (`codex-args:`, `gemini_cli_args:`) or in a step that uses an agent action. So
`npm install -g @google/gemini-cli && apt-get install -y jq` and `deno run --allow-all x.ts &&
codex exec ...` count nothing. The short `-y` (Gemini CLI, Qwen Code, Crush) counts only after
the CLI, so `npx -y` does not. Codex's full-access sandbox counts in any spelling:
`--sandbox danger-full-access`, `sandbox_mode` (quoted once, three times or with escaped
quotes, as in `codex exec -c sandbox_mode=\"danger-full-access\"`), the TypeScript SDK's
`sandboxMode` and openai/codex-action's `sandbox:` input. In `.codex/config.toml` the parsed
`sandbox_mode` is read too, at the top level and in each `[profiles.<name>]`, and the finding
adds `approval_policy = "never"` when the same scope sets it. A gated flag's CLI must be the
program: a file or path named after it (`examples/gemini.ts`, `--out codex/`) or a flag's
value (`--provider gemini`) does not count, and for `-y` the CLI must be in command position.
Inside an agent action's step, `--yolo` and `--allow-all-tools` also count as the value of an
args key (`gemini_cli_args`, `codex-args`, `args`), never under `mcp_config`, `settings` or
`prompt`; `-y` counts only beside its CLI.

**This scanner errs toward reporting.** A missed bypass costs more than a false positive, and
a false positive is easy to silence after review: add `open-agent-security: ignore` on the
line, or list the file in `.open-agent-security-ignore` (see below). So a reviewed guard,
help text or test that names a bypass flag may be reported; silence it with an inline mark or
the ignore file. A bypass flag is treated as only mentioned, and not reported, in these forms
only, and the forms of the third and fifth items never apply in code whose logical command
(lines joined by `\`, `^` or backtick continuations) or enclosing call or list (the two
innermost open `(` or `[`) names an agent CLI or agent package:

- inside a comment, a Python docstring or a block comment (strings are skipped whole when
  looking for block comments: template literals with their `${...}`, Groovy and Kotlin, Java
  and Scala triple-quoted strings, Go and Rust raw strings); a block comment never hides a
  line whose command is an agent CLI;
- in documentation, which is prose and not read for these rules: Markdown (`.md`, `.mdx`,
  `.markdown`, `.mkd`), `.rst`, `.adoc`, `.asciidoc`, `.org`, `.txt` and `.tex` files;
  extensionless README, CHANGELOG, CHANGES, CONTRIBUTING, SECURITY, HISTORY, NEWS, AUTHORS,
  CONTRIBUTORS, LICENSE, COPYING, NOTICE, CODE_OF_CONDUCT, MAINTAINERS and TODO files (also
  with a suffix such as `LICENSE-MIT` or `README.txt`); HTML (`.html`, `.htm`) outside
  `<script>` bodies; `<!-- -->` comments in `.vue`, `.svelte`, `.xml` and `.xhtml`; a
  notebook's Markdown and raw cells (only code cells are read); and docs search indexes
  (`search-index.json`, `search_index.json`, `*.search.json`, anything under a `lunr*` or
  `pagefind*` folder, and a JSON file over 64 KB shaped like an MkDocs, Lunr or elasticlunr
  index). The exception: in Markdown files under `.claude/agents`, `.claude/commands`,
  `.claude/skills`, `.gemini/commands`, `.qwen/commands`, `.codex`, `.agents`,
  `.cursor/commands` and `.cursor/rules`, the YAML frontmatter (between a first line `---`
  and the next, within 64 KB) is read as YAML config: a bypass value
  (`permissionMode: bypassPermissions`) is AP01, and an `allowed-tools` entry that allows
  every shell command (`Bash`, `Bash(*)`) is AP06;
- as a quoted literal compared or searched for: `== "--flag"`, `!= "--flag"`, `"--flag" in x`,
  `"--flag" not in x`, `x in ("--a", "--flag")` (not `for x in`), `.includes(`, `.contains(`,
  `.has(`, `.indexOf(`, `.startsWith(`, `.endsWith(`, a `re.*(` or `RegExp(` pattern, a
  JavaScript or Ruby `/regex/` literal; an argument of `grep`, `egrep`, `fgrep`, `rg`, `ag`,
  `ack`, `findstr` or `Select-String` when that tool is the program of the flag's own simple
  command (in command position, case-sensitive, not inside a quoted string such as a prompt);
  a JavaScript `case '--flag':` label; and, in shell only (shell scripts, Makefiles,
  justfiles, shell start-up files and the YAML values and block scalars of `run`, `script`,
  `before_script`, `after_script` and `commands`), a `case` arm pattern (`--flag)` with no
  `(` or `[` open at it, the line before not continued, and a `case ... in` open on an
  earlier line of the same block, at most 200 lines up, or on the same line) or the right
  side of `==`, `!=`, `=~` or `=` (with spaces on both sides) in a `[[ ]]`, `[ ]` or `test`
  command in command position;
- as a value under Claude Code settings' `permissions.deny` or `permissions.ask`, in a JSON or
  YAML file whose name contains `settings`;
- as an item of a list assigned to a name whose last word is `block` (not in YAML, where
  `block:` is an Ansible block), `blocked`, `blocklist`,
  `deny`, `denied`, `denylist`, `forbid`, `forbidden`, `ban`, `banned`, `disallow`,
  `disallowed`, `reject` or `rejected` (`BLOCKED`, `deny`, `forbidden`), when the list names no
  agent CLI and, in code, every other use of the name in the file is a membership test
  (`x in NAME`, `any(f in cmd for f in NAME)`, `NAME.includes(x)`, `NAME.has(x)`); in JSON and
  YAML the key alone qualifies, and in YAML only when every item is a bare value (`- --flag`,
  not `- shell: ...`).

Everything else counts: help text, prompts, error messages and descriptions that name the flag
(even with words such as "never" or "do not"), a function argument in a test assertion
(`expect(validate("--flag"))`), a `"name": "--flag"` entry in a flags catalog, lists named
`BLOCKED_FLAGS`, `ask` or `UNSAFE_ARGS`, a lone quoted flag in an argument list and an item of
a `for` loop's list. Trailing comments are removed before a value is examined, so a comment
after a YAML value does not change how the value is read. Comment markers are found outside
quotes by the file kind's quoting rules: in shell (scripts, Makefiles, env files, Dockerfiles)
a backslash escapes outside quotes and in double quotes, and single quotes have no escapes
(`'\''` is a literal quote); in YAML, TOML, PowerShell and batch files single quotes have no
escapes; elsewhere a backslash escapes in single and double quotes, and in JavaScript,
TypeScript, Go and Kotlin backticks quote too. A trailing comment after code whose logical
command names an agent CLI or package is not removed (`claude -p hi # --flag` is reported); a
whole-line comment is. A deny-list's name is followed through the file with one identifier
index per file, for at most 200 distinct names (list names and pushed-to argument lists); past
that, a flag is reported rather than judged a mention.

Bypass mode written as JSON counts anywhere: nested under another key, inside a JSON string
(a devcontainer command that writes settings), or as the VS Code extension's
`claudeCode.initialPermissionMode`. In `.ini`, `.cfg` and `.service` files `;` starts a
comment only at the start of a line. A file's own report
format cannot hide anything either: only a whole `.json` or `.sarif` file that is exactly a
JSON, SARIF or GitLab SAST report from this scanner, or an `.xml` file that opens as its JUnit
report, is skipped, never a script, workflow, Dockerfile or agent config file. AP03 reads
workflows in `.github/workflows/` at any depth, so nested projects count, and follows a local
composite action (`uses: ./.github/actions/review`, its `action.yml` or `action.yaml`) or
reusable workflow (`uses: ./.github/workflows/claude.yml`) up to three levels, from the root
of the workflow's repository.

AP05 also checks every string of an agent config file (JSON, JSONC or `.codex/config.toml`),
up to 32 levels deep and 20,000 values: a known token format anywhere (`ghp_...`,
`Bearer ...`), or a credential-shaped value under a secret-named key (`apiKey`,
`clientSecret`, `bearer_token`). Codex's `http_headers` are read as a server's headers. A
value the server checks already report (env, headers, arguments, URL) is reported once.

AP04 also covers MCP servers run from a container: a `docker` or `podman` `run`/`create`
whose image has no `@sha256:` digest (`ghcr.io/org/server:latest`, or no tag at all) is
unpinned, and the finding names the image. The image is the first argument shaped like an
image reference that is neither a known flag's value (`docker run --help`'s value flags and
Podman's common ones) nor purely numeric (`--memory-swappiness 0`). A local image name with no
registry, namespace or tag (`postgres`) is still AP04, with the detail "local image; pin a
digest or build in CI".

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

## What the scanner reads and skips

- Standard library only, Python 3.11 or newer.
- It reads files and matches fixed patterns. It starts no server, runs no model and sends
  nothing over the network. Run it with `python -I` (as the GitHub Action does) and
  nothing in the scanned folder can be imported. To run the package as a module, use
  `python -I -m open_agent_security .`: plain `python -m` puts the current folder first on
  the import path, so a scanned repository's own `tomllib.py`, `argparse.py` or
  `open_agent_security/` would be imported. The `open-agent-security` command and the
  pre-commit hook are not affected.
- In the scanned folder it reads regular files up to 1 MB with these extensions: `.json`,
  `.jsonc`, `.json5`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.properties`,
  `.env`, `.py`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.mts`, `.cts`, `.sh`, `.bash`,
  `.zsh`, `.fish`, `.ps1`, `.bat`, `.cmd`, `.go`, `.rs`, `.rb`, `.java`, `.kt`, `.scala`,
  `.groovy`, `.php`, `.cs`, `.swift`, `.lua`, `.pl`, `.c`, `.h`, `.cpp`, `.ex`, `.exs`,
  `.dart`, `.vue`, `.svelte`, `.html`, `.nix`, `.tf`, `.hcl`, `.ipynb`, `.code-workspace`,
  `.service`, `.j2`, `.jinja`, `.tpl`, `.txt`, `.md` and `.mk` (documentation among them is
  prose for AP01 and AP02; see above); also Makefiles (`Makefile`,
  `GNUmakefile`), justfiles, `Procfile`, Dockerfiles (`Dockerfile`, `Containerfile`,
  `Dockerfile.<tag>`, `*.dockerfile`, `*.containerfile`), `.env` files, shell start-up files
  (`.zshrc`, `.bashrc`, `.bash_aliases`, `.bash_profile`, `.zprofile`, `.profile`, `.envrc`,
  `.zshenv`, with `#` comments) and extensionless scripts that start with `#!`; names are
  compared without regard to case. Any other regular file up to the size limit, except
  documentation, is searched for bypass markers (`--dangerously-skip-permissions`,
  `--dangerously-bypass-approvals-and-sandbox`, `bypassPermissions`, `danger-full-access`,
  `sandbox_mode`, `--allow-all-tools`, `--allow-all-paths`, `--yolo`, `--approval-mode`,
  `--dangerously-allow-all`, `--yes-always`) as bytes, and read as text when it holds one, so
  no file kind hides a bypass. An oversized documentation file holding a marker does not make
  the scan incomplete. `.pytest_cache`, `.mypy_cache` and
  `.ruff_cache` folders are not entered, like `__pycache__`.
  It never follows symlinks and never opens FIFOs or other special files (each file is checked
  with `lstat` right before it is opened and with `fstat` after, and refused if the two differ,
  so this holds on Windows too, where `O_NOFOLLOW` and `O_NONBLOCK` do not exist; a file
  swapped for a symlink between the two calls is caught by the comparison); it lists them in
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
  `AUTH_URL`, `KEY_ID`, `PRIMARY_KEY_COLUMN`). In agent configuration outside server entries
  (every other value of the file is walked), the test is stricter, since most keys there are
  not about credentials: a known token format counts anywhere; `Bearer ` or `Basic `
  (case-sensitive) only under a header-like key (`authorization`, `*auth*`, `headers`) or as
  the whole value; a name whose last word is `key` only with a qualifying word (`api`,
  `secret`, `access`, `private`, `signing`, `auth`, `client`, `service`, `master`,
  `encryption`), so `projectKey`, `cacheKey`, `sortKey`, `primaryKey`, `apiKeyHelper` and
  `keybindings` are not secrets; and a value that reads as a lower-case path
  (`scripts/get-key-v2`) or as prose (three or more words) is never reported unless it holds a
  known token format. Treat redaction as a safeguard, not a guarantee for every secret format.
- `--host` reads the MCP config files of Claude Desktop, Claude Code, Cursor, VS Code,
  Windsurf and Devin Desktop, and `~/.claude/settings.json`, following symlinks and up to
  5 MB each. It shows paths under your home folder as `~/`.

## Suppressed findings in SARIF and JSON

A suppressed finding is not dropped: JSON always lists it, and SARIF lists it with
`--sarif-suppressed` (or `sarif-suppressed = true` in the config file), so every
suppression can be audited. It never counts towards the verdict, the exit code, the headline or the findings
count. Each one says how it was suppressed:

| Suppressed by | Kind | Justification | Location |
|---|---|---|---|
| an inline `open-agent-security: ignore` mark | `inSource` | `inline 'open-agent-security: ignore' mark on line 4` | the marked line |
| a rule-scoped entry in `.open-agent-security-ignore` | `external` | `.open-agent-security-ignore entry 'AP10 legacy/Dockerfile'` | the entry's line |
| a config `ignore` entry | `external` | its `reason`, or `config ignore entry 'fixtures/' in .open-agent-security.toml` | not given |
| a rule turned off in the config | `external` | `rule AP10 turned off in .open-agent-security.toml` | not given |

A rule turned off still runs, so its findings can be listed; if its check fails, that is a
note rather than an incomplete scan. An entry that ignores a path for every rule skips the
file or folder unread, so nothing in it was found and nothing is listed; such files and
folders are counted in the note, as before. Suppressed findings are redacted and cut
exactly like reported ones (justifications too, since they quote the scanned folder's
files), and keep the `id` (SARIF fingerprint) they would have unsuppressed, so removing a
suppression does not open a "new" alert in a consumer that uses that fingerprint. At most
5,000 are listed; past that they are only counted, with a note.

By default SARIF leaves suppressed findings out and adds a notification such as `3
suppressed findings are not listed; see the JSON output or use --sarif-suppressed`; the
invocation's `suppressed` property counts them either way. With `--sarif-suppressed`, a
suppressed finding is a normal result (same `ruleId`, `level`, message, location
and fingerprint) with `suppressions` (SARIF 2.1.0 §3.27.23, §3.35):

```json
"suppressions": [{
  "kind": "external", "status": "accepted",
  "justification": "pinned upstream",
  "location": {"physicalLocation": {"artifactLocation": {"uri": ".open-agent-security-ignore", "uriBaseId": "%SRCROOT%"}, "region": {"startLine": 2}}}
}]
```

In JSON, it is in `suppressed_findings` with the keys of a finding plus `suppression`:
`{"kind": "inSource", "justification": "...", "file": "run.sh", "line": 4}` (`file` and
`line` are null when not known).

What consumers do with them:

- **GitHub code scanning**: GitHub's SARIF support and alert documentation does not
  mention `result.suppressions`, so we can't say how an uploaded suppressed result is shown;
  it may appear as an open alert, an error-level one may fail the code scanning check, and
  a rule turned off would still alert once per finding. GitHub's documentation also says
  code scanning computes its own `primaryLocationLineHash` fingerprint rather than using
  this scanner's, and keeps only the top 5,000 results per run, by severity. Leave
  suppressed findings out of uploads to GitHub (the default; the Action passes
  `--no-sarif-suppressed`).
- **GitLab** does not read SARIF, and its SAST report has no suppression field, so the
  gitlab-sast output leaves suppressed findings out (the JSON output still lists them).
- **Other SARIF tools**: whether a tool honours SARIF suppressions is up to the tool, and
  we have not confirmed the behaviour of specific ones (Microsoft SARIF viewers,
  DefectDojo, Azure DevOps and others are unknown). A tool that ignores the
  `suppressions` property shows these results as ordinary ones. Check your tool's SARIF
  import documentation, and try it on a test upload, before turning on
  `--sarif-suppressed`.
