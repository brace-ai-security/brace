# open-agent-security field report, November 2026

This report covers one run of `open-agent-security` (the development version with rules AP20
to AP23) on 110 public GitHub repositories that use AI agents. It measures two things: how
often each rule fires, and how many of its findings are false positives. Everything here is
aggregate. No repository is named, linked or quoted, and the patterns are described only in
general terms.

**Maintainers were not notified.** Nobody was contacted, and no issue, pull request or post
was made anywhere. Whether to disclose anything is the BRACE owner's decision (see
[Disclosure candidates](#disclosure-candidates)). A scan doesn't show that a project uses
BRACE, so nothing was added to ADOPTERS.md.

## Method

- **Selection.** Candidates came from GitHub code search, read-only, for agent files:
  `.mcp.json`, `CLAUDE.md`, `.claude/settings.json`, `.cursor/mcp.json`,
  `.gemini/settings.json`, `AGENTS.md`, `.cursorrules`, and workflows that use
  `anthropics/claude-code-action`, `openai/codex-action` or
  `google-github-actions/run-gemini-cli`. Repository search on four agent topics (more than
  200 stars) added more. That gave 309 unique candidates. Forks, archived repositories,
  repositories over 1.5 GB and repositories with no push since November 2025 were dropped,
  leaving 290. The sample is the 60 with the most stars plus a seeded random 50 of the rest
  (at least 5 stars). The mix runs from single-file skill collections to large monorepos.
- **Cloning.** `git clone --depth 1` into a temporary folder, with hooks and symlinks off.
  All 110 succeeded. No code from any clone was run.
- **Scanning.** `python3 -I scan.py <clone> --json --fail-on none --no-config`, run from a
  neutral folder. `--no-config` stops a repository's own config file from suppressing
  anything. None of the 110 had an ignore file or inline marks. The median scan took 16 s of
  wall time on a heavily loaded machine.
- **Labelling.** Each finding got one of three labels:
  - **tp**: the setup the rule describes;
  - **fp**: the rule misread the input;
  - **intended**: the scanner's documented err-toward-reporting class, such as tests, fixtures,
    vendored files, examples, schemas or code that names a flag to guard against it.

  Every AP20 to AP23 finding was read individually. For AP01 (3,123 findings), a seeded
  random sample of 30 findings outside test paths was read line by line. The other rules were
  spot-checked with 10 findings each. The rest were labelled by path class, as recorded in
  `tools/brace/fieldreport/autolabel.py` with the per-finding decisions in
  `overrides-2026-11.json`.
- **Tooling.** `tools/brace/fieldreport/harness.py` (clone, scan, label, stats) can repeat
  the run. The clones were deleted afterwards.

## Results

63 of the 110 repositories (57%) had at least one finding after the fixes below. 6 scans
were incomplete because each of those repositories had files over the 1 MB read limit (all
bundled JavaScript or data). No scan failed. The median repository had one finding.

| Rule | Severity | Repos | Prevalence | Findings |
|---|---|---|---|---|
| AP10 Agent image not pinned to a digest | low | 37 | 33.6% | 217 |
| AP01 Agent runs with all permission checks turned off | high | 29 | 26.4% | 3,123 |
| AP04 MCP server installed from an unpinned package | high | 19 | 17.3% | 72 |
| AP23 Hook or skill runs code fetched from the internet | high | 12 | 10.9% | 21 |
| AP06 Agent allowed to run any shell command | high | 10 | 9.1% | 202 |
| AP09 Lethal combination (likely) | medium | 8 | 7.3% | 10 |
| AP20 Agent tools approved automatically, without review | medium | 4 | 3.6% | 4 |
| AP02 Unattended agent in CI with permission checks turned off | critical | 2 | 1.8% | 3 |
| AP22 Hidden Unicode characters in agent instructions | high | 2 | 1.8% | 11 |
| AP21 Agent workflow anyone can trigger with a comment or issue | high | 1 | 0.9% | 1 |
| AP05 Secret written directly in agent configuration | high | 1 | 0.9% | 1 |
| AP07 Remote MCP server reached over plain HTTP | medium | 1 | 0.9% | 1 |
| AP03, AP08 | | 0 | 0% | 0 |

One repository accounts for 2,737 of the AP01 findings: recorded session transcripts and
tool schemas used as test snapshots, which list `danger-full-access` as a value.

### False positives

| Rule | Read by hand | tp | intended | fp | FP rate (read) |
|---|---|---|---|---|---|
| AP20 | 4 of 4 | 4 | 0 | 0 | 0% |
| AP21 | 1 of 1 | 1 | 0 | 0 | 0% |
| AP22 | 11 of 11 | 11 | 0 | 0 | 0% |
| AP23, first run | 116 of 116 | 19 | 2 | 95 | 82% |
| AP23, after the fix | 21 of 21 | 19 | 2 | 0 | 0% |
| AP01 (sample outside tests) | 30 | 9 | 15 | 6 | 20% before the fix, 0% after |
| AP06 | 10 | 10 | 0 | 0 | 0% |
| AP04 | 10 | 9 | 1 | 0 | 0% |
| AP10 | 10 | 8 | 2 | 0 | 0% |
| AP09 | 10 | 7 | 3 | 0 | 0% (inferred, marked *likely*) |
| AP02, AP05, AP07 | all | 3, 0, 1 | 0, 1, 0 | 0 | 0% |

Labelling by path class puts 93% of AP01 findings in the intended class (tests, fixtures,
snapshots, schemas), almost all of them in the one repository above. In the 30-finding sample
outside test paths, 9 pass a bypass to an agent the code launches (true positives).
Half name the value in type definitions, preset tables, help strings or messages, which
the scanner reports on purpose. The 6 false positives were all Quarto documents.

### Scanner bugs found and fixed

1. **AP23 read data pipes as code.** `curl ... | python3 -m json.tool` and
   `curl ... | python3 -c "..."` (common in skills that call APIs) were reported. Now a
   script runtime (python, node, ruby, perl, bun, deno) counts only bare or with `-`, that is
   when it runs stdin. Shells and PowerShell still count with any flags.
2. **AP23 read prose as a command.** Text that names the pattern itself (`curl ... | sh`,
   `curl|bash`, written with no URL or argument) was reported. A download now has to name a
   target.
3. **Quarto and R Markdown were not documentation.** `.qmd` and `.rmd` files that explain
   bypass flags were reported as AP01. They're now prose, like Markdown.

Each fix has regression cases in `tools/brace/tests/scan/test_regressions.py`. The run was
repeated after the fixes, and the numbers above are from the second run.

## Patterns

- **Skills that install tools with `curl | sh` (AP23)** are the most common new finding. Their
  instructions tell the agent to pipe a vendor's install script, or a script from a personal
  GitHub account's default branch, into a shell. The agent runs whatever that URL serves that
  day.
- **Skill and command frontmatter with `allowed-tools: Bash` (AP06)** clusters in large
  skill collections. A few repositories account for most of the 202 findings.
- **Committed auto-approval (AP20):** `enableAllProjectMcpServers: true` in a committed
  `.claude/settings.json` or `settings.local.json`, and Gemini CLI MCP servers with
  `trust: true`.
- **Hidden characters (AP22)** were all stray zero-width spaces, word joiners and a mid-file
  byte-order mark in skill files, copied into several vendored copies of the same skills.
  None hid an instruction. They're still worth removing, since a reviewer can't tell a stray
  character from a payload.
- **Comment and issue triggers (AP21):** one issue-triage workflow had
  `claude-code-action`'s write-access check opened to everyone. It had other mitigations
  (an egress firewall, narrow permissions, a restricted tool list), and the finding is
  correct. Workflows that keep the default check, or gate on `author_association`, were not
  reported.
- **Unpinned MCP packages (AP04)** remain common in shared MCP config collections and
  examples.

## Limitations

- 110 repositories chosen by search for agent files are not a random sample of GitHub. They
  overrepresent agent tooling and skill collections, which inflates AP06 and AP23.
- One reviewer labelled everything. The new rules were read in full, but the older rules
  were sampled or labelled by path class, so their FP rates are estimates.
- AP21 and AP20 fired too rarely here to estimate an FP rate with any confidence.
- Shallow clones see only the default branch, and files over 1 MB were not read (6
  incomplete scans).
- The machine was heavily loaded during the run, so the runtimes are not benchmarks.

## Disclosure candidates

For the owner to decide. Nothing was disclosed.

- The **AP21** workflow: anyone can open an issue that a write-capable agent job reads. It
  is mitigated, but it's the shape behind 2025's CI agent incidents.
- **AP20 `enableAllProjectMcpServers: true` committed to a shared repository** (2
  repositories): anyone who opens the project starts its MCP servers without a prompt.
- **AP23 skills that pipe a personal account's default-branch install script into a shell**
  (a few repositories with broad reach as skill collections): a compromise of that account
  reaches every user of the skill.

AP22 findings, AP01 test fixtures and unpinned images are not worth a disclosure.
