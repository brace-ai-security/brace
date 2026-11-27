"""Cursor hook: deny network and destructive shell commands, and MCP servers not on an allowlist.

Install at /usr/local/share/cursor-policy/guard.py (the path hooks.json names), owned by root and
not writable by users. Cursor runs it before each shell command (`guard.py shell`) and each MCP
tool call (`guard.py mcp`), passing the event as JSON on stdin; it answers with JSON on stdout:
{"permission": "allow" | "deny" | "ask", "userMessage": ..., "agentMessage": ...}.

Follows: https://cursor.com/docs/agent/hooks  (beforeShellExecution, beforeMCPExecution)
As of: 2026-11-27. Check the page before deploying; event fields change between releases.

Python standard library only. It fails closed: input it cannot read is denied.
BRACE B01, B05, E02; anti-patterns AP06, AP09.
"""
import json
import re
import sys

# Splits a command line into words, also inside quotes and subshells (`bash -c "curl ..."`).
WORDS = re.compile(r"[\s;|&()`$<>'\"=]+")
# Programs that reach the network or destroy data. A command using one is denied.
DENIED_PROGRAMS = frozenset({"curl", "wget", "nc", "ncat", "ssh", "scp", "sudo"})
# Programs a person must approve each time.
ASK_PROGRAMS = frozenset({"rm", "git", "npm", "pip"})
# MCP servers the agent may call, by the URL of a remote server or the command line of a local
# one, as the event reports them. Everything else is denied.
ALLOWED_MCP_URLS = frozenset({"https://api.githubcopilot.com/mcp/"})
ALLOWED_MCP_COMMANDS = frozenset()


def answer(permission, why=""):
    out = {"permission": permission}
    if why:
        out["userMessage"] = out["agentMessage"] = why
    json.dump(out, sys.stdout)
    return 0


def shell(event):
    programs = {w.rsplit("/", 1)[-1] for w in WORDS.split(str(event.get("command", ""))) if w}
    if programs & DENIED_PROGRAMS:
        return answer("deny", "Blocked by policy: network and privilege commands are not allowed.")
    if programs & ASK_PROGRAMS:
        return answer("ask", "Policy asks a person to approve this command.")
    return answer("allow")


def mcp(event):
    if str(event.get("url", "")) in ALLOWED_MCP_URLS or str(event.get("command", "")) in ALLOWED_MCP_COMMANDS:
        return answer("allow")
    return answer("deny", "Blocked by policy: this MCP server is not on the allowlist.")


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return answer("deny", "Blocked by policy: the hook input could not be read.")
    if not isinstance(event, dict):
        return answer("deny", "Blocked by policy: the hook input could not be read.")
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    if kind == "shell":
        return shell(event)
    if kind == "mcp":
        return mcp(event)
    return answer("deny", "Blocked by policy: unknown hook event.")


if __name__ == "__main__":
    sys.exit(main())
