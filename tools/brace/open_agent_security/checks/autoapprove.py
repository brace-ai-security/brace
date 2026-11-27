"""AP18: settings that start MCP servers or run tool calls without asking, and AP06 for the
any-command allow forms of Gemini CLI (and Qwen Code) and the Cursor CLI.

Only setting names documented by each product are read, structurally, from JSON:

- Claude Code: `enableAllProjectMcpServers: true` (every server in the project's .mcp.json
  starts without the approval prompt).
- MCP server entries in any config: a non-empty `alwaysAllow` (Cline, Roo Code) or `autoApprove`
  (Cline, Kiro, Amazon Q) list, or `alwaysAllow`/`autoApprove: true`; Gemini CLI's and Qwen
  Code's `trust: true` (every tool call of that server runs without confirmation).
- VS Code: `chat.tools.autoApprove: true` and its later name `chat.tools.global.autoApprove`.
- AP06: `run_shell_command` with no command restriction in Gemini CLI's `allowedTools` or
  `tools.allowed` (Qwen Code reads the same settings), and `Shell(*)` in the Cursor CLI's
  `permissions.allow`.
"""
from __future__ import annotations

import re
from typing import Iterator

from ..model import CheckContext, Document, Finding, ParseError
from ..parse.mcp_json import is_json

CLAUDE_SETTINGS = re.compile(r"(?:^|/)\.claude/settings(?:\.local)?\.json$|(?:^|/)managed-settings\.json$", re.I)
GEMINI_SETTINGS = re.compile(r"(?:^|/)\.(?:gemini|qwen)/settings\.json$", re.I)
VSCODE_SETTINGS = re.compile(r"(?:^|/)(?:\.vscode/settings|settings)\.json$", re.I)
CURSOR_CLI = re.compile(r"(?:^|/)\.cursor/cli(?:-config)?\.json$", re.I)
VSCODE_AUTO = ("chat.tools.autoApprove", "chat.tools.global.autoApprove")
APPROVE_KEYS = ("alwaysAllow", "autoApprove")
GEMINI_SHELL = {"run_shell_command", "ShellTool", "run_shell_command(*)", "ShellTool(*)"}
CURSOR_SHELL = {"Shell(*)", "Shell(**)", "Shell(*:*)", "Shell"}
SHOWN_TOOLS = 5  # tool names listed in a finding's detail


def json_of(doc: Document):
    """The file's parsed JSON, or None when it is not JSON or does not parse (the engine already
    notes a parse failure of agent config)."""
    if not is_json(doc.source):
        return None
    try:
        return doc.json()
    except ParseError:
        return None


def tool_list(value) -> str:
    names = [str(v) for v in value[:SHOWN_TOOLS]]
    more = f" and {len(value) - SHOWN_TOOLS} more" if len(value) > SHOWN_TOOLS else ""
    return "[" + ", ".join(names) + "]" + more


class AutoApproval:
    name = "auto-approval"
    emits = ("AP18", "AP06")
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        data = json_of(doc)
        if not isinstance(data, dict):
            return
        where, at = doc.source.display, doc.line_of
        if CLAUDE_SETTINGS.search(where) and data.get("enableAllProjectMcpServers") is True:
            yield Finding("AP18", where, at(("enableAllProjectMcpServers",)),
                          "enableAllProjectMcpServers: true (project MCP servers start without approval)")
        if VSCODE_SETTINGS.search(where):
            for key in VSCODE_AUTO:
                if data.get(key) is True:
                    yield Finding("AP18", where, at((key,)), f"{key}: true (every tool call runs without asking)")
        for s in doc.servers:
            for key in APPROVE_KEYS:
                value = s.raw.get(key)
                if value is True or (isinstance(value, list) and value):
                    shown = "true" if value is True else tool_list(value)
                    yield Finding("AP18", where, at(s.path + (key,)), f"{s.name}: {key} {shown}")
            if s.raw.get("trust") is True:
                yield Finding("AP18", where, at(s.path + ("trust",)),
                              f"{s.name}: trust: true (every tool call runs without asking)")
        if GEMINI_SETTINGS.search(where):
            tools = data.get("tools")
            for path, value in ((("allowedTools",), data.get("allowedTools")),
                                (("tools", "allowed"), tools.get("allowed") if isinstance(tools, dict) else None)):
                if isinstance(value, list):
                    for tool in value:
                        if isinstance(tool, str) and tool.replace(" ", "") in GEMINI_SHELL:
                            yield Finding("AP06", where, at(path), f'{".".join(path)} "{tool}"')
        if CURSOR_CLI.search(where):
            perms = data.get("permissions")
            allow = perms.get("allow") if isinstance(perms, dict) else None
            for tool in allow if isinstance(allow, list) else ():
                if isinstance(tool, str) and tool.replace(" ", "") in CURSOR_SHELL:
                    yield Finding("AP06", where, at(("permissions", "allow")), f'permissions.allow "{tool}"')
