# brace.py — the BRACE sign-off checker

`brace.py` checks the supplied `.brace/` evidence record against the [BRACE checklist](../../CHECKLIST.md). High-stakes, high-autonomy or unrated deployments return **FINDINGS**; lower-risk deployments keep GO/NO-GO record results. How results are worded, and why exit code 0 never authorizes deployment, is stated once in [TOOLS.md](../../TOOLS.md#how-results-are-worded).

It checks the record. It does not test your agent. The evidence links in the record
point to the tests you ran (see the [verification guide](../../CHECKLIST-VERIFICATION.md)).

## Install

You need Python 3.10 or newer and PyYAML (3.11 or newer for `brace.py scan`, the
open-agent-security scanner). `jsonschema` is optional; without it, `brace.py` uses a small
built-in validator.

    pip install pyyaml jsonschema

Copy (vendor) this whole `tools/brace/` folder into your repository at `tools/brace/`.
Keeping the checker in your repository means it is reviewed and versioned with your code.

## Start a record

    python tools/brace/brace.py init

This creates `.brace/` with:

| File | What it is |
|---|---|
| `deployment.yaml` | What the agent does, its stakes and autonomy rating, who holds each role, and who may approve. |
| `record.yaml` | All 53 checklist items, each starting as `not_reviewed`. The `lead` placeholder names the role that usually leads the item ([ROLES.md](../../ROLES.md)). |
| `manifest.yaml` | The inputs that define the agent type: container, harness, prompt, model, config. |
| `exceptions/` | One file per accepted risk. |
| `na/` | One file per item that doesn't apply. |

`init` won't overwrite an existing `.brace/` folder.

## Fill it in

For each item in `record.yaml`, set `outcome` to one of:

- `pass` — add at least one `evidence` entry with a `link` and a `date`.
- `gap` — the item isn't met. What happens next depends on its gate:
  - **Blocker**: an open, non-waivable finding; blocks a lower-risk record GO.
  - **Required**: add a risk acceptance file in `.brace/exceptions/` and set `exception:` to its name (without `.yaml`).
  - **Detection**: remains an open finding when stakes or autonomy are high. Otherwise, treat it like Required.
- `na` — add a file in `.brace/na/` with the reason, evidence, and reviewer, and set `na:` to its name.

Exception files have no expiry date. They stay until someone removes them, and the
re-review rules in the checklist decide when to look again.

## Check

    python tools/brace/brace.py check

Options:

- `--dir PATH` — the repository root that holds `.brace/` (default: the current folder).
- `--approvals github|git|off` — how to check approvals (see below).
- `--strict` — treat an approval that couldn't be verified as blocking. Use this in CI.
- `--json FILE` — also write the result as JSON (`-` prints it). The JSON has
  `decision` (`FINDINGS` for high-risk/unrated deployments), `notice`, `reasons`, `warnings`, `counts`, and one entry per item. Consumers that assumed `decision` has only GO/NO-GO must handle FINDINGS explicitly. Item status `blocked` means an unresolved record condition, not a high-risk deployment veto.

The checker reports unresolved record conditions (exit 1) when:

1. a file doesn't match its schema (this is exit code 2, not a NO-GO);
2. the stakes and autonomy rating is missing or incomplete;
3. any of the 53 items is missing or still `not_reviewed`;
4. a `pass` has no evidence with both a link and a date;
5. an `na` has no N/A file, the file is for another item, or it lacks a reason, evidence, or reviewer;
6. a `gap` breaks its gate rule, or its risk acceptance is missing, for another item, incomplete, or not approved;
7. any exception file exists for a Blocker item, or for a Detection item on a high-stakes or high-autonomy deployment;
8. the agent-type-id in `deployment.yaml` no longer matches `manifest.yaml`.

## Export for auditors and questionnaires

    python tools/brace/brace.py export --format html --output brace-record.html
    python tools/brace/brace.py export --format csv  --output brace-record.csv
    python tools/brace/brace.py export --format json --output brace-record.json

One row per checklist item: ID, title, gate, outcome, the check's status and problems, lead,
evidence links with dates, the latest evidence date, and for a risk acceptance or N/A decision
its file, approver (`accepted_by` or `reviewer`), date, tracking link and reason. Exception and
N/A files have no expiry field, so the `expires` column stays empty unless a file adds one. The
deployment's name, environment, release, checklist date, stakes and autonomy rating and
agent-type-id head the export, with the check's decision and notice.

- `--format html` is one self-contained, print-friendly page: inline CSS, no scripts and no
  external resources (its Content-Security-Policy allows none). Every value is HTML-escaped
  and only `http(s)` links become links.
- `--format csv` joins lists with ` | ` and prefixes a cell that a spreadsheet would run as a
  formula with `'`.
- `--approvals` (default `off`) sets how the status column verifies approvals, as in `check`;
  the export records which mode it used. Exit code 2 when the record is invalid; otherwise 0,
  whatever the outcomes (run `check` to gate).

Framework mappings are published as JSON next to their pages (`mappings/*.json`, generated
from the Markdown tables by `tools/site/gen_mappings_json.py`), so a questionnaire or GRC tool
can import which BRACE items address each OWASP, NIST AI RMF, ISO/IEC 42001 or MITRE ATLAS
entry.

## Approval model

A name typed into a file doesn't prove anyone approved it. So `brace.py` doesn't trust
`accepted_by` or `reviewer`. Instead, an exception or N/A file counts as approved only if:

- the **latest commit that changed the file** is part of a **merged pull request**;
- that pull request has an **approving review** from someone in `approvals.approvers`
  (a user like `@carol`, or any active member of a team like `@acme/ai-governance`);
- the approver **did not open** the pull request; and
- the file is **unchanged** since the approving review. If someone edits the file
  later, it needs a new approved pull request.

During a pull request run, the pull request being checked also counts before it is
merged, with a warning. The workflow re-runs when a review is submitted.

Approval modes:

| Mode | What it checks |
|---|---|
| `github` | Everything above, using the GitHub API. Needs `GITHUB_TOKEN` and `GITHUB_REPOSITORY`. Team approvers need a token with `read:org`. |
| `git` | Only that each file is committed and has no local changes. Approval is reported as not verified. |
| `off` | Nothing. Approval is reported as not verified. |

Without `--approvals`, the checker uses `github` when `approvals.provider` is `github`
and both variables are set, `git` inside a git repository, and `off` otherwise.
With `--strict`, "not verified" is an unresolved record finding.

## Agent-type-id

    python tools/brace/brace.py hash

prints the fingerprint of the inputs in `.brace/manifest.yaml`. Paths are relative to
the repository root. Copy the value into `agent_type_id.value` in `deployment.yaml`, and
set `agent_type_id.manifest`. From then on, `check` recomputes it. If any input changed,
the record has an unresolved finding until someone reviews it again and records the new value.

How the fingerprint is computed:

1. For each input, compute a digest. For a `value`, it is the SHA-256 of the UTF-8 text.
   For a file, it is the SHA-256 of its bytes. For a folder, it is the SHA-256 of
   `"<relative path>\n<sha256 of file>\n"` for each file, in sorted order of relative
   path (with `/` separators), skipping files and folders whose names start with a dot.
2. Make a list of `{"name": ..., "digest": ...}`, sorted by name. Turn it into JSON
   with no spaces (`separators=(",", ":")`) and sorted keys, encoded as UTF-8.
3. The agent-type-id is `sha256:` plus the SHA-256 of that JSON.

Input names must be unique.

## Set up CI (GitHub Actions)

1. Copy `templates/brace-check.yml` to `.github/workflows/brace-check.yml`.
2. Copy the lines from `templates/CODEOWNERS.example` into `.github/CODEOWNERS`, with
   your team names. Turn on "Require review from Code Owners" for your main branch.
3. If any approver is a team, create a token that can read team membership
   (`read:org`) and save it as the repository secret `BRACE_GITHUB_TOKEN`.
4. Make the "BRACE check" job a required status check before release.

The workflow runs `brace.py check --approvals github --strict` on pull requests,
on reviews, and on pushes to `main`.

## Security map and action plan

Two more scripts turn a review into something people can act on. `brace-review`
runs them; you can also run them yourself.

`topology.py` builds a map of what the agent connects to: models, tools, MCP
servers, databases and outside APIs. It is saved as a [CycloneDX 1.7](https://cyclonedx.org/)
file (`schemas/cyclonedx-1.7/`, Apache-2.0).

    python tools/brace/topology.py build . -o brace-topology.cdx.json --agent-config config/agent.yaml
    python tools/brace/topology.py add-edge . --from tool:issue_refund --to api:payments \
        --label "sends refunds" --risk writes,money --evidence src/tools/payments.py:56 --quote "r = httpx.post("
    python tools/brace/topology.py validate brace-topology.cdx.json
    python tools/brace/topology.py mermaid brace-topology.cdx.json
    python tools/brace/topology.py record brace-topology.cdx.json            # create/update .brace/topology.cdx.json?
    python tools/brace/topology.py record brace-topology.cdx.json --apply    # only after a person says yes

`build` reads `.mcp.json`, the review inventory and the agent config. Parts that
only the code reveals are added with `add-node`, `add-edge` and `set-zone`. Each
needs a `path:line` and the exact code on that line, or it is refused. They are
kept in `brace-topology.overlay.json` and re-checked on every build; an entry
whose code changed is left off the map and listed as stale. `record` compares
the new map with `.brace/topology.cdx.json`, proposes creating or updating it, and
writes only with `--apply` (exit 3 means "a change is proposed").

`action_plan.py` joins the map with `brace-findings.json`:

    python tools/brace/action_plan.py brace-findings.json brace-topology.cdx.json \
        -o brace-action-plan.md --csv brace-actions.csv --strict

The report has the map coloured by what needs fixing, the risky connections in
plain words, an action list with a priority and a lead role, and numbered fix steps. `--strict` fails if a finding names a part that is
not on the map, if a gap has no fix steps, or if a step reads above grade 12
(Flesch-Kincaid, with code names counted as short words). The CSV loads into
most issue trackers.

More outputs from the same data:

    python tools/brace/action_plan.py brace-findings.json brace-topology.cdx.json -o brace-action-plan.md \
        --html brace-action-plan.html --json brace-action-plan.json --sarif brace.sarif --fail-on blocker

| Option | What you get |
|---|---|
| `--html` | One web page that walks through the plan: summary, map, risky connections, action list, and a card per action with its own small diagram, steps, test code and "done when". Diagrams load Mermaid from a pinned CDN version; without it the diagram text still shows. |
| `--json` | The plan for CI and other tools, schema `brace-action-plan/1` ([`schemas/action-plan.schema.json`](schemas/action-plan.schema.json)). |
| `--sarif` | SARIF 2.1.0, so each action shows up in GitHub code scanning and other SARIF tools. Blocker/Required gaps are errors, Detection gaps warnings, items that need proof notes. |
| `--fail-on` | Exit 3 when an action matches: `blocker` (a Blocker gap), `gap` (any gap), `any`, or `none` (default). |

Exit codes: 0 written, 1 input notes with `--strict`, 2 bad input, 3 `--fail-on` matched.

See [examples/billing-agent/](examples/billing-agent/) for a full example, including the web page.

### Topology report: declared vs found in code

`topology.py report` writes one web page that shows what the agent connects to.
It needs no internet connection.

    python tools/brace/topology.py report brace-topology.cdx.json --findings brace-findings.json -o topology.html

The page compares two things:

- **Declared**: what the settings list. That is `.mcp.json`, the tool list, and the
  optional `connections:` list in the agent config. Each entry names a service or
  store the agent is meant to reach, for example
  `{from: tool:book_flight, to: api:fares, kind: external_api, name: fares API, label: books tickets}`.
- **Found in code**: what the reviewer traced with `add-node` and `add-edge`.

Each part and line has one of three states:

| State | On the map | What to do |
|---|---|---|
| Confirmed | solid line | Nothing. It is declared and in the code. |
| Declared only | dashed line | Remove it if it is not needed. |
| Undeclared | thick purple line with a `!` | Check it. Then declare it or remove it. This is the most important state. |

A reply from a service back to the agent counts as part of the declared call into that
service, so it is not marked undeclared.

Rows are trust zones. A zone nobody has shown is drawn hatched as "Unknown network".
Findings show as badges. The shape gives the gate: octagon Blocker, triangle
Required, circle Detection. Select a part or line to see its evidence, findings,
the role that usually leads each fix, and the fix steps. Tables below the map list the same facts, for screen
readers and print.

Findings are listed most urgent first: by gate, then by reach. Reach is how many
connections and dangerous combinations the finding's parts touch, shown in words
such as "Affects 4 connections, 1 dangerous combination." A finding may carry an
optional OWASP AIVSS score (`"aivss": {"score": 7.4, "version": "0.8", "vector": "..."}`).
The page shows it when present. It is never required.

See [examples/travel-agent/](examples/travel-agent/) for a full example.

### Dangerous combinations (B05)

BRACE item B05 (Destructive-action interception) asks which agents can read
outside text, reach private data or systems, and change things or talk to the
outside, all in one context. The map records this as capability tags on parts:

| Tag | Meaning |
|---|---|
| `untrusted_input` | Reads text an outsider can write: web pages, email, tickets, uploads, third-party tool output. |
| `private_data` | Reaches customer or personal data, secrets, or internal stores. |
| `external_send` | Can send data out: email, requests to outside services, posting. |
| `destructive` | Can change or delete things, or move money. |

Tags come from three places, and the page shows which one:

- **declared**: `capabilities: {tool:send_itinerary: [external_send]}` in the agent config;
- **reviewer**: `topology.py add-tag . --ref api:analytics --tag external_send --evidence src/x.py:17 --quote "..."`.
  The quote must be on that line, as for other overlay entries. `--tag none` records that a part has none of the four;
- **inferred**: only where it is obvious. A data store has private data. A connection
  marked `money` makes its target destructive, and one marked `untrusted_input` tags the outside end.

For each agent and agent loop, the tool follows calls (including MCP server tools and
sub-agents) to find every tagged part it can reach. It flags two combinations:

- outside text + private data + sending out: **can be tricked into leaking data**;
- outside text + changing things: **can be tricked into harmful actions**.

A part with no tags and no traced onward connection is **unknown**, not safe. When
only one tag is missing and some reachable parts are unknown, the combination is
shown as **possible**. The overview lists each combination with a plain explanation,
the parts involved, a "Show on the map" button that highlights the path, and four
ways to fix it: remove a tool, split the agent, add human approval, or limit what the
sending tool can reach. The CycloneDX file keeps tags as `brace:capability:<tag>`
properties and combinations as `brace:combination:<type>:<agent>` properties on the metadata.

The map does not know whether an approval step already guards an action. Record
that in the B05 finding.

### Found on the host, and scanner output

`build` can also read MCP server settings from the machine where the agent runs,
and the output of two MCP scanners. These count as "found", like traced code:

    python tools/brace/topology.py build . -o map.cdx.json --host-config          # this machine's client settings
    python tools/brace/topology.py build . -o map.cdx.json --host-file ~/.cursor/mcp.json
    python tools/brace/topology.py build . -o map.cdx.json --import-scan agent-scan.json --import-scan cisco.json

`--host-config` reads Claude Desktop, Claude Code (`~/.claude.json`, managed
`managed-mcp.json`), Cursor, VS Code and Windsurf settings for the current operating
system. `open_agent_security/host_scan.py` lists the paths and their sources.
`--import-scan` (`scan_import.py`) reads Snyk Agent Scan `--json` output (v0.5 and v0.6
layouts) and Cisco mcp-scanner `--format raw` output. Neither runs a scan.

Only names are kept: the file and JSON key, server name, transport, command name, URL
without user, query or fragment, and the *names* of `env` keys and headers. Values of
`env`, headers and secret-looking arguments are never copied. Files over 5 MB are
refused, and all text is treated as untrusted. See [examples/host-scan/](examples/host-scan/).

### CycloneDX shape

MCP tools are top-level services. Their server lists them in its dependency entry
with `provides`. `dependsOn` only means "calls". What moves along a connection is
a `data` flow on the service (`flow`, `classification`, `name`, `source`,
`destination`). Data stores carry a `data` entry with a classification. Evidence uses
simple properties: `brace:edge:<to>`, `brace:declared_edge:<to>`, `brace:quote:file`
and `brace:quote:text`. The `brace:` names are provisional.

### SPDX 3 output: not planned for now (recommendation, not a decision)

SPDX 3.0 has AI and Dataset profiles, so BRACE could emit SPDX 3 JSON-LD: the
model maps to `ai_AIPackage`, data stores to `dataset_DatasetPackage`, agent units
and tools to `software_Package`, and edges to `Relationship` (`dependsOn`, `uses`,
`trainedOn`). But SPDX 3 has no service, endpoint, trust-zone or data-flow element,
which is most of what the map is for, so those would become `comment` text or
`Annotation`s that other tools ignore. A one-way export would take about two to
three days plus a validator in CI (`spdx3-validate`) and ongoing upkeep of a second
format. The recommendation is to keep CycloneDX 1.7 as the only output and add an
SPDX 3 export only if a buyer or regulator asks for SPDX by name.

## Run it as a GitHub Action

[`action/action.yml`](action/action.yml) is a composite GitHub Action. It builds the
map (optional), writes the plan in every format, puts it in the job summary (the
map renders there), uploads the report folder and the SARIF, compares the map with
`.brace/topology.cdx.json`, and fails on your threshold. It runs no model and needs
no secrets. Copy [`templates/brace-action-plan.yml`](templates/brace-action-plan.yml)
to `.github/workflows/`; it uses the vendored copy with `uses: ./tools/brace/action`.

| Input | Default | Meaning |
|---|---|---|
| `findings` | `brace-findings.json` | The review's findings. |
| `topology` | `brace-topology.cdx.json` | The map; rebuilt first when `build-topology` is `true`. |
| `build-topology`, `agent-config`, `tools-config` | `false`, empty | Rebuild the map from `.mcp.json`, config and the reviewer's overlay. |
| `fail-on` | `blocker` | `blocker`, `gap`, `any` or `none`. |
| `strict` | `true` | Fail on input notes. |
| `record`, `record-drift` | `.brace/topology.cdx.json`, `warn` | Compare the map with the record: `warn`, `fail` or `off`. The Action never writes the record; a person runs `topology.py record --apply`. |
| `upload-sarif`, `upload-artifact` | `true`, `true` | SARIF upload needs `permissions: security-events: write`; it is skipped with a warning if code scanning is not available. |

Outputs: `actions`, `gaps`, `blocker-gaps`, `record-status`, `report-dir`.
The review itself (the `brace-review` skill) runs before this, outside the Action.

## Import red-team and eval results

Some items need test results, such as R02 (prompt injection) or B05 (destructive
actions). If you test your agent with an attack tool, `import-results` can read the
tool's results file and add it as evidence in `record.yaml`.

    python tools/brace/brace.py import-results garak results/garak.report.jsonl
    python tools/brace/brace.py import-results garak results/garak.report.jsonl --item R02 --item B05

The first command only reads the file. It prints the tool and version, the run date,
how many tests passed and failed, the attack types it found, and the items those
attack types suggest. It writes nothing. The second command adds one evidence entry
to each item you name. You can also use `--suggested` to add it to every suggested item.

| Tool | File to give it | How to make the file |
|---|---|---|
| `garak` | `report.jsonl` | garak writes it on every run (not the hitlog or HTML report). |
| `promptfoo` | JSON results | `promptfoo eval -o results.json` (also `promptfoo redteam eval`). |
| `pyrit` | JSON list or JSONL of attack results or scores | `[r.model_dump(mode="json") for r in memory.get_attack_results()]`, saved with `json.dump`. Scores work the same way. |
| `inspect` | Eval log in JSON | `inspect eval ... --log-format=json`, or `inspect log convert --to json` for a `.eval` file. |

Each evidence entry has a `link` to the results file, the run `date`, and a `note`. The
note gives the tool and version, pass and fail counts, attack types and the file's
SHA-256 hash, so a reviewer can tell if the file was changed later. Importing the same
file again is skipped.

What the command will and won't do:

- **It never marks an item `pass`.** A clean run is evidence, but a person still decides
  whether it covers the item.
- **A run where any attack got through is evidence of a gap.** An item still at
  `not_reviewed` becomes `gap`. If the item is already `pass` or `na`, it stays as it is
  and you get a warning to review it. The command exits with code 1.
- **It treats the file as untrusted.** It reads JSON only and never runs anything from
  the file. Files over 50 MB are refused (change this with `--max-bytes`). Text from the file
  is cleaned and shortened before it is printed or saved.
- **It keeps the comments in `record.yaml`** when it can. If the file layout is unusual,
  it rewrites the file as plain YAML and tells you.

Other options: `--link URL` stores a link (for example a CI artifact) instead of the
file path. `--date YYYY-MM-DD` sets the date. `--tool-version` fills in a version the
file doesn't record (PyRIT files usually don't). `--dry-run` shows the changes without
writing them.

How results are counted:

- **garak:** each probe and detector pair. "Failed" means the detector found a hit.
- **promptfoo:** each test row. Rows that errored are counted apart from passes and fails.
- **PyRIT:** an attack whose outcome is `success`, or a true/false score of `true`, means
  the attack worked. That counts as failed. Undetermined results and other score types
  are counted apart.
- **Inspect:** the task decides what a score means. By default a correct score (`C` or 1)
  means the defense held. If your task scores the attack instead, add `--invert`.

The attack types come from probe, plugin or task names. They map to items like this:
prompt injection → R02, R01, B05; jailbreak → R02, R10; data exfiltration → R03, B09;
excessive agency → B01, B02, B05, E08; tool misuse → B05, R01, E04, E06; personal data
or system prompt leakage → R03. These are suggestions only. A tool name doesn't prove
the test matched the checklist recipe. Check the test against
[the verification guide](../../CHECKLIST-VERIFICATION.md) before you rely on it.

## Other commands

    python tools/brace/brace.py items          # the 53 items, gates, and lead roles
    python tools/brace/brace.py items --json
    python tools/brace/brace.py export --format html|csv|json   # see "Export for auditors"

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Record conditions met (or command succeeded); not deployment authorization |
| 1 | Unresolved record findings; not a high-risk deployment verdict |
| 2 | Invalid input or usage error: a file is missing, isn't valid YAML, doesn't match its schema, or the GitHub API couldn't be read |

## For BRACE maintainers

`brace_items.json` and `templates/.brace/record.yaml` are generated from
`CHECKLIST.md` and `ROLES.md`:

    python tools/brace/gen_items.py          # regenerate
    python tools/brace/gen_items.py --check  # exit 1 if out of date

Run the tests with:

    python -m pytest tools/brace/tests -q
