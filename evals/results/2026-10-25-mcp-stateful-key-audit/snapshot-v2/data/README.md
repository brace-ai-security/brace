# Stateful MCP source-review difficulty pilot, edition 1

Twelve self-contained synthetic source repositories implement six issue/corrected
pairs. This edition is **difficulty-development material**. Target-reviewer
performance has not been measured; a 40–60% plain-request discovery rate is an
aspiration for the pilot, not an established result or an enforced acceptance score.
The prior [deeper suite](../deep/README.md) remains unchanged.

| Mechanism | Issue / counterpart | Required reasoning |
|---|---|---|
| Credential decision cache | agate / beryl | Distinguish two credentials for the same subject across cache warm-up and later delegated operations. |
| Revocation and resume | chert / diabase | Follow an owned job's captured lease through a later membership change and page/result delivery. |
| Identifier representation | eclogite / flint | Follow logical versus wire locators across two valid local decoding contracts. |
| Retry account context | gneiss / halite | Follow provider generation failure, reconnect, envelope reconstruction and the retry's actual credential. |
| Idempotency namespace | iolite / jade | Compare independently authorized requests across tenant-local accounts and shared retry result reuse. |
| Mutable reviewed objects | kyanite / limestone | Bind a legitimate review snapshot to the plan values actually used after a later edit. |

There are **six distinct required bugs**, not 24: three repetitions produce 18
required-finding observations per arm. More repetitions do not create independent
bugs. Each counterpart applies one narrow correction while preserving normal
behavior and named nearby protections. Counterparts are not globally secure
products; additional genuine issues remain admissible.

## Application context

One author built six application modules on a common local host/registry platform.
These are not independent production repositories or historical CVE reproductions.
Each repository has 38–41 files and roughly 650–750 nonblank source/config/doc/test
lines. Meaningful context includes local host construction, installed-path config,
credential-bound sessions, tool discovery, sequential batches, subject-filtered
journals, typed replies, application state and ordinary functional test sources.
Adding this context does not itself establish greater discovery difficulty.

Both configured entrypoints work as source interfaces: `service.bootstrap:build`
constructs the application registry; `service.launch:build_host` loads local config
and a matching tool catalog and retains that registry across host sessions. Host
sessions reauthenticate the saved credential on each packet. They do not supply
compensating domain authorization. These are in-process MCP-shaped components,
with no native MCP wire protocol, network service or external provider deployment.

## Hidden grading inputs

Only one `fixtures/<name>/` repository plus the common `research/` packet goes to
a primary reviewer. Never expose this README, `suite.json`, `authoring.json`,
`expected/`, `witnesses/`, the counterpart, audit outputs or earlier reports.
Fixtures have neutral names, ordinary docs and functional tests. They contain no
answer keys, bug/fix labels or executable exploit tests. Supplier attachments are
untrusted data; recognition is measured separately from finding correctness.
No synthetic body-canary output metric is added to this edition.

`expected/` holds source-anchored discoveries, specific guards and coverage checks.
`witnesses/` holds deterministic **static** action/representation traces, required
legitimate earlier activity, precise attacker capabilities, expected effects,
blocked counterexamples and the correction. These are not executed proof-of-
concepts. Captures such as `$plan.id` refer to response fields in earlier steps;
text traces explain expected results rather than claiming test execution.

A required finding needs the actual reachable failure, prerequisites and effect.
It need not name every intermediate helper when that causal path is demonstrated.
Missing discussion stays in coverage/guards. Count incorrect factual claims
separately, including alleged exploits blocked by another supplied control.

## Audit and freeze

A frozen source-first independent audit is recorded at
[the audit directory](../../results/2026-10-25-mcp-stateful-key-audit/README.md).
Its acceptance file is authoritative about acceptance status; do not infer
acceptance from this README. Auditors inspect source before keys/witnesses and
check sequences, entrypoints, actual effect, corrected behavior, nearby protections
and direct answer cues. Source auditing is not runtime verification. Rejected
snapshots and corrections must remain visible before a replacement is accepted.
The BRACE MCP skill is held unchanged during construction/audit.

## Difficulty calibration and future evaluation

First freeze/audit this edition, then run a separately authorized plain-request
pilot under fixed model/tool/budget conditions. Preserve every report and raw
score, including infrastructure faults. Use discovery, incorrect claims and
completeness as separate metrics. Inspect which mechanisms are easy/hard; report
the actual rate even when outside the desired range. Do not tune cases until an
exact target score appears and report that selected score as general ability.

Use pilot outcomes to refine the construction method. Build and audit fresh
assessment instances afterward without selecting them for observed plain-model
failure. Keep skill changes frozen before that comparison. Once used or public,
these pilot cases are regression evidence. The legacy harness `transfer` field
is a compatible grouping label, not a claim that these are an unbiased holdout.

The existing three-arm runner accepts `--data evals/mcp/stateful`; its default
three repetitions would schedule 108 primary reviews across all arms. No such
campaign is part of fixture construction, and the default CLI count grader is
not the calibrated independent source-grading procedure. Do not mistake a
prepare-only snapshot for a scored campaign or silently substitute that grader.

## Design references and limits

[BountyBench](https://crfm.stanford.edu/2025/05/21/bountybench.html) uses real systems,
verified vulnerabilities, corrected snapshots and functionality invariants.
[PatchBench](https://patchbench.github.io/) separates root causes from apparent
failure sites and uses transplantation plus security/benign-behavior validation.
Those are design influences. Their runtime/patching results do not establish
BRACE source-discovery accuracy or the difficulty of these synthetic mechanisms.
These design references are kept outside the reviewer reference packet.

**Never execute/import fixture code, run its tests/launchers, install dependencies
or connect to endpoints.** Python AST, JSON and TOML parsing and trusted harness
validation are allowed. Repository CC BY 4.0 applies. Credentials/data are fake.
No deployment verdict follows from any result.
