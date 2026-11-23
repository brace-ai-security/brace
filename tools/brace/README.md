# brace.py — the BRACE sign-off checker

`brace.py` checks the supplied `.brace/` evidence record against the [BRACE checklist](../../CHECKLIST.md). High-stakes, high-autonomy or unrated deployments return **FINDINGS**, with evidence gaps and unknowns, never a BRACE GO/NO-GO deployment verdict. Lower-risk deployments retain GO/NO-GO record results. Neither a clean report nor exit code 0 authorizes deployment.

Accountable people own any high-risk rollout: gradual stages, bounded exposure, close monitoring, explicit stop conditions, tested recovery and review before expansion.

It checks the record. It does not test your agent. The evidence links in the record
point to the tests you ran (see the [verification guide](../../CHECKLIST-VERIFICATION.md)).

## Install

You need Python 3.10 or newer and PyYAML. `jsonschema` is optional; without it,
`brace.py` uses a small built-in validator.

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
plain words, an action list with a priority, a lead role and a blank "assigned
to", and numbered fix steps. `--strict` fails if a finding names a part that is
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

## Other commands

    python tools/brace/brace.py items          # the 53 items, gates, and lead roles
    python tools/brace/brace.py items --json

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
