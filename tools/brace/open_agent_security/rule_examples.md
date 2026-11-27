# open-agent-security rule examples

A short before and after for each built-in rule, shown by `open-agent-security explain RULE`,
in SARIF rule help, in the Markdown report and in the agent-prompt output. catalog.py reads this
file (it ships in the package); keep each example small, accurate and free of real secrets.
Each rule is a `## APnn` heading followed by a `Before:` and an `After:` fenced block.

## AP01

Before:

```text
claude --dangerously-skip-permissions -p "fix the tests"
"defaultMode": "bypassPermissions"
```

After:

```text
claude -p "fix the tests" --allowedTools "Bash(npm test)" "Edit"
"defaultMode": "default"
```

## AP02

Before:

```text
- run: claude -p "triage this issue" --dangerously-skip-permissions
```

After:

```text
permissions:
  contents: read
# ...
- run: claude -p "triage this issue" --allowedTools "Read" "Grep"
```

## AP03

Before:

```text
on: pull_request_target
```

After:

```text
on: pull_request
```

## AP04

Before:

```text
"args": ["-y", "some-mcp-server"]
```

After:

```text
"args": ["-y", "some-mcp-server@1.4.2"]
```

## AP05

Before:

```text
"env": {"GITHUB_TOKEN": "<the token itself>"}
```

After:

```text
"env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
```

## AP06

Before:

```text
"allow": ["Bash(*)"]
```

After:

```text
"allow": ["Bash(npm test)", "Bash(git status)"],
"deny": ["Bash(curl:*)", "Bash(rm -rf:*)"]
```

## AP07

Before:

```text
"url": "http://mcp.example.com/mcp"
```

After:

```text
"url": "https://mcp.example.com/mcp"
```

## AP08

Before:

```text
"args": ["run", "--privileged", "-v", "/var/run/docker.sock:/var/run/docker.sock", "tool"]
```

After:

```text
"args": ["run", "--rm", "-v", "./data:/data:ro", "tool"]
```

## AP09

Before:

```text
one agent reads issues, reads private repositories and can post to the web
```

After:

```text
agent A reads issues, with no private data and no network
agent B holds private data, and a person approves each outbound action
```

## AP10

Before:

```text
FROM python:3.12
```

After:

```text
FROM python:3.12@sha256:<digest of the image you tested>
```
