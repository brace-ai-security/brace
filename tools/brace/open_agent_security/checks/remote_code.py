"""AP21: a hook or skill that runs code fetched from the internet.

Read in two places:

- hook commands: every `command` string under the `hooks` key of a Claude Code settings file
  (.claude/settings*.json) or a plugin's hooks/hooks.json, read structurally;
- the files of skills, commands, subagents, hooks and plugins (anything under .claude/skills,
  .claude/commands, .claude/agents, .claude/hooks, .agents/skills or a .claude-plugin folder, and
  any SKILL.md), read as text: a skill's instructions are commands the agent will run.

What counts: a download piped into an interpreter (`curl ... | sh`, `wget -qO- ... | bash`,
`iwr ... | iex`), or run from a process substitution or command substitution
(`bash <(curl ...)`, `sh -c "$(curl ...)"`). Downloading a file and running it later is not
matched; the pipe or substitution is the high-signal shape.
"""
from __future__ import annotations

import re
from typing import Iterator

from ..limits import MAX_VALUE, WALK_DEPTH, WALK_VALUES
from ..model import CheckContext, Document, Finding
from .autoapprove import json_of

FETCH = r"(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)"
INTERPRETER = r"(?:sudo[ \t]{1,20}(?:-[\w-]{1,20}[ \t]{1,20}){0,3})?(?:ba|z|k|da|fi)?sh|python[0-9.]{0,4}|node|bun|deno|ruby|perl|iex|Invoke-Expression|pwsh|powershell"
REMOTE_EXEC = re.compile(
    rf"(?<![\w-]){FETCH}(?![\w-])[^\n|;&]{{0,500}}\|[ \t]{{0,20}}(?:{INTERPRETER})(?![\w.-])|"
    rf"(?<![\w-])(?:(?:ba|z|k)?sh|source|\.)[ \t]{{1,20}}<\([ \t]{{0,20}}{FETCH}(?![\w-])|"
    rf"(?<![\w-])(?:(?:ba|z|k)?sh|python[0-9.]{{0,4}})[ \t]{{1,20}}-c[ \t]{{1,20}}[\"']?\$\([ \t]{{0,20}}{FETCH}(?![\w-])",
    re.I)
HOOKS_FILE = re.compile(r"(?:^|/)(?:\.claude/settings(?:\.local)?\.json|hooks/hooks\.json)$", re.I)
SKILL_DIRS = ((".claude", "skills"), (".claude", "commands"), (".claude", "agents"), (".claude", "hooks"),
              (".agents", "skills"))


def skill_file(display: str) -> bool:
    """A file of a skill, command, subagent, hook or plugin, by its folders (see the module docstring)."""
    parts = display.lower().split("/")
    folders = parts[:-1]
    return parts[-1] == "skill.md" or ".claude-plugin" in folders or \
        any(folders[i:i + 2] == list(pair) for pair in SKILL_DIRS for i in range(len(folders) - 1))


def hook_commands(node, path: tuple, out: list, depth: int = 0) -> None:
    """(key path, command) for each `command` string in a hooks block, bounded in depth and count."""
    if depth > WALK_DEPTH or len(out) >= WALK_VALUES:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "command" and isinstance(v, str):
                out.append((path + (k,), v[:MAX_VALUE]))
            else:
                hook_commands(v, path + (k,), out, depth + 1)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hook_commands(v, path + (i,), out, depth + 1)


def shown(m: re.Match) -> str:
    return " ".join(m.group(0).split())


class RemoteCode:
    name = "remote-code"
    emits = ("AP21",)
    scope = "file"

    def run(self, doc: Document, ctx: CheckContext) -> Iterator[Finding]:
        src = doc.source
        where = src.display
        if HOOKS_FILE.search(where):
            data = json_of(doc)
            if isinstance(data, dict) and isinstance(data.get("hooks"), (dict, list)):
                commands: list = []
                hook_commands(data["hooks"], ("hooks",), commands)
                for path, command in commands:
                    m = REMOTE_EXEC.search(command)
                    if m:
                        yield Finding("AP21", where, doc.line_of(path[:2]), f"hook runs {shown(m)}")
            return
        if src.origin != "repo" or not skill_file(where):
            return
        line, last = 1, 0
        for m in REMOTE_EXEC.finditer(src.text):
            line += src.text.count("\n", last, m.start())
            last = m.start()
            yield Finding("AP21", where, line, f"runs {shown(m)}")
