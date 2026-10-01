# BRACE and MITRE ATLAS

This page maps every tactic, technique, and sub-technique in [MITRE ATLAS](https://atlas.mitre.org/) to the items in the [BRACE sign-off checklist](../CHECKLIST.md). It uses ATLAS data release [v2026.09](https://github.com/mitre-atlas/atlas-data/releases/tag/v2026.09) (collection version 2026.09, published 15 September 2026; 16 tactics, 120 techniques, 88 sub-techniques), retrieved on 2026-10-01 from the [atlas-data repository](https://github.com/mitre-atlas/atlas-data). Each row says whether passing BRACE items would block the technique in a deployed agent, only reduce or detect it, or not touch it.

## How to read this mapping
- **Direct** — passing the listed BRACE items prevents the technique or contains its damage in an agent deployment.
- **Partial** — the listed items reduce the impact or help detect it, but don't prevent it.
- **Out of scope** — BRACE doesn't address it; the row says why in a few words (for example, model training, physical access, or work done on the attacker's own systems).
Passing a BRACE item is not proof that a technique is stopped; test it with the [verification recipes](../CHECKLIST-VERIFICATION.md).

Item IDs refer to the [checklist](../CHECKLIST.md), most relevant first. An item counts only when its result is Pass. A technique listed under more than one tactic has the same mapping in each section. Sub-techniques are shown as "Technique: Sub-technique", the way the ATLAS site names them.

## Summary

| Tactic | Techniques | Direct | Partial | Out of scope |
|---|---|---|---|---|
| [Reconnaissance](#reconnaissance-amlta0002) | 18 | 0 | 8 | 10 |
| [Resource Development](#resource-development-amlta0003) | 29 | 0 | 8 | 21 |
| [AI Attack Adaptation](#ai-attack-adaptation-amlta0001) | 25 | 0 | 14 | 11 |
| [Initial Access](#initial-access-amlta0004) | 18 | 2 | 14 | 2 |
| [AI Model Access](#ai-model-access-amlta0000) | 4 | 0 | 3 | 1 |
| [Execution](#execution-amlta0005) | 13 | 6 | 7 | 0 |
| [Persistence](#persistence-amlta0006) | 20 | 6 | 14 | 0 |
| [Privilege Escalation](#privilege-escalation-amlta0012) | 4 | 1 | 3 | 0 |
| [Defense Evasion](#defense-evasion-amlta0007) | 19 | 2 | 15 | 2 |
| [Credential Access](#credential-access-amlta0013) | 7 | 2 | 5 | 0 |
| [Discovery](#discovery-amlta0008) | 17 | 0 | 14 | 3 |
| [Lateral Movement](#lateral-movement-amlta0015) | 9 | 1 | 7 | 1 |
| [Collection](#collection-amlta0009) | 8 | 2 | 6 | 0 |
| [Command and Control](#command-and-control-amlta0014) | 5 | 0 | 5 | 0 |
| [Exfiltration](#exfiltration-amlta0010) | 9 | 2 | 5 | 2 |
| [Impact](#impact-amlta0011) | 20 | 5 | 13 | 2 |
| **Total (tactic rows)** | **225** | **29** | **141** | **55** |
| **Unique techniques and sub-techniques** | **208** | **26** | **128** | **54** |

The tactic rows add up to 225, not 208, because 14 techniques sit under more than one tactic. The last row counts each technique once.

## Reconnaissance (AML.TA0002)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0000](https://atlas.mitre.org/techniques/AML.T0000) | Search Open Technical Databases | Out of scope | — | Public research read by the attacker before any contact with the deployment. |
| [AML.T0000.000](https://atlas.mitre.org/techniques/AML.T0000.000) | Search Open Technical Databases: Journals and Conference Proceedings | Out of scope | — | Reading published papers happens outside the deployment. |
| [AML.T0000.001](https://atlas.mitre.org/techniques/AML.T0000.001) | Search Open Technical Databases: Pre-Print Repositories | Out of scope | — | Reading pre-prints happens outside the deployment. |
| [AML.T0000.002](https://atlas.mitre.org/techniques/AML.T0000.002) | Search Open Technical Databases: Technical Blogs | Out of scope | — | Reading public blogs happens outside the deployment. |
| [AML.T0000.003](https://atlas.mitre.org/techniques/AML.T0000.003) | Search Open Technical Databases: Scan Databases | Partial | B08, E06 | B08 keeps agent services off networks they don't need; E06 means a listed endpoint still demands authentication. |
| [AML.T0001](https://atlas.mitre.org/techniques/AML.T0001) | Search Open AI Vulnerability Analysis | Out of scope | — | Studying published model weaknesses happens outside the deployment. |
| [AML.T0003](https://atlas.mitre.org/techniques/AML.T0003) | Search Victim-Owned Websites | Out of scope | — | Reading the victim's public website happens outside the deployment. |
| [AML.T0004](https://atlas.mitre.org/techniques/AML.T0004) | Search Application Repositories | Out of scope | — | Searching public app stores happens outside the deployment. |
| [AML.T0006](https://atlas.mitre.org/techniques/AML.T0006) | Active Scanning | Partial | B08, E06, R08 | Isolation and an authenticating gateway shrink what a scan can reach; R08 alerts on probing. |
| [AML.T0006.000](https://atlas.mitre.org/techniques/AML.T0006.000) | Active Scanning: Enumerate Hosted AI Resources | Partial | E06, E01 | The gateway rejects unauthenticated calls to found agents; E01 names who owns the hosting platform's side. |
| [AML.T0006.001](https://atlas.mitre.org/techniques/AML.T0006.001) | Active Scanning: Query Platform Metadata APIs | Partial | E01, B02 | E01 assigns the platform owner for metadata APIs; scoped tokens limit what a leaked identity can list. |
| [AML.T0006.002](https://atlas.mitre.org/techniques/AML.T0006.002) | Active Scanning: Scan for Exposed AI Infrastructure | Partial | B08, E06 | B08 tests that agent backends have no unapproved exposure; E06 requires authentication on every call. |
| [AML.T0006.003](https://atlas.mitre.org/techniques/AML.T0006.003) | Active Scanning: Probe AI Agent Trigger Channels | Partial | R01, E07, R08 | R01 and E07 authenticate webhook and message senders, so probes from strangers are rejected; R08 alerts on repeats. |
| [AML.T0064](https://atlas.mitre.org/techniques/AML.T0064) | Gather RAG-Indexed Targets | Partial | R04 | Finding the sources is not blocked, but R04 limits who can add or change indexed content. |
| [AML.T0087](https://atlas.mitre.org/techniques/AML.T0087) | Gather Victim Identity Information | Out of scope | — | Collecting staff and identity details happens outside the deployment. |
| [AML.T0095](https://atlas.mitre.org/techniques/AML.T0095) | Search Open Websites/Domains | Out of scope | — | Searching public websites happens outside the deployment. |
| [AML.T0095.000](https://atlas.mitre.org/techniques/AML.T0095.000) | Search Open Websites/Domains: Code Repositories | Partial | B03, B12 | B03 keeps secrets out of checked-in config, so public code holds no working keys; B12 controls what gets committed. |
| [AML.T0116](https://atlas.mitre.org/techniques/AML.T0116) | Autonomous Reconnaissance | Out of scope | — | The attacker's own agent does the research, outside the deployment. |

## Resource Development (AML.TA0003)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0002](https://atlas.mitre.org/techniques/AML.T0002) | Acquire Public AI Artifacts | Out of scope | — | Downloading public artifacts happens outside the deployment. |
| [AML.T0002.000](https://atlas.mitre.org/techniques/AML.T0002.000) | Acquire Public AI Artifacts: Datasets | Out of scope | — | Downloading public datasets happens outside the deployment. |
| [AML.T0002.001](https://atlas.mitre.org/techniques/AML.T0002.001) | Acquire Public AI Artifacts: Models | Out of scope | — | Downloading public models happens outside the deployment. |
| [AML.T0002.002](https://atlas.mitre.org/techniques/AML.T0002.002) | Acquire Public AI Artifacts: AI Agent Configuration | Partial | B03, B02 | A leaked config holds no long-lived secrets under B03, and any token it names is narrowly scoped under B02. |
| [AML.T0008](https://atlas.mitre.org/techniques/AML.T0008) | Acquire Infrastructure | Out of scope | — | Buying servers or cloud accounts happens outside the deployment. |
| [AML.T0008.000](https://atlas.mitre.org/techniques/AML.T0008.000) | Acquire Infrastructure: AI Development Workspaces | Out of scope | — | Renting compute for attack work happens outside the deployment. |
| [AML.T0008.001](https://atlas.mitre.org/techniques/AML.T0008.001) | Acquire Infrastructure: Consumer Hardware | Out of scope | — | Buying hardware happens outside the deployment. |
| [AML.T0008.002](https://atlas.mitre.org/techniques/AML.T0008.002) | Acquire Infrastructure: Domains | Partial | B09 | Registering a domain isn't blocked, but the egress allowlist stops the agent from reaching it. |
| [AML.T0008.003](https://atlas.mitre.org/techniques/AML.T0008.003) | Acquire Infrastructure: Physical Countermeasures | Out of scope | — | Physical items such as printed patterns are outside BRACE. |
| [AML.T0008.004](https://atlas.mitre.org/techniques/AML.T0008.004) | Acquire Infrastructure: Serverless | Partial | B09 | B09 limits allowed services by resource and tenant, since attacker code can sit on a trusted platform's domain. |
| [AML.T0008.005](https://atlas.mitre.org/techniques/AML.T0008.005) | Acquire Infrastructure: AI Service Proxies | Out of scope | — | Reselling access to AI services happens outside the deployment. |
| [AML.T0016](https://atlas.mitre.org/techniques/AML.T0016) | Obtain Capabilities | Out of scope | — | Gathering attack tools happens outside the deployment. |
| [AML.T0016.000](https://atlas.mitre.org/techniques/AML.T0016.000) | Obtain Capabilities: Adversarial AI Attack Implementations | Out of scope | — | Gathering attack code happens outside the deployment. |
| [AML.T0016.001](https://atlas.mitre.org/techniques/AML.T0016.001) | Obtain Capabilities: Software Tools | Out of scope | — | Gathering general software tools happens outside the deployment. |
| [AML.T0016.002](https://atlas.mitre.org/techniques/AML.T0016.002) | Obtain Capabilities: Generative AI | Out of scope | — | The attacker's own use of AI models is outside the deployment. |
| [AML.T0016.003](https://atlas.mitre.org/techniques/AML.T0016.003) | Obtain Capabilities: Exploits | Out of scope | — | Gathering exploits happens outside the deployment; patching is general IT work. |
| [AML.T0016.004](https://atlas.mitre.org/techniques/AML.T0016.004) | Obtain Capabilities: AI Agent Tools | Out of scope | — | Tools for the attacker's own agent are outside the deployment. |
| [AML.T0017](https://atlas.mitre.org/techniques/AML.T0017) | Develop Capabilities | Out of scope | — | Building attack tools happens outside the deployment. |
| [AML.T0017.000](https://atlas.mitre.org/techniques/AML.T0017.000) | Develop Capabilities: Adversarial AI Attacks | Out of scope | — | Building model attacks happens outside the deployment. |
| [AML.T0017.001](https://atlas.mitre.org/techniques/AML.T0017.001) | Develop Capabilities: Autonomous Exploit Development | Out of scope | — | The attacker's agent writing exploits is outside the deployment. |
| [AML.T0017.002](https://atlas.mitre.org/techniques/AML.T0017.002) | Develop Capabilities: AI Agent Tools | Out of scope | — | Building tools for the attacker's agent is outside the deployment. |
| [AML.T0021](https://atlas.mitre.org/techniques/AML.T0021) | Establish Accounts | Out of scope | — | Creating attacker accounts on outside services is outside the deployment. |
| [AML.T0060](https://atlas.mitre.org/techniques/AML.T0060) | Publish Hallucinated Entities | Partial | B11, B09, E02 | No package manager under B11 and an egress allowlist under B09 stop the agent fetching a made-up name; people can still fall for it. |
| [AML.T0079](https://atlas.mitre.org/techniques/AML.T0079) | Stage Capabilities | Out of scope | — | Setting up attacker infrastructure happens outside the deployment. |
| [AML.T0115](https://atlas.mitre.org/techniques/AML.T0115) | Publish Poisoned AI Artifacts | Partial | E02, C05 | Publishing isn't blocked, but vetting, pinning, and signature checks keep unapproved artifacts out. |
| [AML.T0115.000](https://atlas.mitre.org/techniques/AML.T0115.000) | Publish Poisoned AI Artifacts: Datasets | Partial | C05, E02 | C05 links each dataset change to the model and its tests; BRACE doesn't inspect training data. |
| [AML.T0115.001](https://atlas.mitre.org/techniques/AML.T0115.001) | Publish Poisoned AI Artifacts: Models | Partial | C05, E02 | Signature and file-format checks before loading reject unapproved models; a signed bad model can still pass. |
| [AML.T0115.002](https://atlas.mitre.org/techniques/AML.T0115.002) | Publish Poisoned AI Artifacts: AI Agent Tools | Partial | E02, E04, E03 | Tools are vetted, scanned, and pinned before use; a review can still miss a well-hidden payload. |
| [AML.T0128](https://atlas.mitre.org/techniques/AML.T0128) | Compromise Infrastructure | Out of scope | — | Taking over third-party infrastructure happens outside the deployment. |

## AI Attack Adaptation (AML.TA0001)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0005](https://atlas.mitre.org/techniques/AML.T0005) | Create Proxy AI Model | Out of scope | — | The attacker builds a copy model on their own systems. |
| [AML.T0005.000](https://atlas.mitre.org/techniques/AML.T0005.000) | Create Proxy AI Model: Train Proxy via Gathered AI Artifacts | Out of scope | — | Training a copy from public artifacts happens outside the deployment. |
| [AML.T0005.001](https://atlas.mitre.org/techniques/AML.T0005.001) | Create Proxy AI Model: Train Proxy via Replication | Partial | B07, R08 | Per-user and per-tenant quotas slow mass querying; R08 can flag the volume. |
| [AML.T0005.002](https://atlas.mitre.org/techniques/AML.T0005.002) | Create Proxy AI Model: Use Pre-Trained Model | Out of scope | — | Using an off-the-shelf model happens outside the deployment. |
| [AML.T0018](https://atlas.mitre.org/techniques/AML.T0018) | Manipulate AI Model | Partial | C05, C03, C04 | Signature checks before load and drift checks on self-hosted weights catch changed files, not a model poisoned before signing. |
| [AML.T0018.000](https://atlas.mitre.org/techniques/AML.T0018.000) | Manipulate AI Model: Poison AI Model | Partial | C05, C06 | C05 ties weight and training changes to tests before promotion; tests can't prove a model is clean. |
| [AML.T0018.001](https://atlas.mitre.org/techniques/AML.T0018.001) | Manipulate AI Model: Modify AI Model Architecture | Partial | C05, C03, C04 | Changed self-hosted model files fail the signature and identity checks; hosted models are outside your view. |
| [AML.T0018.002](https://atlas.mitre.org/techniques/AML.T0018.002) | Manipulate AI Model: Embed Malware | Partial | C05, E02, B11 | C05 requires a signer check and a scan for pickle formats; B11 limits what loaded code can reach. |
| [AML.T0018.003](https://atlas.mitre.org/techniques/AML.T0018.003) | Manipulate AI Model: Modify Prompt Construction Logic | Partial | C05, C03, A03 | Chat templates bundled with self-hosted models are covered by signature and identity checks; hidden provider changes are not. |
| [AML.T0042](https://atlas.mitre.org/techniques/AML.T0042) | Verify Attack | Out of scope | — | Testing attacks on the attacker's own copy happens outside the deployment. |
| [AML.T0043](https://atlas.mitre.org/techniques/AML.T0043) | Craft Adversarial Data | Out of scope | — | Crafting inputs to fool a model's predictions is a model-robustness issue. |
| [AML.T0043.000](https://atlas.mitre.org/techniques/AML.T0043.000) | Craft Adversarial Data: White-Box Optimization | Out of scope | — | Needs full model access and targets model robustness. |
| [AML.T0043.001](https://atlas.mitre.org/techniques/AML.T0043.001) | Craft Adversarial Data: Black-Box Optimization | Out of scope | — | Targets model robustness through repeated queries. |
| [AML.T0043.002](https://atlas.mitre.org/techniques/AML.T0043.002) | Craft Adversarial Data: Black-Box Transfer | Out of scope | — | Built on the attacker's copy model; targets model robustness. |
| [AML.T0043.003](https://atlas.mitre.org/techniques/AML.T0043.003) | Craft Adversarial Data: Manual Modification | Out of scope | — | Hand-edited inputs that fool a model target model robustness. |
| [AML.T0043.004](https://atlas.mitre.org/techniques/AML.T0043.004) | Craft Adversarial Data: Insert Backdoor Trigger | Out of scope | — | Depends on a backdoored model, which is a training-time issue (see AML.T0018.000). |
| [AML.T0065](https://atlas.mitre.org/techniques/AML.T0065) | LLM Prompt Crafting | Partial | R02, B05 | BRACE assumes crafted prompts will get through and relies on R02 containment and B05 gates to stop the harm. |
| [AML.T0066](https://atlas.mitre.org/techniques/AML.T0066) | Retrieval Content Crafting | Partial | R04, R02 | R04 limits who can add content and tracks each chunk's trust level; R02 treats retrieved text as data. |
| [AML.T0088](https://atlas.mitre.org/techniques/AML.T0088) | Generate Deepfakes | Out of scope | — | Making fake media happens outside the deployment. |
| [AML.T0102](https://atlas.mitre.org/techniques/AML.T0102) | Generate Malicious Commands | Partial | B11, R03, R08 | No shell under B11, parameterized commands under R03, and R08 alerts limit commands an agent generates. |
| [AML.T0117](https://atlas.mitre.org/techniques/AML.T0117) | Autonomous Attack-Path Adaptation | Partial | R09, B07 | If your own agent is the one adapting, R09 flags chains of allowed steps and B07 caps its loops. |
| [AML.T0118](https://atlas.mitre.org/techniques/AML.T0118) | Autonomous AI Agent Communication | Partial | E07, R05, A06 | Peer messages are authenticated and checked, memory is isolated, and parent prompts are recorded. |
| [AML.T0118.000](https://atlas.mitre.org/techniques/AML.T0118.000) | Autonomous AI Agent Communication: Communication via Shared Artifacts | Partial | R05, B08 | Memory isolation and write checks limit shared notes between runs; other shared stores are only limited by B08. |
| [AML.T0118.001](https://atlas.mitre.org/techniques/AML.T0118.001) | Autonomous AI Agent Communication: Direct Agent Communication | Partial | E07, E08, A06 | Each peer message is authenticated and checked against what that peer may ask; delegation can't add power. |
| [AML.T0124](https://atlas.mitre.org/techniques/AML.T0124) | Autonomous Attack Orchestration | Partial | B07, E08, E09 | Budgets cap how many sub-agents start, delegation can't add power, and the recursive stop reaches them all. |

## Initial Access (AML.TA0004)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0010](https://atlas.mitre.org/techniques/AML.T0010) | AI Supply Chain Compromise | Partial | E02, B10, C05 | Dependencies, images, and models are vetted, pinned, and signature-checked; a compromised approved release can still get in. |
| [AML.T0010.000](https://atlas.mitre.org/techniques/AML.T0010.000) | AI Supply Chain Compromise: Hardware | Out of scope | — | Hardware supply chain attacks are outside BRACE. |
| [AML.T0010.001](https://atlas.mitre.org/techniques/AML.T0010.001) | AI Supply Chain Compromise: AI Software | Partial | E02, B10, C05 | Pinned, vetted dependencies block silent swaps; a bad version you approved still runs. |
| [AML.T0010.002](https://atlas.mitre.org/techniques/AML.T0010.002) | AI Supply Chain Compromise: Data | Partial | C05, R04 | C05 records dataset versions for training you run; R04 limits who can write to retrieval sources. |
| [AML.T0010.003](https://atlas.mitre.org/techniques/AML.T0010.003) | AI Supply Chain Compromise: Model | Partial | C05, E02 | Signer and format checks before loading reject unapproved models; a signed bad model can still pass. |
| [AML.T0010.004](https://atlas.mitre.org/techniques/AML.T0010.004) | AI Supply Chain Compromise: Container Registry | Direct | B10, C03, C04 | The image is pinned by digest and its signature is checked, so an overwritten tag is rejected. |
| [AML.T0010.005](https://atlas.mitre.org/techniques/AML.T0010.005) | AI Supply Chain Compromise: AI Agent Tool | Partial | E02, E03, E04, B01 | Tools are vetted, fingerprinted, and scanned, and only allowlisted tools load; hidden remote code changes can slip by. |
| [AML.T0012](https://atlas.mitre.org/techniques/AML.T0012) | Valid Accounts | Partial | B03, B02, B04, R08 | Short-lived, holder-bound tokens limit reuse, scopes limit reach, and revocation cuts off the account. |
| [AML.T0015](https://atlas.mitre.org/techniques/AML.T0015) | Evade AI Model | Partial | R02, A07 | R02 requires harm to stay blocked even when a detector model is fooled; A07 treats a failing checker as a failed control. |
| [AML.T0049](https://atlas.mitre.org/techniques/AML.T0049) | Exploit Public-Facing Application | Partial | B11, B08, E02 | A minimal runtime and network isolation limit what an exploited app can reach; finding app bugs is general security work. |
| [AML.T0052](https://atlas.mitre.org/techniques/AML.T0052) | Phishing | Partial | B05, R08 | B05 gates outbound messages, so a hijacked agent can't send phishing unapproved; phishing of people by other means is outside BRACE. |
| [AML.T0052.000](https://atlas.mitre.org/techniques/AML.T0052.000) | Phishing: Spearphishing via Social Engineering LLM | Partial | R02, B05 | Containment limits what a manipulated agent can do, but BRACE doesn't stop a chat model from talking a user into something. |
| [AML.T0052.001](https://atlas.mitre.org/techniques/AML.T0052.001) | Phishing: Deepfake-Assisted Phishing | Out of scope | — | Fake voice or video aimed at people is outside BRACE. |
| [AML.T0078](https://atlas.mitre.org/techniques/AML.T0078) | Drive-by Compromise | Partial | R01, R02, B09, B05 | Fetched pages are untrusted data, the egress allowlist limits sites, and action gates block the harm an injected page asks for. |
| [AML.T0093](https://atlas.mitre.org/techniques/AML.T0093) | Prompt Infiltration via Public-Facing Application | Partial | R01, R02, R04, R05 | Content from public apps is checked and kept apart from instructions; retrieval and memory limit how long it stays. |
| [AML.T0119](https://atlas.mitre.org/techniques/AML.T0119) | Exploit Automated Artifact Processing Pipeline | Partial | B11, R01, B08 | A minimal, isolated runtime and input checks limit what a booby-trapped artifact can do in a pipeline. |
| [AML.T0131](https://atlas.mitre.org/techniques/AML.T0131) | Crafted AI Assistant Links | Partial | R02, B05, B06 | A pre-filled prompt is still contained by R02, and approvals show the exact action before it runs. |
| [AML.T0132](https://atlas.mitre.org/techniques/AML.T0132) | Misconfigured or Publicly Exposed AI Services | Direct | E06, B08, C04 | Every call must pass an authenticating gateway, isolation is tested, and drift checks catch a loosened rule. |

## AI Model Access (AML.TA0000)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0040](https://atlas.mitre.org/techniques/AML.T0040) | AI Model Inference API Access | Partial | E06, B07 | The gateway authenticates and rate-limits callers; legitimate query access is still possible. |
| [AML.T0041](https://atlas.mitre.org/techniques/AML.T0041) | Physical Environment Access | Out of scope | — | Physical access to data collection is outside BRACE. |
| [AML.T0044](https://atlas.mitre.org/techniques/AML.T0044) | Full AI Model Access | Partial | B02, B08 | Scoped access and isolation protect self-hosted weights; a provider's weights are outside your control. |
| [AML.T0047](https://atlas.mitre.org/techniques/AML.T0047) | AI-Enabled Product or Service | Partial | R03 | R03 limits sensitive data in responses and logs that could reveal model details. |

## Execution (AML.TA0005)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0011](https://atlas.mitre.org/techniques/AML.T0011) | User Execution | Partial | C05, E02, B11 | Vetting and signature checks screen artifacts, and a minimal runtime limits what they can do if run. |
| [AML.T0011.000](https://atlas.mitre.org/techniques/AML.T0011.000) | User Execution: Unsafe AI Artifacts | Partial | C05, B11, E02 | C05 checks signer and file format and requires a scan for pickle files; B11 limits the damage of what slips through. |
| [AML.T0011.001](https://atlas.mitre.org/techniques/AML.T0011.001) | User Execution: Malicious Package | Partial | E02, B10, B11 | Packages are vetted and pinned into a signed image; a bad package you approved still runs. |
| [AML.T0011.002](https://atlas.mitre.org/techniques/AML.T0011.002) | User Execution: Poisoned AI Agent Tool | Partial | E02, E04, E03, B05 | Tools are vetted and scanned, changes are blocked, and B05 gates the harmful actions a bad tool asks for. |
| [AML.T0011.003](https://atlas.mitre.org/techniques/AML.T0011.003) | User Execution: Malicious Link | Partial | B09, B11 | The egress allowlist blocks the link's destination for the agent; links clicked by people are outside BRACE. |
| [AML.T0050](https://atlas.mitre.org/techniques/AML.T0050) | Command and Scripting Interpreter | Direct | B11, B01, R03 | Shells are removed or sandboxed, only listed tools run, and generated commands use argument lists, not raw strings. |
| [AML.T0051](https://atlas.mitre.org/techniques/AML.T0051) | LLM Prompt Injection | Direct | R02, B05, B02, R01 | BRACE assumes some injections work; R02 requires proof that B05 gates and B02 scopes still block the resulting action. |
| [AML.T0051.000](https://atlas.mitre.org/techniques/AML.T0051.000) | LLM Prompt Injection: Direct | Partial | B02, E08, R02 | The agent can only use the user's own scoped authority; harmful text the model writes is a model-safety issue. |
| [AML.T0051.001](https://atlas.mitre.org/techniques/AML.T0051.001) | LLM Prompt Injection: Indirect | Direct | R01, R02, B05, B02 | Outside content is untrusted data, and R02 tests that action gates and scopes hold when the model obeys it. |
| [AML.T0051.002](https://atlas.mitre.org/techniques/AML.T0051.002) | LLM Prompt Injection: Triggered | Direct | R02, B05, R01 | An injection set off by an event is contained the same way: gated actions and scoped tools, tested under R02. |
| [AML.T0053](https://atlas.mitre.org/techniques/AML.T0053) | AI Agent Tool Invocation | Direct | B01, B02, B05, E08 | Only listed tools exist, tokens are scoped, high-impact calls need approval, and delegation can't add power. |
| [AML.T0100](https://atlas.mitre.org/techniques/AML.T0100) | AI Agent Clickbait | Direct | B05, B09, R02 | Consequential clicks need approval, and the egress allowlist blocks navigation to unlisted sites. |
| [AML.T0103](https://atlas.mitre.org/techniques/AML.T0103) | Deploy AI Agent | Partial | A01, E08, R08 | Every agent needs its own identity and bounded authority, so an unknown agent stands out; R08 alerts on it. |

## Persistence (AML.TA0006)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0018](https://atlas.mitre.org/techniques/AML.T0018) | Manipulate AI Model | Partial | C05, C03, C04 | Signature checks before load and drift checks on self-hosted weights catch changed files, not a model poisoned before signing. |
| [AML.T0018.000](https://atlas.mitre.org/techniques/AML.T0018.000) | Manipulate AI Model: Poison AI Model | Partial | C05, C06 | C05 ties weight and training changes to tests before promotion; tests can't prove a model is clean. |
| [AML.T0018.001](https://atlas.mitre.org/techniques/AML.T0018.001) | Manipulate AI Model: Modify AI Model Architecture | Partial | C05, C03, C04 | Changed self-hosted model files fail the signature and identity checks; hosted models are outside your view. |
| [AML.T0018.002](https://atlas.mitre.org/techniques/AML.T0018.002) | Manipulate AI Model: Embed Malware | Partial | C05, E02, B11 | C05 requires a signer check and a scan for pickle formats; B11 limits what loaded code can reach. |
| [AML.T0018.003](https://atlas.mitre.org/techniques/AML.T0018.003) | Manipulate AI Model: Modify Prompt Construction Logic | Partial | C05, C03, A03 | Chat templates bundled with self-hosted models are covered by signature and identity checks; hidden provider changes are not. |
| [AML.T0020](https://atlas.mitre.org/techniques/AML.T0020) | Training Data Poisoning | Partial | C05, E02 | C05 links each training dataset change to the model and its test results; BRACE doesn't inspect training data. |
| [AML.T0061](https://atlas.mitre.org/techniques/AML.T0061) | LLM Prompt Self-Replication | Partial | B05, R05, E07 | Outbound sends are gated, memory writes are checked, and peer messages are untrusted, which slows a spreading prompt. |
| [AML.T0070](https://atlas.mitre.org/techniques/AML.T0070) | RAG Poisoning | Partial | R04, R02 | R04 limits who can add content and supports quarantine; poison from an approved source still gets indexed. |
| [AML.T0080](https://atlas.mitre.org/techniques/AML.T0080) | AI Agent Context Poisoning | Partial | R05, R02, R06 | Memory is isolated and checked on write, and bad entries can be traced and removed; thread context is only contained. |
| [AML.T0080.000](https://atlas.mitre.org/techniques/AML.T0080.000) | AI Agent Context Poisoning: Memory | Direct | R05, R06 | R05 tests that a poisoned run can't plant instructions in another run's memory; R06 finds and removes bad entries. |
| [AML.T0080.001](https://atlas.mitre.org/techniques/AML.T0080.001) | AI Agent Context Poisoning: Thread | Partial | R02, B05 | Instructions planted in one thread are contained by action gates, not removed. |
| [AML.T0081](https://atlas.mitre.org/techniques/AML.T0081) | Modify AI Agent Configuration | Direct | B12, C03, C04 | Config changes go only through review, and drift checks catch and roll back an edited prompt or tool list. |
| [AML.T0093](https://atlas.mitre.org/techniques/AML.T0093) | Prompt Infiltration via Public-Facing Application | Partial | R01, R02, R04, R05 | Content from public apps is checked and kept apart from instructions; retrieval and memory limit how long it stays. |
| [AML.T0099](https://atlas.mitre.org/techniques/AML.T0099) | AI Agent Tool Data Poisoning | Partial | R01, R02, B05 | Tool output is untrusted data, and action gates block what poisoned data asks for; the bad data stays at the source. |
| [AML.T0110](https://atlas.mitre.org/techniques/AML.T0110) | AI Agent Tool Poisoning | Partial | E02, E03, E04, B01 | Tools are vetted, pinned, fingerprinted, and scanned; hidden changes to remote code can slip by. |
| [AML.T0110.000](https://atlas.mitre.org/techniques/AML.T0110.000) | AI Agent Tool Poisoning: Definition and Instructions | Direct | E03, E04, E02, B05 | Descriptions are scanned before use and locked by fingerprint, and B05 gates any harmful action they push. |
| [AML.T0110.001](https://atlas.mitre.org/techniques/AML.T0110.001) | AI Agent Tool Poisoning: Implementation | Partial | E02, E03, B11 | Vetting and pinning cover code you can see; remote tool code can change behind the same definition. |
| [AML.T0110.002](https://atlas.mitre.org/techniques/AML.T0110.002) | AI Agent Tool Poisoning: Runtime Response | Direct | R01, R02, E06, B05 | Tool responses are validated as untrusted data at the gateway, and action gates block what they ask for. |
| [AML.T0121](https://atlas.mitre.org/techniques/AML.T0121) | AI Agent Environment Reconstruction | Direct | E09, R12, B04, B11 | The stop revokes access and blocks orphaned restarts, and the runtime has no downloader to rebuild tools. |
| [AML.T0125](https://atlas.mitre.org/techniques/AML.T0125) | Create Account | Direct | B02, B05 | Agent tokens can't do admin actions such as creating accounts, and B02 tests that they fail. |

## Privilege Escalation (AML.TA0012)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0012](https://atlas.mitre.org/techniques/AML.T0012) | Valid Accounts | Partial | B03, B02, B04, R08 | Short-lived, holder-bound tokens limit reuse, scopes limit reach, and revocation cuts off the account. |
| [AML.T0053](https://atlas.mitre.org/techniques/AML.T0053) | AI Agent Tool Invocation | Direct | B01, B02, B05, E08 | Only listed tools exist, tokens are scoped, high-impact calls need approval, and delegation can't add power. |
| [AML.T0054](https://atlas.mitre.org/techniques/AML.T0054) | LLM Jailbreak | Partial | R02, B05, B02 | Actions don't depend on model guardrails, so gates and scopes still hold; harmful text is a model-safety issue. |
| [AML.T0105](https://atlas.mitre.org/techniques/AML.T0105) | Escape to Host | Partial | B11, B08, B02 | B11 requires a hardened container or microVM; a blocked probe doesn't prove every escape fails. |

## Defense Evasion (AML.TA0007)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0015](https://atlas.mitre.org/techniques/AML.T0015) | Evade AI Model | Partial | R02, A07 | R02 requires harm to stay blocked even when a detector model is fooled; A07 treats a failing checker as a failed control. |
| [AML.T0054](https://atlas.mitre.org/techniques/AML.T0054) | LLM Jailbreak | Partial | R02, B05, B02 | Actions don't depend on model guardrails, so gates and scopes still hold; harmful text is a model-safety issue. |
| [AML.T0067](https://atlas.mitre.org/techniques/AML.T0067) | LLM Trusted Output Components Manipulation | Out of scope | — | Making answers look trustworthy to users is answer quality, which BRACE keeps separate from security. |
| [AML.T0067.000](https://atlas.mitre.org/techniques/AML.T0067.000) | LLM Trusted Output Components Manipulation: Citations | Out of scope | — | Fake or misused citations are answer quality, which BRACE doesn't check. |
| [AML.T0068](https://atlas.mitre.org/techniques/AML.T0068) | LLM Prompt Obfuscation | Partial | R01, R08, R02 | Input checks and monitoring look for encoded payloads; meaning-level hiding can slip by, so R02 containment still applies. |
| [AML.T0071](https://atlas.mitre.org/techniques/AML.T0071) | False RAG Entry Injection | Partial | R04, R01 | R04 limits who can write to the index and labels each chunk's source and trust level. |
| [AML.T0073](https://atlas.mitre.org/techniques/AML.T0073) | Impersonation | Partial | E07, R01, A04 | Peer and service senders must prove who they are, and labels the model supplies are never trusted; impersonating people to people is outside BRACE. |
| [AML.T0074](https://atlas.mitre.org/techniques/AML.T0074) | Masquerading | Partial | E05, B10, E03 | Lookalike tool names are flagged, images are checked by digest, and changed tools are blocked. |
| [AML.T0076](https://atlas.mitre.org/techniques/AML.T0076) | Corrupt AI Model | Partial | C05, B11 | C05 checks file format and requires approved, scanned exceptions for pickle; B11 limits what runs on load. |
| [AML.T0081](https://atlas.mitre.org/techniques/AML.T0081) | Modify AI Agent Configuration | Direct | B12, C03, C04 | Config changes go only through review, and drift checks catch and roll back an edited prompt or tool list. |
| [AML.T0092](https://atlas.mitre.org/techniques/AML.T0092) | Manipulate User LLM Chat History | Direct | R13, E10, E11 | The execution audit is kept apart from chat history, and the agent can't erase or rewrite it. |
| [AML.T0094](https://atlas.mitre.org/techniques/AML.T0094) | Delay Execution of LLM Instructions | Partial | R05, R09, B05 | Memory write checks, sequence detection, and action gates limit a delayed instruction when it fires. |
| [AML.T0097](https://atlas.mitre.org/techniques/AML.T0097) | Virtualization/Sandbox Evasion | Partial | R10, C06 | R10 and C06 test an agent that knows it is watched; BRACE can't prove such checks catch every evasion. |
| [AML.T0107](https://atlas.mitre.org/techniques/AML.T0107) | Exploitation for Defense Evasion | Partial | E02, B11, E06 | Known flaws are tracked, the runtime is minimal, and required checks fail closed. |
| [AML.T0109](https://atlas.mitre.org/techniques/AML.T0109) | AI Supply Chain Rug Pull | Partial | E02, E03, C05 | Pinned versions block silent updates and changed tool definitions are blocked; remote code can change behind the same name. |
| [AML.T0111](https://atlas.mitre.org/techniques/AML.T0111) | AI Supply Chain Reputation Inflation | Partial | E02 | E02 reviews source, publisher, and permissions, since stars and namespaces don't prove code is safe. |
| [AML.T0123](https://atlas.mitre.org/techniques/AML.T0123) | Obfuscated Files or Information | Partial | R01, E04, R08 | Inputs and tool metadata are checked for encoded content, and R08 tests encoded payloads. |
| [AML.T0129](https://atlas.mitre.org/techniques/AML.T0129) | Triggers in Multimodal Inputs | Partial | R01, R02 | R01 checks every input type for hidden instructions; R02 containment covers what the checks miss. |
| [AML.T0134](https://atlas.mitre.org/techniques/AML.T0134) | AI Targeted Cloaking | Partial | R01, R02, B05 | Content shown only to the agent is still untrusted data, and action gates block what it asks for. |

## Credential Access (AML.TA0013)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0055](https://atlas.mitre.org/techniques/AML.T0055) | Unsecured Credentials | Direct | B03, B02, R03 | Secrets stay out of prompts, images, and config, issued tokens are short-lived and scoped, and outputs are redacted. |
| [AML.T0082](https://atlas.mitre.org/techniques/AML.T0082) | RAG Credential Harvesting | Partial | R03, R04, B03 | R03 strips secrets from retrieved text before the model sees it; detection of secrets in documents is not complete. |
| [AML.T0083](https://atlas.mitre.org/techniques/AML.T0083) | Credentials from AI Agent Configuration | Direct | B03, E06, B02 | The agent's config holds no long-lived secrets, and the gateway holds backend credentials instead of the agent. |
| [AML.T0090](https://atlas.mitre.org/techniques/AML.T0090) | OS Credential Dumping | Partial | B03, B11 | Holder-bound, short-lived tokens limit stolen ones; a non-root runtime makes dumping harder. |
| [AML.T0098](https://atlas.mitre.org/techniques/AML.T0098) | AI Agent Tool Credential Harvesting | Partial | R03, B02 | R03 strips secrets from tool output, and scoped tokens limit which sources the agent can read. |
| [AML.T0106](https://atlas.mitre.org/techniques/AML.T0106) | Exploitation for Credential Access | Partial | B03, E02, B11 | Short-lived, bound tokens limit what an exploit steals; patching is general security work. |
| [AML.T0113](https://atlas.mitre.org/techniques/AML.T0113) | Steal Web Session Cookie | Partial | B03, R03 | Binding tokens to their holder makes stolen sessions fail elsewhere where services support it. |

## Discovery (AML.TA0008)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0007](https://atlas.mitre.org/techniques/AML.T0007) | Discover AI Artifacts | Partial | B02, B08 | Scoped access and isolation limit which model stores and datasets the agent can see. |
| [AML.T0013](https://atlas.mitre.org/techniques/AML.T0013) | Discover AI Model Ontology | Out of scope | — | Querying a model to learn its output classes is a model-level issue. |
| [AML.T0014](https://atlas.mitre.org/techniques/AML.T0014) | Discover AI Model Family | Out of scope | — | Working out which model family is used is a model-level issue. |
| [AML.T0062](https://atlas.mitre.org/techniques/AML.T0062) | Discover LLM Hallucinations | Out of scope | — | The attacker can find made-up names by querying any public model. |
| [AML.T0063](https://atlas.mitre.org/techniques/AML.T0063) | Discover AI Model Outputs | Partial | R03 | R03 limits extra data, such as scores, in responses and logs. |
| [AML.T0069](https://atlas.mitre.org/techniques/AML.T0069) | Discover LLM System Information | Partial | B03, R03 | BRACE doesn't keep prompts secret, but B03 keeps credentials out of them, so a leak exposes no keys. |
| [AML.T0069.000](https://atlas.mitre.org/techniques/AML.T0069.000) | Discover LLM System Information: Special Character Sets | Partial | R02, R01 | Labeling each input's source keeps trust out of delimiters an attacker can copy. |
| [AML.T0069.001](https://atlas.mitre.org/techniques/AML.T0069.001) | Discover LLM System Information: System Instruction Keywords | Partial | B01, B05 | Knowing function names doesn't grant tools outside the allowlist or skip action gates. |
| [AML.T0069.002](https://atlas.mitre.org/techniques/AML.T0069.002) | Discover LLM System Information: System Prompt | Partial | B03, R03 | A revealed system prompt exposes no credentials when B03 is met. |
| [AML.T0075](https://atlas.mitre.org/techniques/AML.T0075) | Enterprise Resource Discovery | Partial | B02, B08 | Scoped tokens and isolation limit which accounts and systems the agent can list. |
| [AML.T0084](https://atlas.mitre.org/techniques/AML.T0084) | Discover AI Agent Configuration | Partial | B11, B03, B01 | File access is limited, configs hold no secrets, and a minimal tool list reveals little. |
| [AML.T0084.000](https://atlas.mitre.org/techniques/AML.T0084.000) | Discover AI Agent Configuration: Embedded Knowledge | Partial | R04, B02 | Search enforces the requester's access, so the agent reveals only sources that user may see. |
| [AML.T0084.001](https://atlas.mitre.org/techniques/AML.T0084.001) | Discover AI Agent Configuration: Tool Definitions | Partial | B01, B02 | A minimal, scoped tool list limits what discovery reveals. |
| [AML.T0084.002](https://atlas.mitre.org/techniques/AML.T0084.002) | Discover AI Agent Configuration: Activation Triggers | Partial | R01, B05 | Trigger messages must come from authenticated senders, and actions they cause are gated. |
| [AML.T0084.003](https://atlas.mitre.org/techniques/AML.T0084.003) | Discover AI Agent Configuration: Call Chains | Partial | R03, B11 | Parameterized commands and a minimal runtime remove most code-execution paths a call chain could reveal. |
| [AML.T0089](https://atlas.mitre.org/techniques/AML.T0089) | Enterprise Environment Discovery | Partial | B08, B11 | Isolation and a minimal runtime limit what the agent can see of the wider network and host. |
| [AML.T0133](https://atlas.mitre.org/techniques/AML.T0133) | Discover AI Agent Runtime Capabilities | Partial | B01, R08 | A minimal tool list limits what probing reveals; R08 alerts on repeated denied calls. |

## Lateral Movement (AML.TA0015)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0012](https://atlas.mitre.org/techniques/AML.T0012) | Valid Accounts | Partial | B03, B02, B04, R08 | Short-lived, holder-bound tokens limit reuse, scopes limit reach, and revocation cuts off the account. |
| [AML.T0052](https://atlas.mitre.org/techniques/AML.T0052) | Phishing | Partial | B05, R08 | B05 gates outbound messages, so a hijacked agent can't send phishing unapproved; phishing of people by other means is outside BRACE. |
| [AML.T0052.000](https://atlas.mitre.org/techniques/AML.T0052.000) | Phishing: Spearphishing via Social Engineering LLM | Partial | R02, B05 | Containment limits what a manipulated agent can do, but BRACE doesn't stop a chat model from talking a user into something. |
| [AML.T0052.001](https://atlas.mitre.org/techniques/AML.T0052.001) | Phishing: Deepfake-Assisted Phishing | Out of scope | — | Fake voice or video aimed at people is outside BRACE. |
| [AML.T0053](https://atlas.mitre.org/techniques/AML.T0053) | AI Agent Tool Invocation | Direct | B01, B02, B05, E08 | Only listed tools exist, tokens are scoped, high-impact calls need approval, and delegation can't add power. |
| [AML.T0091](https://atlas.mitre.org/techniques/AML.T0091) | Use Alternate Authentication Material | Partial | B03, B02, B04 | Tokens are audience-limited and holder-bound where supported, so a stolen one fails elsewhere. |
| [AML.T0091.000](https://atlas.mitre.org/techniques/AML.T0091.000) | Use Alternate Authentication Material: Application Access Token | Partial | B02, B03, B04 | Other services reject a token issued for a different audience; holder binding depends on service support. |
| [AML.T0091.001](https://atlas.mitre.org/techniques/AML.T0091.001) | Use Alternate Authentication Material: Web Session Cookie | Partial | B03 | Holder-bound sessions fail on another machine where the service supports binding. |
| [AML.T0122](https://atlas.mitre.org/techniques/AML.T0122) | Exploitation of Remote Services | Partial | B08, B09, E06 | Isolation and egress rules limit which services the agent can reach to exploit. |

## Collection (AML.TA0009)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0035](https://atlas.mitre.org/techniques/AML.T0035) | AI Artifact Collection | Partial | B02, B08, R03 | Scoped access and isolation limit which models and datasets an agent can collect. |
| [AML.T0036](https://atlas.mitre.org/techniques/AML.T0036) | Data from Information Repositories | Partial | B02, R04 | Tokens and search are limited to the requester's tenant and scopes. |
| [AML.T0037](https://atlas.mitre.org/techniques/AML.T0037) | Data from Local System | Partial | B11, B03 | A minimal runtime holds little data, and no long-lived secrets sit on disk. |
| [AML.T0085](https://atlas.mitre.org/techniques/AML.T0085) | Data from AI Services | Partial | B02, R04, R08 | Access checks limit results to what the requester may see; R08 flags unusual volume. |
| [AML.T0085.000](https://atlas.mitre.org/techniques/AML.T0085.000) | Data from AI Services: RAG Databases | Direct | R04, B02 | Search enforces the requesting tenant's access on each chunk, so prompting can't pull other users' documents. |
| [AML.T0085.001](https://atlas.mitre.org/techniques/AML.T0085.001) | Data from AI Services: AI Agent Tools | Direct | B02, E08, B01 | Tools act with the original user's scoped authority, so prompting can't reach data that user can't. |
| [AML.T0126](https://atlas.mitre.org/techniques/AML.T0126) | Automated Collection | Partial | B07, R09, B02 | Rate limits and sequence detection catch bulk reads; scopes limit what is in reach. |
| [AML.T0127](https://atlas.mitre.org/techniques/AML.T0127) | Data Staged | Partial | R09, B08 | R09 flags many reads before a send; isolation limits where data can be staged. |

## Command and Control (AML.TA0014)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0072](https://atlas.mitre.org/techniques/AML.T0072) | Cyber Communication Channel | Partial | B09, R08 | The egress allowlist blocks unknown destinations; allowed services can still carry hidden traffic. |
| [AML.T0096](https://atlas.mitre.org/techniques/AML.T0096) | AI Service API | Partial | B09, E06, R08 | Egress rules and gateway logs limit and record AI API traffic; commands hidden in normal requests are hard to spot. |
| [AML.T0108](https://atlas.mitre.org/techniques/AML.T0108) | AI Agent | Partial | B09, B11, B01, R09 | No shell, limited egress, and a minimal tool list shrink an agent's use as a relay; sequence checks look for misuse. |
| [AML.T0114](https://atlas.mitre.org/techniques/AML.T0114) | AI Service Web Interface | Partial | B09, R08 | Egress rules limit which AI web services are reachable; R08 watches unexpected outbound traffic. |
| [AML.T0120](https://atlas.mitre.org/techniques/AML.T0120) | AI Artifact Repository | Partial | B09, E02 | Egress rules limit reachable repositories by resource and tenant; pinned artifacts don't pull new objects. |

## Exfiltration (AML.TA0010)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0024](https://atlas.mitre.org/techniques/AML.T0024) | Exfiltration via AI Inference API | Partial | B07, R03 | Rate quotas slow mass querying, and R03 limits sensitive data in responses. |
| [AML.T0024.000](https://atlas.mitre.org/techniques/AML.T0024.000) | Exfiltration via AI Inference API: Infer Training Data Membership | Out of scope | — | Learning what was in the training set is a model-training privacy issue. |
| [AML.T0024.001](https://atlas.mitre.org/techniques/AML.T0024.001) | Exfiltration via AI Inference API: Invert AI Model | Out of scope | — | Rebuilding training data from model outputs is a model-training privacy issue. |
| [AML.T0024.002](https://atlas.mitre.org/techniques/AML.T0024.002) | Exfiltration via AI Inference API: Extract AI Model | Partial | B07, E06 | Per-user and fleet quotas and gateway rate limits slow the bulk queries needed to copy a model. |
| [AML.T0025](https://atlas.mitre.org/techniques/AML.T0025) | Exfiltration via Cyber Means | Partial | B09, R08 | The egress allowlist limits destinations and R08 alerts on unexpected outbound traffic. |
| [AML.T0056](https://atlas.mitre.org/techniques/AML.T0056) | Extract LLM System Prompt | Partial | B03, R03 | BRACE doesn't keep prompts secret, but a leaked prompt holds no credentials when B03 is met. |
| [AML.T0057](https://atlas.mitre.org/techniques/AML.T0057) | LLM Data Leakage | Partial | R03, R04, B02 | Secrets are stripped and access is scoped before data reaches the model; what the user may see can still be leaked to them. |
| [AML.T0077](https://atlas.mitre.org/techniques/AML.T0077) | LLM Response Rendering | Direct | R03, B09 | R03 blocks client auto-fetch of images and links or allows only approved URLs. |
| [AML.T0086](https://atlas.mitre.org/techniques/AML.T0086) | Exfiltration via AI Agent Tool Invocation | Direct | B05, B09, R02 | Sending anything outside needs approval, and the egress allowlist limits destinations and the data sent. |

## Impact (AML.TA0011)

| ATLAS ID | Technique | Coverage | BRACE items | How BRACE addresses it |
|---|---|---|---|---|
| [AML.T0015](https://atlas.mitre.org/techniques/AML.T0015) | Evade AI Model | Partial | R02, A07 | R02 requires harm to stay blocked even when a detector model is fooled; A07 treats a failing checker as a failed control. |
| [AML.T0029](https://atlas.mitre.org/techniques/AML.T0029) | Denial of AI Service | Partial | B07, E06 | Per-user, tenant, and fleet quotas limit floods through the agent; network-level floods need other defenses. |
| [AML.T0031](https://atlas.mitre.org/techniques/AML.T0031) | Erode AI Model Integrity | Out of scope | — | Wearing down a model's accuracy with crafted inputs is a model-robustness issue. |
| [AML.T0034](https://atlas.mitre.org/techniques/AML.T0034) | Cost Harvesting | Direct | B07, R09 | Hard limits on tokens, cost, tool calls, and sub-agents stop spending at a set ceiling. |
| [AML.T0034.000](https://atlas.mitre.org/techniques/AML.T0034.000) | Cost Harvesting: Excessive Queries | Direct | B07, E06 | Per-user, tenant, and fleet quotas cap request volume and cost. |
| [AML.T0034.001](https://atlas.mitre.org/techniques/AML.T0034.001) | Cost Harvesting: Resource-Intensive Queries | Direct | B07 | Token, time, and cost limits stop each costly request at its budget. |
| [AML.T0034.002](https://atlas.mitre.org/techniques/AML.T0034.002) | Cost Harvesting: Agentic Resource Consumption | Direct | B07, R09 | Loop, tool-call, and cost limits stop the run, and R09 flags unusual resource use. |
| [AML.T0046](https://atlas.mitre.org/techniques/AML.T0046) | Spamming AI System with Chaff Data | Out of scope | — | Flooding an ML detector with junk to waste analysts' time doesn't involve agent actions. |
| [AML.T0048](https://atlas.mitre.org/techniques/AML.T0048) | External Harms | Partial | B05, R12 | Action gates block many harmful actions and R12 sets up repair; harm from model text is not covered. |
| [AML.T0048.000](https://atlas.mitre.org/techniques/AML.T0048.000) | External Harms: Financial Harm | Partial | B05, B06 | Payment changes need a specific, single-use approval; fraud that doesn't use the agent is outside BRACE. |
| [AML.T0048.001](https://atlas.mitre.org/techniques/AML.T0048.001) | External Harms: Reputational Harm | Partial | B05, R03 | Outbound posts and messages need approval; harmful replies shown to users are not blocked. |
| [AML.T0048.002](https://atlas.mitre.org/techniques/AML.T0048.002) | External Harms: Societal Harm | Partial | B05 | Publishing outside is gated, but harmful text in replies is a model-safety issue. |
| [AML.T0048.003](https://atlas.mitre.org/techniques/AML.T0048.003) | External Harms: User Harm | Partial | B05, B02 | Gates and scopes limit what the agent can do to users' accounts; harmful replies are not blocked. |
| [AML.T0048.004](https://atlas.mitre.org/techniques/AML.T0048.004) | External Harms: AI Intellectual Property Theft | Partial | B02, B09, B08 | Scoped access and egress rules limit copying of models and data out of the deployment. |
| [AML.T0059](https://atlas.mitre.org/techniques/AML.T0059) | Erode Dataset Integrity | Partial | R04, R06 | Write limits and source records let you find and remove bad entries in retrieval and memory stores. |
| [AML.T0101](https://atlas.mitre.org/techniques/AML.T0101) | Data Destruction via AI Agent Tool Invocation | Direct | B05, B02, R12 | Deletes are blocked by default unless approved, and R12 sets how stopped writes are repaired. |
| [AML.T0112](https://atlas.mitre.org/techniques/AML.T0112) | Machine Compromise | Partial | B11, B08 | A minimal, isolated runtime limits what a compromised component can reach. |
| [AML.T0112.000](https://atlas.mitre.org/techniques/AML.T0112.000) | Machine Compromise: Local AI Agent | Partial | B11, B01, B05 | BRACE expects a sandbox and gated actions; agents running on a user's own machine often lack both. |
| [AML.T0112.001](https://atlas.mitre.org/techniques/AML.T0112.001) | Machine Compromise: AI Artifacts | Partial | C05, B11 | Signer and format checks screen artifacts, and an isolated runtime limits embedded code. |
| [AML.T0130](https://atlas.mitre.org/techniques/AML.T0130) | AI Agent Response Biasing | Partial | R05, R04, R02 | Memory write checks block a saved "trust this source" note; biased replies within one session are not blocked. |

## Limits

- BRACE covers deployed agents: their tools, identity, network, memory, retrieval, and stop and audit paths. It does not cover model training or the model supply chain beyond C05 and E02, so training-time attacks are Partial at best.
- Many Direct rows are Direct because BRACE contains the damage, not because it stops the attack. Prompt injection still reaches the model; R02 requires proof that scopes and action gates block what it asks for.
- Reconnaissance and resource development done on the attacker's own systems are Out of scope. BRACE only limits what that work can later reach.
- Harmful or misleading text that the model writes for a user is a model-safety and answer-quality problem. BRACE does not filter it, so related Impact rows are Partial.
- This mapping is BRACE's judgment. MITRE has not reviewed or endorsed it.
- ATLAS changes often; v2026.09 added 11 techniques and sub-techniques. Recheck this mapping on each new ATLAS release. Last checked 2026-10-01.

---
*Part of [BRACE](../README.md), a security framework for autonomous AI agents. CC BY 4.0.*
