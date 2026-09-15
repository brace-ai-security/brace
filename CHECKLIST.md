# BRACE sign-off checklist

A production-readiness review covering all five BRACE aspects: **Build-time, Run-time, Agent, Configuration, and Ecosystem**. Use it before first deployment, when a release changes the agent's authority or behavior, and during periodic operational reviews.

The checklist applies to both an agent that is **hijacked or misused** and a **misaligned agent acting on its own**. It checks containment, detection, attribution, and recovery. It does not establish that a model's intent is aligned.

## How to use this checklist

1. **Define the deployment.** Record its task, environment, tenants, data sensitivity, permitted actions, autonomy level, and worst credible damage. Include tools, retrieval, memory, auxiliary models, and sub-agents in scope.
2. **Walk through all five aspects.** Assign an owner to every item. Check an item only when the deployed configuration meets it and you can link to evidence: a reviewed artifact, an enforced policy, a trace, or a dated test result. A plan or vendor claim alone does not pass.
3. **Record every outcome.** Use **Pass**, **Gap**, or **N/A** in the evidence record below. Partial implementation is a Gap. N/A requires an explanation and reviewer approval; an absent control is not N/A. For example, memory checks can be N/A only if the agent has no persistent memory.
4. **Apply the priority gates across all five sections.** The section letters describe *where to review*; the gate labels describe *what blocks release*. Do not stop after Build-time or after the first passing section.
5. **Complete the sign-off record.** Resolve blockers, document permitted deferrals, and set the next review date.

### Priority gates

| Label | Sign-off rule |
|---|---|
| **G1 — Blocking** | Every applicable item must pass. An unmet G1 item means **do not ship**; it cannot be waived as residual risk. |
| **G2 — Harden the substrate** | Every applicable item must pass or have an explicit, approved, time-bounded risk acceptance. |
| **G3 — Active detection** | Every applicable item must pass for high-stakes or high-autonomy deployments. For lower-stakes deployments, a gap needs an explicit, approved, time-bounded risk acceptance. |

Classify the deployment's stakes and autonomy before evaluating gaps, with a named approver and rationale. A missing classification is a blocker. Passing many items does not compensate for a blocking failure.

**References:** C1–C9 are BRACE's [nine controls](README.md#the-framework-in-one-screen). **Obs-T1** means identity fields, **Obs-T2** context-size logging, and **Obs-T3** sub-agent provenance; these are observability requirements, not priority gates. Configuration and Ecosystem apply those same controls to release management and shared services.

## B — Build-time

**Question:** Have we bounded what this agent can do before it ever runs?

[Read the Build-time guide](guides/build-time/index.html).

### Capabilities and credentials

- [ ] **B01 · G1 · C4 — Minimal tool surface.** List every built-in tool, MCP server, API, executable, and filesystem capability exposed to this agent type, with a task-specific justification. Enforce a role-scoped allowlist; verify an unlisted tool cannot be invoked.
- [ ] **B02 · G1 · C2 — Least-privilege access.** Scope credentials to named operations and resources, including tenant boundaries. Test that an allowed read succeeds while an out-of-scope write, admin operation, and cross-tenant request are denied. Remove wildcard and inherited human permissions.
- [ ] **B03 · G2 · C2 — Credential lifetime and handling.** Issue short-lived credentials through a controlled identity or secrets service. Keep standing secrets out of prompts, images, and checked-in configuration. Demonstrate expiration and rotation, and justify the chosen lifetime.
- [ ] **B04 · G1 · C2 — Independent revocation.** Demonstrate that an operator can revoke this agent's access independently of the launching user and without relying on the agent to cooperate. Verify that subsequent requests fail, including from an already-open session.

### Harness enforcement

- [ ] **B05 · G1 · C4 — Destructive-action interception.** Define high-impact operations, including deletion, destructive database updates, force-pushes, infrastructure teardown, payment changes, and external sends. Deny them by default in the execution path unless an authorized higher-tier approval permits the specific action. Test alternate tools and raw API or shell paths that could perform the same operation.
- [ ] **B06 · G1 · C4 — Approval integrity.** Bind approval to the actual operation, target, arguments, and permitted scope. Show the reviewer the intended effect. Test that changed arguments, an expired approval, or an unauthorized approver cannot release the action, and that approval-service failure does not silently permit it.
- [ ] **B07 · G2 · C4 — Hard execution budgets.** Enforce limits outside the model for iterations, elapsed time, tokens, cost, tool-call rate, and sub-agent fan-out. Exercise each applicable limit and record how execution stops or escalates when it is reached.

### Environment and build artifacts

- [ ] **B08 · G2 · C1 — Environment isolation.** Document the agent's reachable systems and data. Test that it has no route to unauthorized production resources, the admin plane, host services, or other tenants. Enforce isolation through the infrastructure, not solely through prompt instructions. For every allowed connection, also verify inbound and response validation under **R01–R02**, including API responses and messages from connected services; network access does not make their content trusted.
- [ ] **B09 · G2 · C1 — Egress allowlist.** Allow only task-required outbound destinations. Test a prohibited destination and attempted bypass paths, including direct access around a proxy or gateway. Record the denial and confirm it reaches the responsible operator.
- [ ] **B10 · G2 · C3 — Pinned, verified image.** Pin the container by digest, verify its signature before execution, and retain its build provenance and dependency inventory. Demonstrate rejection of an unapproved or modified image.
- [ ] **B11 · G2 · C3 — Minimal, isolated runtime.** Remove unused shells, downloaders, package managers, mounts, and privileges. Use a kernel-isolated runtime appropriate to untrusted execution, and test that the agent cannot access host resources outside its approved boundary.
- [ ] **B12 · G1 · C4 — Reviewed harness and instructions.** Version and review the harness, system prompt, and rules files before release. Restrict production changes to an attributable release process. Link the deployed versions to the approved review; complete the full configuration checks in section C.

**Evidence to attach:** capability inventory; permission and denial tests; approval records; budget tests; network policy; image digest and signature verification; harness and prompt review.

## R — Run-time

**Question:** When hostile input reaches a running agent, do containment, detection, and recovery still work?

[Read the Run-time guide](guides/run-time/index.html).

### Input, output, retrieval, and memory

- [ ] **R01 · G2 · C5 — Validate every input boundary, including API responses.** Inventory API responses (including errors and streamed content), tool and connector outputs, incoming webhooks/callbacks, peer messages, user input, fetched pages, files, and retrieved chunks. Authenticate senders and verify signatures where applicable; treat content from authenticated or internal services as untrusted too. Before content reaches model context or downstream execution, enforce expected types, schemas, size limits, and content validation, including checks for attack payloads and embedded prompt-injection instructions. Reject or quarantine invalid payloads; required validation failures must not silently admit unchecked content. Test malformed, oversized, spoofed, and adversarial responses from each integration.
- [ ] **R02 · G2 · C5 — Separate data from instructions and test injection containment.** Keep API responses, connector messages, and other external content out of trusted system and policy channels; label their source and trust level. Test prompt injection in otherwise schema-valid responses, including free-text fields, error messages, documents, and tool output. Validation and channel separation cannot guarantee prevention of prompt injection: demonstrate that credential scopes, tool authorization, and destructive-action gates still block harmful actions if the model follows an injected instruction.
- [ ] **R03 · G2 · C5/C9 — Prevent output and log leakage.** Remove secrets and restrict sensitive data before tool stdout, debug output, or responses reach model context, external recipients, or ordinary logs. Use synthetic secrets in tests and verify both the blocked disclosure and the retained, redacted audit evidence.
- [ ] **R04 · G2 · C5/C6 — Retrieval-corpus integrity.** Restrict who and what can ingest into the index. Preserve source, ingestion time, trust tier, and access permissions per chunk; enforce the requesting tenant's access at retrieval. Demonstrate detection or removal of poisoned, stale, and revoked content.
- [ ] **R05 · G3 · C6 — Memory isolation and write validation.** Scope memory by tenant, agent type, instance, and task as appropriate; deny cross-scope access unless explicitly authorized. Validate writes and test that one poisoned run cannot silently seed instructions into another run's memory.
- [ ] **R06 · G3 · C6 — Memory provenance and cleanup.** For an entry, retrieve its writer, timestamp, task, source input, and decision-time context size. Demonstrate finding, quarantining, and removing contaminated entries and controlling their reuse in later sessions.

### Detection and operational limits

- [ ] **R07 · G2 · Obs-T2 — Decision-time context size.** Log context size for each action at decision time, using a documented unit. Verify it survives tool handoffs and is queryable alongside the action's identity and outcome; see the [telemetry conventions](otel-conventions.md).
- [ ] **R08 · G3 · C7 — Security monitoring.** Maintain security rules and baselines distinct from answer-quality monitoring. Exercise encoded payloads, unexpected egress, out-of-scope writes, privilege escalation, and repeated denied calls; verify that alerts reach a named responder.
- [ ] **R09 · G3 · C7/Obs-T2 — Sequence and context-aware detection.** Test suspicious sequences of individually allowed actions, unusual fan-out, and resource consumption. Compare behavior across context-size ranges so a long-context failure is not hidden by one fleet-wide baseline.
- [ ] **R10 · G3 · C7 — Misaligned-behavior review.** If deliberate misalignment is in scope, exercise second-model or sequence-pattern review against representative evasive behavior. Record what it can and cannot detect; it must not replace deterministic access and action controls. Deeper intent detection belongs to a separate model-level AI-control program.

### Stop, explain, and recover

- [ ] **R11 · G1 · C8 — Tested kill switch.** Name the authorized operator, stop mechanism, and risk-matched halt-time budget. Run a dated drill against the current deployment that stops new actions, running work, and tool sessions. Include descendants in the ecosystem drill (E09).
- [ ] **R12 · G1 · C8 — Safe state after stopping.** Define what happens to in-flight writes, queued actions, and external side effects. Demonstrate reconciliation or compensation where cancellation is impossible, with no unattended restart or orphaned work left able to act.
- [ ] **R13 · G1 · C9 — Full execution audit.** Capture proposed actions, tool calls and relevant arguments, authorization decisions, denials, approvals, results, errors, and timestamps as an execution graph. Reconstruct a representative run from the record, including failed actions, rather than relying on its final answer.
- [ ] **R14 · G2 · C9 — Recovery integrity.** Where logs or checkpoints drive recovery, make them tamper-evident and verify them before use. Reject a modified checkpoint in a test. Replay an interrupted run with idempotency protections and confirm that irreversible sends, writes, or payments are not executed twice.

**Evidence to attach:** boundary and leakage tests; retrieval and memory provenance samples; context-size traces; triggered alerts; kill-switch timing; a reconstructed run; tamper and replay tests.

## A — Agent

**Question:** Can we identify, scope, stop, and explain every agent and model involved in an action?

[Read the Agent guide](guides/agent/index.html).

- [ ] **A01 · G1 · C2/Obs-T1 — Distinct agent identity.** Give the agent its own non-human identity, separate from the launching user and unrelated agents. Demonstrate that permissions and revocation attach to that identity, even when a user initiates the run.
- [ ] **A02 · G1 · Obs-T1 — All six identity fields.** Verify that every action records **accountable party, operational owner, tenant, agent-type-id, agent-instance-id, and trace context**. Inspect successful, denied, failed, and background actions, not only the main request path.
- [ ] **A03 · G1 · Obs-T1 — Content-derived type identity.** Compute the agent-type-id from the container digest, harness, system prompt, model identifier/version, and configuration. Retain the input manifest and hash procedure. Verify that changing any included artifact changes the ID and that the same manifest reproduces it.
- [ ] **A04 · G1 · C9/Obs-T1 — Trustworthy attribution.** Assign instance and tenant identity through the trusted execution layer rather than accepting model-supplied labels. Test that the agent cannot impersonate another instance or tenant in requests or audit records, and that trace context survives asynchronous handoffs.
- [ ] **A05 · G1 · C8/C9/Obs-T1 — Operational lookup.** Starting from a suspicious action, find the responsible team, current operator, deployment manifest, and live instance. Demonstrate targeting the correct instance or affected agent type for containment without revoking the launching user's unrelated access.
- [ ] **A06 · G3 · Obs-T3 — Parent and prompt provenance.** For every spawned agent, record its own type and instance IDs, parent link, trace linkage, and the prompt the parent supplied. Trace a nested action back to that prompt; protect sensitive prompt content with restricted storage and an explicit redaction policy.
- [ ] **A07 · G3 · C7/Obs-T1 — Every model in the loop.** Inventory verifiers, judges, rerankers, and world models. Give each an identity derived from its available model version or digest, prompt, and configuration, and attribute its decisions. Demonstrate that a swapped, drifted, or failing checker is treated as failure of the control that depends on it.

**Evidence to attach:** identity issuance and revocation records; sample actions with all six fields; manifest/hash tests; impersonation test; operator lookup drill; nested trace and parent prompt; checker inventory.

## C — Configuration

**Question:** Is the configuration we approved the configuration that is actually running?

[Read the Configuration guide](guides/configuration/index.html).

- [ ] **C01 · G2 · C1–C6/Obs-T1 — Complete release manifest.** Inventory the container, harness, system prompt, rules files, model, built-in tools, MCP servers, capability scopes, memory/retrieval settings, identity bindings, network rules, and execution budgets. Include auxiliary models and security-policy versions; identify each artifact's owner and immutable reference where available.
- [ ] **C02 · G2 · C1–C7 — Review security-relevant changes.** Require attributable diffs and review for changes to the manifest and its policies. Show who may change production configuration. Record emergency changes with an owner, reason, expiry, and follow-up review.
- [ ] **C03 · G1 · Obs-T1 — Match release identity to running state.** Freeze the identity-defining artifacts per release and verify the running configuration against the approved manifest. Emit the corresponding agent-type-id. Test that an altered prompt, model, or tool configuration cannot continue presenting the old approved identity undetected.
- [ ] **C04 · G2 · C1/C3/C4/Obs-T1 — Detect drift per agent.** Compare running images, harness settings, prompts, MCP lists, capabilities, and network policies with their declared baseline. Simulate a prompt edit, added tool, and loosened egress rule; verify an alert and the documented block, quarantine, or rollback response within a defined interval.
- [ ] **C05 · G2 · C3/C4/C7 — Control dependency and model changes.** Pin versions where supported and record resolved versions at execution. For remote services or model aliases that can change behind a stable name, document that limitation, monitor changes, and define when re-evaluation or suspension is required. A local configuration hash alone cannot prove remote behavior is unchanged.
- [ ] **C06 · G2 · C4–C9 — Re-test changed behavior.** Before promotion, run representative allowed tasks and adversarial cases against the release candidate. Include destructive-action denial, access boundaries, injection containment, audit attribution, and stopping behavior; include retrieval, memory, and checker tests where used. Retain results for the exact candidate manifest.
- [ ] **C07 · G2 · C8/C9 — Rollback and restart.** Keep an approved recovery configuration and demonstrate rollback. Account for changed credentials, memory/index state, checkpoints, and queued work; do not restore revoked permissions or replay unsafe side effects merely because the old artifact is available.
- [ ] **C08 · G2 · Obs-T1/Obs-T2/Obs-T3 — Connect configuration to execution.** From a trace, retrieve the release manifest, decision-time context sizes, and applicable parent-supplied prompts. Preserve references for the audit retention period, with access controls for sensitive artifacts.

**Evidence to attach:** release manifest; approved diffs; running-state comparison; drift drill; remote-version limitations; release evaluation results; rollback test; trace-to-manifest lookup.

## E — Ecosystem

**Question:** Do the tools, peer agents, vendors, and shared services enforce their half of every control?

[Read the Ecosystem guide](guides/ecosystem/index.html) and [MCP gateway guide](guides/mcp-gateway/index.html).

### Supply chain and tool boundaries

- [ ] **E01 · G2 · C1–C9 — Map shared responsibilities.** Inventory external tools, MCP servers, peer/sub-agents, registries, identity services, gateways, stop channels, and audit services. For each relevant control, name the agent-team owner and the shared-platform or vendor owner, with evidence for both halves. An upstream service does not make its controls N/A.
- [ ] **E02 · G2 · C3/C5 — Vet and pin dependencies.** Review tool/server source or available provenance, publisher identity, permissions, update path, and known vulnerabilities before approval. Pin versions/digests and verify signatures where available. Record remote-service or unsigned-artifact limitations and the compensating checks.
- [ ] **E03 · G2 · C5 — Re-check tools on load.** Fingerprint the approved tool description and schema, then compare on every load or refresh. Exercise a changed description, schema, or implementation version; block unexpected changes pending review. Track vulnerability notices and identify which deployments use an affected dependency.
- [ ] **E04 · G2 · C5 — Inspect tool metadata.** Scan descriptions and schemas before exposing them to the model for hidden instructions, invisible/control characters, role overrides, encoded payloads, and exfiltration destinations. Bound lengths and sanitize or reject suspicious content. Verify that scanning errors do not silently admit unchecked metadata.
- [ ] **E05 · G2 · C2/C5 — Verified, namespaced tools.** Resolve each tool through a verified server identity plus tool name. Flag confusing lookalikes and duplicates across servers; test that a new server cannot silently substitute its tool for an approved one.
- [ ] **E06 · G2 · C1/C2/C4/C5/C9 — Enforced gateway boundary.** Route MCP traffic through a gateway that authenticates, authorizes, validates calls and responses, rate-limits, and audits decisions. Test direct-server bypass, invalid credentials, malformed responses, and policy/scanner outages. Required enforcement must fail closed.

### Delegation and shared operations

- [ ] **E07 · G2 · C2/C5 — Untrusted peer messages.** Authenticate the sending agent, validate message types and schemas, and authorize what that peer may request. Test forged identity, cross-tenant requests, and instructions passed through a compromised peer. A valid sender identity does not make message content trusted.
- [ ] **E08 · G1 · C2/C4 — Bounded delegated authority.** Give sub-agents only the capabilities authorized for their assigned task. Enforce each child's role and any explicit higher-tier authorization; a parent must not gain a denied capability simply by asking a more privileged peer to act. Exercise that escalation attempt.
- [ ] **E09 · G1 · C8 — Recursive shutdown.** Run a drill spanning a parent, nested children, remote workers, queued tasks, and open tool sessions where present. Verify the stop reaches every descendant within the declared budget, revokes access as needed, and prevents orphaned retries or restarts. Record how already-committed external effects are reconciled.
- [ ] **E10 · G1 · C9/Obs-T1 — Audit across service boundaries.** Reconstruct a run through the gateway, tool services, and delegated workers with all six identity fields preserved. Verify that the agent cannot erase or rewrite its audit history and that a vendor boundary does not leave actions unattributable.
- [ ] **E11 · G2 · C9 — Protect shared evidence.** Define audit retention, access, redaction, integrity verification, and export/recovery procedures. Test retrieval of a historical run and detect missing records or pipeline failure. Specify safe handling when required audit evidence cannot be captured.
- [ ] **E12 · G3 · C7/C8 — Fleet incident response.** Exercise compromise of a shared tool or agent type. Identify affected instances and tenants, quarantine the dependency, revoke relevant access, stop impacted work, and notify the named responders. Verify cross-agent abuse and budget alerts reach the team that can act.

**Evidence to attach:** dependency and responsibility inventory; provenance and fingerprint checks; metadata and lookalike tests; gateway bypass/outage tests; peer authorization tests; recursive-stop drill; cross-service audit trace; fleet incident exercise.

## Evidence and exception record

Keep a completed copy with the release. Use one row per checklist item; link to durable, access-controlled evidence. Reuse one test artifact across related items when it proves each requirement, but record each item's outcome separately.

| Item ID | Outcome: Pass / Gap / N/A | Owner | Evidence link and test date | Gap or N/A rationale |
|---|---|---|---|---|
| B01 | | | | |
| …one row for each remaining item… | | | | |

For every permitted G2 or G3 deferral, also complete:

| Item ID | Exposed threat and affected systems | Compensating control and evidence | Risk accepted by / date | Remediation owner and tracking link | Expiry / review date |
|---|---|---|---|---|---|
| | | | | | |

**Deferral rules:** No G1 waivers. No G3 deferrals for high-stakes or high-autonomy deployments. A blank, expired, or unapproved exception is an unresolved gap. N/A decisions must name their reviewer and the evidence showing the feature or exposure is absent.

## Final sign-off

### Deployment record

| Field | Record |
|---|---|
| Deployment, environment, and release | |
| Task, allowed actions, and data/tenant scope | |
| Stakes and autonomy classification, rationale, and approver | |
| Agent-type-id and release-manifest link | |
| Accountable party and operational owner | |
| Reviewer(s) and review date | |
| Evidence-record link and exception-record link | |
| Kill-switch drill date, measured halt time, and allowed budget | |
| Decision: GO / NO-GO | |
| Sign-off approver and date | |
| Next scheduled review | |

### Decision checks

- [ ] All **five aspects** have been reviewed; every item has an outcome, owner, and evidence or an approved N/A rationale.
- [ ] Every applicable **G1** item passes.
- [ ] Every applicable **G2** item passes or has a valid, approved risk acceptance.
- [ ] Every applicable **G3** item passes for a high-stakes or high-autonomy deployment; permitted lower-stakes deferrals have valid, approved risk acceptance.
- [ ] Operators can access the stop mechanism, response instructions, evidence, and recovery procedure.
- [ ] The approver has recorded the decision for the exact configuration being released.

**GO only when every decision check above is satisfied. Otherwise, NO-GO.**

### When to repeat the review

**Re-mint the agent-type-id whenever an identity-defining artifact changes:** container, harness, system prompt, model, or configuration, including the capability set. Re-run this checklist for the new release; reuse evidence only after confirming it still applies to that exact configuration.

Also reopen affected checks after tool/server or checker changes, changes to memory or retrieval trust boundaries, shared-platform policy changes, incidents, failed drills, detected drift, or expired exceptions. Keep the scheduled review even if no release occurs, because credentials, dependencies, owners, and external services can change independently.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
