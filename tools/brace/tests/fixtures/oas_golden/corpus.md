### open-agent-security

| Severity | Problem | Where | Fix |
|---|---|---|---|
| critical | [Unattended agent in CI with permission checks turned off](https://braceframework.org/anti-patterns/#ap02-unattended-agent-in-ci-with-permission-checks-turned-off) | sub/\.github/workflows/triage\.yml:8 | Keep approvals on, give the job read-only permissions, and run untrusted-input jobs without repository secrets. |
| critical | [Unattended agent in CI with permission checks turned off](https://braceframework.org/anti-patterns/#ap02-unattended-agent-in-ci-with-permission-checks-turned-off) | sub/\.github/workflows/triage\.yml:9 | Keep approvals on, give the job read-only permissions, and run untrusted-input jobs without repository secrets. |
| critical | [Unattended agent in CI with permission checks turned off](https://braceframework.org/anti-patterns/#ap02-unattended-agent-in-ci-with-permission-checks-turned-off) | sub/\.gitlab-ci\.yml:2 | Keep approvals on, give the job read-only permissions, and run untrusted-input jobs without repository secrets. |
| critical | [Agent workflow triggered by pull\_request\_target](https://braceframework.org/anti-patterns/#ap03-agent-workflow-triggered-by-pull_request_target) | sub/\.github/workflows/triage\.yml:2 | Use pull\_request for agent jobs, or split the job so the agent never sees secrets or a write token while it reads outside content. |
| high | [Agent runs with all permission checks turned off](https://braceframework.org/anti-patterns/#ap01-agent-runs-with-all-permission-checks-turned-off) | sub/\.claude/settings\.json:7 | Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs. |
| high | [Agent runs with all permission checks turned off](https://braceframework.org/anti-patterns/#ap01-agent-runs-with-all-permission-checks-turned-off) | sub/deploy\.sh:1 | Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs. |
| high | [Agent runs with all permission checks turned off](https://braceframework.org/anti-patterns/#ap01-agent-runs-with-all-permission-checks-turned-off) | sub/scripts/fix\.sh:3 | Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs. |
| high | [Agent runs with all permission checks turned off](https://braceframework.org/anti-patterns/#ap01-agent-runs-with-all-permission-checks-turned-off) | sub/tools/agent\.py:1 | Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs. |
| high | [MCP server installed from an unpinned package](https://braceframework.org/anti-patterns/#ap04-mcp-server-installed-from-an-unpinned-package) | sub/\.cursor/mcp\.json:5 | Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile. |
| high | [MCP server installed from an unpinned package](https://braceframework.org/anti-patterns/#ap04-mcp-server-installed-from-an-unpinned-package) | sub/\.mcp\.json:3 | Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile. |
| high | [MCP server installed from an unpinned package](https://braceframework.org/anti-patterns/#ap04-mcp-server-installed-from-an-unpinned-package) | sub/\.mcp\.json:13 | Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile. |
| high | [MCP server installed from an unpinned package](https://braceframework.org/anti-patterns/#ap04-mcp-server-installed-from-an-unpinned-package) | sub/\.mcp\.json:25 | Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile. |
| high | [Secret written directly in agent configuration](https://braceframework.org/anti-patterns/#ap05-secret-written-directly-in-agent-configuration) | sub/\.claude/settings\.json:10 | Load the secret from the environment or a secret manager, use a short-lived scoped token, and rotate the exposed one. |
| high | [Secret written directly in agent configuration](https://braceframework.org/anti-patterns/#ap05-secret-written-directly-in-agent-configuration) | sub/\.mcp\.json:10 | Load the secret from the environment or a secret manager, use a short-lived scoped token, and rotate the exposed one. |
| high | [Secret written directly in agent configuration](https://braceframework.org/anti-patterns/#ap05-secret-written-directly-in-agent-configuration) | sub/\.mcp\.json:22 | Load the secret from the environment or a secret manager, use a short-lived scoped token, and rotate the exposed one. |
| high | [Agent allowed to run any shell command](https://braceframework.org/anti-patterns/#ap06-agent-allowed-to-run-any-shell-command) | sub/\.claude/settings\.json:3 | Allow only the specific commands the task needs, such as Bash\(npm test\), and keep deny rules for network and destructive commands. |
| high | [Agent tool container can take over the host](https://braceframework.org/anti-patterns/#ap08-agent-tool-container-can-take-over-the-host) | sub/\.mcp\.json:25 | Drop these flags. Mount only the folders the tool needs, read-only where possible. |
| medium | [Remote MCP server reached over plain HTTP](https://braceframework.org/anti-patterns/#ap07-remote-mcp-server-reached-over-plain-http) | sub/\.mcp\.json:19 | Use https, and authenticate the server. |
| medium | [Lethal combination: untrusted input, private data and a way out](https://braceframework.org/anti-patterns/#ap09-lethal-combination-untrusted-input-private-data-and-a-way-out) | sub/\.mcp\.json:3 | Split the capabilities across agents, remove one leg, or require a person to approve every outbound or consequential action. |
| low | [Agent image not pinned to a digest](https://braceframework.org/anti-patterns/#ap10-agent-image-not-pinned-to-a-digest) | sub/Dockerfile:1 | Pin the base image by digest \(image@sha256:...\) and update it on purpose. |
| low | [Agent image not pinned to a digest](https://braceframework.org/anti-patterns/#ap10-agent-image-not-pinned-to-a-digest) | sub/Dockerfile:5 | Pin the base image by digest \(image@sha256:...\) and update it on purpose. |

<details>
<summary>AP02: Unattended agent in CI with permission checks turned off</summary>

**Why:** A CI agent with no approvals and the job's token can be steered by anyone who can write an issue, PR, commit message or file it reads, and then push code, read secrets or publish packages.

**Fix:** Keep approvals on, give the job read-only permissions, and run untrusted-input jobs without repository secrets.

**Before:**

```text
- run: claude -p "triage this issue" --dangerously-skip-permissions
```

**After:**

```text
permissions:
  contents: read
# ...
- run: claude -p "triage this issue" --allowedTools "Read" "Grep"
```

**Hardened template:** `templates/policy/README.md`

</details>

<details>
<summary>AP03: Agent workflow triggered by pull\_request\_target</summary>

**Why:** pull\_request\_target runs with the base repository's secrets and write token on events from forks. An agent that reads the fork's PR text or code can be told to leak or misuse them.

**Fix:** Use pull\_request for agent jobs, or split the job so the agent never sees secrets or a write token while it reads outside content.

**Before:**

```text
on: pull_request_target
```

**After:**

```text
on: pull_request
```

</details>

<details>
<summary>AP01: Agent runs with all permission checks turned off</summary>

**Why:** Every tool call, including shell commands and file deletes, runs without approval. One prompt injection in a file, issue or web page the agent reads can run any command as you.

**Fix:** Remove the bypass. Allow specific tools instead, and run unattended agents in a throwaway sandbox with no secrets and no network beyond what the task needs.

**Before:**

```text
claude --dangerously-skip-permissions -p "fix the tests"
"defaultMode": "bypassPermissions"
```

**After:**

```text
claude -p "fix the tests" --allowedTools "Bash(npm test)" "Edit"
"defaultMode": "default"
```

**Hardened template:** `templates/policy/README.md`

</details>

<details>
<summary>AP04: MCP server installed from an unpinned package</summary>

**Why:** npx/uvx/bunx fetch the newest version at every start. A hijacked or malicious update becomes code running with your agent's access, with no review.

**Fix:** Pin an exact version \(for example pkg@1.4.2\), or install it once from a reviewed lockfile.

**Before:**

```text
"args": ["-y", "some-mcp-server"]
```

**After:**

```text
"args": ["-y", "some-mcp-server@1.4.2"]
```

</details>

<details>
<summary>AP05: Secret written directly in agent configuration</summary>

**Why:** Config files get committed, copied and read by the agent itself. A literal token is long-lived, shared and easy to leak through the agent's output.

**Fix:** Load the secret from the environment or a secret manager, use a short-lived scoped token, and rotate the exposed one.

**Before:**

```text
"env": {"GITHUB_TOKEN": "<the token itself>"}
```

**After:**

```text
"env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
```

</details>

<details>
<summary>AP06: Agent allowed to run any shell command</summary>

**Why:** An allow-rule like Bash\(\*\) or a bare Bash lets the agent run any command without asking. That includes curl to send your files out, rm -rf and git push --force.

**Fix:** Allow only the specific commands the task needs, such as Bash\(npm test\), and keep deny rules for network and destructive commands.

**Before:**

```text
"allow": ["Bash(*)"]
```

**After:**

```text
"allow": ["Bash(npm test)", "Bash(git status)"],
"deny": ["Bash(curl:*)", "Bash(rm -rf:*)"]
```

**Hardened template:** `templates/policy/claude-code/managed-settings.json`

</details>

<details>
<summary>AP08: Agent tool container can take over the host</summary>

**Why:** --privileged, a mounted Docker socket, host networking or a mounted root filesystem remove the container boundary. A compromised tool then controls the machine.

**Fix:** Drop these flags. Mount only the folders the tool needs, read-only where possible.

**Before:**

```text
"args": ["run", "--privileged", "-v", "/var/run/docker.sock:/var/run/docker.sock", "tool"]
```

**After:**

```text
"args": ["run", "--rm", "-v", "./data:/data:ro", "tool"]
```

</details>

<details>
<summary>AP07: Remote MCP server reached over plain HTTP</summary>

**Why:** Tool calls, results and credentials cross the network unencrypted and can be read or changed in transit, including the tool descriptions the model trusts.

**Fix:** Use https, and authenticate the server.

**Before:**

```text
"url": "http://mcp.example.com/mcp"
```

**After:**

```text
"url": "https://mcp.example.com/mcp"
```

</details>

<details>
<summary>AP09: Lethal combination: untrusted input, private data and a way out</summary>

**Why:** The same agent can read content an attacker controls, reach private data and send data or act outside. Prompt injection then becomes data theft; no system prompt reliably stops it.

**Fix:** Split the capabilities across agents, remove one leg, or require a person to approve every outbound or consequential action.

**Before:**

```text
one agent reads issues, reads private repositories and can post to the web
```

**After:**

```text
agent A reads issues, with no private data and no network
agent B holds private data, and a person approves each outbound action
```

</details>

<details>
<summary>AP10: Agent image not pinned to a digest</summary>

**Why:** A mutable tag such as :latest can change under you, so what you tested is not what runs.

**Fix:** Pin the base image by digest \(image@sha256:...\) and update it on purpose.

**Before:**

```text
FROM python:3.12
```

**After:**

```text
FROM python:3.12@sha256:<digest of the image you tested>
```

</details>

- note: \.open-agent-security-ignore: 2 entries; inline ignore marks: 1 finding; 2 findings suppressed; 0 files and 1 folder not scanned because of ignore entries
