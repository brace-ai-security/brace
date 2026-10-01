# BRACE sign-off checklist

Use this checklist to decide if an AI agent is ready for production. It covers all five BRACE aspects: **Build-time, Run-time, Agent, Configuration, and Ecosystem**.

Run it at three times:

- before the first deployment;
- when a release changes what the agent can do or how it behaves;
- at regular operating reviews.

The checklist covers two kinds of trouble. An attacker may **hijack or misuse** the agent. Or the agent may be **misaligned and act on its own**. Either way, the checklist asks whether you can contain the damage, detect it, trace who did what, and recover. It does not prove that a model means well.

## How to use this checklist

1. **Describe the deployment.** Write down the agent's task, environment, tenants (customers or accounts whose data must stay separate), data sensitivity, allowed actions, and level of autonomy. Also write down the worst damage it could credibly cause. Include tools, retrieval, memory, helper models, and sub-agents.
2. **Go through all five aspects.** Give every item an owner. Mark an item done only when the deployed setup meets it and you can link to proof. Proof means a reviewed artifact, an enforced policy, a trace, or a dated test result. A plan or a vendor claim is not proof.
3. **Record every result.** Use **Pass**, **Gap**, or **N/A** in the evidence record below. A partial fix is a Gap. N/A needs a reason and a reviewer's approval. A missing control is not N/A. For example, memory checks are N/A only if the agent has no memory that lasts between runs.
4. **Apply the priority gates in all five sections.** The section letters say *where to look*. The gate labels say *what blocks release*. Don't stop after Build-time or after the first section that passes.
5. **Use the verification recipes.** The [verification guide](CHECKLIST-VERIFICATION.md) gives each item a test, the result to expect, and the evidence to keep. Test the release candidate. Use separate test resources and fake data, and write down how the test setup differs from production.
6. **Finish the sign-off record.** Fix blockers, write down any allowed deferrals, and set the next review date.

### Working with operational limits

Build the strongest controls you can prove in your real deployment. Some items include three notes:

- **Why this is hard** explains where proof is difficult.
- **If you can't fully do it** gives a fallback that still contains damage or helps you recover.
- **Tradeoffs you can accept** names costs that are fine to pay, and ones that are not.

**Choose tradeoffs on purpose.** Extra delay, manual work, fewer features, and written-down uncertainty can be fair prices for safety. When you accept a risk, record the exposure, who accepts it, what reduces it, and when it expires or gets reviewed. Accepting a tradeoff never excuses a broken security boundary that the checklist requires.

For each fallback, record:

- what it proves and where it applies;
- the evidence behind it;
- what is still uncertain;
- how failures are handled;
- an owner and the next review date.

A fallback does not pass automatically. Check whether it meets the original requirement. If it doesn't, keep the Gap and apply the gate rules below. If a gap blocks release, cut the agent's powers or autonomy, or remove the integration at fault. Then re-test that actual setup. Judge the risk by how the agent now behaves. Don't just rename the deployment to dodge a gate. Improve coverage over time, and never claim more than your evidence shows.

**Start with the top three in each aspect.** The **IF YOU DO NOTHING ELSE** items are the first things to build in each aspect. Each appears only once. For production sign-off, every applicable G1 item and the G2/G3 rules still apply.

**Where this comes from, and its limits:** BRACE chose its nine controls, six identity fields, top-three picks, and G1/G2/G3 rules. OWASP, NIST, MCP, and OpenTelemetry do not require them word for word. The [dated source review](SOURCE-REVIEW.md) links each item to supporting guidance and lists corrections and limits. This checklist reviews control design and evidence. It does not guarantee that a deployment is secure.

### How to read the identifiers

Checklist headings use several kinds of codes. The numbers name items. They do not show order or priority. Keep the codes the same when you reorder items.

| Example | Meaning |
|---|---|
| **B05**, **R01**, **A03**, **C01**, **E06** | A BRACE checklist item. The letter names the aspect: Build-time, Run-time, Agent, Configuration, or Ecosystem. The number is the item's fixed ID in that aspect. |
| **G1**, **G2**, **G3** | A BRACE [priority gate](#priority-gates). The gate sets how a gap affects release. |
| **C1**–**C9** | A BRACE [security control](README.md#the-framework-in-one-screen). These are not the same as Configuration items such as **C01**. |
| **Obs-T1**–**Obs-T3** | A BRACE [observability requirement](README.md#the-framework-in-one-screen): identity fields, context-size logging, or sub-agent provenance (where a sub-agent came from). |

Codes owned by other groups are outside references, not BRACE codes. When one appears, link it to its official source. Examples include [ASI01–ASI10](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), [RFC 7009](https://www.rfc-editor.org/info/rfc7009/), and [ISO/IEC 42001](https://www.iso.org/standard/81230.html).

### Priority gates

| Label | Sign-off rule |
|---|---|
| **G1 — Blocking** | Every applicable item must pass. If a G1 item fails, **do not ship**. It cannot be waived as accepted risk. |
| **G2 — Harden the substrate** | Every applicable item must pass, or have a written, approved risk acceptance with an end date. |
| **G3 — Active detection** | For high-stakes or high-autonomy deployments, every applicable item must pass. For lower-stakes deployments, a gap needs a written, approved risk acceptance with an end date. |

Before you judge any gaps, rate the deployment's potential harm and autonomy. Write down why, and name who approved the rating. A missing rating blocks release. Passing many items does not make up for one blocking failure.

**References:** C1–C9 are BRACE's [nine controls](README.md#the-framework-in-one-screen). **Obs-T1** is identity fields, **Obs-T2** is context-size logging, and **Obs-T3** is sub-agent provenance. These are observability requirements, not gates. The Configuration and Ecosystem sections apply the same controls to releases and shared services.

## B — Build-time

**Question:** Have we limited what this agent can do before it ever runs?

[Read the Build-time guide](guides/build-time/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#b--build-time).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **B05 · G1 · C4 — Destructive-action interception.** **List the high-impact operations. These include deletes, destructive database updates, force-pushes, tearing down infrastructure, payment changes, and sending anything outside. Block them by default in the execution path. Allow one only when a reviewer or system with higher authority approves that specific action. When the action runs, authorize its operation, target, and arguments, and block it if they aren't allowed. A list of blocked words or command names is not enough. Test other tools and raw API or shell paths that could do the same thing. Treat deleting audit records, or changing how long they are kept, as high-impact too. That includes asking a more powerful tool or peer to do it. Some agents can do all three of these in one context: read untrusted input, reach sensitive data or systems, and change things or talk to the outside. For those agents, treat every consequential action as high-impact. The exception is a design that stops untrusted content from picking the tool, destination, or arguments. Examples are plan-then-execute, a two-model pattern, or capability tracking such as CaMeL. Record which of the three each agent type has.**

- [ ] **B02 · G1 · C2 — Least-privilege access.** **Limit credentials to named operations and resources, including tenant boundaries. Test that an allowed read works. Test that an out-of-scope write, an admin action, and a request for another tenant's data all fail. Limit each token to its intended audience, so other services reject it. Remove wildcard permissions and permissions inherited from people.**

- [ ] **B01 · G1 · C4 — Minimal tool surface.** **List every built-in tool, MCP server, API, program, and file permission this agent type can use. Give a task-based reason for each. Enforce a role-based allowlist, and check that an unlisted tool can't be called. Don't base allow or approval decisions on hints a server gives about its own tools, such as "read-only." MCP treats those hints as untrusted unless you trust the server.**

### Remaining checks

#### Capabilities and credentials

- [ ] **B03 · G2 · C2 — Credential lifetime and handling.** Issue short-lived credentials from a managed identity or secrets service. Keep long-lived secrets out of prompts, images, and checked-in config. Where the service supports it, bind tokens to their holder (mTLS, DPoP, or workload proof tokens). Then a copied token won't work from another machine. Don't use fixed API keys when short-lived or federated credentials are available. Show that credentials expire and rotate, and explain why you chose their lifetime.
- [ ] **B04 · G1 · C2 — Independent revocation.** Show that an operator can cut off this agent's access without cutting off the user who launched it. The agent must not need to cooperate. Set and measure the longest time before the cutoff takes effect. Count cached tokens, self-contained tokens, and open sessions. A trusted enforcement point must block later calls within a time limit that fits the potential harm. Revoking only the refresh token is not enough. If tokens live longer than that limit, push the revocation to each service (for example, with OpenID CAEP session-revoked events) or make the tokens shorter-lived.

#### Harness enforcement

- [ ] **B06 · G1 · C4 — Approval integrity.** Tie each approval to the agent instance that asked, and to the exact operation, target, arguments, and scope. Record who approved it and when it expires. Show the reviewer what the action will do. Make approvals single-use, or set clear limits on a broader grant. When the action runs, check permissions and the relevant resource state again. Record each use of an approval in one step, so parallel calls can't go past the grant. Test changed arguments, a different agent instance, expired approvals, replay, parallel reuse, and approvers without authority. If the approval service fails, the action must not quietly go ahead.
- [ ] **B07 · G2 · C4 — Hard execution budgets.** Enforce limits outside the model on loop count, run time, tokens, cost, tool-call rate, and how many sub-agents it can start. Also set spend and rate quotas per user or service, per tenant, and across the whole fleet. That way, many small runs can't use up shared capacity. Hit each limit in a test, and record how the run stops or escalates.

#### Environment and build artifacts

- [ ] **B08 · G2 · C1 — Environment isolation.** Write down every system and data store the agent can reach. Test that it has no path to unapproved production resources, admin systems, host services, or other tenants. Enforce this in the infrastructure, not only in the prompt. For each allowed connection, also check input and response validation under **R01–R02**, including API responses and messages from connected services. Being allowed on the network does not make their content trusted.
- [ ] **B09 · G2 · C1 — Egress allowlist.** Allow only the outside destinations the task needs. Test a blocked destination and ways around the block, such as going straight past a proxy or gateway. Cover redirects, DNS changes and rebinding, IPv4 and IPv6, and cloud metadata or loopback addresses where they apply. An allowed domain can still host an attacker's account or receive leaked data. So also limit which resources and tenants the agent can reach, and what data it can send. Record each block and confirm the right operator hears about it.
- [ ] **B10 · G2 · C3 — Pinned, verified image.** Pin the container by digest. Before it runs, check its digest and signature against an approved signing key, or an approved certificate identity and issuer. Keep its build provenance (the record of how it was built) and its list of dependencies. Check provenance fields such as the builder, source repository, build type, and the parameters set from outside the build (SLSA `externalParameters`) against what you expect. Keep the verifier patched. Cosign versions before 2.6.2 and 3.0.4 could accept a bundle whose transparency-log entry didn't match the artifact. Confirm that the admission check covers production namespaces and is set to enforce, not just audit. Show that an unapproved or changed image is rejected.
- [ ] **B11 · G2 · C3 — Minimal, isolated runtime.** Remove shells, downloaders, package managers, mounts, and privileges the agent doesn't need. As a container baseline, meet the Kubernetes Pod Security Standards "restricted" profile or the same controls elsewhere. That means non-root, no privilege escalation, all capabilities dropped, and a seccomp profile set. Where supported, also use a read-only root filesystem and user namespaces; the restricted profile doesn't require those two. For running untrusted code, use a sandbox that fits the threat, such as a microVM or a user-space kernel. Ordinary containers share the host's kernel. For managed runtimes, record the provider's isolation evidence and what you can't see. Test that host access is blocked. A blocked probe does not prove the sandbox resists every escape.
- [ ] **B12 · G1 · C4 — Reviewed harness and instructions.** Version and review the harness, system prompt, and rules files before release. Allow production changes only through a release process that records who made them. Protect source branches from history rewrites, so the reviewed diff stays available. Link the deployed versions to the approved review. Complete the full configuration checks in section C.

**Evidence to attach:** capability inventory and capability-combination record; permission and denial tests; approval records; budget tests; network policy; image digest and signature checks; harness and prompt review.

## R — Run-time

**Question:** When hostile input reaches a running agent, do containment, detection, and recovery still work?

[Read the Run-time guide](guides/run-time/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#r--run-time).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **R11 · G1 · C8 — Tested kill switch.** **Name who may stop the agent and how. The stop path must not depend on the agent's cooperation. The agent's credentials must not be able to change it. Set a maximum stop time that fits the potential harm. Run a dated drill on the current deployment. It must stop new actions, running work, and open tool streams, subscriptions, and tasks. Include an attempt by the agent to disable or delay the stop. Cover sub-agents and their children in the ecosystem drill (E09).**

- [ ] **R13 · G1 · C9 — Full execution audit.** **Record each run as an execution graph: a linked record of every step. It must include proposed actions, tool calls and key arguments, and authorization decisions with the policy version used. It must also include denials, approvals with their IDs, results, errors, and timestamps. Rebuild a typical run from this record, including failed actions. Don't rely on the run's final answer.**

  **Why this is hard:** Agent logs usually show what the agent tried. The destination system knows whether it actually happened. A timeout can mean the call failed, or it worked and the reply was lost. So a local trace can look complete and still have an unknown result.

  **If you can't fully do it:** Give each operation an ID before you send it. Keep receipts or status checks from the destination where you can. Match attempts against the destination's records, and mark unresolved results clearly. Pause dependent actions and retries until each one is resolved. If an integration can't give you enough evidence to trace and recover, limit or remove that path. Sampling and the agent's own reports can't replace the required action record.

  **Tradeoffs you can accept:** Pausing dependent work while an unclear result gets resolved. Keep the attempt, the uncertainty, and the final answer in the graph. Less automation is a fair cost. Missing or made-up action evidence is not a G1 pass.

- [ ] **R01 · G2 · C5 — Validate every input boundary, including API responses.** **List every input the agent receives. That includes API responses (errors and streamed content too), tool and connector output, incoming webhooks and callbacks, messages from other agents, user input, fetched pages, files, and retrieved chunks. Authenticate each sender (prove who sent it), and verify signatures where they exist. Treat content as untrusted even when it comes from an authenticated service or an internal one. Before content reaches the model or runs anywhere, check its type, schema, and size. Also check its content for attack payloads and hidden prompt-injection instructions. Reject or hold aside bad payloads. If a required check fails to run, don't let unchecked content through. Test broken, oversized, faked, and hostile responses from each integration.**

  **Why this is hard:** An API response can be well-formed, correctly signed, and still carry harmful instructions. Free text and streamed responses are hard to inspect fully. Passing a schema check proves the structure, not that the content is safe.

  **If you can't fully do it:** Start with type checks, size limits, sender checks, and rejecting broken content. Add content checks for attack patterns you've seen. Buffer or limit streams when the required checks can't run before use. Keep permissions narrow, and use R02 to contain instructions that slip through. Record which integrations and payload types you tested and which you didn't.

  **Tradeoffs you can accept:** Buffering delay, rejecting some valid responses, or supporting fewer payload types. Incomplete detection of attacks hidden in meaning can get G2 risk acceptance. That needs tested containment and clear limits on what was covered. Schema checks alone don't fully protect against injection.

### Remaining checks

#### Input, output, retrieval, and memory

- [ ] **R02 · G2 · C5 — Separate data from instructions and test injection containment.** Keep API responses, connector messages, and other outside content out of trusted system and policy channels. Label where each piece came from and how much it is trusted. Test prompt injection in responses that pass schema checks. Include free-text fields, error messages, documents, and tool output. Checks and channel separation can't guarantee that prompt injection is prevented. So show that credential limits, tool permissions, and destructive-action gates still block harm if the model follows an injected instruction. Repeat each attack and include adaptive versions. One failed attempt makes a defense look stronger than it is. B05 covers agents that combine untrusted input, sensitive access, and outside actions.

  **Why this is hard:** A model may follow an instruction hidden in normal-looking data, even with separate channels. A fixed set of injection tests can't prove that every injection will fail. Model behavior can also change from run to run.

  **If you can't fully do it:** Assume some injections will work. Send the forbidden calls they would cause straight to your credential limits, egress rules, and action gates. Also run full end-to-end examples. Limit the tools and data the agent can reach. When containment is uncertain, make high-impact actions draft-only, or require approval for each one. Report structure checks, injection detection, and blocked side effects as separate results.

  **Tradeoffs you can accept:** Fewer finished tasks, fewer tools, and more approvals, each for one specific action. Remaining detection gaps can get G2 acceptance with clear exposure and separate proof of containment. The required access and destructive-action gates still apply.

- [ ] **R03 · G2 · C5/C9 — Prevent output and log leakage.** Remove secrets and limit sensitive data before tool output, debug output, or responses reach the model, outside recipients, or normal logs. Some clients fetch URLs on their own when they display output, such as Markdown images and link previews. These can leak data without any tool call, so block them or allow only approved URLs. Check generated output before it goes into SQL, a shell, an HTML page, or anything else that runs it. Use parameterized queries and commands (for example, argument lists for shell calls), and the right escaping for each context. Test with fake secrets and injection payloads. Confirm that leaks and unintended execution are blocked, and that redacted audit evidence is kept.
- [ ] **R04 · G2 · C5/C6 — Retrieval-corpus integrity.** The **retrieval corpus** is the set of documents the agent searches for context. Its **index** stores those documents, or smaller passages called chunks, in a search engine or vector database. Limit which identities and sources can add or change content there. For each chunk, keep its source, when it was added, its trust level, and its access permissions. Enforce the requesting tenant's access when searching. Test an unapproved attempt to add content and a search across tenants. Also test quarantining, expiring, and revoking access to seeded test documents. Confirm the affected chunks disappear from search results and caches within a stated time. See the [R04 recipe](CHECKLIST-VERIFICATION.md#r--run-time).

  **Why this is hard:** Removing a document from the index doesn't remove copies in caches, running contexts, summaries, or memory. Permission changes can take time to spread. And if the model leaves a document out of its answer, that doesn't prove search excluded it.

  **If you can't fully do it:** Set a limit you can measure, such as "no revoked chunks in new search results after N minutes." Check current access at search time, clear caches, and stop or restart affected runs when needed. If you can't find all affected copies, quarantine the whole collection and rebuild it from approved sources. Record copies that remain and how long they were exposed. Don't claim you removed every derived copy.

  **Tradeoffs you can accept:** A stated revocation delay that fits the risk, search downtime, or less search coverage while you rebuild. Record the exposure during the delay and any G2 exception. Where access must end right away, block the affected searches and runs until revocation takes effect.

- [ ] **R05 · G3 · C6 — Memory isolation and write validation.** Separate memory by tenant, agent type, instance, and task as needed. Block access across those lines unless it is clearly approved. Check what gets written to memory. Test that one poisoned run can't quietly plant instructions in another run's memory. Don't move the agent's own output into trusted memory without review, and let unverified entries expire. Write checks must also cover content that arrives through ordinary queries, not just special write paths.

  **Why this is hard:** A saved preference or summary can act as an instruction in a later session. Write checks can't always tell a useful memory from a harmful one, especially when agents share memory across tasks.

  **If you can't fully do it:** Start with memory per task or per instance, and turn sharing off by default. Allow only defined memory fields. Require review before an entry moves into shared, long-lived memory. If a store can't keep memory separate, turn off saved writes or sharing for that workflow. Test the reduced setup, and record any feature you turned off to get there.

  **Tradeoffs you can accept:** Less personalization, repeated work, or shared memory that only holds reviewed entries. Turning off saved writes or sharing can reduce exposure. Any remaining memory-control gap can be deferred only where G3 allows.

- [ ] **R06 · G3 · C6 — Memory provenance and cleanup.** For any memory entry, look up who wrote it, when, for which task, from what input, and the context size at the time. Show that you can find, quarantine, and remove bad entries, and control their reuse in later sessions.

  **Why this is hard:** Summaries and other derived memories can lose their link to the source that tainted them. Deleting one known entry can leave related content in use. Tracking each entry's source can't recover history that was never recorded.

  **If you can't fully do it:** Keep source and writer links on new entries and on summaries made from them. When the history is incomplete, quarantine or reset the affected memory area and its caches. Restart affected sessions and rebuild from known sources. Record the wider reset and the useful memory it cost. Keep missing provenance as a Gap until you can show it. A cleanup alone does not restore it.

  **Tradeoffs you can accept:** Losing useful memories, and the cost of resetting a wider area when a precise cleanup isn't possible. Missing provenance stays a G3 gap. Record what was thrown away and how trusted memory will be rebuilt.

#### Detection and operational limits

- [ ] **R07 · G2 · Obs-T2 — Decision-time context size.** For each action, log how full the model's context was when it decided, in tokens. Document how you count. Say whether each value was measured, estimated, or unavailable. Cover cached input, compaction (shrinking the context), and limits the provider hides. Per-call billing totals don't automatically equal context size. Use them only if your counting method shows they match. A missing value is a clear gap, never zero. Check that the value survives tool handoffs and can be searched next to the action's identity and result. See the [telemetry conventions](otel-conventions.md).
- [ ] **R08 · G3 · C7 — Security monitoring.** Keep security rules and baselines separate from answer-quality monitoring. Test encoded payloads, unexpected outbound traffic, writes outside scope, privilege escalation, and repeated denied calls. Check that alerts reach a named responder.
- [ ] **R09 · G3 · C7/Obs-T2 — Sequence and context-aware detection.** Test suspicious chains of actions that are each allowed on their own. Also test unusual fan-out and resource use. Compare behavior across context-size ranges, so one fleet-wide baseline doesn't hide failures in long contexts. If the agent could be hijacked while using only allowed tools, check each high-impact action against the original task before it runs. Use a checker that doesn't see the untrusted content in between, and measure what it misses.

  **Why this is hard:** Real research and data theft can look alike step by step. Real attack examples may be rare. A detector tuned only to test cases can miss real behavior, or flood responders with false alarms.

  **If you can't fully do it:** Start with a few clear signals. Examples: an unusual number of reads followed by an outside send, repeated denials, too many sub-agents, or a used-up budget. Measure how many seeded attacks you catch, how many false alarms you raise, and how fast alerts arrive, for each context-size range. Use hard rate and cost limits, and limit destinations, while you improve detection. Say exactly which sequences you cover and which you miss. Basic rules don't prove general sequence detection.

  **Tradeoffs you can accept:** A narrower, written detection scope, and a measured false-alarm rate that responders can handle. For lower-stakes deployments, defer broader coverage under G3 while keeping hard limits. Where G3 blocks release, reduce the real exposure or finish the required coverage.

- [ ] **R10 · G3 · C7 — Misaligned-behavior review.** If deliberate misalignment is in scope, test a second model or pattern review against realistic evasive behavior. Record what it can and can't catch. Include what the reviewer can see: actions, arguments, and any visible reasoning. Reasoning the reviewer can't see is a stated gap. Include red-team runs by an agent that knows it is being watched. This review must not replace rule-based access and action controls that don't depend on a model's judgment. Deeper checks on intent belong in a separate AI-control program at the model level.

  **Why this is hard:** Actions don't reliably reveal hidden intent. A second model can share the first model's blind spots. Catching labeled evasive examples doesn't prove you will catch deliberate misalignment.

  **If you can't fully do it:** Make narrow claims about behavior you can see. An example is catching attempts to split a forbidden operation across several calls. Keep a record of misses and false positives. Rely on separate permission limits, action approvals, and stop controls for containment. Where detection falls short, reduce autonomy or remove high-impact powers. Record an unproven detector as a gap. Never label the model's intent as safe.

  **Tradeoffs you can accept:** Uncertainty about hidden intent, as long as claims stay limited to measured behavior. This checklist does not certify alignment. Less autonomy and more review are also fine. Missing required behavior detection still falls under G3.

#### Stop, explain, and recover

- [ ] **R12 · G1 · C8 — Safe state after stopping.** Decide what happens to writes in progress, queued actions, and outside side effects. Where you can't cancel something, show how you check and fix the result (reconcile) or undo it another way (compensate). No restart may happen unattended, and no orphaned work may be left able to act.

  **Why this is hard:** An outside action may already be done when the stop arrives. Emails can't reliably be unsent. Payments, writes, and queued jobs each cancel and reconcile differently.

  **If you can't fully do it:** For each operation, record whether it can be blocked, canceled, or only reconciled afterward. Stop new work from being sent, turn off retries, check the destination's state, and send unclear results to a named operator. For operations with no workable recovery path, remove autonomous execution or use an approved draft-then-commit flow. Measure stopping new work separately from resolving work already done. Stopping the process alone does not pass this check.

  **Tradeoffs you can accept:** Slower manual reconciliation and fewer autonomous actions. Some completed effects may need reconciling rather than reversing, following the written safe-state procedure. Untracked effects, or work that keeps its authority past the stop time limit, still block release.

- [ ] **R14 · G2 · C9 — Recovery integrity.** If logs or checkpoints drive recovery, make them tamper-evident. Before using them, verify them against a separately protected trust anchor or signing key. Test that verification rejects changed checkpoints. It must also catch truncation, rollback to an older valid checkpoint, and replacement of a whole hash chain. For automatic recovery, confirm the destination supports idempotency: sending the same request twice has the effect of sending it once. Replay only within the destination's documented scope and time window. Confirm that actions you can't undo don't happen twice. Where support is missing or the result is unclear, check that replay pauses for reconciliation instead of sending again.

  **Why this is hard:** Not every outside API supports idempotency keys or a reliable status check. A crash between a successful remote action and the local checkpoint can make replay repeat that action. A local table of past requests doesn't close that gap.

  **If you can't fully do it:** Use idempotency enforced by the destination where it exists. Write a durable operation record before sending. If the result is unclear, pause replay and reconcile using the destination's evidence or an operator. Don't retry blindly. Turn off automatic replay for side effects that don't support it, and document that limit. Reject checkpoints you can't verify, and recover from a trusted state. Manual recovery doesn't prove automatic replay is safe.

  **Tradeoffs you can accept:** Manual recovery, slower completion, and no automatic replay for unsupported integrations. Never call blind retries of unclear, permanent actions "safe replay." Remaining recovery-control gaps need allowed G2 acceptance.

**Evidence to attach:** input-boundary and leakage tests; retrieval and memory provenance samples; context-size traces; triggered alerts; kill-switch timing; a rebuilt run; tamper and replay tests.

## A — Agent

**Question:** Can we identify, limit, stop, and explain every agent and model involved in an action?

[Read the Agent guide](guides/agent/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#a--agent).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **A01 · G1 · C2/Obs-T1 — Distinct agent identity.** **Give the agent its own non-human identity. Keep it separate from the user who launched it and from unrelated agents. Show that permissions and revocation belong to that identity, even when a user starts the run.**

- [ ] **A02 · G1 · Obs-T1 — All six identity fields.** **Check that every action records the accountable party, operational owner, tenant, agent-type-id, agent-instance-id, and trace context. Look at successful, denied, failed, and background actions, not just the main request path.**

- [ ] **A03 · G1 · Obs-T1 — Content-derived type identity.** **Compute the agent-type-id as a hash of the container digest, harness, system prompt, model ID and version, and configuration. The model part includes checkpoint and fine-tune or adapter references where they apply. Keep the list of inputs (the manifest) and the hashing steps. Check that changing any input changes the ID, and that the same manifest gives the same ID.**

  **Why this is hard:** A hash only covers the inputs you can see. It can't prove that a hosted model's hidden weights or training stayed the same behind the same name.

  **If you can't fully do it:** Hash the exact local artifacts and the model, checkpoint, and adapter references you have, using a manifest anyone can rebuild. Record the model name you asked for separately from the version the provider says it served. Mark hidden information clearly. State that the ID fingerprints this recorded setup. Handle changes behind remote names under C05. Never use the agent app's release number as the model's identity. Never present a local hash as proof of the provider's hidden state.

  **Tradeoffs you can accept:** A fingerprint that covers only the recorded setup, with the provider's hidden details clearly outside the claim. Track changes behind remote names under C05. Missing hashes or model references for artifacts you control still fail this G1 item.

### Remaining checks

- [ ] **A04 · G1 · C9/Obs-T1 — Trustworthy attribution.** Assign instance and tenant identity in the trusted execution layer. Don't accept labels the model supplies. Record the delegated subject — the user or system whose authority is being used — separately from the agent's identity. Test that the agent can't pose as another instance or tenant in requests or audit records. Test that trace context survives handoffs between async jobs. Treat trace IDs and caller-supplied labels only as a way to link records. They never prove identity or permission.
- [ ] **A05 · G1 · C8/C9/Obs-T1 — Operational lookup.** Start from one suspicious action. Find the team responsible, the current operator, the deployment manifest, and the live instance. Show that you can contain the right instance or agent type without cutting off the launching user's other access.
- [ ] **A06 · G3 · Obs-T3 — Parent and prompt provenance.** For every sub-agent, record its own type and instance IDs, a link to its parent, trace links, and the prompt the parent gave it. Trace a nested action back to that prompt. Protect sensitive prompt text with restricted storage and a clear redaction policy. Standard GenAI instrumentation records prompts only when you turn that on, so confirm it is on for this path.
- [ ] **A07 · G3 · C7/Obs-T1 — Every model in the loop.** List all helper models, such as verifiers, judges, rerankers, and world models. Give each one an identity based on its available model version or digest, its prompt, and its configuration, and record which decisions it made. Show that a swapped, drifting, or failing checker counts as a failure of the control that depends on it.

**Evidence to attach:** identity issuing and revocation records; sample actions with all six fields; manifest and hash tests; impersonation test; operator lookup drill; nested trace and parent prompt; list of checker models.

## C — Configuration

**Question:** Is the configuration we approved the one that is actually running?

[Read the Configuration guide](guides/configuration/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#c--configuration).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **C01 · G2 · C1–C6/Obs-T1 — Complete release manifest.** **Write a release manifest: a list of everything that makes up this release. Include the container, harness, system prompt, rules files, model, built-in tools, MCP servers, permission scopes, memory and retrieval settings, identity bindings, network rules, and execution budgets. Include security-policy versions. Add a separate model record for every model: the main agent model, sub-agent models, and helper models such as embedding models and rerankers. For each, record the provider, model ID, exact version or checkpoint, and any adapter or fine-tune version. For training or fine-tuning you run yourself, also record the training job ID, base-model version, training code and config version, dataset version, and the digest of the output. The agent app's release number alone is not enough. Use the [model provenance fields](CHECKLIST-VERIFICATION.md#model-provenance-fields) to separate recorded versions from details a provider doesn't share. Check each model ID you request against the provider's versioning docs. Mark it as a pinned snapshot or as an alias that can change, and record which doc you used and its date. Naming rules differ by provider and model generation. Name each artifact's owner and a reference that can't change, where one exists. A machine-readable format, such as CycloneDX ML-BOM or the SPDX 3.0 AI and Dataset profiles, lets tools check the manifest.**

  **Why this is hard:** Teams can usually find their own training jobs and datasets. A hosted provider may not share its pretraining runs, weights, or data versions. Separate the records your team should have from the details the provider keeps private.

  **If you can't fully do it:** Fill in model records from serving metadata, registries, and training-job output. Require full history for training your team runs. Clearly label fields the provider hides, and keep where and when you checked. Prefer a fixed provider snapshot when one exists. Record missing training history your team should have as a Gap, and rebuild it first. Never make up training versions. Never treat a provider alias as a training job ID.

  **Tradeoffs you can accept:** Provider pretraining details that are clearly marked as not shared, as long as your own model-selection and training records are complete. A G2 gap in visibility or history can get written acceptance with an owner and review date. Unknown records must never be written down as real versions.

- [ ] **C03 · G1 · Obs-T1 — Match release identity to running state.** **Freeze the artifacts that define identity for each release. Check the running setup against the approved manifest, and emit the matching agent-type-id. Include the digest and signature of weights and adapters you host yourself. Test that a changed prompt, model, weights file, or tool setup can't keep showing the old approved identity without being caught.**

  **Why this is hard:** A manifest or an ID the agent reports about itself can stay the same while the running prompt, tool setup, or hosted model changes. You may not be able to inspect a provider's internals yourself.

  **If you can't fully do it:** Observe local artifacts and deployment settings yourself, not from what the agent reports, and compare them with the manifest. Block or quarantine any mismatch you find. Check the served model's metadata when the provider shares it. Limit the claim to artifacts you control and provider references you can see. Track hidden remote state under C05. A provider's limits never excuse an unchecked local setup. Changed local artifacts must never keep their approved identity unnoticed.

  **Tradeoffs you can accept:** Checks limited to artifacts you control and provider references you can see, with hidden remote state handled under C05. More frequent checks may cost time and compute. Unchecked local artifacts, or unnoticed changes to declared local settings, still block release.

- [ ] **C04 · G2 · C1/C3/C4/Obs-T1 — Detect drift per agent.** **Compare running images, harness settings, prompts, MCP server lists, permissions, network policies, and self-hosted model weights against their approved baseline. Simulate a prompt edit, an added tool, and a looser egress rule. Check that each one raises an alert and gets the documented response — block, quarantine, or rollback — within a set time.**

### Remaining checks

- [ ] **C02 · G2 · C1–C7 — Review security-relevant changes.** Require diffs with a named author, plus review, for changes to the manifest and its policies. Show who is allowed to change production config. Record emergency changes with an owner, a reason, an end date, and a follow-up review.

- [ ] **C05 · G2 · C3/C4/C7 — Control dependency, model, and training changes.** Pin dependency versions. Where supported, also pin each model's base version, checkpoint or weights, and fine-tune or adapter version. Before promotion, link any changed training run, dataset, or training code or config to the model it produced and to its test results. Record the model version actually served, when the runtime or provider shares it, separately from the name you requested. Before loading weights, adapters, or datasets you host, check their signature against an approved signer (for example, with OpenSSF Model Signing). Also check their file format. Pickle-based formats can run code when loaded, so they need an approved exception and a scan. Test swapping a model, checkpoint, or adapter, and check that it triggers review and re-testing. Some remote services or names can change behind a fixed name. For those, record missing training and version details clearly. Watch available version metadata and provider notices, and decide when to re-test or stop using the model. A local config hash alone can't prove remote behavior is unchanged. A pinned snapshot fixes the weights, not the provider's serving systems, which can change under the same ID. Keep scheduled re-testing.

  **Why this is hard:** A hosted service may change behind a name without sharing a version ID or training history. Behavior tests can catch some changes, but they can't prove nothing hidden changed.

  **If you can't fully do it:** Prefer pinned snapshots. Otherwise keep both the requested and the observed IDs, watch provider notices, and schedule realistic tests with a named owner. Limit permissions and autonomy while you're unsure of the version. Decide in advance what triggers a pause or a move to an approved alternative. Record gaps from names that can change, and any allowed risk acceptance. Tests and provider notices help manage uncertainty. They don't prove the model's identity is fixed.

  **Tradeoffs you can accept:** The ease of a hosted model, with less reproducibility and possibly slower detection of changes, once that exposure has written G2 acceptance. Set a testing schedule and decide when use must stop. If the uncertainty matters too much, choose a pinned alternative or reduce the agent's powers.

- [ ] **C06 · G2 · C4–C9 — Re-test changed behavior.** Before promotion, run typical allowed tasks and attack cases against the release candidate. Include destructive-action denial, access limits, injection containment, audit attribution, and stopping. Include retrieval, memory, and checker tests where they apply. If misalignment is in scope, include attempts to slip past monitoring and the stop path. Keep the results for the exact candidate manifest.
- [ ] **C07 · G2 · C8/C9 — Rollback and restart.** Keep an approved recovery setup and show that rollback works. Confirm each hosted model it names is still offered, and record the announced retirement date. Account for changed credentials, memory and index state, checkpoints, and queued work. Don't restore revoked permissions or replay unsafe side effects just because the old artifact still exists.
- [ ] **C08 · G2 · Obs-T1/Obs-T2/Obs-T3 — Connect configuration to execution.** From a trace, look up the release manifest, the context sizes at each decision, and any prompts a parent passed to a sub-agent. Keep these links for the full audit retention period. Control access to sensitive artifacts.

**Evidence to attach:** release manifest; approved diffs; running-state comparison; drift drill; remote-version limits; release test results; rollback test; trace-to-manifest lookup.

## E — Ecosystem

**Question:** Do the tools, other agents, vendors, and shared services enforce their half of every control?

[Read the Ecosystem guide](guides/ecosystem/index.html) and [MCP gateway guide](guides/mcp-gateway/index.html). [Verification recipes for this section](CHECKLIST-VERIFICATION.md#e--ecosystem).

### **IF YOU DO NOTHING ELSE — TOP 3**

- [ ] **E06 · G2 · C1/C2/C4/C5/C9 — Enforced gateway boundary.** **Send MCP calls through a gateway, or a similar enforcement layer, that the agent can't get around. Authenticate each caller (prove who they are), authorize each action, and validate calls and responses. Enforce rate limits and log every decision. For HTTP and OAuth, check the token's issuer, intended audience, expiry, and scopes. Use properly authorized credentials for the services behind the gateway. Never pass an unchecked token through. For local tools that talk over standard input/output (stdio), control process launch, file access, credentials, and networking in the host or sandbox. An HTTP gateway alone doesn't cover these. Test going around the gateway straight to the server, bad credentials, broken responses, and outages of the policy engine or scanner. MCP copies some request details into headers. If routing or policy uses those headers, reject any request whose headers don't match its body, before checking policy. Store any cached tool list or response separately for each authorization context. When the gateway is itself an OAuth client, check the issuer (`iss`, RFC 9207). Also protect discovery URLs against SSRF (tricking a server into calling places it shouldn't). Required checks must fail closed: if a required check can't run, block the action.**

- [ ] **E08 · G1 · C2/C4 — Bounded delegated authority.** **Give sub-agents only the powers approved for their task. Enforce each child's role and any explicit approval from a higher authority. A parent must not gain a power it was denied just by asking a more powerful peer to act. Narrow credentials at each hop, for example with token exchange or transaction tokens. Authorize based on the original subject (the user or system whose authority is used) and the current actor. Earlier actors in a delegation chain are for the record only, not a reason to grant access. Test that escalation attempt.**

  **Why this is hard:** A powerful peer may treat a low-privilege agent's request as a normal task. Knowing who sent the last message doesn't prove what the original requester was allowed to do. Delegation limits can also get lost across several hops.

  **If you can't fully do it:** Carry the verified original identity, tenant, and allowed scope all the way to where the action runs. If a peer can't enforce those limits, delegate only to peers with no more relevant authority. Or use a narrow task credential, or require separate approval for that exact privileged action. If none of these can be enforced, turn off that delegation path. Trusting a peer's prompt does not pass this blocking check.

  **Tradeoffs you can accept:** Less flexible delegation, narrower child roles, or separate approval for each action. These keep the authorization boundary intact. Quiet privilege gains can never pass this G1 check. Turn off the path if you can't enforce the boundary.

- [ ] **E09 · G1 · C8 — Recursive shutdown.** **Run a drill across a parent, nested children, remote workers, queued work, and open tool streams, subscriptions, and tasks, where they exist. Check that the stop reaches every descendant within the set time. It must revoke access as needed and prevent orphaned retries or restarts. Record how outside effects that already happened are reconciled.**

  **Why this is hard:** Remote workers, disconnected children, queued work, and open tool streams, subscriptions, and tasks can outlive the parent. A stop message can arrive late or get lost. Remote effects that already happened may not be cancelable.

  **If you can't fully do it:** Combine stop signals that spread down the tree with revocation, time limits on tasks, and short-lived leases that must be renewed to keep working. Block new work from being sent. Test that disconnected workers lose the ability to act within the stop time limit. Decide separately how long-running calls get canceled or reconciled. Leave out remote execution paths that can't meet the time limit. Record completed effects separately and reconcile them under R12.

  **Tradeoffs you can accept:** Fewer remote workers, the overhead of renewing leases, and slower completion. A set stop time is fine when it is tested and fits the potential harm. A worker that keeps its authority past that time is a blocking gap.

### Remaining checks

#### Supply chain and tool boundaries

- [ ] **E01 · G2 · C1–C9 — Map shared responsibilities.** List the outside tools, MCP servers, peer agents, sub-agents, registries, identity services, gateways, stop channels, and audit services. For each control that applies, name the owner on the agent team and the owner on the shared platform or vendor side. Keep evidence for both halves. Using an upstream service doesn't make its controls N/A.
- [ ] **E02 · G2 · C3/C5 — Vet and pin dependencies.** Before approving a tool or server, review its source code or available provenance, publisher, permissions, update path, and known vulnerabilities. Include model files, adapters, and datasets. Pin versions or digests, and verify signatures where they exist. A registry's namespace check shows who controls a publisher account, not that the code is safe. Record the limits of remote services and unsigned artifacts, and the extra checks you use instead.
- [ ] **E03 · G2 · C5 — Re-check tools on load.** Take a fingerprint of each approved tool's description and schema. Compare it every time the tool loads, the cache refreshes, or the server says its tool list changed. Don't use a cached definition when the re-check fails. Test a changed description, schema, or implementation version, and block unexpected changes until they are reviewed. A fingerprint of the description and schema catches changes to that metadata, not hidden changes to remote code. Pin or attest the implementation where you can see it. For remote implementations, record what you can't inspect and when you'll review them again. Track vulnerability notices, and find which deployments use an affected dependency.
- [ ] **E04 · G2 · C5 — Inspect tool metadata.** Before the model sees them, scan server instructions, tool names, titles, descriptions, input and output schemas, annotations, and prompt and resource templates. Look for hidden instructions, references to other servers' tools, invisible or control characters, role overrides, encoded payloads, and places data could be sent. Limit lengths, and clean or reject anything suspicious. Check that a scanner error doesn't quietly let unchecked metadata through.

  **Why this is hard:** Hidden instructions can be written in plain language, with no strange encoding or control characters. Scanners can also flag honest descriptions. A clean scan doesn't prove a tool is trustworthy.

  **If you can't fully do it:** Use a small approved tool catalog, with reviewed, versioned descriptions and schemas. Block unexpected changes. Keep rule-based limits and known-pattern checks even without advanced scanning. Limit each tool's powers regardless of what its metadata says. Turn a tool off when the required inspection isn't available. Record what the scanner covers and misses. Manual review and pattern scans are useful layers. They don't prove every poisoned tool is caught.

  **Tradeoffs you can accept:** A smaller catalog, review delays, and some honest metadata getting rejected. Limited scanning for attacks hidden in meaning can get G2 acceptance, as long as tool powers are limited separately. Known-pattern tests don't prove you can catch every poisoned tool.

- [ ] **E05 · G2 · C2/C5 — Verified, namespaced tools.** Identify each tool by a verified server identity plus the tool name. Base server identity on the verified endpoint, credential, or registry namespace. A server's self-reported name is neither unique nor trustworthy. Flag lookalike and duplicate names across servers. Test that a new server can't quietly swap its tool in for an approved one.

#### Delegation and shared operations

- [ ] **E07 · G2 · C2/C5 — Untrusted peer messages.** Authenticate the sending agent (prove its identity) on every message, even validly signed ones. Validate message types and schemas, and check what that peer is allowed to ask for. Where a replay could repeat an action, check freshness and track nonces or request IDs. Checking the sender alone doesn't stop replays. Test faked identity, replayed requests, requests across tenants, and instructions passed along by a compromised peer. Verify signed agent cards where they exist. A card says who an agent is, not what it may do. Check callback and webhook URLs against SSRF. A valid sender doesn't make a message's content trusted.

- [ ] **E10 · G1 · C9/Obs-T1 — Audit across service boundaries.** Rebuild a run across the gateway, tool services, and delegated workers, with all six identity fields kept. Check that the agent can't erase or rewrite its audit history, either directly or by asking a more powerful tool or peer. Check that a vendor boundary doesn't leave any action untraceable to the agent and instance that did it.

  **Why this is hard:** Vendor services may drop parent or tenant identity, or return only request receipts. That leaves gaps between your gateway trace and what happened downstream. Shared credentials make attribution even weaker.

  **If you can't fully do it:** Keep verified identity and correlation IDs at your gateway. Map them to vendor job or receipt IDs, and match them against any destination records you can get. Where identity can't be passed downstream, use separate, narrow credentials. Record which parts of the history you can't inspect. Gateway logs alone can't prove what happened inside those services. Limit or replace integrations whose evidence can't meet the attribution requirement. Don't mark the whole graph complete.

  **Tradeoffs you can accept:** Extra integration work, slower reconciliation, and leaving out services you can't see into. Mapping verified identity to vendor receipts can support attribution once you've shown it works end to end. Actions that can never be traced still block release.

- [ ] **E11 · G2 · C9 — Protect shared evidence.** Set rules for how long audit records are kept, who can see them, what is redacted, how their integrity is checked, and how they are exported and restored. Test pulling up a past run, and test that missing records or a broken pipeline get noticed. Keep records long enough for investigations and for the law. For example, the EU AI Act requires providers and deployers of high-risk systems to keep automatically generated logs for at least six months (Articles 19 and 26). High-impact actions must fail closed when required audit capture isn't working.

  **Why this is hard:** Audit delivery can fail while the agent keeps working. Buffers can fill up, records can arrive late, and a vendor may keep records for less time than you need. Exported logs may also hold sensitive data.

  **If you can't fully do it:** Use durable local buffering, or another protected audit path, with delivery receipts, backlog limits, and alerts for missing records. Export vendor evidence before the vendor deletes it, and limit who can see it. When buffering runs out or isn't available, pause affected actions before required evidence is lost. Record outages and any evidence you can't get back. A fixed pipeline doesn't bring back missing history.

  **Tradeoffs you can accept:** Short delivery delays while records stay safely stored, extra storage and export costs, and paused work during outages. Limits on retention or delivery can get G2 acceptance only if the required G1 action capture and attribution still hold. Disclose any lost evidence.

- [ ] **E12 · G3 · C7/C8 — Fleet incident response.** Run a drill where a shared tool or agent type is compromised. Find the affected instances and tenants. Quarantine the dependency, revoke the access involved, stop affected work, and alert the named responders. Check that alerts about abuse across agents, and about budgets, reach the team that can act. Name who decides whether to report outside the organization and share information.

**Evidence to attach:** dependency and responsibility list; provenance and fingerprint checks; metadata and lookalike tests; gateway bypass and outage tests; peer authorization tests; recursive-stop drill; cross-service audit trace; fleet incident drill.

## Evidence and exception record

Keep a completed copy with the release. Use one row per checklist item, and link to evidence that is stored safely and access-controlled. One test can serve several items if it proves each one, but record each item's result separately.

| Item ID | Outcome: Pass / Gap / N/A | Owner | Evidence link and test date | Gap or N/A rationale |
|---|---|---|---|---|
| B01 | | | | |
| …one row for each remaining item… | | | | |

For every allowed G2 or G3 deferral, also fill in:

| Item ID | Exposed threat and affected systems | Compensating control and evidence | Risk accepted by / date | Remediation owner and tracking link | Expiry / review date |
|---|---|---|---|---|---|
| | | | | | |

**Deferral rules:** No G1 waivers. No G3 deferrals for high-stakes or high-autonomy deployments. A blank, expired, or unapproved exception counts as an open gap. Every N/A must name its reviewer and the evidence that the feature or exposure doesn't exist.

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

- [ ] All **five aspects** are reviewed. Every item has a result, an owner, and evidence or an approved N/A reason.
- [ ] Every applicable **G1** item passes.
- [ ] Every applicable **G2** item passes or has a valid, approved risk acceptance.
- [ ] For high-stakes or high-autonomy deployments, every applicable **G3** item passes. For lower-stakes deployments, any allowed deferral has a valid, approved risk acceptance.
- [ ] Operators can reach the stop control, response instructions, evidence, and recovery steps.
- [ ] The approver has recorded the decision for the exact setup being released.

**GO only when every decision check above is met. Otherwise, NO-GO.**

### When to repeat the review

**Recompute the agent-type-id whenever an identity-defining artifact changes.** That means the container, harness, system prompt, model (including a new checkpoint, fine-tune, or adapter), or configuration, including the set of powers. Run this checklist again for the new release. Reuse old evidence only after you confirm it still applies to that exact setup.

Also reopen the affected checks after any of these:

- tool, server, or checker changes;
- changes to trust boundaries for memory or retrieval;
- shared-platform policy changes;
- incidents, failed drills, or detected drift;
- expired exceptions.

Keep scheduled reviews even when nothing is released. Credentials, dependencies, owners, and outside services can change on their own.

---

*Part of [BRACE](README.md), a security framework for autonomous AI agents. CC BY 4.0.*
