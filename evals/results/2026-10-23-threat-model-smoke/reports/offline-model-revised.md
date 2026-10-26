# Offline summarizer threat model — revised smoke exercise

Basis: [offline-design.md](../offline-design.md), unversioned “Proposed offline summarizer”; modeled 2026-10-23. All restrictions are claimed requirements, with no observed implementation. Responses are proposed. This development exercise provides no qualification, confirmed vulnerability or deployment verdict.

## Scope, assets and boundaries

A local user selects public text files for an offline model to summarize to that user's console. Claimed requirements prohibit tools, writes, network, persistent memory and sub-agents and restrict reads to selected files. The separate operator controls model/runtime installation; packaging and shared-workstation resource limits are undecided. Permitted use is summarization. No payments or private-data retrieval exist in this design. Worst credible harms within scope are misleading output and shared-host exhaustion; broader host compromise is conditional on unsafe packaging or unbounded OS permissions.

| Material asset | Actor / owner | Boundary and scenario |
|---|---|---|
| Public input and summary integrity | File author may be malicious; local user selects inputs; harness/output owner unknown | Author → selected file → model → console; OFF-01, OFF-03 |
| Runtime/model artifacts, harness instructions, host isolation | Separate operator owns installation; isolation/change responsibility otherwise unspecified | Operator/admission → runtime → shared host; OFF-02 |
| Shared CPU/RAM and availability | Other workstation users; resource owner unknown | Process → shared machine resources; OFF-03 |
| Unrelated workstation files and state | Existence/sensitivity unspecified; host owner unknown | Conditional OS boundary if installation/runtime permits access; OFF-02 |

| Flow crossing | Origin, data and authority | Operation / destination / enforcement owner |
|---|---|---|
| Public author → reader | User-selected public file, possibly malicious instructions | Read selected file only; harness/reader owner unknown |
| Reader → offline model → console | Source text, generated summary | Display to requesting user; harness/output owner unknown |
| Operator → runtime installation | Model/runtime package and instructions | Admit/load executable artifacts; operator known, isolation/change owner unknown |
| Runtime → host resources | Parsing/generation computation | Consume CPU/RAM/time and render output; resource owner unknown |

There is no stated feedback into files, memory or future instructions. Manual copy/paste into another interpreter would add a new boundary. There is no tenant service, approval service, external model provider, credential delegation, MCP transport or tool publication to invent. Ordinary build/test evidence can verify the stated restrictions without adding a production audit system.

## Capability combinations

| Context | Untrusted input | Sensitive access | State change or external communication, with actual destination | Basis |
|---|---|---|---|---|
| Intended summarizer harness | Yes | No under stated requirements | No consequential tool/state/arbitrary-recipient authority; yes only display to requesting user's console | Selected public input; all other capabilities prohibited. Console display does not establish arbitrary messaging or a three-capability action combination. |
| Runtime at OS boundary | Yes | Unknown | Unknown beyond console/resource consumption | Packaging and isolation are undesigned; underlying process privileges need specification and verification. |
| Installation operator | Unknown | Unknown | Yes: installation changes | Separate operator is stated; selected-content exposure and host permissions unknown. Not a sub-agent. |

## Prioritized scenarios and specific mappings

Priority is based on credible scope of harm and reversibility, not assumed likelihood. All mitigations are proposed and not evidence that boundaries work.

| ID / priority | Trigger → entry → steps → boundary → harm and prerequisites | Proposed mitigation / owner | Applicable BRACE items, assumptions and residual exposure |
|---|---|---|---|
| OFF-02 / highest within scope, conditional | Compromised or unsafe model/runtime package → operator loads executable component → runtime accesses unselected workstation files or writes host state → intended selected-file/read-only boundary fails → host/data impact. Requires effective package/process authority not established by the design. | Admit reviewed artifacts; define loader/provenance policy and OS-enforced selected-read/no-write/no-network isolation. Separate operator handles installation; isolation/change owner unknown. | C3 **B11** isolated runtime and **E02** dependency vetting; C1 **B09** host boundary. **B12** reviewed harness/instructions and **C02** change review apply if that mitigation is adopted. **B10** is not selected: no container image is stated. Unspecified configuration items are not copied wholesale. Assumes platform supports required restrictions. Residual: reviewed packages/runtime may contain defects. |
| OFF-03 / medium | Large/pathological selected file or malicious generation instructions → unbounded input/computation/output → shared CPU/RAM exhausted → workstation unavailable. Separately, if console interprets generated control sequences, hostile output can manipulate the visible display. Requires missing/ineffective resource bounds; rendering branch depends on actual console. | Hard input, time, CPU/RAM and generation/output bounds, with cancellation; render untrusted output safely for actual console. Resource/harness/output owners unknown. | C4 **B07** hard execution budgets; C5 **R01** input boundary for bounded input, **R03** output validation for console rendering. **B12 is not a budget control.** Assumes bounds support representative intended files. Residual: bounded jobs still compete for shared resources. |
| OFF-01 / lower consequence | Malicious file author → selected text instructs model to ignore summarization or fabricate facts → model obeys → user receives misleading summary. No extra privilege required and no exfiltration/payment path is stated. | Separate trusted task instructions from source data; assess summary fidelity on benign and hostile inputs; keep runtime authority restricted. Harness/task-quality owner unknown. | C5 **R01** input boundary and **R02** injection containment. Output fidelity/accuracy is not fully specified by security item IDs and needs task-quality acceptance criteria; no unrelated metadata or MCP items are added. Assumes summary is not automatically executed downstream. Residual: separation cannot guarantee faithful summaries. |

All material assets and crossings are covered: summary/input integrity by OFF-01, console and availability by OFF-03, artifacts and conditional unrelated host data by OFF-02. Public input confidentiality is not a stated concern. No persistent-memory poisoning, cross-tenant ERP access, peer messaging or consequential action approval path is supported. **E03–E05** tool publication and **E06–E07** MCP/peer boundary items are therefore not mapped. No full BRACE checklist or Pass/N/A outcomes are assigned.

## Verification needs, not executed

| Scenario | Allowed-task control | Concrete denial/failure and expected destination state | Evidence owner |
|---|---|---|---|
| OFF-02 | Reviewed package loads and summarizes a selected public file offline. | Unapproved/altered artifact is denied admission; a purpose-built probe cannot read an unselected sentinel file, write a designated test destination or contact a local test endpoint. Those destinations remain unread/unchanged/uncontacted. Inspect effective OS enforcement separately from absence of tool APIs. Reviewed harness/instruction changes are accepted only through specified review process, if used. | Installation operator plus isolation/change owner, latter unknown |
| OFF-03 | Representative files summarize within agreed bounds and ordinary output stays legible. | Oversized/pathological input and excessive generation stop at configured time/resource/output limits; shared consumption remains bounded. If console interprets control sequences, adversarial sequences display inertly. No new file/network effect is introduced. | Resource/harness/output owners unknown |
| OFF-01 | Representative public text produces useful, faithful summaries. | Source instructions to ignore task or fabricate claims cannot expand runtime authority; evaluate and disclose remaining summary-fidelity failures. Destination is only requesting user's console, with no tool/file/network action. | Harness/task-quality owner unknown |

## Questions, assumptions and revisit triggers

Batch questions: Which OS/package/loader will enforce selected-file reads, no writes and offline operation? Who owns isolation and resource bounds? What input size, latency and fidelity limits are acceptable? Does the console interpret control sequences? These remain unresolved without preventing this conditional model.

The model assumes public inputs, no automatic execution/reuse of console output, no private retrieval and no added tools/permissions. Validate those requirements later. Adding network, writes, private inputs, memory, tools, sub-agents, shared credentials or output interpretation requires new boundary/capability analysis. Package/runtime changes and different host sharing also trigger review. This model is usable without sibling skills and authorizes no tests or operational changes.
