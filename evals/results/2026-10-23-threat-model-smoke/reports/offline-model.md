# Offline summarizer threat model

Design basis: [offline-design.md](../offline-design.md), “Proposed offline summarizer,” unversioned; modeled 2026-10-23. Requirements are design claims, not implemented controls. This development smoke model is not qualification or deployment approval.

## Scope, assets and boundaries

A local user selects public text files, an offline model summarizes them, and the harness prints the result to the console. The design forbids tools, filesystem writes, network, persistent memory and sub-agents, and restricts input reads to the selected files. There is no payment or private-data retrieval. Installation is controlled by a separate operator. Model/runtime packaging and shared-workstation resource limits remain undecided.

Assets are summary integrity, selected input integrity, local process/host isolation, model/runtime artifacts, workstation availability and visible console output. The local user supplies selections; public file authors may be malicious; the installation operator controls executable artifacts. Runtime/isolation, resource and output owners are unspecified. No tenant system is described; the shared workstation is a host boundary, not evidence of multi-tenancy.

| Crossing | Data / authority / destination | Enforcement and coverage |
|---|---|---|
| Public file author → user selection → input reader | Selected text plus malicious instructions; read authority must remain restricted to selected files | Reader/harness owner unknown; OFF-01, 02 |
| Reader → offline model → console | Text and generated summary; no tool or network authority required | Harness/output owner unknown; OFF-01, 03 |
| Operator → model/runtime installation → host process | Executable/model packaging can inherit workstation identity permissions | Separate operator controls installation; isolation owner unknown; OFF-02 |
| Process → shared CPU/RAM/console | Input size, token generation and runtime computation consume shared resources | Resource owner unknown; OFF-03 |

There is no stated feedback path from console output into memory, files or later instructions. Human copy/paste into another interpreter would create a new boundary and is conditional, not a present capability. No audit service is described; use ordinary build/test evidence for these requirements rather than inventing one.

## Capability combinations

| Context | Untrusted input | Sensitive systems/data | State change / external communication | Basis |
|---|---|---|---|---|
| Summarizer within stated harness requirements | Yes | No | No consequential tool/state/external capability | Malicious public text is allowed. Only selected public reads and console summaries are specified; no writes/network/tools. Console output consumes resources and is addressed separately. |
| Installed runtime at OS boundary | Yes | Unknown | Unknown | No packaging/sandbox design exists; the host process might inherit OS permissions beyond the intended harness. Requirement-level absence does not establish enforced process isolation. |
| Installation operator | Unknown | Unknown | Yes for installation | Separate operator controls installation; exposure to selected content and host permissions unspecified. It is not a model helper or sub-agent. |

The summarizer has no stated three-capability combination. Payment approvals, cross-tenant ERP access, credential delegation and descendant shutdown controls are not justified by this design. Host/runtime authority needs verification without assuming such authority exists.

## Proportionate threat register and mitigation map

| ID / priority | Concrete path and prerequisite | Proposed response / enforcement / owner | BRACE mapping; assumptions and residual exposure |
|---|---|---|---|
| OFF-02 / highest within this scope: unsafe runtime/package reaches shared host | Compromised or unsafe model/runtime packaging → installation operator loads executable component → process reads unrelated workstation files or changes host state. Requires executable/loading permissions beyond the selected-file boundary; these are unknown, not established. | Define provenance/admission checks and OS-enforced read-only selected-file access with no network or writes; review permitted runtime/model loaders. Operator owns installation; isolation owner unknown. | C3 B10, B11, E02; configuration C01, C03–C05; C1 B09. Assumes platform supports the specified restrictions. Residual: admitted artifacts and underlying runtime/kernel can contain defects. |
| OFF-03 / medium: resource exhaustion or unsafe console rendering | Large/pathological selected public file or malicious instructions → excessive input/generation/runtime use → shared workstation becomes unavailable. If model text is emitted verbatim to a terminal interpreting control sequences, generated output may also manipulate displayed console state; terminal rendering is unspecified. | Bound selected input size, generation length, time, RAM and CPU; define cancellation; render untrusted output safely for the actual console. Harness/resource/output owners unknown. | C4 B12; C5 R01–R03, E03–E07. Assumes finite limits suitable for intended public files. Residual: bounded jobs still compete for shared resources; display branch depends on actual console behavior. |
| OFF-01 / lower consequence: malicious source corrupts summary | File author embeds instructions → model follows them instead of summarizing → user receives misleading or instruction-laden output. Requires no extra privilege. Harm is output integrity; downstream execution or exfiltration is not supported by the stated design. | Keep task instructions distinct from file data, identify summaries as generated output, test benign and adversarial summaries against task criteria; preserve tool-free, write-free offline boundary. Harness owner unknown. | C5 R01–R03, E03–E07. Assumes user uses output as a summary, without automatic execution. Residual: instruction separation is no guarantee of factual or complete summaries. |

Every material asset and boundary is covered above: input/summary/console integrity by OFF-01 and OFF-03; runtime artifacts/host isolation by OFF-02; shared availability by OFF-03. Public input confidentiality is not a material design asset, but unrelated workstation data remains conditionally exposed if isolation requirements fail. No persistent-memory poisoning path is stated; no C6 scenario is invented. A separate behavioral monitoring system or incident-response process is not proposed for this limited tool-free design.

## Verification needs (proposed, not executed)

| Scenario | Allowed-task control | Denial/failure case and expected destination state | Evidence owner |
|---|---|---|---|
| OFF-02 | Approved package loads and summarizes a selected public file offline. | Altered/unapproved package is rejected by admission policy. A purpose-built boundary probe cannot read an unselected sentinel file, write a temporary destination or contact a local test endpoint; those destinations remain unread/unchanged/uncontacted. Verify actual OS permissions separately from absence of harness tool APIs. | Installation operator and isolation owner, latter unknown |
| OFF-03 | Representative bounded files summarize within agreed limits; safe ordinary console text remains legible. | Oversized/pathological input and excessive generation terminate at configured bounds; no extra output/write/network effects occur and shared resource consumption stays within agreed limits. If terminal control rendering applies, injected control sequences render inertly. | Resource/harness/output owners unknown |
| OFF-01 | Representative public text yields a useful task-conforming summary. | Source text directing the model to ignore the task or invent facts does not acquire execution authority; assess summary fidelity and report failure rates/limits rather than asserting immunity. Expected output is only a summary on the console; no hidden file/network effect. | Harness owner unknown; task-quality reviewer unspecified |

## Questions, assumptions and revisit conditions

Which OS/runtime/package format will enforce selected-file reads and no network/writes? Who owns isolation and resource limits? What file sizes, latency and quality limits are acceptable? Does console output interpret control sequences? These questions do not block modeling the stated public-input integrity path.

The selected files are public, the model is truly offline, and no output is automatically executed or reused as instructions: all are stated design assumptions to validate later. Adding private inputs, tools, writes, network, memory, sub-agents, shared credentials or automatic output consumption requires a new capability/boundary assessment. Runtime/package changes and deployment to a differently shared workstation also require revisiting OFF-02/03. The selected BRACE items are design prompts, not a full 53-item checklist assessment or Pass/N/A report.
