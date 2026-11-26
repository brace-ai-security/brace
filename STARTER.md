# BRACE Starter: ten checks before an agent touches anything real

For small teams and first agents. These ten checks block the agent failures that
actually happen: prompt injection that turns into stolen data or destroyed systems,
agents with too much access, and incidents nobody can stop or explain. Expect about an
hour for a simple agent.

**Starter is a floor.** It doesn't mean the agent is approved for production. For a
high-stakes or high-autonomy agent, use the full [53-item sign-off checklist](CHECKLIST.md).
Each check below is a short version of a checklist item, and passing it gets you part
of the way to the full item.

**First, run the scan.** It finds several of these problems automatically:

```bash
uvx open-agent-security .          # or: pipx run open-agent-security .
```

| # | Check | Done when | Full item | Scan |
|---|---|---|---|---|
| 1 | **List every tool and cut the rest.** Write down each tool, MCP server, API and file permission the agent can use, with a one-line reason. Remove anything without one. | A tool that isn't on the list can't be called. You tried, and it failed. | [B01](CHECKLIST.md) | AP06 |
| 2 | **Block destructive actions without a person.** Deletes, payments, outbound email, pushes, deploys, permission changes: the harness stops and asks a person to approve that exact action. | Asking the agent to delete something test-only waits for approval. A prompt telling it to skip approval doesn't work. | [B05](CHECKLIST.md) | AP01, AP02 |
| 3 | **Break the lethal combination.** No single agent can read untrusted content, reach private data *and* send data out, unless every outbound action is approved. | For each agent, you can name the leg it lacks, or the approval that guards it. | [B05](CHECKLIST.md), [R02](CHECKLIST.md) | AP09 |
| 4 | **Give the agent its own narrow credentials.** Not your personal token and not the app's admin key. Scope them to the operations it needs. | An out-of-scope write with the agent's credentials fails. | [B02](CHECKLIST.md) | |
| 5 | **No secrets in prompts, config files or images.** Load them at runtime and prefer short-lived tokens. | The scan is clean for AP05, and `git log -p` shows no tokens. Any token that ever leaked has been rotated. | [B03](CHECKLIST.md) | AP05 |
| 6 | **Pin what you run.** Exact versions for MCP servers and dependencies, and digests for images. | No `npx pkg`, `@latest` or floating image tags in the agent's config. | [E02](CHECKLIST.md), [B10](CHECKLIST.md) | AP04, AP10 |
| 7 | **Limit where it can connect.** Allow only the outside destinations the task needs. | A request to a site that isn't on the list fails. | [B09](CHECKLIST.md) | AP07, AP08 |
| 8 | **Treat every model output as untrusted input.** No model text straight into a shell, SQL, HTML or a fetched URL. | Commands use argument lists and queries use parameters. Rendered output can't load remote images. | [R03](CHECKLIST.md) | |
| 9 | **Be able to stop it, and know you can.** One person can cut off the agent (and its sub-agents) without its cooperation, and without locking out the user. | You ran the stop once, timed it, and wrote down the time. | [R11](CHECKLIST.md), [B04](CHECKLIST.md) | |
| 10 | **Log every action, not just the answer.** Record tool calls, arguments, approvals, denials and results, with which agent and version did them. | You can rebuild yesterday's run from the log, including what failed. | [R13](CHECKLIST.md) | |

## Add the scan to CI

```yaml
# .github/workflows/agent-security.yml
name: Agent security
on: [pull_request]
permissions:
  contents: read
jobs:
  open-agent-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: brace-ai-security/open-agent-security@v3.1.0   # or pin a commit SHA
        with:
          fail-on: high
```

Set `upload-sarif: "true"` and grant `security-events: write` to see findings as
annotations on the pull request.

### Badge

Once the scan passes in CI, you can show it:

```markdown
[![Agent security: open-agent-security scan passing](https://img.shields.io/badge/open--agent--security-scan_passing-2ea44f)](https://braceframework.org/anti-patterns/)
```

The badge says only that the automated scan for known-dangerous agent setups passes.
It doesn't claim that the agent completed BRACE Starter or the full checklist, so don't
present it as a certification.

## Next

When the agent handles money, personal data or production systems, or acts without a
person watching, move to the [full checklist](CHECKLIST.md). Use the
[role map](ROLES.md) to see who owns each item.
