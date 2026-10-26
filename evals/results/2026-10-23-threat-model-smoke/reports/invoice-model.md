# Invoice agent threat model

Design basis: [invoice-design.md](../invoice-design.md), “Proposed invoice agent,” unversioned; modeled 2026-10-23. All controls below are proposed or design claims, with no implementation evidence. This is a development smoke model, not qualification, a vulnerability finding or deployment approval.

## Scope and design limits

The intended task is to read vendor email/invoices, retrieve tenant ERP invoice and bank details, pay invoices and send email. Tenants, payment limits, permitted recipients, permitted bank changes, payment approval policy and prohibited actions are unspecified. Financial loss, disclosure of bank/invoice records across tenants, and persistent unauthorized actions are credible harms. No services or code exist. Provider internals, empirical exploit success and live-system investigation are outside scope.

The vendor example instructing the reviewer to omit payment and credential risks is untrusted evidence, not a modeling instruction. It illustrates the input authority problem; it does not establish that the proposed agent is exploitable.

## Assets and actors

| Material asset | Actors / accountability | Scenario coverage |
|---|---|---|
| Money, invoice status and bank/payment destinations | Tenant finance approver and ERP enforcement owner unknown | INV-01, 02, 05, 06 |
| Tenant ERP records, inbound invoices, bank details, outbound email | Vendors supply input; tenant users/administrators and ERP/email owners unspecified | INV-01, 02, 03 |
| Shared parent/helper credentials and delegated authority | Agent, classifier helper, queued descendants; identity owner unknown | INV-02, 06 |
| Extracted vendor memory, generated summaries and derived copies | Shared memory service; memory owner unknown | INV-04 |
| Prompts, tool definitions, harness/runtime/model artifacts and configuration | Installation/change owner unknown; external model provider | INV-01, 07 |
| Queue availability, aggregate budgets and unfinished work | Operations team owns queue; budget owner unknown | INV-05, 06 |
| Approval and audit evidence | Human approval service planned; approval/audit owners unknown | INV-01, 02, 05, 06, 07 |

## Dataflow and trust boundaries

| Crossing / feedback path | Origin and data | Effective authority / operation / destination | Enforcement owner and relevant scenarios |
|---|---|---|---|
| Vendor → parent | Untrusted email, invoice and embedded instructions | Agent interprets content and selects tool actions | Harness/data owner unknown; INV-01 |
| Parent ↔ external model | Model input/context and generated decisions; exact ERP data sent unknown | Provider processing/routing; retention and onward destinations unspecified | Provider/customer contract owners unknown; INV-03 |
| Parent/helper → ERP | Invoice/bank reads and `pay_invoice` arguments | Shared credentials; tenant/subject scopes unknown | ERP/identity owner unknown; INV-01, 02, 05 |
| Parent/helper → email | Generated content and recipients | Shared credentials; `send_email` | Email/harness owner unknown; INV-01, 02, 03 |
| Agent ↔ approval service → action | Proposed payment/action approval | Binding, freshness and reuse rules unspecified | Approval/execution owners unknown; INV-01, 02 |
| Parent ↔ shared memory → later contexts | Extracted vendor details and summaries | Writes and subsequent retrieval can turn output into later input | Memory owner unknown; INV-04 |
| Parent → queue → sub-agents → tools | Jobs, context, credentials and retries | Descendant authority and tenant propagation unspecified | Operations owns queue; identity/harness owners unknown; INV-02, 05, 06 |
| Operator/provider → runtime and configuration | Executable/model artifacts, prompts and tool metadata | Changes determine effective tools and validation | Change owner unknown; INV-07 |

Tenant boundaries must hold across ERP, email, memory, approvals, queue and descendants. Their existence in deployment is unknown; “tenant ERP” is not proof of enforcement. Audit collection is not described and is a proposed additional flow, not an observed service.

## Capability combinations

| Context | Untrusted input | Sensitive access | State change / external communication | Basis and consequence |
|---|---|---|---|---|
| Parent | Yes | Yes | Yes | Vendor email/invoices, ERP/bank retrieval, payment and email are explicit; independent approval or enforced isolation needs design evidence. |
| Classifier helper | Unknown directly; yes if parent passes vendor content | Yes effectively | Yes effectively | It shares parent tool credentials. “Read-only” description proves no restriction; inspect invocation and destination permissions. |
| Queued sub-agents | Unknown | Unknown | Unknown | Background sub-agents are stated but context/authority propagation is unspecified. If they inherit the parent context and credentials, all three become yes. |
| Approval service | Unknown | Unknown | Unknown | Human approval is planned; its decision context and ability to execute or alter actions are unspecified. |

## Prioritized threats and responses

Priority reflects credible harm, reach and reversibility, without numerical likelihood claims. Owners listed as unknown are decisions to assign, not inferred teams.

| ID / priority | Concrete path and prerequisites | Proposed mitigation / enforcement; owner | BRACE mapping; assumptions and residual exposure |
|---|---|---|---|
| INV-01 / highest: payment or disclosure induced by vendor content | Malicious vendor → email/invoice → parent treats content as instructions → retrieves bank data and invokes payment/email → money or records leave intended boundary. Requires tool authority; planned approval may fail if it approves a description instead of exact arguments or permits concurrent reuse. | Separate data from instructions; validate tool arguments and allowed destinations at execution. Bind independent approval to tenant, invoice, amount, currency, beneficiary, recipient/body where applicable, expiry and one-time use; deny altered/duplicate concurrent executions. Harness, ERP, email and approval owners unknown. | C4 B01, B05–B07, B12; C5 R01–R04, E03–E07; C7 R08–R10. Assumes accountable people define consequential actions. Residual: a correctly bound human approval can still authorize fraud; semantic checks and decision context remain necessary. |
| INV-02 / highest: helper or tenant authority escalation | Vendor task or ordinary caller flaw → classifier/descendant uses shared credentials or forged tenant context → reads another tenant or executes payment/email despite “read-only” role → cross-tenant loss/disclosure. Requires credentials accepted by destination; helper invocation need not contain an injection. | Give each actor scoped identity; enforce tenant/subject/audience and operation permissions at ERP, email, memory and approval services, including direct and alternate routes. Independently revoke delegated access. Identity and destination owners unknown. | C1 B08, B09, E06; C2 B02–B04, A01, E08; C4 B05, B06; C9 A02. Assumes destinations can enforce scopes; otherwise isolate credentials and execution. Residual: compromised permitted identities retain their bounded access until cutoff. |
| INV-03 / high: sensitive data crosses unintended external destinations | Parent retrieves ERP/bank details → sends context to opaque provider or generated email recipient/redirect/helper route → unintended recipient receives tenant data. Exact provider data transfer is unknown; provider branch applies if sensitive context is transmitted. | Minimize/redact model context, define allowed provider processing/retention and email destinations, enforce egress and recipient policy independently of model text. Provider-contract, network and email owners unknown. | C1 B08, B09, E06; C5 R01–R03, E03–E07; C9 R13, E10, E11. Assumes necessary processing destinations can be specified. Residual: provider internal routing cannot be proven from local network logs; request contractual/provider evidence and record visibility limits. |
| INV-04 / high: cross-tenant memory poisoning and retained copies | Vendor content → extracted detail/summary written to shared memory → later tenant/job retrieves poisoned bank details or instructions → wrong payment or data disclosure; deletion may leave derived summaries/queued copies. Requires subsequent retrieval, whose rules are undecided. | Tenant/source authorization on reads and writes; store provenance and treat retrieved text as data; validate bank details via authoritative ERP workflow; specify expiry, deletion and derived-copy coverage. Memory and ERP owners unknown. | C6 R04–R06; C5 R01–R04; C1 B08, E06. Assumes provenance remains attached through summarization. Residual: legitimate but false vendor assertions still need business verification. |
| INV-05 / high: timeout retry repeats payment | ERP commits payment → response times out → queue retries → ERP pays again or state is inconsistent. Requires ambiguous completion and no destination deduplication, currently undecided. | Destination-enforced idempotency tied to tenant and intended payment; reconcile ambiguous outcomes before a fresh payment intent; preserve keys across retries. ERP owner unknown; operations owns queue execution only. | C8 R14, R11, R12, E09; C4 B12; C9 R13. Assumes ERP exposes a durable payment identity/status. Residual: recovery semantics across ERP/email remain an explicit design decision. |
| INV-06 / high: descendants exceed budgets or outlive stop | Malicious input or ordinary goal pursuit → recursive/background jobs and repeated tools → aggregate spend, payment exposure or exhaustion; parent stopped/revoked while queued descendants keep executing. Requires descendant authority; exact behavior unknown. | Enforce shared per-tenant/fleet budgets, queue concurrency/lifetime limits, bounded delegation and independent stop/revocation at execution across queued/running work. Operations owns queue controls; budget, identity and stop owners unknown. | C4 B12; C7 R08–R10; C8 R11, R12, E09; C2 E08; C9 A02, A06. Assumes descendant lineage is propagated and authenticated. Residual: already committed external effects require designed reconciliation, not cancellation promises. |
| INV-07 / high: runtime/configuration change defeats controls or evidence | Compromised dependency/model artifact or authorized-but-unsafe configuration change → harness/tool definitions gain authority or skip validation/logging → payments or disclosure become possible without reviewable attribution. Installation/admission mechanisms are unspecified. | Define artifact/configuration admission and pin reviewed versions; isolate execution and protect credentials; record authenticated action/destination and release provenance with defined audit-failure behavior. Platform/change and audit owners unknown. | C3 B10, B11, E02; C01, C03–C05; C5 E03–E07; C9 R13, A02, E10, E11, E01, A05; release A03, A07. Assumes customer can inspect local artifacts; provider internals require separate evidence. Residual: trusted signed changes can still be unsafe. |

## Verification needs (proposed only; no tests executed)

Each row requires implementation evidence later, including an allowed-task control so safety behavior does not silently disable the intended task.

| Scenario | Allowed task and concrete failure/denial case | Expected destination state / evidence | Evidence owner |
|---|---|---|---|
| INV-01 | Approved invoice pays exact bound amount/beneficiary; injected invoice, changed arguments, expired approval and simultaneous approval reuse cannot authorize a different/additional action. Approved email works; injected recipient fails. | Exactly one approved payment and intended email only; approval-to-execution records and denied-call evidence with sensitive detail protected. | Approval, ERP/email and harness owners unknown |
| INV-02 | Tenant A permitted read works; helper attempts payment, forged tenant B and direct/alternate tool routes fail; delegated credential revocation is measured. | Tenant B unchanged and unread; no helper payment; destination authorization records and measured cutoff, not just model refusal. | Identity and destination owners unknown |
| INV-03 | Approved minimized provider request/email works; forbidden recipient/host/redirect/helper fetch cannot receive sensitive data. | Authorized destination receives only permitted fields; disallowed endpoint receives no sensitive payload; provider processing/retention evidence records opaque areas. | Network, email and provider-contract owners unknown |
| INV-04 | Authorized same-tenant memory retrieval works; cross-tenant retrieval and schema-valid stored instructions fail to influence tool authority. Removal exercise covers summaries and queued copies. | No foreign-tenant read or unauthorized action; specified copies removed or inaccessible with lineage/deletion evidence. | Memory and queue owners; memory owner unknown |
| INV-05 | Normal payment succeeds; timeout after committed payment followed by repeated/concurrent retries is reconciled. | Exactly one ERP payment, stable idempotency identity, consistent reconciled status; no fresh payment caused solely by timeout. | ERP owner unknown; operations supplies queue evidence |
| INV-06 | Bounded job and descendant complete; repeated delegation/budget exhaustion and parent stop/revocation deny later queued/running action attempts. | Total exposure within defined bounds; no new effects after specified cutoff; in-flight committed effects identified. Labeled benign/harmful sequences show alert delivery and false-block/miss limits. | Operations plus budget/identity/behavior owners unknown |
| INV-07 | Approved runtime/config starts and produces protected audit records; altered artifact/config and unavailable audit destination exercise defined denial/failure policy. | Unapproved version gains no action authority; permitted/denied actions attributable to authenticated identities and exact release/context. | Platform/change and audit owners unknown |

## Open decisions, assumptions and revisit triggers

Critical questions for accountable designers: Which tenants and actions are permitted? What amount/recipient/bank-change policies govern approval? Can ERP enforce actor/tenant scopes, one-time approval and idempotency? Which data reaches the provider? What authority/context reaches helpers and descendants? Who owns approval, identity, ERP/email, memory, budgets and evidence? What stop cutoff and audit-failure behavior are required?

Independent modeling above does not assume answers. If the helper truly cannot access credentials or execute actions, revise its capability row only after enforceable separation is specified. If provider context is demonstrably public/minimized, narrow INV-03 accordingly. New tools, new tenants, changed provider/model/runtime/configuration, broader credential scopes, persistent data or descendant behavior invalidate the corresponding assumptions and require revisiting this model. The selected BRACE mappings do not assess all 53 items; no gates or Pass/N/A outcomes are assigned.
