# brace.py — the BRACE sign-off checker

`brace.py` reads a `.brace/` folder in your agent's codebase and tells you whether the
release is a **GO** or a **NO-GO** under the [BRACE sign-off checklist](../../CHECKLIST.md).
It lists every reason for a NO-GO in plain language, so you know what to fix.

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
  - **G1**: release is blocked. G1 items can't be waived.
  - **G2**: add a risk acceptance file in `.brace/exceptions/` and set `exception:` to its name (without `.yaml`).
  - **G3**: blocked when the deployment is high stakes or high autonomy. Otherwise, treat it like G2.
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
  `decision`, `reasons`, `warnings`, `counts`, and one entry per item.

The checker blocks release when:

1. a file doesn't match its schema (this is exit code 2, not a NO-GO);
2. the stakes and autonomy rating is missing or incomplete;
3. any of the 53 items is missing or still `not_reviewed`;
4. a `pass` has no evidence with both a link and a date;
5. an `na` has no N/A file, the file is for another item, or it lacks a reason, evidence, or reviewer;
6. a `gap` breaks its gate rule, or its risk acceptance is missing, for another item, incomplete, or not approved;
7. any exception file exists for a G1 item, or for a G3 item on a high-stakes or high-autonomy deployment;
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
With `--strict`, "not verified" blocks release.

## Agent-type-id

    python tools/brace/brace.py hash

prints the fingerprint of the inputs in `.brace/manifest.yaml`. Paths are relative to
the repository root. Copy the value into `agent_type_id.value` in `deployment.yaml`, and
set `agent_type_id.manifest`. From then on, `check` recomputes it. If any input changed,
the release is blocked until someone reviews it again and records the new value.

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

## Other commands

    python tools/brace/brace.py items          # the 53 items, gates, and lead roles
    python tools/brace/brace.py items --json

## Exit codes

| Code | Meaning |
|---|---|
| 0 | GO (or the command worked) |
| 1 | NO-GO |
| 2 | Invalid input or usage error: a file is missing, isn't valid YAML, doesn't match its schema, or the GitHub API couldn't be read |

## For BRACE maintainers

`brace_items.json` and `templates/.brace/record.yaml` are generated from
`CHECKLIST.md` and `ROLES.md`:

    python tools/brace/gen_items.py          # regenerate
    python tools/brace/gen_items.py --check  # exit 1 if out of date

Run the tests with:

    python -m pytest tools/brace/tests -q
