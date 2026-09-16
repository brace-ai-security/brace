# BRACE sign-off checklist

A review for production readiness covering all five BRACE aspects: **Build-time, Run-time, Agent, Configuration, and Ecosystem**. Use it before first deployment, when a release changes the agent's authority or behavior, and during periodic operational reviews.

The checklist applies to both an agent that is **hijacked or misused** and a **misaligned agent acting on its own**. It checks containment, detection, attribution, and recovery. It does not prove that a model’s intentions are safe.

## How to use this checklist

1. **Define the deployment.** Record its task, environment, tenants, data sensitivity, permitted actions, autonomy level, and worst credible damage. Include tools, retrieval, memory, auxiliary models, and sub-agents in scope.
2. **Walk through all five aspects.** Assign an owner to every item. Check an item only when the deployed configuration meets it and you can link to evidence: a reviewed artifact, an enforced policy, a trace, or a dated test result. A plan or vendor claim alone does not pass.
3. **Record every outcome.** Use **Pass**, **Gap**, or **N/A** in the evidence record below. Partial implementation is a Gap. N/A requires an explanation and reviewer approval; an absent control is not N/A. For example, memory checks can be N/A only if the agent has no persistent memory.
4. **Apply the priority gates across all five sections.** The section letters describe *where to review*; the gate labels describe *what blocks release*. Do not stop after Build-time or after the first passing section.
5. **Use the verification recipes.** The [verification guide](CHECKLIST-VERIFICATION.md) gives a concrete procedure, expected result, and evidence to retain for every item. Run applicable tests against the release candidate, using isolated test resources and synthetic data; record differences from production.
6. **Complete the sign-off record.** Resolve blockers, document permitted deferrals, and set the next review date.

### Working with operational limits

Implement the strongest controls you can demonstrate in your actual deployment. **Operational challenge** notes below explain where proof is difficult; **Practical fallback** notes give useful containment or recovery options when the ideal mechanism is unavailable.

**Accept tradeoffs deliberately.** Added latency, manual work, reduced functionality, and documented uncertainty can be reasonable costs of operating safely. When accepting risk, record the exposure, who accepts it, the controls that reduce it, and the review or expiry date. Accepting a tradeoff does not excuse failure of a required security boundary.

For each fallback, record **what it can demonstrate, where it applies, supporting evidence, remaining uncertainty, how failures are handled, an owner, and the next review date**. A fallback is not automatically a Pass: evaluate whether it meets the original requirement. Where it does not, retain the Gap and apply the priority rules below. If a gap blocks release, reduce the agent's capabilities or autonomy, or remove the affected integration, then re-test that actual configuration. Reassess risk based on the changed behavior; do not merely relabel the deployment to avoid a gate. Improve coverage over time without claiming guarantees the evidence cannot establish.

**Start with the top three in each aspect.** The bold **IF YOU DO NOTHING ELSE** items are the first implementation priorities within that aspect. Each appears only once in the checklist. For production sign-off, all applicable G1 requirements and the G2/G3 rules still apply.

**Basis and limits:** BRACE’s nine controls, six identity fields, top-three selections, and G1/G2/G3 sign-off rules are project design choices, not requirements prescribed verbatim by OWASP, NIST, MCP, or OpenTelemetry. The [dated source review](SOURCE-REVIEW.md) maps the checklist to supporting guidance and records corrections and verification limits. This is a review of control design and evidence, not a guarantee that a deployment is secure.

### Priority gates

| Label | Sign-off rule |
|---|---|
| **G1 — Blocking** | Every applicable item must pass. An unmet G1 item means **do not ship**; it cannot be waived as residual risk. |
| **G2 — Harden the substrate** | Every applicable item must pass or have an explicit, approved, time-bounded risk acceptance. |
| **G3 — Active detection** | Every applicable item must pass for high-stakes or high-autonomy deployments. For lower-stakes deployments, a gap needs an explicit, approved, time-bounded risk acceptance. |

Before evaluating gaps, classify the deployment’s potential harm and level of autonomy. Record the rationale and name the approver. A missing classification is a blocker. Passing many items does not compensate for a blocking failure.

**References:** C1–C9 are BRACE's [nine controls](README.md#the-framework-in-one-screen). **Obs-T1** means identity fields, **Obs-T2** context-size logging, and **Obs-T3** sub-agent provenance; these are observability requirements, not priority gates. Configuration and Ecosystem apply those same controls to release management and shared services.

## B — Build-time

**Question:** Have we bounded what this agent can do before it ever runs?

[Read the Build-time guide](guides/build-time/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#b--build-time).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **B05 · G1 · C4 — Destructive-action interception.** **Define high-impact operations, including deletion, destructive database updates, force-pushes, infrastructure teardown, payment changes, and external sends. Deny them by default in the execution path unless a reviewer or system with the required higher authority approves the specific action. Authorize the operation, target, and arguments at execution time; a list of blocked strings or command names is insufficient. Test alternate tools and raw API or shell paths that could perform the same operation.**

- [ ] **B02 · G1 · C2 — Least-privilege access.** **Scope credentials to named operations and resources, including tenant boundaries. Test that an allowed read succeeds while an out-of-scope write, admin operation, and cross-tenant request are denied. Remove wildcard and inherited human permissions.**

- [ ] **B01 · G1 · C4 — Minimal tool surface.** **List every built-in tool, MCP server, API, executable, and filesystem capability exposed to this agent type, with a task-specific justification. Enforce a role-scoped allowlist; verify an unlisted tool cannot be invoked.**

### Remaining checks

#### Capabilities and credentials

- [ ] **B03 · G2 · C2 — Credential lifetime and handling.** Issue short-lived credentials through a controlled identity or secrets service. Keep standing secrets out of prompts, images, and checked-in configuration. Demonstrate expiration and rotation, and justify the chosen lifetime.
- [ ] **B04 · G1 · C2 — Independent revocation.** Demonstrate that an operator can revoke this agent's access independently of the launching user and without relying on the agent to cooperate. Declare and measure the maximum time until enforcement takes effect, including cached tokens, self-contained tokens, and existing sessions. Block subsequent calls at a trusted enforcement point within a time limit appropriate to the potential harm; revoking a refresh token alone is insufficient.

#### Harness enforcement

- [ ] **B06 · G1 · C4 — Approval integrity.** Bind approval to the actual operation, target, arguments, and permitted scope. Show the reviewer the intended effect. Use single-use approvals or an explicitly bounded authorization grant. Re-check permissions and relevant resource state at execution, and record approval use atomically so concurrent calls cannot exceed the grant. Test changed arguments, expired approvals, replay, concurrent reuse, and unauthorized approvers; approval-service failure must not silently permit execution.
- [ ] **B07 · G2 · C4 — Hard execution budgets.** Enforce limits outside the model for iterations, elapsed time, tokens, cost, tool-call rate, and sub-agent fan-out. Exercise each applicable limit and record how execution stops or escalates when it is reached.

#### Environment and build artifacts

- [ ] **B08 · G2 · C1 — Environment isolation.** Document the agent's reachable systems and data. Test that it has no route to unauthorized production resources, the admin plane, host services, or other tenants. Enforce isolation through the infrastructure, not solely through prompt instructions. For every allowed connection, also verify inbound and response validation under **R01–R02**, including API responses and messages from connected services; network access does not make their content trusted.
- [ ] **B09 · G2 · C1 — Egress allowlist.** Allow only task-required outbound destinations. Test a prohibited destination and attempted bypass paths, including direct access around a proxy or gateway. Cover redirects, DNS changes and rebinding, both IPv4 and IPv6, and cloud metadata or loopback destinations where relevant. An allowed domain may still host attacker-controlled tenants or receive leaked data: also restrict which resources and tenants the agent can access and what data it can send. Record the denial and confirm it reaches the responsible operator.
- [ ] **B10 · G2 · C3 — Pinned, verified image.** Pin the container by digest, verify its digest and signature against an approved signing key or an approved certificate identity and issuer before execution, and retain its build provenance and dependency inventory. Demonstrate rejection of an unapproved or modified image.
- [ ] **B11 · G2 · C3 — Minimal, isolated runtime.** Remove unused shells, downloaders, package managers, mounts, and privileges. For untrusted code execution, use a sandbox boundary appropriate to the threat model, such as a microVM or user-space kernel; ordinary containers share the host kernel. For managed runtimes, record provider isolation evidence and visibility limits. Test forbidden host access, while recognizing that a failed access probe does not prove resistance to every sandbox escape.
- [ ] **B12 · G1 · C4 — Reviewed harness and instructions.** Version and review the harness, system prompt, and rules files before release. Restrict production changes to an attributable release process. Link the deployed versions to the approved review; complete the full configuration checks in section C.

**Evidence to attach:** capability inventory; permission and denial tests; approval records; budget tests; network policy; image digest and signature verification; harness and prompt review.

## R — Run-time

**Question:** When hostile input reaches a running agent, do containment, detection, and recovery still work?

[Read the Run-time guide](guides/run-time/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#r--run-time).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **R11 · G1 · C8 — Tested kill switch.** **Name the authorized operator and stop mechanism. Set a maximum halt time appropriate to the potential harm. Run a dated drill against the current deployment that stops new actions, running work, and tool sessions. Include descendants in the ecosystem drill (E09).**

- [ ] **R13 · G1 · C9 — Full execution audit.** **Capture proposed actions, tool calls and relevant arguments, authorization decisions, denials, approvals, results, errors, and timestamps as an execution graph. Reconstruct a representative run from the record, including failed actions, rather than relying on its final answer.**

  **Operational challenge:** Agent logs usually show attempted calls, while destination systems know whether side effects actually committed. A timeout can mean either failure or success with a lost response, so a complete-looking local trace may still have an unknown outcome.

  **Practical fallback:** Assign operation IDs before dispatch and retain destination receipts or status queries where available. Reconcile attempts with destination records and represent unresolved outcomes explicitly; stop dependent actions and retries pending resolution. If an integration cannot provide evidence adequate for attribution and recovery, restrict or remove that execution path. Sampling and agent self-reports cannot substitute for the required action record.

  **Acceptable tradeoffs:** Accept pausing dependent work while an ambiguous result is resolved. Keep the attempt, uncertainty, and eventual resolution in the graph. Limited automation is an acceptable cost; missing or fabricated action evidence is not a passing G1 result.

- [ ] **R01 · G2 · C5 — Validate every input boundary, including API responses.** **Inventory API responses (including errors and streamed content), tool and connector outputs, incoming webhooks/callbacks, peer messages, user input, fetched pages, files, and retrieved chunks. Authenticate senders and verify signatures where applicable; treat content from authenticated or internal services as untrusted too. Before content reaches model context or downstream execution, enforce expected types, schemas, size limits, and content validation, including checks for attack payloads and embedded prompt-injection instructions. Reject or quarantine invalid payloads; if required validation fails, do not admit unchecked content. Test malformed, oversized, spoofed, and adversarial responses from each integration.**

  **Operational challenge:** An API response can be well-formed, correctly signed, and still contain malicious instructions. Free text and streamed responses are especially difficult to inspect completely; a passing schema check establishes structure, not safety.

  **Practical fallback:** Enforce types, size limits, sender checks, and rejection of malformed content first. Add content checks for demonstrated attack patterns, and buffer or restrict streams where required checks cannot run before use. Keep privileges narrow and use R02 to contain instructions that pass inspection. Record which integrations and payload types were exercised and which remain unverified.

  **Acceptable tradeoffs:** Accept buffering latency, rejection of some legitimate responses, or a smaller supported payload set. Incomplete semantic attack detection can receive G2 risk acceptance with tested containment and explicit coverage limits; schema validation is not complete injection protection.

### Remaining checks

#### Input, output, retrieval, and memory

- [ ] **R02 · G2 · C5 — Separate data from instructions and test injection containment.** Keep API responses, connector messages, and other external content out of trusted system and policy channels; label their source and trust level. Test prompt injection in otherwise schema-valid responses, including free-text fields, error messages, documents, and tool output. Validation and channel separation cannot guarantee prevention of prompt injection: demonstrate that credential scopes, tool authorization, and destructive-action gates still block harmful actions if the model follows an injected instruction.

  **Operational challenge:** A model may follow an instruction embedded in ordinary-looking data despite channel separation. A finite set of injection tests cannot prove that all injections will be prevented, and model behavior may vary between runs.

  **Practical fallback:** Assume some injections will succeed. Test the resulting prohibited calls directly against credential scopes, egress rules, and action gates, as well as running end-to-end examples. Restrict exposed tools and data; make high-impact operations draft-only or subject to action-specific approval when containment is uncertain. Report structural validation, injection detection, and blocked side effects as separate results.

  **Acceptable tradeoffs:** Accept reduced task completion, fewer tools, and more action-specific approvals. Remaining detection uncertainty can receive G2 acceptance with explicit exposure and independent containment evidence; required access and destructive-action gates still apply.

- [ ] **R03 · G2 · C5/C9 — Prevent output and log leakage.** Remove secrets and restrict sensitive data before tool stdout, debug output, or responses reach model context, external recipients, or ordinary logs. Validate generated output before downstream SQL, shell, HTML rendering, or other execution; use parameterized operations and context-appropriate escaping. Use synthetic secrets and injection payloads in tests and verify that disclosure and unintended execution are blocked and that redacted audit evidence is retained.
- [ ] **R04 · G2 · C5/C6 — Retrieval-corpus integrity.** The **retrieval corpus** is the collection of documents the agent searches for context. Its **index** stores searchable documents or smaller passages, called chunks, in a search engine or vector database. Restrict which identities and sources can add or update content in that store. Preserve source, ingestion time, trust tier, and access permissions per chunk; enforce the requesting tenant's access at retrieval. Test an unauthorized attempt to add content, a cross-tenant search, and the quarantine, expiry, and access revocation of seeded test documents. Confirm the affected chunks are unavailable through retrieval and caches within a declared propagation time. See the [R04 recipe](CHECKLIST-VERIFICATION.md#r--run-time).

  **Operational challenge:** Removing a document from the index does not remove copies in caches, active contexts, summaries, or downstream memory. Permission changes may take time to propagate, and a model omitting a document from its answer does not prove that retrieval excluded it.

  **Practical fallback:** Define a measurable boundary, such as no revoked chunks entering new retrieval results after a stated interval. Enforce current access checks at retrieval, invalidate caches, and stop or restart affected active runs when necessary. If affected copies cannot be identified, quarantine the relevant collection and rebuild from approved sources. Record remaining copies and the period of exposure; do not claim complete removal from every derived artifact.

  **Acceptable tradeoffs:** Accept a stated, risk-appropriate revocation delay, retrieval downtime, or reduced search coverage while rebuilding. Record exposure during the delay and any G2 exception. Where access must end immediately, block affected retrieval and runs until revocation is effective.

- [ ] **R05 · G3 · C6 — Memory isolation and write validation.** Scope memory by tenant, agent type, instance, and task as appropriate; deny cross-scope access unless explicitly authorized. Validate writes and test that one poisoned run cannot silently seed instructions into another run's memory.

  **Operational challenge:** A stored preference or summary can become an instruction in a later session. Write validation cannot reliably distinguish every useful memory from a malicious one, especially when agents share memory across tasks.

  **Practical fallback:** Start with per-task or per-instance memory and deny sharing by default. Permit only defined memory fields and require review before promoting entries into shared, persistent memory. If a store cannot enforce isolation, disable persistent writes or shared reuse for that workflow. Test the reduced configuration and record any capability disabled to achieve the boundary.

  **Acceptable tradeoffs:** Accept loss of personalization, repeated work, or reviewed-only shared memory. Disabling persistent writes or sharing can reduce exposure. Any remaining memory-control gap can be deferred only where G3 permits.

- [ ] **R06 · G3 · C6 — Memory provenance and cleanup.** For an entry, retrieve its writer, timestamp, task, source input, and decision-time context size. Demonstrate finding, quarantining, and removing contaminated entries and controlling their reuse in later sessions.

  **Operational challenge:** Summaries and derived memories may lose their connection to the source that contaminated them. Deleting a known entry then leaves related content in use, and individual-entry provenance cannot retrospectively establish missing lineage.

  **Practical fallback:** Preserve source and writer links on new entries and derived summaries. When lineage is incomplete, quarantine or reset the affected namespace and its caches, restart affected sessions, and rebuild from known sources. Record the broader reset and resulting loss of useful memory. Keep missing provenance as a gap until demonstrated; a cleanup alone does not restore it.

  **Acceptable tradeoffs:** Accept loss of useful memories and the cost of resetting a wider namespace when precise cleanup is impossible. Missing provenance remains a G3 gap; record what was discarded and how trusted memory will be rebuilt.

#### Detection and operational limits

- [ ] **R07 · G2 · Obs-T2 — Decision-time context size.** Log context size for each action at decision time, using tokens and a documented counting method. State whether the value is measured, estimated, or unavailable, including cached input, compaction, and provider-hidden context limits; per-call billing totals are not automatically context occupancy. An unavailable value remains an explicit gap, not zero. Verify it survives tool handoffs and is queryable alongside the action's identity and outcome; see the [telemetry conventions](otel-conventions.md).
- [ ] **R08 · G3 · C7 — Security monitoring.** Maintain security rules and baselines distinct from answer-quality monitoring. Exercise encoded payloads, unexpected egress, out-of-scope writes, privilege escalation, and repeated denied calls; verify that alerts reach a named responder.
- [ ] **R09 · G3 · C7/Obs-T2 — Sequence and context-aware detection.** Test suspicious sequences of individually allowed actions, unusual fan-out, and resource consumption. Compare behavior across context-size ranges so a long-context failure is not hidden by one fleet-wide baseline.

  **Operational challenge:** Legitimate research and data collection for abuse can produce similar action sequences. Real attack examples may be scarce, and a detector tuned only to synthetic fixtures can miss production behavior or overwhelm responders with false alarms.

  **Practical fallback:** Start with a few specific signals: unusual read volume followed by an external send, repeated denials, excessive fan-out, or budget exhaustion. Measure seeded-attack detection, benign false alarms, and delivery time by context-size range. Use hard rate/cost limits and restricted destinations while improving detection. State exactly which sequences are covered and which are missed; basic rules do not establish general sequence detection.

  **Acceptable tradeoffs:** Accept a narrower documented detection scope and a measured false-alarm rate responders can handle. For lower-stakes deployments, defer broader coverage under G3 while maintaining hard limits. Where G3 blocks release, reduce actual exposure or complete required coverage.

- [ ] **R10 · G3 · C7 — Misaligned-behavior review.** If deliberate misalignment is in scope, exercise second-model or sequence-pattern review against representative evasive behavior. Record what it can and cannot detect; it must not replace deterministic access and action controls. Deeper intent detection belongs to a separate model-level AI-control program.

  **Operational challenge:** Observed actions do not reliably reveal hidden intent. A second model can share the acting model's blind spots, and success on labeled evasive examples does not establish that deliberate misalignment will be detected.

  **Practical fallback:** Make narrow claims about observable behavior, such as detecting attempts to split a prohibited operation across calls. Retain misses and false positives, and rely on independent permission limits, action approvals, and stop mechanisms for containment. Reduce autonomy or remove high-impact capabilities where detection is inadequate. Record an unproven detection capability as a gap; do not label the model's intent safe.

  **Acceptable tradeoffs:** Accept uncertainty about hidden intent while limiting claims to measured behavioral signals; this checklist does not certify alignment. Accept reduced autonomy and additional review. Missing required behavioral detection remains subject to G3.

#### Stop, explain, and recover

- [ ] **R12 · G1 · C8 — Safe state after stopping.** Define what happens to in-flight writes, queued actions, and external side effects. Demonstrate reconciliation or compensation where cancellation is impossible, with no unattended restart or orphaned work left able to act.

  **Operational challenge:** An external action may already be committed when the stop signal arrives. Emails cannot be unsent reliably, and payments, writes, and queued jobs have different cancellation and reconciliation behavior.

  **Practical fallback:** For each operation, record whether it can be blocked, canceled, or only reconciled after completion. Stop new dispatch, disable retries, inspect destination state, and route ambiguous outcomes to a named operator. For operations without a workable recovery path, remove autonomous execution or use an approved draft/commit workflow. Measure stopping new work separately from resolving committed effects; stopping the process alone does not pass this check.

  **Acceptable tradeoffs:** Accept slower manual reconciliation and restricted autonomous actions. Identified committed effects may require reconciliation rather than reversal under the documented safe-state procedure. Untracked effects or work retaining authority beyond the stop budget remain blocking.

- [ ] **R14 · G2 · C9 — Recovery integrity.** Where logs or checkpoints drive recovery, make them tamper-evident and verify them before use against a separately protected trust anchor or signing key. Test that verification rejects modified checkpoints and detects truncation, rollback to an older valid checkpoint, and replacement of an entire hash chain. For automatic recovery, confirm that the destination supports idempotency: repeating a request must not repeat its effect. Replay only within the destination’s documented scope and retention window, and verify that irreversible effects are not duplicated. For unsupported or ambiguous effects, verify replay pauses for reconciliation instead of reissuing them.

  **Operational challenge:** Not every external API supports idempotency keys or a reliable status query. A crash between a successful remote action and the local checkpoint can cause replay to repeat the action; a local deduplication table alone does not close that gap.

  **Practical fallback:** Use destination-enforced idempotency where supported and durable operation records before dispatch. If the outcome is ambiguous, pause replay and reconcile through destination evidence or an operator instead of retrying blindly. Disable automatic replay for unsupported side effects and document that limitation. Reject unverifiable checkpoints and recover from a trusted state; manual recovery does not prove automatic replay is safe.

  **Acceptable tradeoffs:** Accept manual recovery, delayed completion, and disabling automatic replay for unsupported integrations. Do not describe blind retries of ambiguous irreversible actions as safe replay. Remaining recovery-control gaps require permitted G2 acceptance.

**Evidence to attach:** boundary and leakage tests; retrieval and memory provenance samples; context-size traces; triggered alerts; kill-switch timing; a reconstructed run; tamper and replay tests.

## A — Agent

**Question:** Can we identify, scope, stop, and explain every agent and model involved in an action?

[Read the Agent guide](guides/agent/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#a--agent).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **A01 · G1 · C2/Obs-T1 — Distinct agent identity.** **Give the agent its own non-human identity, separate from the launching user and unrelated agents. Demonstrate that permissions and revocation attach to that identity, even when a user initiates the run.**

- [ ] **A02 · G1 · Obs-T1 — All six identity fields.** **Verify that every action records accountable party, operational owner, tenant, agent-type-id, agent-instance-id, and trace context. Inspect successful, denied, failed, and background actions, not only the main request path.**

- [ ] **A03 · G1 · Obs-T1 — Content-derived type identity.** **Compute the agent-type-id from the container digest, harness, system prompt, model identifier/version (including checkpoint and fine-tune/adapter references where applicable), and configuration. Retain the input manifest and hash procedure. Verify that changing any included artifact changes the ID and that the same manifest reproduces it.**

  **Operational challenge:** A hash identifies the configuration inputs you can observe. It cannot prove that a hosted model's undisclosed weights or training history stayed unchanged behind the same alias.

  **Practical fallback:** Hash the exact local artifacts and available model/checkpoint/adapter references using a reproducible manifest. Record requested aliases separately from observed served versions and explicitly mark undisclosed information. State that the ID fingerprints this recorded configuration; manage changes behind remote references under C05. Never substitute the agent application release number for model identity or present a local hash as proof of hidden provider state.

  **Acceptable tradeoffs:** Accept a fingerprint limited to recorded configuration, with undisclosed provider internals explicitly outside that claim. Track changes behind remote references under C05. Missing hashes or model references for artifacts you control still fail this G1 requirement.

### Remaining checks

- [ ] **A04 · G1 · C9/Obs-T1 — Trustworthy attribution.** Assign instance and tenant identity through the trusted execution layer rather than accepting model-supplied labels. Test that the agent cannot impersonate another instance or tenant in requests or audit records, and that trace context survives asynchronous handoffs. Treat trace IDs and caller-supplied labels as correlation data, never as authentication or authorization evidence.
- [ ] **A05 · G1 · C8/C9/Obs-T1 — Operational lookup.** Starting from a suspicious action, find the responsible team, current operator, deployment manifest, and live instance. Demonstrate targeting the correct instance or affected agent type for containment without revoking the launching user's unrelated access.
- [ ] **A06 · G3 · Obs-T3 — Parent and prompt provenance.** For every spawned agent, record its own type and instance IDs, parent link, trace linkage, and the prompt the parent supplied. Trace a nested action back to that prompt; protect sensitive prompt content with restricted storage and an explicit redaction policy.
- [ ] **A07 · G3 · C7/Obs-T1 — Every model in the loop.** Inventory verifiers, judges, rerankers, and world models. Give each an identity derived from its available model version or digest, prompt, and configuration, and attribute its decisions. Demonstrate that a swapped, drifted, or failing checker is treated as failure of the control that depends on it.

**Evidence to attach:** identity issuance and revocation records; sample actions with all six fields; manifest/hash tests; impersonation test; operator lookup drill; nested trace and parent prompt; checker inventory.

## C — Configuration

**Question:** Is the configuration we approved the configuration that is actually running?

[Read the Configuration guide](guides/configuration/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#c--configuration).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **C01 · G2 · C1–C6/Obs-T1 — Complete release manifest.** **Inventory the container, harness, system prompt, rules files, model, built-in tools, MCP servers, capability scopes, memory/retrieval settings, identity bindings, network rules, and execution budgets. Include security-policy versions and a separate model provenance record for every primary agent model, sub-agent model, and auxiliary model, including embeddings and rerankers. Record provider, model ID, exact version/checkpoint, and any adapter or fine-tune version. For training or fine-tuning you control, also record the training run/job ID, base-model version, training code/configuration version, dataset snapshot/version, and output artifact digest. The agent application release number alone is insufficient. Use the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields) to distinguish recorded versions from information a provider does not expose. Identify each artifact's owner and immutable reference where available.**

  **Operational challenge:** Teams can usually retrieve their own training jobs and datasets, but a hosted provider may not disclose pretraining runs, weights, or data versions. Distinguish records your team should hold from information the provider does not disclose.

  **Practical fallback:** Complete model records from serving metadata, registries, and training-job outputs. Require lineage for training your team controls; explicitly label provider-hidden fields and retain the disclosure source and date. Prefer a stable provider snapshot when available. Record missing training history your team should hold as a gap and prioritize reconstructing it; do not invent training versions or treat a provider alias as a training-run identifier.

  **Acceptable tradeoffs:** Accept explicitly undisclosed provider pretraining details when your own model-selection and training records are complete. A G2 visibility or lineage gap may receive explicit acceptance with an owner and review date; unknown records must not become claimed versions.

- [ ] **C03 · G1 · Obs-T1 — Match release identity to running state.** **Freeze the identity-defining artifacts per release and verify the running configuration against the approved manifest. Emit the corresponding agent-type-id. Test that an altered prompt, model, or tool configuration cannot continue presenting the old approved identity undetected.**

  **Operational challenge:** A manifest or self-reported agent ID can remain unchanged while the running prompt, tool configuration, or hosted model changes. Remote provider internals may be impossible to inspect independently.

  **Practical fallback:** Compare independently observed local artifacts and deployment settings against the manifest, and block or quarantine detected mismatches. Check served model metadata when exposed. Bound the claim to controlled artifacts and observable provider references, explicitly tracking hidden remote state under C05. A provider visibility limitation does not excuse an unverified local configuration or allow altered local artifacts to retain their approved identity undetected.

  **Acceptable tradeoffs:** Accept verification limited to controlled artifacts and observable provider references, with hidden remote state handled under C05. More frequent checks may cost time and compute. Unverified local artifacts or undetected changes to declared local configuration remain blocking.

- [ ] **C04 · G2 · C1/C3/C4/Obs-T1 — Detect drift per agent.** **Compare running images, harness settings, prompts, MCP lists, capabilities, and network policies with their declared baseline. Simulate a prompt edit, added tool, and loosened egress rule; verify an alert and the documented block, quarantine, or rollback response within a defined interval.**

### Remaining checks

- [ ] **C02 · G2 · C1–C7 — Review security-relevant changes.** Require attributable diffs and review for changes to the manifest and its policies. Show who may change production configuration. Record emergency changes with an owner, reason, expiry, and follow-up review.

- [ ] **C05 · G2 · C3/C4/C7 — Control dependency, model, and training changes.** Pin dependency versions and each model's base-model version, checkpoint/weights, and fine-tune or adapter version where supported. Link a changed training run, training dataset, or training code/configuration to its resulting model artifact and evaluation results before promotion. Record the model version actually served when the runtime/provider exposes it, separately from the requested model alias. Test a model/checkpoint or adapter substitution and verify it triggers review and re-evaluation. For remote services or aliases that can change behind a stable name, record unavailable training/version information explicitly, monitor available version metadata and provider notices, and define when re-evaluation or suspension is required. A local configuration hash alone cannot prove remote behavior is unchanged.

  **Operational challenge:** A hosted service may change behind an alias without exposing a served-version identifier or training lineage. Behavioral evaluation can reveal some regressions but cannot prove that no hidden change occurred.

  **Practical fallback:** Prefer pinned snapshots; otherwise retain both requested and observed identifiers, monitor available provider notices, and schedule representative evaluations with a named owner. Limit permissions and autonomy while version certainty is low, and define triggers to suspend use or move to an approved alternative. Record mutable-alias pinning gaps and any permitted risk acceptance. Evaluations and provider notices manage uncertainty; they do not establish immutable identity.

  **Acceptable tradeoffs:** Accept hosted-model convenience with reduced reproducibility and possible delay in detecting changes when that exposure receives explicit G2 acceptance. Set an evaluation schedule and define when use must be suspended. Choose a pinned alternative or reduce capabilities if that uncertainty is too consequential.

- [ ] **C06 · G2 · C4–C9 — Re-test changed behavior.** Before promotion, run representative allowed tasks and adversarial cases against the release candidate. Include destructive-action denial, access boundaries, injection containment, audit attribution, and stopping behavior; include retrieval, memory, and checker tests where used. Retain results for the exact candidate manifest.
- [ ] **C07 · G2 · C8/C9 — Rollback and restart.** Keep an approved recovery configuration and demonstrate rollback. Account for changed credentials, memory/index state, checkpoints, and queued work; do not restore revoked permissions or replay unsafe side effects merely because the old artifact is available.
- [ ] **C08 · G2 · Obs-T1/Obs-T2/Obs-T3 — Connect configuration to execution.** From a trace, retrieve the release manifest, decision-time context sizes, and applicable parent-supplied prompts. Preserve references for the audit retention period, with access controls for sensitive artifacts.

**Evidence to attach:** release manifest; approved diffs; running-state comparison; drift drill; remote-version limitations; release evaluation results; rollback test; trace-to-manifest lookup.

## E — Ecosystem

**Question:** Do the tools, peer agents, vendors, and shared services enforce their half of every control?

[Read the Ecosystem guide](guides/ecosystem/index.html) and [MCP gateway guide](guides/mcp-gateway/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#e--ecosystem).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **E06 · G2 · C1/C2/C4/C5/C9 — Enforced gateway boundary.** **Route MCP calls through a gateway or equivalent enforcement layer that the agent cannot bypass. Authenticate callers, authorize actions, validate calls and responses, enforce rate limits, and audit decisions. For HTTP/OAuth, validate token issuer, intended audience, expiry, and scopes; use appropriately authorized downstream credentials, not unvalidated token passthrough. For local tools using standard input/output (stdio), enforce restrictions on process launch, filesystem access, credentials, and networking in the host or sandbox; an HTTP gateway alone does not cover them. Test direct-server bypass, invalid credentials, malformed responses, and policy/scanner outages. Required enforcement must fail closed: deny the action when a required check cannot run.**

- [ ] **E08 · G1 · C2/C4 — Bounded delegated authority.** **Give sub-agents only the capabilities authorized for their assigned task. Enforce each child’s role and any explicit authorization from a higher authority; a parent must not gain a denied capability simply by asking a more privileged peer to act. Exercise that escalation attempt.**

  **Operational challenge:** A privileged peer may interpret a low-privilege agent's request as a legitimate task. Authenticating the immediate sender does not establish the original requester's authority, and delegation constraints can be lost across multiple hops.

  **Practical fallback:** Carry verified originating identity, tenant, and authorized scope to the final execution boundary. If a peer cannot enforce those constraints, restrict delegation to peers with no greater relevant authority, use a narrowly scoped task credential, or require independent authorization for the exact privileged action. Disable that delegation path if none is enforceable; trusting a peer's prompt does not satisfy this blocking check.

  **Acceptable tradeoffs:** Accept less flexible delegation, narrower child roles, or independent action approval. These can preserve the authorization boundary. Silent privilege amplification cannot pass this G1 check; disable the path if the boundary is unenforceable.

- [ ] **E09 · G1 · C8 — Recursive shutdown.** **Run a drill spanning a parent, nested children, remote workers, queued tasks, and open tool sessions where present. Verify the stop reaches every descendant within the declared budget, revokes access as needed, and prevents orphaned retries or restarts. Record how already-committed external effects are reconciled.**

  **Operational challenge:** Remote workers, disconnected children, queued tasks, and open tool sessions may outlive the parent. A stop message can be delayed or lost, and already-committed remote effects may not be cancellable.

  **Practical fallback:** Combine recursive stop signals with revocation, bounded task lifetimes, and short-lived execution leases that require renewal. Prevent new dispatch and test that disconnected workers lose the ability to act within the stop budget; define separately how long-running calls are canceled or reconciled. Exclude remote execution paths that cannot meet that budget. Record committed effects separately and reconcile them under R12.

  **Acceptable tradeoffs:** Accept fewer remote workers, lease-renewal overhead, and slower completion. A defined stop interval is acceptable when it is tested and appropriate to the potential harm. A worker retaining authority beyond that interval is a blocking gap.

### Remaining checks

#### Supply chain and tool boundaries

- [ ] **E01 · G2 · C1–C9 — Map shared responsibilities.** Inventory external tools, MCP servers, peer agents, sub-agents, registries, identity services, gateways, stop channels, and audit services. For each relevant control, name the agent-team owner and the shared-platform or vendor owner, with evidence for both halves. An upstream service does not make its controls N/A.
- [ ] **E02 · G2 · C3/C5 — Vet and pin dependencies.** Review tool/server source or available provenance, publisher identity, permissions, update path, and known vulnerabilities before approval. Pin versions/digests and verify signatures where available. Record remote-service or unsigned-artifact limitations and the compensating checks.
- [ ] **E03 · G2 · C5 — Re-check tools on load.** Fingerprint the approved tool description and schema, then compare on every load or refresh. Exercise a changed description, schema, or implementation version; block unexpected changes pending review. A description/schema fingerprint detects metadata changes, not hidden remote code changes. Pin or attest implementation artifacts where observable; record what you cannot inspect in remote implementations and define when to review them again. Track vulnerability notices and identify which deployments use an affected dependency.
- [ ] **E04 · G2 · C5 — Inspect tool metadata.** Scan descriptions and schemas before exposing them to the model for hidden instructions, invisible/control characters, role overrides, encoded payloads, and exfiltration destinations. Bound lengths and sanitize or reject suspicious content. Verify that scanning errors do not silently admit unchecked metadata.

  **Operational challenge:** Hidden instructions can be written in ordinary language with no suspicious encoding or control characters. Metadata scanners may also flag legitimate descriptions, so clean scan results do not establish that a tool is trustworthy.

  **Practical fallback:** Use a small approved tool catalog with reviewed, versioned descriptions and schemas. Block unexpected changes and retain deterministic limits and known-pattern checks even if advanced scanning is unavailable. Restrict capabilities independently of metadata, and disable a tool when required inspection is unavailable. Record scanner coverage and misses; manual review and known-pattern scanning are useful layers, not proof that all tool poisoning is prevented.

  **Acceptable tradeoffs:** Accept a smaller catalog, review delays, and occasional rejection of legitimate metadata. Limited semantic scanner coverage can receive G2 acceptance with independent capability restrictions; known-pattern tests do not establish universal tool-poisoning detection.

- [ ] **E05 · G2 · C2/C5 — Verified, namespaced tools.** Resolve each tool through a verified server identity plus tool name. Flag confusing lookalikes and duplicates across servers; test that a new server cannot silently substitute its tool for an approved one.

#### Delegation and shared operations

- [ ] **E07 · G2 · C2/C5 — Untrusted peer messages.** Authenticate the sending agent, validate message types and schemas, and authorize what that peer may request. Use freshness checks and nonce/request-ID tracking where replay could repeat an action; authentication alone does not prevent replay. Test forged identity, replayed requests, cross-tenant requests, and instructions passed through a compromised peer. A valid sender identity does not make message content trusted.

- [ ] **E10 · G1 · C9/Obs-T1 — Audit across service boundaries.** Reconstruct a run through the gateway, tool services, and delegated workers with all six identity fields preserved. Verify that the agent cannot erase or rewrite its audit history and that a vendor boundary does not leave actions unattributable.

  **Operational challenge:** Vendor services may omit parent/tenant identity or expose only request receipts, leaving gaps between your gateway trace and downstream actions. Shared credentials further weaken attribution.

  **Practical fallback:** Retain verified identity and correlation IDs at your gateway, map them to vendor job/receipt IDs, and reconcile with available destination records. Use separate scoped credentials where downstream identity propagation is unavailable. Record which parts of the execution history you cannot inspect; gateway logging alone cannot prove their internal execution history. Restrict or replace integrations whose evidence cannot satisfy the required attribution rather than marking the full graph complete.

  **Acceptable tradeoffs:** Accept integration overhead, reconciliation delays, and exclusion of opaque services. Mapping verified identity to vendor receipts can support attribution when demonstrated end to end. Irrecoverably unattributable actions remain blocking.

- [ ] **E11 · G2 · C9 — Protect shared evidence.** Define audit retention, access, redaction, integrity verification, and export/recovery procedures. Test retrieval of a historical run and detect missing records or pipeline failure. Define how execution is handled safely when required audit evidence cannot be captured.

  **Operational challenge:** Audit delivery can fail while the agent keeps acting; buffers can fill, records can arrive late, and vendor retention may be shorter than your investigation window. Exported logs may also contain sensitive data.

  **Practical fallback:** Use durable local buffering or another protected audit path with delivery acknowledgments, backlog limits, and missing-record alerts. Export vendor evidence within its retention window and restrict access. Pause affected actions before required evidence is lost when buffering is exhausted or unavailable. Record outages and irrecoverable gaps explicitly; a recovered pipeline does not recreate missing history.

  **Acceptable tradeoffs:** Accept bounded delivery delays while records remain durably protected, added storage/export cost, and paused work during outages. Retention or delivery limitations can receive G2 acceptance only where required G1 action capture and attribution still hold; disclose lost evidence.

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

**Recompute the agent-type-id whenever an identity-defining artifact changes:** container, harness, system prompt, model (including a new checkpoint or fine-tune/adapter), or configuration, including the capability set. Re-run this checklist for the new release; reuse evidence only after confirming it still applies to that exact configuration.

Also reopen affected checks after tool/server or checker changes, changes to memory or retrieval trust boundaries, shared-platform policy changes, incidents, failed drills, detected drift, or expired exceptions. Keep the scheduled review even if no release occurs, because credentials, dependencies, owners, and external services can change independently.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
